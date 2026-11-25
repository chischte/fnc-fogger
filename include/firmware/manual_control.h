#pragma once
#include <stdint.h>
#include "firmware/fogger_timing.h"

// Volatile commissioning commands stop on network loss, not viewer inactivity.
class ManualControl {
 public:
  static constexpr uint32_t LEASE_MS = 0;
  uint32_t foggerPeriodMs() const { return FoggerTiming::periodMs(foggerPercent_); }
  bool set(bool active, uint8_t fanPercent, uint8_t foggerPercent, uint32_t now);
  bool renew(uint8_t fanPercent, uint8_t foggerPercent, uint32_t now);
  void stop();
  void poll(uint32_t now, bool networkAvailable = true);
  bool commanded() const { return commanded_; }
  bool active() const { return active_; }
  bool interrupted() const { return interrupted_; }
  uint8_t fanPercent() const { return fanPercent_; }
  uint8_t foggerPercent() const { return foggerPercent_; }
  bool foggerOn(uint32_t now) const;
 private:
  bool commanded_ = false;
  bool active_ = false;
  bool interrupted_ = false;
  uint8_t fanPercent_ = 0;
  uint8_t foggerPercent_ = 0;
  uint32_t cycleStartedAt_ = 0;
};
