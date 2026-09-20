"""Validated commands and one serial connection shared by all browser clients."""
import os
import re
import threading
import time
import logging
import serial
from serial.tools import list_ports
from grasp import setting, width_to_claw_angle

logger = logging.getLogger("octavius.control")

FIXED = {"STOP", "STATUS", "HOME", "CLAW_INC", "CLAW_DEC",
         "PITCH_UP", "PITCH_DOWN", "YAW_LEFT", "YAW_RIGHT"}
ALIASES = {"LEFT": "YAW_LEFT", "RIGHT": "YAW_RIGHT", "UP": "PITCH_UP",
           "DOWN": "PITCH_DOWN",
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
    # Servo.write() on the Nano accepts nothing outside this range.
    ranges = {"PITCH_ANGLE": (0, 180), "CLAW_ANGLE": (0, 180)}
    if verb in ranges and len(parts) == 2 and re.fullmatch(r"[0-9]{1,3}", parts[1]):
        low, high = ranges[verb]
        if low <= int(parts[1]) <= high:
            return f"{verb} {int(parts[1])}"
    raise ValueError("Unknown command or value outside calibrated limits.")

class NanoRejected(RuntimeError):
    """The Nano answered ERR; the serial link is fine, so keep it open."""

TASKS = {"pick_up", "put_down"}
# The Nano jumps straight to a written angle and reports no motion, so tasks
# walk the servo there in small timed steps. The pitch limits mirror stepPitch()
# in the sketch, which clamps to 0..120.
RAMP_STEP_DEG = 2
RAMP_STEP_SECONDS = 0.025
SETTLE_SECONDS = 0.3
PITCH_LIMITS = (0, 120)
STATUS_REPLY = re.compile(r"OK STATUS yaw=(\d+) pitch=(\d+) claw=(\d+)")

class Arm:
    def __init__(self):
        self.connection = None
        self.lock = threading.Lock()
        self.simulate = os.getenv("OCTAVIUS_SIMULATE", "0") == "1"
        self.port = os.getenv("OCTAVIUS_SERIAL_PORT", "auto")
        self.abort = threading.Event()
        self.task_active = False
        self.sim_angles = {"yaw": 90, "pitch": 90, "claw": 90}

    def status(self):
        return {"connected": bool(self.connection and self.connection.is_open),
                "simulated": self.simulate, "port": self.port}

    def send(self, command):
        command = normalize_command(command)
        logger.info("command requested command=%s simulated=%s", command, self.simulate)
        # STOP must get through a running task, which holds the lock.
        if command == "STOP" and self.task_active:
            self.abort.set()
            return "OK STOP (task aborting)"
        # Never accumulate clicks into a queue of unexpected future movement.
        if not self.lock.acquire(blocking=False):
            logger.warning("command rejected command=%s reason=busy", command)
            raise RuntimeError("Nano is busy; try again in a moment.")
        try:
            return self._exchange(command)
        finally:
            self.lock.release()

    def _exchange(self, command):
        """One command and its reply. The caller must hold self.lock."""
        try:
            if self.simulate:
                verb, *args = command.split()
                if verb in ("PITCH_ANGLE", "CLAW_ANGLE"):
                    self.sim_angles[verb.split("_")[0].lower()] = int(args[0])
                return f"SIMULATED {command}"
            if not self.connection or not self.connection.is_open:
                port = self.port
                if port == "auto":
                    candidates = [p.device for p in list_ports.comports()
                                  if p.vid is not None]
                    logger.info("serial auto-detect candidates=%s", candidates)
                    if len(candidates) != 1:
                        logger.error("serial auto-detect failed candidates=%s", candidates)
                        raise RuntimeError("Select OCTAVIUS_SERIAL_PORT in .env; could not identify one Nano.")
                    port = candidates[0]
                logger.info("serial opening port=%s baud=115200", port)
                self.connection = serial.Serial(port, 115200, timeout=0.15, write_timeout=1)
                time.sleep(2)
                self.connection.reset_input_buffer()
                logger.info("serial opened port=%s", port)
            logger.info("serial write command=%s", command)
            self.connection.write((command + "\n").encode("ascii"))
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                reply = self.connection.readline().decode("ascii", errors="replace").strip()
                # The Nano tails each OK with " yaw=.. pitch=.. claw=..".
                expected = "OK " + command.split()[0]
                if reply == expected or reply.startswith(expected + " "):
                    logger.info("serial reply command=%s reply=%s", command, reply)
                    return reply
                if reply.startswith("ERR"):
                    logger.warning("serial rejected command=%s reply=%s", command, reply)
                    raise NanoRejected(reply)
            logger.error("serial timeout command=%s port=%s", command, self.port)
            raise RuntimeError("Nano did not acknowledge. Upload the main Octavius sketch, not a repeating test.")
        except (serial.SerialException, OSError, RuntimeError) as exc:
            logger.warning("serial command failed command=%s error_type=%s detail=%s",
                           command, type(exc).__name__, str(exc))
            if self.connection and not isinstance(exc, NanoRejected):
                self.connection.close()
                self.connection = None
                logger.info("serial connection cleared")
            raise

    def _read_angles(self):
        if self.simulate:
            return dict(self.sim_angles)
        reply = self._exchange("STATUS")
        match = STATUS_REPLY.fullmatch(reply)
        if not match:
            raise RuntimeError("Could not read the arm position: " + reply)
        return dict(zip(("yaw", "pitch", "claw"), map(int, match.groups())))

    def _pause(self, seconds):
        """Sleep, waking early if STOP arrives. True means the task was aborted."""
        if self.simulate:
            return self.abort.is_set()
        return self.abort.wait(seconds)

    def _ramp(self, verb, start, target):
        """Walk one joint to target in small steps. False means the task was aborted."""
        position = start
        while position != target:
            if self.abort.is_set():
                return False
            position += max(-RAMP_STEP_DEG, min(RAMP_STEP_DEG, target - position))
            self._exchange(f"{verb} {position}")
            if self._pause(RAMP_STEP_SECONDS):
                return False
        return not self._pause(SETTLE_SECONDS)

    def run_task(self, name, width_cm=None):
        """pick_up: close the claw on the object, then raise the arm.
        put_down: lower the arm, then open the claw."""
        if name not in TASKS:
            raise ValueError("Unknown task.")
        cfg = {key: int(setting(key)) for key in
               ("OCTAVIUS_PICKUP_PITCH", "OCTAVIUS_PUTDOWN_PITCH", "OCTAVIUS_CLAW_OPEN_ANGLE")}
        for key in ("OCTAVIUS_PICKUP_PITCH", "OCTAVIUS_PUTDOWN_PITCH"):
            if not PITCH_LIMITS[0] <= cfg[key] <= PITCH_LIMITS[1]:
                raise ValueError(f"{key} in .env must be between {PITCH_LIMITS[0]} and {PITCH_LIMITS[1]}.")
        claw_angle = width_to_claw_angle(width_cm) if name == "pick_up" else cfg["OCTAVIUS_CLAW_OPEN_ANGLE"]
        if not 0 <= claw_angle <= 180:
            raise ValueError("OCTAVIUS_CLAW_OPEN_ANGLE in .env must be between 0 and 180.")
        pitch_target = cfg["OCTAVIUS_PICKUP_PITCH"] if name == "pick_up" else cfg["OCTAVIUS_PUTDOWN_PITCH"]
        # Claw first when picking up, pitch first when putting down.
        moves = [("CLAW_ANGLE", "claw", claw_angle), ("PITCH_ANGLE", "pitch", pitch_target)]
        if name == "put_down":
            moves.reverse()

        logger.info("task requested task=%s width_cm=%s simulated=%s", name, width_cm, self.simulate)
        if not self.lock.acquire(blocking=False):
            logger.warning("task rejected task=%s reason=busy", name)
            raise RuntimeError("Nano is busy; try again in a moment.")
        self.abort.clear()
        self.task_active = True
        steps, aborted = [], False
        try:
            angles = self._read_angles()
            for verb, joint, target in moves:
                steps.append(f"{verb} {target}")
                if not self._ramp(verb, angles[joint], target):
                    aborted = True
                    break
            if aborted:
                self._exchange("STOP")
            logger.info("task complete task=%s steps=%s aborted=%s", name, steps, aborted)
            return {"task": name, "claw_angle": claw_angle, "pitch": pitch_target,
                    "steps": steps, "aborted": aborted}
        finally:
            self.task_active = False
            self.lock.release()
