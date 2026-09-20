# Main Nano sketch

| Signal | Joint | Default hardware |
| --- | --- | --- |
| D2 | Left/right yaw | Continuous rotation |
| D3 | Up/down pitch | Positional |
| D4 | Tong | Positional |

D2 was reported to spin continuously. `write(90)` is approximately stop on
that servo; it does NOT mean 90 degrees. Calibrate YAW_STOP with the linkage
detached. Yaw pulses automatically stop after 110 ms.
If D2 was replaced with a positional servo, set `YAW_CONTINUOUS = false`.

Upload this sketch instead of a test sketch for Pi control. The baud rate is
115200 with newline-terminated commands. Select the exact physical Nano model.
Serial Monitor must be closed when the Pi controls the Nano.

Servo power comes from a suitable external regulated supply. Connect servo
grounds and Nano GND together. Signal wires go to D2/D3/D4; the Pi connects
to Nano USB. Verify the powered CrunchLabs board's pinout and power routing
before combining its power with Nano USB.

Pitch moves in three-degree steps inside 70–110 degrees. Claw moves slowly
between 45 and 65 degrees. Calibrate these values with the linkage disconnected;
slow movement does not limit force. Startup positions are commanded immediately.

Commands: YAW_LEFT, YAW_RIGHT, PITCH_UP, PITCH_DOWN, CLAW_OPEN, CLAW_CLOSE,
WAVE, HOME, STOP, PITCH_ANGLE 70..110, CLAW_ANGLE 35..80.
Commands acknowledge when accepted, not when motion completes.
Busy commands are rejected instead of queued. STOP is read during movement,
cancels the wave, and holds positional joints. It does not cut servo power.
Keep a physical servo power switch accessible.

WAVE lifts slightly, makes balanced short yaw movements, and restores the
pitch target. Continuous yaw has no position feedback; home and timed return
cannot recover its exact original orientation.
