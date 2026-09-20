#include <Servo.h>
#include <string.h>
#include <stdlib.h>
#include <ctype.h>

const byte YAW_PIN = 2;
const byte PITCH_PIN = 3;
const byte CLAW_PIN = 4;

const int YAW_LOW = 0;
const int YAW_HIGH = 180;
const int YAW_STEP = 5;

const int PITCH_LOW = 0;
const int PITCH_HIGH = 180;
const int PITCH_STEP = 5;

const int CLAW_LOW = 0;
const int CLAW_HIGH = 180;

const int CLAW_OPEN = 125;
const int CLAW_CLOSED = 80;
const int CLAW_STEP = 5;

Servo yaw;
Servo pitch;
Servo claw;

int yawAngle = 90;
int yawTarget = 90;

int pitchAngle = 90;
int pitchTarget = 90;

int clawAngle = CLAW_OPEN;
int clawTarget = CLAW_OPEN;

unsigned long lastStep = 0;

byte waveStage = 0;

int savedYaw = 90;
int savedPitch = 90;

char buffer[48];
byte length = 0;
bool overflow = false;

void stopAll() {
  waveStage = 0;

  yawTarget = yawAngle;
  pitchTarget = pitchAngle;
  clawTarget = clawAngle;
}

void yawMove(bool left) {
  yawTarget = constrain(
    yawTarget + (left ? -YAW_STEP : YAW_STEP),
    YAW_LOW,
    YAW_HIGH
  );
}

bool moving() {
  return yawAngle != yawTarget ||
         pitchAngle != pitchTarget ||
         clawAngle != clawTarget;
}

void stepServo(Servo &servo, int &current, int target) {
  if (current == target) {
    return;
  }

  current += target > current ? 1 : -1;
  servo.write(current);
}

void tick() {
  unsigned long now = millis();

  if (now - lastStep >= 25) {
    lastStep = now;

    stepServo(yaw, yawAngle, yawTarget);
    stepServo(pitch, pitchAngle, pitchTarget);
    stepServo(claw, clawAngle, clawTarget);
  }

  if (waveStage && !moving()) {
    switch (waveStage++) {
      case 1:
        yawMove(true);
        break;

      case 2:
        yawMove(false);
        break;

      case 3:
        yawMove(false);
        break;

      case 4:
        yawMove(true);
        break;

      case 5:
        yawTarget = savedYaw;
        pitchTarget = savedPitch;
        break;

      default:
        waveStage = 0;
        break;
    }
  }
}

void handle(char *line) {
  for (char *p = line; *p; ++p) {
    *p = toupper((unsigned char)*p);
  }

  char *verb = strtok(line, " ");
  char *arg = strtok(NULL, " ");
  char *extra = strtok(NULL, " ");

  if (!verb) {
    return;
  }

  if (!strcmp(verb, "STOP") && !arg) {
    stopAll();
    Serial.println("OK STOP");
    return;
  }

  if (moving() || waveStage) {
    Serial.println("ERR busy");
    return;
  }

  if (extra) {
    Serial.println("ERR arguments");
    return;
  }

  if (!strcmp(verb, "PITCH_ANGLE") ||
      !strcmp(verb, "CLAW_ANGLE")) {

    if (!arg || !*arg) {
      Serial.println("ERR angle required");
      return;
    }

    for (char *p = arg; *p; ++p) {
      if (!isdigit((unsigned char)*p)) {
        Serial.println("ERR invalid angle");
        return;
      }
    }

    if (strlen(arg) > 3) {
      Serial.println("ERR angle range");
      return;
    }

    int value = atoi(arg);
    bool isPitch = !strcmp(verb, "PITCH_ANGLE");

    int minimum = isPitch
      ? PITCH_LOW
      : min(CLAW_LOW, CLAW_HIGH);

    int maximum = isPitch
      ? PITCH_HIGH
      : max(CLAW_LOW, CLAW_HIGH);

    if (value < minimum || value > maximum) {
      Serial.println("ERR angle range");
      return;
    }

    if (isPitch) {
      pitchTarget = value;
    } else {
      clawTarget = value;
    }

  } else if (arg) {
    Serial.println("ERR unexpected argument");
    return;

  } else if (!strcmp(verb, "YAW_LEFT")) {
    yawMove(true);

  } else if (!strcmp(verb, "YAW_RIGHT")) {
    yawMove(false);

  } else if (!strcmp(verb, "PITCH_UP")) {
    pitchTarget = max(PITCH_LOW, pitchAngle - PITCH_STEP);

  } else if (!strcmp(verb, "PITCH_DOWN")) {
    pitchTarget = min(PITCH_HIGH, pitchAngle + PITCH_STEP);

  } else if (!strcmp(verb, "CLAW_OPEN")) {
    clawTarget = min(CLAW_OPEN, clawAngle + CLAW_STEP);

  } else if (!strcmp(verb, "CLAW_CLOSE")) {
    clawTarget = max(CLAW_CLOSED, clawAngle - CLAW_STEP);

  } else if (!strcmp(verb, "HOME")) {
    yawTarget = 90;
    pitchTarget = 90;
    clawTarget = CLAW_OPEN;

  } else if (!strcmp(verb, "WAVE")) {
    savedYaw = yawAngle;
    savedPitch = pitchAngle;

    pitchTarget = max(PITCH_LOW, pitchAngle - PITCH_STEP);
    waveStage = 1;

  } else {
    Serial.println("ERR unknown command");
    return;
  }

  Serial.print("OK ");
  Serial.println(verb);
}

void setup() {
  Serial.begin(115200);

  yaw.attach(YAW_PIN);
  pitch.attach(PITCH_PIN);
  claw.attach(CLAW_PIN);

  yaw.write(yawAngle);
  pitch.write(pitchAngle);
  claw.write(clawAngle);

  Serial.println("Octavius ready");
}

void loop() {
  tick();

  for (
    byte count = 0;
    count < 32 && Serial.available();
    ++count
  ) {
    char c = Serial.read();

    if (c == '\r') {
      continue;
    }

    if (c == '\n') {
      if (overflow) {
        Serial.println("ERR command too long");
      } else {
        buffer[length] = '\0';

        if (length) {
          handle(buffer);
        }
      }

      length = 0;
      overflow = false;

    } else if (!overflow) {
      if (length < sizeof(buffer) - 1) {
        buffer[length++] = c;
      } else {
        overflow = true;
      }
    }
  }
}
