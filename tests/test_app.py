import io
import json
import sys
import wave
from pathlib import Path
from unittest.mock import patch
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"pi"))
import app as server
from control import normalize_command
from omni import Omni
from setup_local import setup
from summarize_usage import summarize

@pytest.fixture
def client(monkeypatch):
    server.app.config.update(TESTING=True, SESSION_COOKIE_SECURE=False)
    monkeypatch.setattr(server,"pair_code","123456")
    monkeypatch.setattr(server.arm,"simulate",True)
    server.attempts.clear()
    with server.app.test_client() as c:
        yield c

HEADERS={"X-Octavius":"1"}
def test_page_assets(client):
    assert client.get("/").status_code == 200
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/style.css").status_code == 200

def pair(client):
    return client.post("/pair",json={"code":"123456"},headers=HEADERS)

def test_auth_and_command(client):
    assert client.post("/command",json={"command":"HOME"},headers=HEADERS).status_code==401
    assert pair(client).status_code==200
    assert client.post("/command",json={"command":"HOME"}).status_code==403
    assert client.post("/command",json={"command":"HOME"},headers={**HEADERS,"Origin":"https://evil.test"}).status_code==403
    response=client.post("/command",json={"command":"left"},headers=HEADERS)
    assert response.json["nano_response"]=="SIMULATED YAW_LEFT"
    assert client.get("/command?cmd=HOME").status_code==405

@pytest.mark.parametrize("cmd",["",None,"HOME\nCLAW_DEC","PITCH_ANGLE 181","CLAW_ANGLE nope","YAW_LEFT 999","PITCH_ANGLE -1"])
def test_bad_commands(cmd):
    with pytest.raises(ValueError): normalize_command(cmd)

def test_pair_limit(client):
    for _ in range(5): client.post("/pair",json={"code":"bad"},headers=HEADERS)
    assert pair(client).status_code==429

def test_disabled_means_no_network(client,monkeypatch):
    pair(client)
    monkeypatch.setattr(server.omni,"enabled",False)
    with patch("omni.httpx.Client",side_effect=AssertionError("network forbidden")):
        assert client.post("/interpret",data={"text":"home","live":"false"},headers=HEADERS).json["mode"]=="practice"
        assert client.post("/interpret",data={"text":"home","live":"true"},headers=HEADERS).status_code==400

def wav_bytes():
    buf=io.BytesIO()
    with wave.open(buf,"wb") as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(b"\0"*3200)
    return buf.getvalue()

def test_multimodal_and_usage(tmp_path):
    model=Omni();model.enabled=True;model.key="test-secret-only";model.ledger=tmp_path/"calls.jsonl"
    payload={"choices":[{"message":{"content":json.dumps({"reply":"Ready","command":"HOME","heard":"home"})}}],
             "usage":{"prompt_tokens":10,"completion_tokens":5}}
    with patch("omni.httpx.Client") as client:
        response=client.return_value.__enter__.return_value.post.return_value
        response.status_code=200;response.json.return_value=payload
        result=model.interpret("home",b"\xff\xd8frame",wav_bytes(),True)
        request=client.return_value.__enter__.return_value.post.call_args.kwargs["json"]
        assert [p["type"] for p in request["messages"][1]["content"]]==["text","image_url","input_audio"]
        assert result["command"]=="HOME"
    ledger=model.ledger.read_text()
    assert "test-secret-only" not in ledger
    assert json.loads(ledger)["total_tokens"]==15
    summarize(model.ledger,tmp_path/"summary")
    assert json.loads((tmp_path/"summary/usage_summary.json").read_text())["calls"]==1

def test_no_automatic_motion(client,monkeypatch):
    pair(client)
    monkeypatch.setattr(server.omni,"interpret",lambda *a,**k:dict(reply="Home?",command="HOME"))
    monkeypatch.setattr(server.arm,"send",lambda *a:pytest.fail("model triggered movement"))
    assert client.post("/interpret",data={"text":"home"},headers=HEADERS).json["command"]=="HOME"

def test_reject_model_action(tmp_path):
    model=Omni();model.enabled=True;model.key="test";model.ledger=tmp_path/"ledger"
    with patch("omni.httpx.Client") as client:
        response=client.return_value.__enter__.return_value.post.return_value
        response.status_code=200
        response.json.return_value={"choices":[{"message":{"content":'{"command":"EXEC rm"}'}}]}
        with pytest.raises(ValueError):model.interpret("home",live=True)
    assert json.loads(model.ledger.read_text())["total_tokens"] is None

def test_certificate_setup_is_repeatable(tmp_path):
    from cryptography import x509
    setup(tmp_path)
    ca=(tmp_path/"certs/ca.crt").read_bytes()
    env=(tmp_path/".env").read_text()
    setup(tmp_path)
    assert (tmp_path/"certs/ca.crt").read_bytes()==ca
    assert "OCTAVIUS_OMNI_ENABLED=0" in env
    leaf=x509.load_pem_x509_certificate((tmp_path/"certs/server.crt").read_bytes())
    root=x509.load_pem_x509_certificate(ca)
    leaf.verify_directly_issued_by(root)

def test_error_is_not_success(client,monkeypatch):
    pair(client)
    def fail(cmd): raise RuntimeError("Nano did not acknowledge.")
    monkeypatch.setattr(server.arm,"send",fail)
    assert client.post("/command",json={"command":"STOP"},headers=HEADERS).status_code==503

