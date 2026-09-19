#include <Servo.h>

Servo yawServo;
Servo pitchServo;

const byte YAW_PIN = 2;
const byte PITCH_PIN = 3;

// Conservative positions for a small demonstration.
// Swap the values if either servo moves in the opposite direction.
const int YAW_HOME = 90;
const int YAW_LEFT = 80;
const int YAW_RIGHT = 100;

const int PITCH_HOME = 90;
const int PITCH_UP = 70;
const int PITCH_DOWN = 110;

const unsigned int SERVO_STEP_DELAY_MS = 18;
const unsigned long PAUSE_AFTER_LIFT_MS = 400;
const unsigned long PAUSE_AFTER_WAVE_MS = 400;
const unsigned long WAIT_BETWEEN_CYCLES_MS = 3000;

int yawAngle = YAW_HOME;
int pitchAngle = PITCH_HOME;

void moveSmooth(Servo &servo, int &currentAngle, int targetAngle) {
  int direction = (targetAngle > currentAngle) ? 1 : -1;

  while (currentAngle != targetAngle) {
    currentAngle += direction;
    servo.write(currentAngle);
    delay(SERVO_STEP_DELAY_MS);
  }
}

void logStep(const char *message) {
  Serial.print(millis());
  Serial.print(" ms | ");
  Serial.println(message);
}

void setup() {
  Serial.begin(115200);

  yawServo.attach(YAW_PIN);
  pitchServo.attach(PITCH_PIN);

  yawServo.write(YAW_HOME);
  pitchServo.write(PITCH_HOME);
  logStep("D2+D3 sequence test started");
  delay(1000);
}

void loop() {
  logStep("D3 lifting arm");
  moveSmooth(pitchServo, pitchAngle, PITCH_UP);
  delay(PAUSE_AFTER_LIFT_MS);

  logStep("D2 waving left");
  moveSmooth(yawServo, yawAngle, YAW_LEFT);
  delay(PAUSE_AFTER_WAVE_MS);

  logStep("D2 waving right");
  moveSmooth(yawServo, yawAngle, YAW_RIGHT);
  delay(PAUSE_AFTER_WAVE_MS);

  logStep("D2 waving left again");
  moveSmooth(yawServo, yawAngle, YAW_LEFT);
  delay(PAUSE_AFTER_WAVE_MS);

  logStep("D2 returning home");
  moveSmooth(yawServo, yawAngle, YAW_HOME);
  delay(PAUSE_AFTER_WAVE_MS);

  logStep("D3 lowering arm");
  moveSmooth(pitchServo, pitchAngle, PITCH_DOWN);
  delay(WAIT_BETWEEN_CYCLES_MS);
}
