#pragma once
#include <stdint.h>

struct SensorFailure {
  uint32_t outages = 0;
  uint32_t restarts = 0;
  uint32_t lastFailureMs = 0;
  uint32_t lastRecoveryMs = 0;
  bool failed = false;

  void observe(bool valid, uint32_t now) {
    if (!valid && !failed) { ++outages; lastFailureMs = now; }
    if (valid && failed) lastRecoveryMs = now;
    failed = !valid;
  }
};

struct SensorDiagnostics {
  SensorFailure co2;
  SensorFailure sht45;
  uint32_t busRestarts = 0;
  uint32_t lastHeaterStartMs = 0;
  bool heaterActive = false;
};
