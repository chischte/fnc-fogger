#pragma once

#include <stdint.h>

struct ActuatorStatus {
  bool hardwareReady = false;
  bool rpmValid = false;
  uint32_t rpm = 0;
  uint8_t fanPercent = 0;
  bool foggerOn = false;
  bool startupActive = false;
  bool startupComplete = false;
  bool aborted = false;
  uint8_t completedPulses = 0;
  uint8_t completedFanPulses = 0;
  bool foggerTestActive = false;
};

class StartupTest {
 public:
  static constexpr uint32_t FAN_PULSE_MS = 3000;
  static constexpr uint32_t FAN_PAUSE_MS = 1000;
  static constexpr uint32_t FOGGER_PULSE_MS = 100;
  static constexpr uint32_t FOGGER_PAUSE_MS = 100;
  static constexpr uint32_t START_DELAY_MS = 1000;

  void begin(uint32_t now);
  void poll(uint32_t now);
  void abort();
  const ActuatorStatus& status() const { return status_; }

 private:
  enum class Phase { waiting, running, pause, complete, aborted };
  void pollFogger(uint32_t now);
  Phase phase_ = Phase::waiting;
  uint32_t phaseStartedAt_ = 0;
  uint32_t foggerPhaseStartedAt_ = 0;
  ActuatorStatus status_;
};