def test_provider_failure_logged_without_retry(tmp_path):
    import httpx
    model=Omni();model.enabled=True;model.key="private-test";model.ledger=tmp_path/"calls"
    with patch("omni.httpx.Client") as client:
        post=client.return_value.__enter__.return_value.post
        post.side_effect=httpx.ConnectError("offline")
        with pytest.raises(RuntimeError): model.interpret("home",live=True)
        assert post.call_count==1
    record=json.loads(model.ledger.read_text())
    assert record["ok"] is False
    assert record["total_tokens"] is None
    assert "private-test" not in model.ledger.read_text()

def test_bad_media_does_not_spend(tmp_path):
    model=Omni();model.enabled=True;model.key="test";model.ledger=tmp_path/"calls"
    with patch("omni.httpx.Client",side_effect=AssertionError("network forbidden")):
        with pytest.raises(ValueError):model.interpret("home",audio=b"not wav",live=True)
    assert not model.ledger.exists()


class FakeSerial:
    is_open = True
    def __init__(self, replies): self.replies = list(replies); self.written = []
    def write(self, data): self.written.append(data)
    def readline(self): return (self.replies.pop(0) + "\n").encode() if self.replies else b""
    def close(self): self.is_open = False

def _arm(replies):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pi"))
    from control import Arm
    arm = Arm(); arm.connection = FakeSerial(replies)
    return arm

def test_nano_err_keeps_serial_open():
    arm = _arm(["ERR busy"])
    with pytest.raises(RuntimeError, match="busy"):
        arm.send("YAW_LEFT")
    assert arm.connection is not None and arm.connection.is_open

def test_ok_must_match_command():
    arm = _arm(["OK CLAW_DEC", "OK YAW_LEFT"])
    assert arm.send("YAW_LEFT") == "OK YAW_LEFT"


def test_reply_may_carry_the_angle_report():
    arm = _arm(["OK YAW_LEFT yaw=85 pitch=90 claw=90"])
    assert arm.send("YAW_LEFT") == "OK YAW_LEFT yaw=85 pitch=90 claw=90"


def test_reply_for_another_command_is_still_ignored():
    arm = _arm(["OK YAW_RIGHT yaw=95 pitch=90 claw=90", "OK YAW_LEFT yaw=85 pitch=90 claw=90"])
    assert arm.send("YAW_LEFT") == "OK YAW_LEFT yaw=85 pitch=90 claw=90"


def test_width_to_claw_angle(monkeypatch):
    from grasp import width_to_claw_angle
    for name in ("OCTAVIUS_CLAW_NARROW_CM", "OCTAVIUS_CLAW_NARROW_ANGLE", "OCTAVIUS_CLAW_WIDE_CM",
                 "OCTAVIUS_CLAW_WIDE_ANGLE", "OCTAVIUS_GRIP_MARGIN_DEG"):
        monkeypatch.delenv(name, raising=False)
    assert width_to_claw_angle(7) == 80
    assert width_to_claw_angle(9) == 85
    assert width_to_claw_angle(8) == 83
    monkeypatch.setenv("OCTAVIUS_GRIP_MARGIN_DEG", "2")
    assert width_to_claw_angle(9) == 83

@pytest.mark.parametrize("width", [None, "8", True, float("nan"), 6.9, 9.1, 0, -3])
def test_bad_widths(width):
    from grasp import width_to_claw_angle
    with pytest.raises(ValueError): width_to_claw_angle(width)

def test_pickup_and_putdown_routes(client):
    assert client.post("/pickup", json={"width_cm": 8}, headers=HEADERS).status_code == 401
    pair(client)
    assert client.post("/pickup", json={"width_cm": 8}).status_code == 403
    picked = client.post("/pickup", json={"width_cm": 8}, headers=HEADERS).json
    assert picked["steps"] == ["CLAW_ANGLE 83", "PITCH_ANGLE 60"] and not picked["aborted"]
    assert client.post("/pickup", json={"width_cm": 20}, headers=HEADERS).status_code == 400
    assert client.post("/pickup", json={}, headers=HEADERS).status_code == 400
    put = client.post("/putdown", headers=HEADERS).json
    assert put["steps"] == ["PITCH_ANGLE 110", "CLAW_ANGLE 110"]

def test_task_ramps_each_joint_in_order():
    arm = _arm(["OK STATUS yaw=90 pitch=90 claw=90"] + ["OK CLAW_ANGLE"] * 4 + ["OK PITCH_ANGLE"] * 15)
    arm.simulate = False
    with patch.object(arm, "_pause", return_value=False):
        result = arm.run_task("pick_up", 8)
    sent = [w.decode().strip() for w in arm.connection.written]
    assert sent[0] == "STATUS"
    assert [c.split()[0] for c in sent[1:]] == ["CLAW_ANGLE"] * 4 + ["PITCH_ANGLE"] * 15
    assert sent[4] == "CLAW_ANGLE 83" and sent[-1] == "PITCH_ANGLE 60"
    assert result["steps"] == ["CLAW_ANGLE 83", "PITCH_ANGLE 60"]

def test_stop_aborts_a_running_task():
    arm = _arm(["OK STATUS yaw=90 pitch=90 claw=90", "OK CLAW_ANGLE", "OK STOP"])
    calls = []
    def pause(seconds):
        calls.append(seconds)
        arm.send("STOP")          # arrives while the task holds the lock
        return arm.abort.is_set()
    with patch.object(arm, "_pause", side_effect=pause):
        result = arm.run_task("pick_up", 8)
    assert result["aborted"] is True
    assert [w.decode().strip() for w in arm.connection.written][-1] == "STOP"
    assert not arm.task_active and not arm.lock.locked()
