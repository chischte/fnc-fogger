#include "firmware/manual_control.h"

bool ManualControl::set(bool active, uint8_t fanPercent, uint8_t foggerPercent,
                        uint32_t now) {
  if (fanPercent > 100 || foggerPercent > 100 || (!active && (fanPercent || foggerPercent))) {
    return false;
  }
  if (!active_ || foggerPercent_ != foggerPercent) {
    cycleStartedAt_ = now;
  }
  commanded_ = true;
  active_ = active;
  expired_ = false;
  fanPercent_ = fanPercent;
  foggerPercent_ = foggerPercent;
  renewedAt_ = now;
  return true;
}

bool ManualControl::renew(uint8_t fanPercent, uint8_t foggerPercent, uint32_t now) {
  if (!active_ || now - renewedAt_ >= LEASE_MS ||
      fanPercent != fanPercent_ || foggerPercent != foggerPercent_) {
    return false;
  }
  renewedAt_ = now;
  return true;
}

void ManualControl::stop() {
  active_ = false;
  fanPercent_ = 0;
  foggerPercent_ = 0;
}

void ManualControl::poll(uint32_t now) {
  if (active_ && now - renewedAt_ >= LEASE_MS) {
    stop();
    expired_ = true;
  }
  if (active_ && now - cycleStartedAt_ >= FOGGER_PERIOD_MS) {
    cycleStartedAt_ += ((now - cycleStartedAt_) / FOGGER_PERIOD_MS) * FOGGER_PERIOD_MS;
  }
}

bool ManualControl::foggerOn(uint32_t now) const {
  return active_ && now - cycleStartedAt_ < FOGGER_PERIOD_MS * foggerPercent_ / 100;
}
