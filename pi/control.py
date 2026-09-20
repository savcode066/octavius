"""Validated commands and one serial connection shared by all browser clients."""
import os
import re
import threading
import time
import serial
from serial.tools import list_ports

FIXED = {"STOP", "HOME", "WAVE", "CLAW_OPEN", "CLAW_CLOSE",
         "PITCH_UP", "PITCH_DOWN", "YAW_LEFT", "YAW_RIGHT"}
ALIASES = {"LEFT": "YAW_LEFT", "RIGHT": "YAW_RIGHT", "UP": "PITCH_UP",
           "DOWN": "PITCH_DOWN", "OPEN": "CLAW_OPEN", "CLOSE": "CLAW_CLOSE",
           "ELBOW_LEFT": "YAW_LEFT", "ELBOW_RIGHT": "YAW_RIGHT",
           "ELBOW_UP": "PITCH_UP", "ELBOW_DOWN": "PITCH_DOWN"}

def normalize_command(value):
    if not isinstance(value, str) or len(value) > 40:
        raise ValueError("Enter a short arm command.")
    parts = value.upper().split()
    if not parts:
        raise ValueError("Enter an arm command.")
    verb = ALIASES.get(parts[0], parts[0])
    if verb in FIXED and len(parts) == 1:
        return verb
    ranges = {"PITCH_ANGLE": (70, 110), "CLAW_ANGLE": (35, 80)}
    if verb in ranges and len(parts) == 2 and re.fullmatch(r"[0-9]{1,3}", parts[1]):
        low, high = ranges[verb]
        if low <= int(parts[1]) <= high:
            return f"{verb} {int(parts[1])}"
    raise ValueError("Unknown command or value outside calibrated limits.")

class Arm:
    def __init__(self):
        self.connection = None
        self.lock = threading.Lock()
        self.simulate = os.getenv("OCTAVIUS_SIMULATE", "0") == "1"
        self.port = os.getenv("OCTAVIUS_SERIAL_PORT", "auto")

    def status(self):
        return {"connected": bool(self.connection and self.connection.is_open),
                "simulated": self.simulate, "port": self.port}

    def send(self, command):
        command = normalize_command(command)
        # Never accumulate clicks into a queue of unexpected future movement.
        if not self.lock.acquire(blocking=False):
            raise RuntimeError("Nano is busy; try again in a moment.")
        try:
            if self.simulate:
                return f"SIMULATED {command}"
            if not self.connection or not self.connection.is_open:
                port = self.port
                if port == "auto":
                    candidates = [p.device for p in list_ports.comports()
                                  if p.vid is not None]
                    if len(candidates) != 1:
                        raise RuntimeError("Select OCTAVIUS_SERIAL_PORT in .env; could not identify one Nano.")
                    port = candidates[0]
                self.connection = serial.Serial(port, 115200, timeout=0.15, write_timeout=1)
                time.sleep(2)
                self.connection.reset_input_buffer()
            self.connection.write((command + "\n").encode("ascii"))
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                reply = self.connection.readline().decode("ascii", errors="replace").strip()
                if reply.startswith("OK "):
                    return reply
                if reply.startswith("ERR"):
                    raise RuntimeError(reply)
            raise RuntimeError("Nano did not acknowledge. Upload the main Octavius sketch, not a repeating test.")
        except (serial.SerialException, OSError, RuntimeError):
            if self.connection:
                self.connection.close()
                self.connection = None
            raise
        finally:
            self.lock.release()
