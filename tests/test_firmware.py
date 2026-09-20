"""Compile the Nano sketch for the desktop and drive it through real click patterns.

These cover the stepping and limit logic only. A simulated servo always reaches
its target, so nothing here proves the physical arm moves.
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
PITCH_LOW, PITCH_HIGH, PITCH_STEP = 60, 140, 3
CLAW_MIN, CLAW_MAX, CLAW_STEP = 80, 125, 2
CLAW_HOME = (CLAW_MIN + CLAW_MAX) // 2


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


def taps(command, count, gap=200):
    """A burst of button presses at a realistic phone tapping rate."""
    return [line for _ in range(count) for line in (command, f"@{gap}")]


def test_claw_moves_one_step_per_press(simulator):
    states = run(simulator, taps("CLAW_DEC", 4) + ["@500"])
    positions = [s["claw"] for s in states if s["step"].startswith("@")]
    assert positions[:4] == [CLAW_HOME - CLAW_STEP * n for n in range(1, 5)]


def test_claw_needs_many_presses_to_cross_its_range(simulator):
    """The old 5 degree step crossed the range in 5 presses, which read as on/off."""
    span = (CLAW_MAX - CLAW_MIN) // CLAW_STEP
    assert span >= 20
    states = run(simulator, taps("CLAW_DEC", span) + ["@2000"])
    assert states[-2]["claw"] == CLAW_MIN


def test_pitch_stops_at_the_calibrated_limit(simulator):
    """Replays the 117 presses from the 2026-09-20 log that drove pitch to 0."""
    states = run(simulator, taps("PITCH_UP", 117) + ["@3000"])
    assert states[-2]["pitch"] == PITCH_LOW
    assert states[-2]["pitch_target"] == PITCH_LOW


def test_target_never_runs_past_the_limit(simulator):
    """A target parked beyond the stop is what makes the joint ignore presses."""
    states = run(simulator, taps("PITCH_UP", 117) + taps("PITCH_DOWN", 1) + ["@500"])
    assert min(s["pitch_target"] for s in states if "pitch_target" in s) == PITCH_LOW
    assert states[-2]["pitch"] == PITCH_LOW + PITCH_STEP


def test_yaw_is_bounded_in_both_directions(simulator):
    right = run(simulator, taps("YAW_RIGHT", 60) + ["@3000"])
    left = run(simulator, taps("YAW_LEFT", 60) + ["@3000"])
    assert right[-2]["yaw"] == 140
    assert left[-2]["yaw"] == 60


def test_rapid_presses_accumulate_without_a_busy_error(simulator):
    states = run(simulator, ["CLAW_DEC"] * 5 + ["@1000"])
    assert states[-2]["claw"] == CLAW_HOME - CLAW_STEP * 5
    assert "ERR" not in states[-1]["output"]


def test_claw_angle_outside_the_range_is_refused(simulator):
    states = run(simulator, ["CLAW_ANGLE 60", "@500"])
    assert "ERR angle range" in states[-1]["output"]
    assert states[-2]["claw"] == CLAW_HOME
