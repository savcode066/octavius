// Drives the real Nano sketch on the desktop so the stepping and limit logic
// can be tested without hardware.
//
// stdin is a script, one instruction per line:
//   <COMMAND>  send that line to the sketch over the simulated serial port
//   @<ms>      let <ms> milliseconds pass, running loop() each millisecond
//
// stdout is one JSON object per instruction, reporting what the servos hold.
#include "Servo.h"

#include <cstdio>
#include <iostream>

unsigned long simulatedMillis = 0;
SerialStub Serial;

#include "octavius_arm.ino"

static void drainSerial() {
  while (Serial.available()) {
    loop();
  }
}

static void advance(unsigned long ms) {
  for (unsigned long i = 0; i < ms; ++i) {
    ++simulatedMillis;
    loop();
  }
}

static void report(const std::string &instruction) {
  std::printf(
      "{\"step\": \"%s\", \"yaw\": %d, \"pitch\": %d, \"claw\": %d}\n",
      instruction.c_str(), yaw.value, pitch.value, claw.value);
}

int main() {
  setup();
  report("setup");

  std::string line;
  while (std::getline(std::cin, line)) {
    if (!line.empty() && line.back() == '\r') {
      line.pop_back();
    }
    if (line.empty()) {
      continue;
    }

    if (line[0] == '@') {
      advance(std::strtoul(line.c_str() + 1, nullptr, 10));
    } else {
      Serial.incoming += line;
      Serial.incoming += "\n";
      drainSerial();
    }
    report(line);
  }

  std::printf("{\"step\": \"serial\", \"output\": \"");
  for (char c : Serial.outgoing) {
    if (c == '\n') {
      std::printf("\\n");
    } else {
      std::putchar(c);
    }
  }
  std::printf("\"}\n");
  return 0;
}
