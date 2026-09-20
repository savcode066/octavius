#include <Servo.h>
#include <string.h>
#include <stdlib.h>
#include <ctype.h>

const byte YAW_PIN = 2;
const byte PITCH_PIN = 3;
const byte CLAW_PIN = 4;

// Servo.write() clamps to this range: it turns anything negative into 0 and
// anything above 180 into 180. Reaching further needs writeMicroseconds(),
// not a wider angle.
const int ANGLE_LOW = 0;
const int ANGLE_HIGH = 180;

// Degrees per press. Each press moves the servo immediately.
const int YAW_STEP = 5;
const int PITCH_STEP = 5;
const int CLAW_STEP = 5;

const int YAW_START = 90;
const int PITCH_START = 90;
const int CLAW_START = 90;

Servo yaw;
Servo pitch;
Servo claw;

int yawAngle = YAW_START;
int pitchAngle = PITCH_START;
int clawAngle = CLAW_START;

char buffer[48];
byte length = 0;
bool overflow = false;

void stepYaw(int delta) {
  yawAngle = constrain(yawAngle + delta, ANGLE_LOW, ANGLE_HIGH);
  yaw.write(yawAngle);
}

void stepPitch(int delta) {
  pitchAngle = constrain(pitchAngle + delta, 60, 120);
  pitch.write(pitchAngle);
}

void stepClaw(int delta) {
  clawAngle = constrain(clawAngle + delta, ANGLE_LOW, ANGLE_HIGH);
  claw.write(clawAngle);
}

// Nothing moves on its own, so STOP only reasserts the current position.
void stopAll() {
  yaw.write(yawAngle);
  pitch.write(pitchAngle);
  claw.write(clawAngle);
}

// Tails every OK so the Pi log records where each joint was left. These are
// the angles last commanded, not measured: a stalled servo still reports them.
void reportAngles() {
  Serial.print(" yaw=");
  Serial.print(yawAngle);
  Serial.print(" pitch=");
  Serial.print(pitchAngle);
  Serial.print(" claw=");
  Serial.println(clawAngle);
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
    Serial.print("OK STOP");
    reportAngles();
    return;
  }

  if (!strcmp(verb, "STATUS") && !arg) {
    Serial.print("OK STATUS");
    reportAngles();
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

    if (value < ANGLE_LOW || value > ANGLE_HIGH) {
      Serial.println("ERR angle range");
      return;
    }

    if (!strcmp(verb, "PITCH_ANGLE")) {
      stepPitch(value - pitchAngle);
    } else {
      stepClaw(value - clawAngle);
    }

  } else if (arg) {
    Serial.println("ERR unexpected argument");
    return;

  } else if (!strcmp(verb, "YAW_LEFT")) {
    stepYaw(-YAW_STEP);

  } else if (!strcmp(verb, "YAW_RIGHT")) {
    stepYaw(YAW_STEP);

  } else if (!strcmp(verb, "PITCH_UP")) {
    stepPitch(-PITCH_STEP);

  } else if (!strcmp(verb, "PITCH_DOWN")) {
    stepPitch(PITCH_STEP);

  } else if (!strcmp(verb, "CLAW_INC")) {
    stepClaw(CLAW_STEP);

  } else if (!strcmp(verb, "CLAW_DEC")) {
    stepClaw(-CLAW_STEP);

  } else if (!strcmp(verb, "HOME")) {
    stepYaw(YAW_START - yawAngle);
    stepPitch(PITCH_START - pitchAngle);
    stepClaw(CLAW_START - clawAngle);

  } else {
    Serial.println("ERR unknown command");
    return;
  }

  Serial.print("OK ");
  Serial.print(verb);
  reportAngles();
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
