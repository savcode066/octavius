#include <Servo.h>
#include <stdlib.h>
#include <string.h>

// The Nano controls the servos. Do not power the servos from the Nano.
const byte YAW_PIN = 2;    // continuous-rotation servo: left/right
const byte PITCH_PIN = 3;  // positional servo: up/down
const byte CLAW_PIN = 4;   // positional servo: gentle claw

Servo yawServo;
Servo pitchServo;
Servo clawServo;

// Continuous-rotation servos use pulse widths instead of positions.
// If left/right are reversed, swap YAW_LEFT_US and YAW_RIGHT_US.
const int YAW_STOP_US = 1500;
const int YAW_LEFT_US = 1470;
const int YAW_RIGHT_US = 1530;
const unsigned long YAW_STEP_MS = 180;

// Conservative limits. Tune these with the arm disconnected first.
const int PITCH_HOME = 90;
const int PITCH_MIN = 70;
const int PITCH_MAX = 110;
const int PITCH_STEP = 5;
const int PITCH_WAVE_STEP = 3;

const int CLAW_OPEN = 45;
const int CLAW_CLOSED = 70;
const int CLAW_MIN = 35;
const int CLAW_MAX = 80;
const unsigned int POSITION_STEP_DELAY_MS = 22;
const unsigned long YAW_WAVE_MS = 110;

int pitchAngle = PITCH_HOME;
int clawAngle = CLAW_OPEN;

char inputBuffer[48];
byte inputLength = 0;

int clampValue(int value, int minimum, int maximum) {
  if (value < minimum) return minimum;
  if (value > maximum) return maximum;
  return value;
}

void stopYaw() {
  yawServo.writeMicroseconds(YAW_STOP_US);
}

void moveYaw(int pulseWidth, unsigned long durationMs) {
  yawServo.writeMicroseconds(pulseWidth);
  delay(durationMs);
  stopYaw();
}

void movePosition(Servo &servo, int &current, int target, int minimum, int maximum) {
  target = clampValue(target, minimum, maximum);

  while (current != target) {
    current += (target > current) ? 1 : -1;
    servo.write(current);
    delay(POSITION_STEP_DELAY_MS);
  }
}

void home() {
  // A continuous-rotation yaw servo has no absolute home position.
  // HOME stops it and returns the other two servos to their safe positions.
  stopYaw();
  movePosition(pitchServo, pitchAngle, PITCH_HOME, PITCH_MIN, PITCH_MAX);
  movePosition(clawServo, clawAngle, CLAW_OPEN, CLAW_MIN, CLAW_MAX);
}

void wave() {
  // Very small pitch movement first, then four short yaw movements.
  movePosition(pitchServo, pitchAngle, pitchAngle - PITCH_WAVE_STEP, PITCH_MIN, PITCH_MAX);
  delay(150);
  movePosition(pitchServo, pitchAngle, pitchAngle + PITCH_WAVE_STEP, PITCH_MIN, PITCH_MAX);
  delay(200);

  moveYaw(YAW_LEFT_US, YAW_WAVE_MS);
  delay(150);
  moveYaw(YAW_RIGHT_US, YAW_WAVE_MS);
  delay(150);
  moveYaw(YAW_LEFT_US, YAW_WAVE_MS);
  delay(150);
  moveYaw(YAW_RIGHT_US, YAW_WAVE_MS);
  home();
}

void printOk(const char *command) {
  Serial.print("OK ");
  Serial.println(command);
}

void handleCommand(char *command) {
  char *verb = strtok(command, " ");
  char *argument = strtok(NULL, " ");

  if (verb == NULL) return;

  // Fixed, safe commands.
  if (strcmp(verb, "STOP") == 0) {
    stopYaw();
    printOk("STOP");
  } else if (strcmp(verb, "HOME") == 0) {
    home();
    printOk("HOME");
  } else if (strcmp(verb, "WAVE") == 0) {
    wave();
    printOk("WAVE");
  } else if (strcmp(verb, "CLAW_OPEN") == 0) {
    movePosition(clawServo, clawAngle, CLAW_OPEN, CLAW_MIN, CLAW_MAX);
    printOk("CLAW_OPEN");
  } else if (strcmp(verb, "CLAW_CLOSE") == 0) {
    movePosition(clawServo, clawAngle, CLAW_CLOSED, CLAW_MIN, CLAW_MAX);
    printOk("CLAW_CLOSE");
  } else if (strcmp(verb, "PITCH_UP") == 0 || strcmp(verb, "ELBOW_UP") == 0) {
    movePosition(pitchServo, pitchAngle, pitchAngle - PITCH_STEP, PITCH_MIN, PITCH_MAX);
    printOk("PITCH_UP");
  } else if (strcmp(verb, "PITCH_DOWN") == 0 || strcmp(verb, "ELBOW_DOWN") == 0) {
    movePosition(pitchServo, pitchAngle, pitchAngle + PITCH_STEP, PITCH_MIN, PITCH_MAX);
    printOk("PITCH_DOWN");
  } else if (strcmp(verb, "YAW_LEFT") == 0 || strcmp(verb, "ELBOW_LEFT") == 0) {
    unsigned long duration = YAW_STEP_MS;
    if (argument != NULL) duration = clampValue(atoi(argument), 50, 750);
    moveYaw(YAW_LEFT_US, duration);
    printOk("YAW_LEFT");
  } else if (strcmp(verb, "YAW_RIGHT") == 0 || strcmp(verb, "ELBOW_RIGHT") == 0) {
    unsigned long duration = YAW_STEP_MS;
    if (argument != NULL) duration = clampValue(atoi(argument), 50, 750);
    moveYaw(YAW_RIGHT_US, duration);
    printOk("YAW_RIGHT");
  } else if (strcmp(verb, "PITCH_ANGLE") == 0 && argument != NULL) {
    int target = clampValue(atoi(argument), PITCH_MIN, PITCH_MAX);
    movePosition(pitchServo, pitchAngle, target, PITCH_MIN, PITCH_MAX);
    printOk("PITCH_ANGLE");
  } else if (strcmp(verb, "CLAW_ANGLE") == 0 && argument != NULL) {
    int target = clampValue(atoi(argument), CLAW_MIN, CLAW_MAX);
    movePosition(clawServo, clawAngle, target, CLAW_MIN, CLAW_MAX);
    printOk("CLAW_ANGLE");
  } else {
    Serial.print("ERR unknown or incomplete command: ");
    Serial.println(verb);
  }
}

void readSerialCommands() {
  while (Serial.available() > 0) {
    char character = Serial.read();

    if (character == '\r') continue;

    if (character == '\n') {
      inputBuffer[inputLength] = '\0';
      if (inputLength > 0) handleCommand(inputBuffer);
      inputLength = 0;
    } else if (inputLength < sizeof(inputBuffer) - 1) {
      inputBuffer[inputLength++] = character;
    } else {
      inputLength = 0;
      Serial.println("ERR command too long");
    }
  }
}

void setup() {
  Serial.begin(115200);

  yawServo.attach(YAW_PIN);
  pitchServo.attach(PITCH_PIN);
  clawServo.attach(CLAW_PIN);

  pitchServo.write(pitchAngle);
  clawServo.write(clawAngle);
  stopYaw();

  Serial.println("Octavius arm ready");
}

void loop() {
  readSerialCommands();
}
