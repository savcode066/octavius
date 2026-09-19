#!/usr/bin/env python3
"""Octavius local control server.

Serves the iPhone controller and relays safe, named commands to an Arduino Nano.
"""

import os
import time
from pathlib import Path

import serial
from flask import Flask, jsonify, request, send_from_directory

SERIAL_PORT = os.environ.get("OCTAVIUS_SERIAL_PORT", "/dev/ttyACM0")
SERIAL_BAUD = int(os.environ.get("OCTAVIUS_SERIAL_BAUD", "115200"))
UPLOAD_DIRECTORY = Path(__file__).parent / "uploads"
ALLOWED_COMMANDS = {
    "WAVE",
    "HOME",
    "CLAW_OPEN",
    "CLAW_CLOSE",
    "ELBOW_LEFT",
    "ELBOW_RIGHT",
    "ELBOW_UP",
    "ELBOW_DOWN",
}

app = Flask(__name__, static_folder="web")
serial_connection = None


def nano_connection():
    """Open the Nano lazily so the server can start before USB is attached."""
    global serial_connection
    if serial_connection and serial_connection.is_open:
        return serial_connection

    serial_connection = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=1)
    time.sleep(2)  # Nano commonly resets when serial opens.
    return serial_connection


def send_command(command: str) -> str:
    connection = nano_connection()
    connection.reset_input_buffer()
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
    ).strip().upper()

    if requested_command not in ALLOWED_COMMANDS:
        return jsonify(error="Unknown command", allowed=sorted(ALLOWED_COMMANDS)), 400

    try:
        nano_response = send_command(requested_command)
        return jsonify(command=requested_command, nano_response=nano_response)
    except (serial.SerialException, OSError) as error:
        return jsonify(error=f"Could not reach Nano on {SERIAL_PORT}: {error}"), 503


@app.post("/photo")
def photo():
    """Accept an iPhone Shortcut photo for future vision processing.

    Saving the latest image makes it easy to add OpenCV detection later without
    changing the iPhone Shortcut.
    """
    uploaded_photo = request.files.get("photo")
    if uploaded_photo is None or uploaded_photo.filename == "":
        return jsonify(error="Send an image using the form field named 'photo'."), 400

    UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)
    destination = UPLOAD_DIRECTORY / "latest.jpg"
    uploaded_photo.save(destination)
    return jsonify(status="photo saved", path=str(destination.name))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
