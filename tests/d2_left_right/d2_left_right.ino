#include <Servo.h>

Servo yawServo;

const byte YAW_PIN = 2;

// A continuous-rotation servo uses speed commands, not angle commands.
// Swap these values if the directions are reversed.
const int STOP_US = 1500;
const int LEFT_US = 1475;
const int RIGHT_US = 1525;

const unsigned long MOVE_TIME_MS = 180;
const unsigned long PAUSE_TIME_MS = 1000;

void stopServo() {
  yawServo.writeMicroseconds(STOP_US);
}

void setup() {
  yawServo.attach(YAW_PIN);
  stopServo();
  delay(PAUSE_TIME_MS);
}

void loop() {
  yawServo.writeMicroseconds(LEFT_US);
  delay(MOVE_TIME_MS);
  stopServo();
  delay(PAUSE_TIME_MS);

  yawServo.writeMicroseconds(RIGHT_US);
  delay(MOVE_TIME_MS);
  stopServo();
  delay(PAUSE_TIME_MS);
}
