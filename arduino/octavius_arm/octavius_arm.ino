#include <Servo.h>
#include <string.h>
#include <stdlib.h>
#include <ctype.h>

const byte YAW_PIN = 2;
const byte PITCH_PIN = 3;
const byte CLAW_PIN = 4;

// These limits must stay inside what the linkage can actually reach. A limit
// wider than the mechanism drives the servo into its stop, where it stalls
// while the target keeps counting past it; the joint then ignores further
// presses until the opposite direction has unwound that gap. Widen only after
// checking the endpoint with the linkage disconnected.
const int YAW_LOW = 60;
const int YAW_HIGH = 140;
const int YAW_STEP = 3;

const int PITCH_LOW = 60;
const int PITCH_HIGH = 140;
const int PITCH_STEP = 3;

const int CLAW_MIN = 80;
const int CLAW_MAX = 125;
const int CLAW_STEP = 2;

Servo yaw;
Servo pitch;
Servo claw;

int yawAngle = 90;
int yawTarget = 90;

int pitchAngle = 90;
int pitchTarget = 90;

int clawAngle = (CLAW_MIN + CLAW_MAX) / 2;
int clawTarget = clawAngle;

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

  // Only a running wave blocks input; plain moves accumulate onto the target.
  if (waveStage) {
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

    int minimum = isPitch ? PITCH_LOW : CLAW_MIN;
    int maximum = isPitch ? PITCH_HIGH : CLAW_MAX;

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
    pitchTarget = max(PITCH_LOW, pitchTarget - PITCH_STEP);

  } else if (!strcmp(verb, "PITCH_DOWN")) {
    pitchTarget = min(PITCH_HIGH, pitchTarget + PITCH_STEP);

  } else if (!strcmp(verb, "CLAW_INC")) {
    clawTarget = min(CLAW_MAX, clawTarget + CLAW_STEP);

  } else if (!strcmp(verb, "CLAW_DEC")) {
    clawTarget = max(CLAW_MIN, clawTarget - CLAW_STEP);

  } else if (!strcmp(verb, "HOME")) {
    yawTarget = 90;
    pitchTarget = 90;
    clawTarget = (CLAW_MIN + CLAW_MAX) / 2;

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
