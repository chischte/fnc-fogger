#pragma once
#include <stdint.h>

struct TwoWire {
  uint8_t responses[128] = {};
  uint8_t address = 0;
  unsigned probes = 0;
  void beginTransmission(uint8_t value) { address = value; }
  uint8_t endTransmission() { ++probes; return responses[address]; }
};
inline TwoWire Wire;
