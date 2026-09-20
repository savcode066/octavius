"""Compile the Nano sketch for the desktop and drive it through real click patterns.

These cover the stepping and limit logic only. A simulated servo always lands on
the angle it is given, so nothing here proves the physical arm moves.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIRMWARE = ROOT / "tests" / "firmware"
SKETCH = ROOT / "arduino" / "octavius_arm"

# Keep in step with the sketch constants.
ANGLE_LOW, ANGLE_HIGH = 0, 180
YAW_STEP = PITCH_STEP = CLAW_STEP = 5
START = 90


@pytest.fixture(scope="session")
def simulator(tmp_path_factory):
    compiler = shutil.which("g++")
    if not compiler:
        pytest.skip("g++ is needed to compile the sketch for the desktop")
    binary = tmp_path_factory.mktemp("firmware") / "sim.exe"
    subprocess.run(
        [compiler, "-std=c++17", "-o", str(binary), str(FIRMWARE / "sim_main.cpp"),
         f"-I{FIRMWARE}", f"-I{SKETCH}"],
        check=True, capture_output=True,
    )
    return binary


def run(simulator, script):
    """Feed the sketch a list of commands and @<ms> delays; return each state."""
    result = subprocess.run([str(simulator)], input="\n".join(script) + "\n",
                            capture_output=True, text=True, check=True)
    return [json.loads(line) for line in result.stdout.splitlines()]


def final(states):
    """The last reported position. The very last line is the serial transcript."""
    return states[-2]


def test_one_press_moves_one_step(simulator):
    states = run(simulator, ["PITCH_UP", "PITCH_UP", "PITCH_DOWN"])
    assert [s["pitch"] for s in states[1:4]] == [
        START - PITCH_STEP, START - PITCH_STEP * 2, START - PITCH_STEP]


def test_presses_reach_both_ends(simulator):
    up = run(simulator, ["PITCH_UP"] * 40)
    down = run(simulator, ["PITCH_DOWN"] * 40)
    assert final(up)["pitch"] == ANGLE_LOW
    assert final(down)["pitch"] == ANGLE_HIGH


def test_yaw_and_claw_reach_both_ends(simulator):
    states = run(simulator, ["YAW_RIGHT"] * 40 + ["CLAW_INC"] * 40)
    assert final(states)["yaw"] == ANGLE_HIGH
    assert final(states)["claw"] == ANGLE_HIGH
    states = run(simulator, ["YAW_LEFT"] * 40 + ["CLAW_DEC"] * 40)
    assert final(states)["yaw"] == ANGLE_LOW
    assert final(states)["claw"] == ANGLE_LOW


def test_a_limit_never_costs_a_press_coming_back(simulator):
    """Pressing past the end must not bank presses that the way back has to undo."""
    states = run(simulator, ["PITCH_UP"] * 100 + ["PITCH_DOWN"])
    assert final(states)["pitch"] == ANGLE_LOW + PITCH_STEP


def test_claw_crosses_its_range_in_many_presses(simulator):
    """The claw reads as on/off if a handful of presses cross the whole range."""
    assert (ANGLE_HIGH - ANGLE_LOW) // CLAW_STEP >= 20


def test_home_returns_every_joint_to_its_start(simulator):
    states = run(simulator, ["YAW_LEFT", "PITCH_UP", "CLAW_DEC", "HOME"])
    assert final(states) == {"step": "HOME", "yaw": START, "pitch": START, "claw": START}


def test_angle_commands_span_the_whole_range(simulator):
    states = run(simulator, ["CLAW_ANGLE 0", "PITCH_ANGLE 180"])
    assert states[1]["claw"] == 0
    assert states[2]["pitch"] == 180
    assert "ERR" not in states[-1]["output"]


def test_angle_above_the_range_is_refused(simulator):
    states = run(simulator, ["PITCH_ANGLE 181"])
    assert "ERR angle range" in states[-1]["output"]
    assert states[1]["pitch"] == START


def test_wave_is_gone(simulator):
    states = run(simulator, ["WAVE"])
    assert "ERR unknown command" in states[-1]["output"]


def test_every_reply_carries_the_angles(simulator):
    """The Pi logs the reply verbatim, so this is what shows up in journalctl."""
    states = run(simulator, ["PITCH_UP", "YAW_LEFT"])
    assert "OK PITCH_UP yaw=90 pitch=85 claw=90" in states[-1]["output"]
    assert "OK YAW_LEFT yaw=85 pitch=85 claw=90" in states[-1]["output"]


def test_status_reports_without_moving(simulator):
    states = run(simulator, ["PITCH_UP", "STATUS"])
    assert "OK STATUS yaw=90 pitch=85 claw=90" in states[-1]["output"]
    assert final(states) == {"step": "STATUS", "yaw": 90, "pitch": 85, "claw": 90}
