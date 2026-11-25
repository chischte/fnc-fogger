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
  interrupted_ = false;
  fanPercent_ = fanPercent;
  foggerPercent_ = foggerPercent;
  return true;
}

bool ManualControl::renew(uint8_t fanPercent, uint8_t foggerPercent, uint32_t) {
  if (!active_ ||
      fanPercent != fanPercent_ || foggerPercent != foggerPercent_) {
    return false;
  }
  return true;
}

void ManualControl::stop() {
  active_ = false;
  fanPercent_ = 0;
  foggerPercent_ = 0;
}

void ManualControl::poll(uint32_t, bool networkAvailable) {
  if (active_ && !networkAvailable) {
    stop();
    interrupted_ = true;
  }
}

bool ManualControl::foggerOn(uint32_t now) const {
  return active_ && foggerPercent_ > 0 &&
      (now - cycleStartedAt_) % foggerPeriodMs() < FoggerTiming::PULSE_MS;
}
