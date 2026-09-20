// Minimal Arduino stand-ins so the Nano sketch can be compiled and driven on a
// desktop. The sketch includes <Servo.h> first, so everything it needs from the
// Arduino core is declared here.
#pragma once
#include <algorithm>
#include <cstddef>
#include <string>

typedef unsigned char byte;

using std::max;
using std::min;

extern unsigned long simulatedMillis;
inline unsigned long millis() { return simulatedMillis; }

inline int constrain(int value, int low, int high) {
  return value < low ? low : (value > high ? high : value);
}

class Servo {
 public:
  int pin = -1;
  int value = -1;
  void attach(int p) { pin = p; }
  void write(int v) { value = v; }
};

class SerialStub {
 public:
  std::string incoming;
  std::string outgoing;
  std::size_t cursor = 0;

  void begin(long) {}
  int available() { return static_cast<int>(incoming.size() - cursor); }
  int read() { return cursor < incoming.size() ? incoming[cursor++] : -1; }
  void print(const char *text) { outgoing += text; }
  void println(const char *text) {
    outgoing += text;
    outgoing += "\n";
  }
};

extern SerialStub Serial;
