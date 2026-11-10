#include <Wire.h>
#include "firmware/i2c_diagnostics.h"

#define assert(condition) do { if (!(condition)) return __LINE__; } while (false)

int main() {
  for (uint8_t& response : Wire.responses) response = 2;
  Wire.responses[0x45] = 0;
  Wire.responses[0x62] = 0;
  I2cDiagnostics scanner;
  assert(!scanner.started() && !scanner.running());
  scanner.start();
  assert(scanner.running() && !scanner.complete());
  assert(scanner.status(0x44) == 255);
  scanner.poll(5);
  assert(Wire.probes == 1 && Wire.address == 0x08);
  scanner.poll(5);
  assert(Wire.probes == 1);
  scanner.start();
  for (uint32_t now = 10; now <= 560; now += 5) scanner.poll(now);
  assert(Wire.probes == 112 && Wire.address == 0x77);
  assert(scanner.complete() && !scanner.running());
  assert(scanner.status(0x44) == 2);
  assert(scanner.status(0x45) == 0 && scanner.status(0x62) == 0);
  scanner.poll(1000);
  assert(Wire.probes == 112);
  Wire.responses[0x44] = 5;
  scanner.start();
  for (uint32_t now = 1005; now <= 1560; now += 5) scanner.poll(now);
  assert(scanner.complete() && scanner.status(0x44) == 5);
  return 0;
}
