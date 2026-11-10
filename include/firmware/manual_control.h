#pragma once
#include <stdint.h>

// Volatile commissioning commands expire when the viewer stops renewing them.
class ManualControl {
 public:
  static constexpr uint32_t LEASE_MS = 30000;
  static constexpr uint32_t FOGGER_PERIOD_MS = 1000;
  bool set(bool active, uint8_t fanPercent, uint8_t foggerPercent, uint32_t now);
  bool renew(uint8_t fanPercent, uint8_t foggerPercent, uint32_t now);
  void stop();
  void poll(uint32_t now);
  bool commanded() const { return commanded_; }
  bool active() const { return active_; }
  bool expired() const { return expired_; }
  uint8_t fanPercent() const { return fanPercent_; }
  uint8_t foggerPercent() const { return foggerPercent_; }
  bool foggerOn(uint32_t now) const;
 private:
  bool commanded_ = false;
  bool active_ = false;
  bool expired_ = false;
  uint8_t fanPercent_ = 0;
  uint8_t foggerPercent_ = 0;
  uint32_t renewedAt_ = 0;
  uint32_t cycleStartedAt_ = 0;
};
