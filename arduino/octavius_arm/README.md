# Arduino Nano arm controller

This sketch controls one arm with three servos.

| Arduino Nano pin | Servo |
| --- | --- |
| D2 | Horizontal elbow, continuous-rotation yaw servo |
| D3 | Vertical elbow, positional pitch servo |
| D4 | Claw, positional servo |

## Wiring

Each servo has three wires:

- Brown/black: external servo-power ground.
- Red: external regulated 5V power.
- Yellow/orange/white: signal wire to the Nano pin in the table above.

Connect the external servo supply's ground to Nano `GND`. Do **not** connect the servo red wires to Nano `5V`.

Connect the Pi to the Nano with a USB data cable. The Pi sends newline-terminated commands at 115200 baud.

The D2 yaw servo is not position-aware. Each left/right command runs it for a
short, limited time and then stops it. Its direction and timing are configured
near the top of `octavius_arm.ino`. D3 and D4 are moved one degree at a time
to keep the pitch and claw motion gentle.

## Upload

1. In Arduino IDE, install the standard `Servo` library if it is not already available.
2. Select the correct Arduino Nano board and USB port.
3. Upload `octavius_arm.ino`.
4. Power the servo supply only after the code uploads and the arm has room to move.

## Commands

The normal commands are:

- `YAW_LEFT` and `YAW_RIGHT`
- `PITCH_UP` and `PITCH_DOWN`
- `CLAW_OPEN` and `CLAW_CLOSE`
- `WAVE`, `HOME`, and `STOP`
- `YAW_LEFT 250` or `YAW_RIGHT 250` for a custom yaw duration in milliseconds
- `PITCH_ANGLE 95` for a safe pitch angle
- `CLAW_ANGLE 55` for a safe claw angle

The old `ELBOW_LEFT`, `ELBOW_RIGHT`, `ELBOW_UP`, and `ELBOW_DOWN` names are
also accepted as aliases.

Tune the angle limits near the top of the sketch before attaching the cardboard shell.
