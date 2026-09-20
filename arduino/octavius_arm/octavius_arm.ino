#include <Servo.h>
#include <string.h>
#include <stdlib.h>
#include <ctype.h>

// D2 was reported to be continuous rotation. write() controls SPEED on that
// hardware, not degrees. Set false ONLY if replaced by a positional servo.
const bool YAW_CONTINUOUS = true;
const int YAW_STOP = 90, YAW_LEFT_SPEED = 87, YAW_RIGHT_SPEED = 93;
const unsigned long YAW_PULSE_MS = 110;
const int PITCH_LOW = 60, PITCH_HIGH = 140;
const int CLAW_LOW = 140, CLAW_HIGH = 60;
// These are requested physical tong positions. The mounted D4 linkage reverses them.
const int CLAW_OPEN = 120, CLAW_CLOSED = 75;
const bool CLAW_REVERSED = true;
const int CLAW_OPEN_COMMAND = CLAW_REVERSED ? CLAW_LOW + CLAW_HIGH - CLAW_OPEN : CLAW_OPEN;
const int CLAW_CLOSED_COMMAND = CLAW_REVERSED ? CLAW_LOW + CLAW_HIGH - CLAW_CLOSED : CLAW_CLOSED;
Servo yaw, pitch, claw;
int yawAngle = 90, yawTarget = 90;
int pitchAngle = 90, pitchTarget = 90;
int clawAngle = CLAW_OPEN_COMMAND, clawTarget = CLAW_OPEN_COMMAND;
unsigned long yawEnd = 0, lastStep = 0;
bool yawMoving = false;
byte waveStage = 0;
int savedYaw = 90, savedPitch = 90;
char buffer[48];
byte length = 0;
bool overflow = false;

void stopAll() {
  waveStage = 0;
  yawMoving = false;
  if (YAW_CONTINUOUS) yaw.write(YAW_STOP);
  yawTarget = yawAngle;
  pitchTarget = pitchAngle;
  clawTarget = clawAngle;
  // Positional servos hold their last position; STOP is not a power cut.
}

void yawMove(bool left) {
  if (YAW_CONTINUOUS) {
    yaw.write(left ? YAW_LEFT_SPEED : YAW_RIGHT_SPEED);
    yawEnd = millis() + YAW_PULSE_MS;
    yawMoving = true;
  } else {
    yawTarget = constrain(yawTarget + (left ? -5 : 5), 80, 100);
  }
}

bool moving() {
  return yawMoving || yawAngle != yawTarget || pitchAngle != pitchTarget || clawAngle != clawTarget;
}

void stepServo(Servo &servo, int &current, int target) {
  if (current == target) return;
  current += target > current ? 1 : -1;
  servo.write(current);
}

void tick() {
  unsigned long now = millis();
  if (yawMoving && (long)(now - yawEnd) >= 0) {
    yaw.write(YAW_STOP);
    yawMoving = false;
  }
  if (now - lastStep >= 25) {
    lastStep = now;
    if (!YAW_CONTINUOUS) stepServo(yaw, yawAngle, yawTarget);
    stepServo(pitch, pitchAngle, pitchTarget);
    stepServo(claw, clawAngle, clawTarget);
  }
  if (waveStage && !moving()) {
    switch(waveStage++) {
      case 1: yawMove(true); break;
      case 2: yawMove(false); break;
      case 3: yawMove(false); break;
      case 4: yawMove(true); break;
      case 5: yawTarget = savedYaw; pitchTarget = savedPitch; break;
      default: waveStage = 0; break;
    }
  }
}

void handle(char *line) {
  for (char *p = line; *p; ++p) *p = toupper((unsigned char)*p);
  char *verb = strtok(line, " ");
  char *arg = strtok(NULL, " ");
  char *extra = strtok(NULL, " ");
  if (!verb) return;
  if (!strcmp(verb, "STOP") && !arg) {
    stopAll(); Serial.println("OK STOP"); return;
  }
  if (moving() || waveStage) { Serial.println("ERR busy"); return; }
  if (extra) { Serial.println("ERR arguments"); return; }
  if (!strcmp(verb, "PITCH_ANGLE") || !strcmp(verb, "CLAW_ANGLE")) {
    if (!arg || !*arg) { Serial.println("ERR angle required"); return; }
    for(char *p=arg; *p; ++p) {
      if (!isdigit((unsigned char)*p)) { Serial.println("ERR invalid angle"); return; }
    }
    if (strlen(arg)>3) { Serial.println("ERR angle range"); return; }
    int value = atoi(arg);
    bool isPitch = !strcmp(verb,"PITCH_ANGLE");
    if (value < (isPitch ? PITCH_LOW : CLAW_LOW) || value > (isPitch ? PITCH_HIGH : CLAW_HIGH)) {
      Serial.println("ERR angle range"); return;
    }
    if (isPitch) pitchTarget = value;
    else clawTarget = CLAW_REVERSED ? CLAW_LOW + CLAW_HIGH - value : value;
  } else if(arg) { Serial.println("ERR unexpected argument"); return;
  } else if(!strcmp(verb,"YAW_LEFT")) yawMove(true);
  } else if(!strcmp(verb,"YAW_LEFT")) yawMove(true);
  else if(!strcmp(verb,"YAW_RIGHT")) yawMove(false);
  else if(!strcmp(verb,"PITCH_UP")) pitchTarget = max(PITCH_LOW, pitchAngle-3);
  else if(!strcmp(verb,"PITCH_DOWN")) pitchTarget = min(PITCH_HIGH, pitchAngle+3);
  else if(!strcmp(verb,"CLAW_OPEN")) clawTarget = CLAW_OPEN_COMMAND;
  else if(!strcmp(verb,"CLAW_CLOSE")) clawTarget = CLAW_CLOSED_COMMAND;
  else if(!strcmp(verb,"HOME")) {
    yawTarget = 90; pitchTarget = 90; clawTarget = CLAW_OPEN_COMMAND;
  } else if(!strcmp(verb,"WAVE")) {
    savedYaw=yawAngle; savedPitch=pitchAngle;
    pitchTarget=max(PITCH_LOW,pitchAngle-3); waveStage=1;
  } else { Serial.println("ERR unknown command"); return; }
  Serial.print("OK "); Serial.println(verb);
}

void setup() {
  Serial.begin(115200);
  yaw.attach(2); pitch.attach(3); claw.attach(4);
  yaw.write(YAW_STOP); pitch.write(pitchAngle); claw.write(clawAngle);
  Serial.println("Octavius ready");
}

void loop() {
  tick();
  // Bounded reads keep motion deadlines responsive even during serial spam.
  for(byte count=0; count<32 && Serial.available(); ++count) {
    char c=Serial.read();
    if(c=='\r') continue;
    if(c=='\n') {
      if(overflow) Serial.println("ERR command too long");
      else { buffer[length]='\0'; if(length) handle(buffer); }
      length=0; overflow=false;
    } else if(!overflow) {
      if(length < sizeof(buffer)-1) buffer[length++]=c;
      else overflow=true;
    }
  }
}
