# Arduino Nano arm controller

This sketch controls one arm with three micro servos.

| Arduino Nano pin | Servo |
| --- | --- |
| D2 | Horizontal elbow |
| D3 | Vertical elbow |
| D4 | Claw |

## Wiring

Each servo has three wires:

- Brown/black: external servo-power ground.
- Red: external regulated 5V power.
- Yellow/orange/white: signal wire to the Nano pin in the table above.

Connect the external servo supply's ground to Nano `GND`. Do **not** connect the servo red wires to Nano `5V`.

Connect the Pi to the Nano with a USB data cable. The Pi sends newline-terminated commands at 115200 baud.

## Upload

1. In Arduino IDE, install the standard `Servo` library if it is not already available.
2. Select the correct Arduino Nano board and USB port.
3. Upload `octavius_arm.ino`.
4. Power the servo supply only after the code uploads and the arm has room to move.

## Commands

`WAVE`, `HOME`, `CLAW_OPEN`, `CLAW_CLOSE`, `ELBOW_LEFT`, `ELBOW_RIGHT`, `ELBOW_UP`, and `ELBOW_DOWN`.

Tune the angle limits near the top of the sketch before attaching the cardboard shell.
