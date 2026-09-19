#!/usr/bin/env python3
"""Small terminal controller for Octavius.

Run this on the Pi while app.py is running, then type the same commands used
by the web page.
"""

import json
import os
import urllib.error
import urllib.request


SERVER_URL = os.environ.get("OCTAVIUS_SERVER_URL", "http://127.0.0.1:5000")


def send(command: str) -> None:
    request = urllib.request.Request(
        f"{SERVER_URL}/command",
        data=json.dumps({"command": command}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            print(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        print(error.read().decode("utf-8"))
    except urllib.error.URLError as error:
        print(f"Could not reach Octavius server: {error.reason}")


print("Octavius terminal control")
print("Type HELP for examples or QUIT to exit.")

while True:
    try:
        command = input("octavius> ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        break

    if not command:
        continue
    if command.upper() in {"QUIT", "EXIT"}:
        break
    if command.upper() == "HELP":
        print("YAW_LEFT, YAW_RIGHT, PITCH_UP, PITCH_DOWN, CLAW_OPEN, CLAW_CLOSE")
        print("YAW_LEFT 250, PITCH_ANGLE 95, CLAW_ANGLE 55, WAVE, HOME, STOP")
        continue

    send(command)
