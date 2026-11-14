#pragma once

#include <stdint.h>

// A humidity deficit is evidence of failed humidification, not a water sensor.
class HumidityEmergency {
 public:
  static constexpr float DEFICIT_RH = 10;
  static constexpr float CO2_TARGET_PPM = 5000;
  static constexpr uint32_t DELAY_MS = 30UL * 60 * 1000;

  void poll(uint32_t now, bool belowThreshold, uint32_t maximumGapMs) {
    if (active_) return;
    if (!belowThreshold) {
      clearPending();
      return;
    }
    if (!pending_ || now - lastObservedAt_ >= maximumGapMs) {
      pending_ = true;
      startedAt_ = now;
    }
    lastObservedAt_ = now;
    if (now - startedAt_ > DELAY_MS) active_ = true;
  }

  void clearPending() { pending_ = false; }
  void release() { active_ = false; clearPending(); }
  bool active() const { return active_; }

 private:
  bool active_ = false;
  bool pending_ = false;
  uint32_t startedAt_ = 0;
  uint32_t lastObservedAt_ = 0;
};
