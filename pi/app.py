"""Octavius phone interface. Run via the supplied service or locally for testing."""
import os
import secrets
import time
import logging
from collections import defaultdict
from pathlib import Path
from threading import Lock
from dotenv import load_dotenv
from flask import Flask, jsonify, request, session, send_from_directory

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

_level_name = os.getenv("OCTAVIUS_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, _level_name, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("octavius.app")

from control import Arm, normalize_command
from omni import Omni

app = Flask(__name__, static_folder="web", static_url_path="/static")
app.config.update(SECRET_KEY=os.getenv("OCTAVIUS_SESSION_SECRET") or secrets.token_hex(32),
                  MAX_CONTENT_LENGTH=2 * 1024 * 1024,
                  SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Strict",
                  SESSION_COOKIE_SECURE=os.getenv("OCTAVIUS_DEV_HTTP", "0") != "1")
arm, omni = Arm(), Omni()
pair_code = os.getenv("OCTAVIUS_PAIR_CODE", "")
attempts = defaultdict(list)
pair_lock = Lock()

@app.before_request
def guard():
    if request.method == "POST":
        if request.headers.get("X-Octavius") != "1":
            logger.warning("rejected post path=%s remote=%s reason=missing_header",
                           request.path, request.remote_addr)
            return jsonify(error="Use the Octavius control page."), 403
        origin = request.headers.get("Origin")
        if origin and origin != request.host_url.rstrip("/"):
            logger.warning("rejected post path=%s remote=%s reason=origin_mismatch",
                           request.path, request.remote_addr)
            return jsonify(error="Untrusted origin."), 403
        if request.path != "/pair" and not session.get("paired"):
            logger.warning("rejected post path=%s remote=%s reason=not_paired",
                           request.path, request.remote_addr)
            return jsonify(error="Enter the pairing code first."), 401

@app.after_request
def headers(response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob: data:; media-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'"
    return response

@app.errorhandler(413)
def too_big(error):
    return jsonify(error="Recording is too large. Limit recordings to 10 seconds."), 413

@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

@app.get("/health")
def health():
    return jsonify(status="ok", paired=bool(session.get("paired")),
                   pairing_configured=bool(pair_code), arm=arm.status(), omni=omni.status())

@app.post("/pair")
def pair():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="Expected JSON."), 400
    with pair_lock:
        now = time.monotonic()
        peer = request.remote_addr
        # Remove expired peers rather than retaining an unbounded map.
        for key in list(attempts):
            attempts[key] = [t for t in attempts[key] if now - t < 60]
            if not attempts[key]:
                del attempts[key]
        if len(attempts[peer]) >= 5:
            logger.warning("pair rejected remote=%s reason=rate_limited", peer)
            return jsonify(error="Wait one minute before trying again."), 429
        attempts[peer].append(now)
        code = payload.get("code")
        if not pair_code or not isinstance(code, str) or not secrets.compare_digest(code, pair_code):
            logger.warning("pair rejected remote=%s reason=invalid_code", peer)
            return jsonify(error="Incorrect pairing code. Find it in the Pi installer output."), 403
        session["paired"] = True
    logger.info("pair accepted remote=%s", peer)
    return jsonify(ok=True)

@app.post("/command")
def command():
    payload = request.get_json(silent=True)
    try:
        if not isinstance(payload, dict):
            raise ValueError("Expected a JSON command.")
        cmd = normalize_command(payload.get("command"))
        logger.info("command start command=%s remote=%s", cmd, request.remote_addr)
        reply = arm.send(cmd)
        logger.info("command complete command=%s reply=%s", cmd, reply)
        return jsonify(command=cmd, nano_response=reply)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except Exception as exc:
        logger.warning("command failed remote=%s error_type=%s detail=%s",
                       request.remote_addr, type(exc).__name__, str(exc))
        return jsonify(error="Nano unavailable or busy. Check USB, main sketch, and serial port. " +
                       (str(exc) if isinstance(exc, RuntimeError) else "")), 503

def run_task(name, width_cm=None):
    try:
        result = arm.run_task(name, width_cm)
        return jsonify(result)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except Exception as exc:
        logger.warning("task failed task=%s remote=%s error_type=%s detail=%s",
                       name, request.remote_addr, type(exc).__name__, str(exc))
        return jsonify(error="Nano unavailable or busy. Check USB, main sketch, and serial port. " +
                       (str(exc) if isinstance(exc, RuntimeError) else "")), 503

@app.post("/pickup")
def pickup():
    payload = request.get_json(silent=True)
    width = payload.get("width_cm") if isinstance(payload, dict) else None
    return run_task("pick_up", width)

@app.post("/putdown")
def putdown():
    return run_task("put_down")

@app.post("/interpret")
def interpret():
    text = request.form.get("text", "").strip()
    if len(text) > 1000:
        return jsonify(error="Keep requests under 1,000 characters."), 400
    photo = request.files.get("photo")
    audio = request.files.get("audio")
    try:
        photo_data = photo.read() if photo else None
        audio_data = audio.read() if audio else None
        logger.info("interpret start remote=%s text_chars=%d photo_bytes=%d audio_bytes=%d",
                    request.remote_addr, len(text),
                    len(photo_data or b""), len(audio_data or b""))
        result = omni.interpret(text, photo_data, audio_data)
        # Interpretation never moves hardware. The user confirms via /command.
        logger.info("interpret complete suggested_command=%s heard=%r",
                    result.get("command"), str(result.get("heard", ""))[:200])
        return jsonify(result)
    except ValueError as exc:
        logger.warning("interpret rejected error=%s", str(exc))
        return jsonify(error=str(exc)), 400
    except RuntimeError as exc:
        logger.warning("interpret failed error=%s", str(exc))
        return jsonify(error=str(exc)), 502
    except Exception:
        logger.exception("interpret failed unexpectedly")
        return jsonify(error="Could not process request. No movement sent."), 500

if __name__ == "__main__":
    cert, key = ROOT / "certs/server.crt", ROOT / "certs/server.key"
    tls = (str(cert), str(key)) if cert.exists() and key.exists() else None
    app.run(host="0.0.0.0", port=5000, ssl_context=tls, threaded=True, debug=False)
