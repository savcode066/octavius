# Main Nano sketch

| Signal | Joint | Hardware |
| --- | --- | --- |
| D2 | Left/right yaw | Positional |
| D3 | Up/down pitch | Positional |
| D4 | Claw | Positional |

Upload this sketch instead of a test sketch for Pi control. The baud rate is
115200 with newline-terminated commands. Select the exact physical Nano model.
Serial Monitor must be closed when the Pi controls the Nano.

Servo power comes from a suitable external regulated supply. Connect servo
grounds and Nano GND together. Signal wires go to D2/D3/D4; the Pi connects
to Nano USB. Verify the powered CrunchLabs board's pinout and power routing
before combining its power with Nano USB.

Every joint starts at 90 degrees and moves 5 degrees per press, applied as soon
as the command arrives. `Servo.write()` accepts 0 through 180 and clamps
anything outside that, so those are the limits; reaching further would need
`writeMicroseconds()`. Nothing here senses where the arm really is, so a press
against a mechanical stop still counts. Lower `YAW_STEP`, `PITCH_STEP` or
`CLAW_STEP` for finer control.

Commands: YAW_LEFT, YAW_RIGHT, PITCH_UP, PITCH_DOWN, CLAW_INC, CLAW_DEC,
HOME, STOP, STATUS, PITCH_ANGLE 0..180, CLAW_ANGLE 0..180.
Every OK ends with ` yaw=.. pitch=.. claw=..`, which the Pi writes to its log.
STATUS reports those without moving anything. They are the angles last
commanded, not measured, so a servo stalled against its stop still reports the
angle it was told to reach.
HOME returns all three joints to 90. Nothing moves on its own, so STOP only
reasserts the current position. It does not cut servo power; keep a physical
servo power switch accessible.
