#include <Servo.h>

Servo pitchServo;

const byte PITCH_PIN = 3;

// This is intentionally a wide test range. Reduce these values if the
// mechanism reaches a hard stop or the servo starts straining.
const int UP_ANGLE = 60;
const int DOWN_ANGLE = 120;
const unsigned long HOLD_TIME_MS = 1000;

void setup() {
  pitchServo.attach(PITCH_PIN);
  pitchServo.write(90);
  delay(HOLD_TIME_MS);
}

void loop() {
  pitchServo.write(UP_ANGLE);
  delay(HOLD_TIME_MS);

  pitchServo.write(DOWN_ANGLE);
  delay(HOLD_TIME_MS);
}
