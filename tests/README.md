# Octavius hardware tests

## D3 up/down test

Open `d3_up_down/d3_up_down.ino` in Arduino IDE and upload it to the Nano.
The test moves the positional servo connected to D3 between 60 and 120 degrees,
holding each position for one second.

Run it with the arm linkage disconnected first. If the servo reaches a hard
stop or strains, reduce `UP_ANGLE` and `DOWN_ANGLE` in the sketch.
