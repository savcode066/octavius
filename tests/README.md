# Octavius hardware tests

## D3 up/down test

Open `d3_up_down/d3_up_down.ino` in Arduino IDE and upload it to the Nano.
The test moves the positional servo connected to D3 between 60 and 120 degrees,
holding each position for one second.

Run it with the arm linkage disconnected first. If the servo reaches a hard
stop or strains, reduce `UP_ANGLE` and `DOWN_ANGLE` in the sketch.

## D2 left/right test

Open `d2_left_right/d2_left_right.ino` in Arduino IDE and upload it to the
Nano. The positional servo connected to D2 moves left, returns home, moves
right, returns home, and repeats.

Run it with the arm linkage disconnected first. If the direction is reversed,
swap `YAW_LEFT` and `YAW_RIGHT`. If it moves too far, reduce the difference
between those values and `YAW_HOME`.

## Main sketch logic

`test_firmware.py` compiles `arduino/octavius_arm` for the desktop with g++,
using the stand-ins in `firmware/`, and drives it through recorded click
patterns. A simulated servo always lands on the angle it is given, so these
cover the stepping and limit logic only, never physical movement.
