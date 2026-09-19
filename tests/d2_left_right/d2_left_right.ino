#include <Servo.h>

Servo yawServo;

const byte YAW_PIN = 2;

// This test assumes D2 is a normal positional servo.
// Swap the left and right values if the directions are reversed.
const int YAW_HOME = 90;
const int YAW_LEFT = 80;
const int YAW_RIGHT = 100;

const unsigned long MOVE_TIME_MS = 500;
const unsigned long PAUSE_TIME_MS = 1000;

void moveTo(int angle) {
  yawServo.write(angle);
  delay(MOVE_TIME_MS);
}

void setup() {
  Serial.begin(115200);
  yawServo.attach(YAW_PIN);
  yawServo.write(YAW_HOME);
  Serial.println("D2 positional left/right test started");
  delay(PAUSE_TIME_MS);
}

void loop() {
  Serial.println("D2 left");
  moveTo(YAW_LEFT);
  delay(PAUSE_TIME_MS);

  Serial.println("D2 home");
  moveTo(YAW_HOME);
  delay(PAUSE_TIME_MS);

  Serial.println("D2 right");
  moveTo(YAW_RIGHT);
  delay(PAUSE_TIME_MS);

  Serial.println("D2 home");
  moveTo(YAW_HOME);
  delay(PAUSE_TIME_MS);
}
