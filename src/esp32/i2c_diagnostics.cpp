#include "firmware/i2c_diagnostics.h"

#include <Wire.h>

#include "firmware/time_utils.h"

namespace {
constexpr uint32_t PROBE_INTERVAL_MS = 5;
constexpr uint8_t NOT_PROBED = 255;
}  // namespace

void I2cDiagnostics::start() {
  if (running_) {
    return;
  }
  for (uint8_t& status : statuses_) {
    status = NOT_PROBED;
  }
  nextAddress_ = FIRST_ADDRESS;
  lastProbeAt_ = 0;
  started_ = true;
  running_ = true;
}

void I2cDiagnostics::poll(uint32_t now) {
  if (!running_ || !hasElapsed(now, lastProbeAt_, PROBE_INTERVAL_MS)) {
    return;
  }
  lastProbeAt_ = now;
  // Probe one address per loop; do not write commands to unidentified devices.
  Wire.beginTransmission(nextAddress_);
  statuses_[nextAddress_ - FIRST_ADDRESS] = Wire.endTransmission();
  if (nextAddress_ == LAST_ADDRESS) {
    running_ = false;
    return;
  }
  ++nextAddress_;
}
