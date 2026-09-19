#include <Servo.h>

// One lightweight right arm. Do not power these servos from the Nano.
const byte HORIZONTAL_PIN = 2;
const byte VERTICAL_PIN = 3;
const byte CLAW_PIN = 4;

Servo horizontalServo;
Servo verticalServo;
Servo clawServo;

// Tune these after the mechanical arm is assembled. Start conservatively.
int horizontalAngle = 90;
int verticalAngle = 90;
int clawAngle = 45;

const int HORIZONTAL_MIN = 55;
const int HORIZONTAL_MAX = 125;
const int VERTICAL_MIN = 60;
const int VERTICAL_MAX = 120;
const int CLAW_OPEN = 45;
const int CLAW_CLOSED = 95;
const int STEP_SIZE = 8;

char inputBuffer[48];
byte inputLength = 0;

int clampAngle(int value, int minimum, int maximum) {
  if (value < minimum) return minimum;
  if (value > maximum) return maximum;
  return value;
}

void applyPose() {
  horizontalServo.write(horizontalAngle);
  verticalServo.write(verticalAngle);
  clawServo.write(clawAngle);
}

void home() {
  horizontalAngle = 90;
  verticalAngle = 90;
  clawAngle = CLAW_OPEN;
  applyPose();
}

void wave() {
  // Keep the motion small and slow while the mechanism is being tuned.
  clawAngle = CLAW_OPEN;
  verticalAngle = 95;
  applyPose();
  delay(250);

  for (byte i = 0; i < 2; i++) {
    horizontalAngle = 112;
    applyPose();
    delay(300);
    horizontalAngle = 72;
    applyPose();
    delay(300);
  }

  home();
}

void handleCommand(const char* command) {
  if (strcmp(command, "WAVE") == 0) {
    wave();
  } else if (strcmp(command, "HOME") == 0) {
    home();
  } else if (strcmp(command, "CLAW_OPEN") == 0) {
    clawAngle = CLAW_OPEN;
    clawServo.write(clawAngle);
  } else if (strcmp(command, "CLAW_CLOSE") == 0) {
    clawAngle = CLAW_CLOSED;
    clawServo.write(clawAngle);
  } else if (strcmp(command, "ELBOW_LEFT") == 0) {
    horizontalAngle = clampAngle(horizontalAngle - STEP_SIZE, HORIZONTAL_MIN, HORIZONTAL_MAX);
    horizontalServo.write(horizontalAngle);
  } else if (strcmp(command, "ELBOW_RIGHT") == 0) {
    horizontalAngle = clampAngle(horizontalAngle + STEP_SIZE, HORIZONTAL_MIN, HORIZONTAL_MAX);
    horizontalServo.write(horizontalAngle);
  } else if (strcmp(command, "ELBOW_UP") == 0) {
    verticalAngle = clampAngle(verticalAngle - STEP_SIZE, VERTICAL_MIN, VERTICAL_MAX);
    verticalServo.write(verticalAngle);
  } else if (strcmp(command, "ELBOW_DOWN") == 0) {
    verticalAngle = clampAngle(verticalAngle + STEP_SIZE, VERTICAL_MIN, VERTICAL_MAX);
    verticalServo.write(verticalAngle);
  } else {
    Serial.print("ERR unknown command: ");
    Serial.println(command);
    return;
  }

  Serial.print("OK ");
  Serial.println(command);
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

  horizontalServo.attach(HORIZONTAL_PIN);
  verticalServo.attach(VERTICAL_PIN);
  clawServo.attach(CLAW_PIN);

  home();
  Serial.println("Octavius arm ready");
}

void loop() {
  readSerialCommands();
}
