#!/usr/bin/env python3
"""Octavius local control server.

Serves the controller page and relays validated commands to the Arduino Nano.
The Nano remains responsible for motion limits and gentle servo movement.
"""

import os
import time
from pathlib import Path
from threading import Lock

import serial
from flask import Flask, jsonify, request, send_from_directory

SERIAL_PORT = os.environ.get("OCTAVIUS_SERIAL_PORT", "/dev/ttyACM0")
SERIAL_BAUD = int(os.environ.get("OCTAVIUS_SERIAL_BAUD", "115200"))
UPLOAD_DIRECTORY = Path(__file__).parent / "uploads"

FIXED_COMMANDS = {
    "STOP",
    "HOME",
    "WAVE",
    "CLAW_OPEN",
    "CLAW_CLOSE",
    "PITCH_UP",
    "PITCH_DOWN",
}

COMMAND_ALIASES = {
    "ELBOW_LEFT": "YAW_LEFT",
    "ELBOW_RIGHT": "YAW_RIGHT",
    "ELBOW_UP": "PITCH_UP",
    "ELBOW_DOWN": "PITCH_DOWN",
    "PITCH": "PITCH_ANGLE",
    "CLAW": "CLAW_ANGLE",
}

app = Flask(__name__, static_folder="web")
serial_connection = None
serial_lock = Lock()


def normalize_command(raw_command: str) -> str:
    """Normalize a typed command and enforce safe ranges before serializing it."""
    compact = " ".join(raw_command.strip().upper().split())
    if not compact:
        raise ValueError("Enter a command.")

    parts = compact.split(" ")
    verb = COMMAND_ALIASES.get(parts[0], parts[0])

    if verb in FIXED_COMMANDS:
        if len(parts) != 1:
            raise ValueError(f"{verb} does not take a value.")
        return verb

    if verb in {"YAW_LEFT", "YAW_RIGHT"}:
        if len(parts) > 2:
            raise ValueError(f"{verb} accepts an optional duration in milliseconds.")
        duration = 180 if len(parts) == 1 else int(parts[1])
        duration = max(50, min(750, duration))
        return f"{verb} {duration}"

    if verb in {"PITCH_ANGLE", "CLAW_ANGLE"}:
        if len(parts) != 2:
            raise ValueError(f"{verb} needs one angle value.")
        angle = int(parts[1])
        if verb == "PITCH_ANGLE":
            angle = max(70, min(110, angle))
        else:
            angle = max(35, min(80, angle))
        return f"{verb} {angle}"

    raise ValueError("Unknown command. Try HOME, YAW_LEFT, PITCH_UP, or CLAW_OPEN.")


def nano_connection():
    """Open the Nano lazily so the server can start before USB is attached."""
    global serial_connection
    if serial_connection and serial_connection.is_open:
        return serial_connection

    serial_connection = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=2)
    time.sleep(2)  # The Nano commonly resets when serial opens.
    serial_connection.reset_input_buffer()
    return serial_connection


def send_command(command: str) -> str:
    # Prevent two browser taps from interleaving bytes on the serial link.
    with serial_lock:
        connection = nano_connection()
        connection.write(f"{command}\n".encode("utf-8"))
        connection.flush()
        return connection.readline().decode("utf-8", errors="replace").strip()


@app.get("/")
def controller():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/health")
def health():
    return jsonify(status="ok", serial_port=SERIAL_PORT)


@app.route("/command", methods=["GET", "POST"])
def command():
    payload = request.get_json(silent=True) or {}
    requested_command = (
        payload.get("command")
        or request.form.get("command")
        or request.args.get("cmd")
        or ""
    )

    try:
        safe_command = normalize_command(str(requested_command))
    except (TypeError, ValueError) as error:
        return jsonify(error=str(error)), 400

    try:
        nano_response = send_command(safe_command)
        return jsonify(command=safe_command, nano_response=nano_response)
    except (serial.SerialException, OSError) as error:
        return jsonify(error=f"Could not reach Nano on {SERIAL_PORT}: {error}"), 503


@app.post("/photo")
def photo():
    """Accept an iPhone Shortcut photo for future vision processing."""
    uploaded_photo = request.files.get("photo")
    if uploaded_photo is None or uploaded_photo.filename == "":
        return jsonify(error="Send an image using the form field named 'photo'."), 400

    UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)
    destination = UPLOAD_DIRECTORY / "latest.jpg"
    uploaded_photo.save(destination)
    return jsonify(status="photo saved", path=str(destination.name))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
