#pragma once

#include <stdint.h>
#include "firmware/control_settings.h"
#include "firmware/pi_controller.h"
#include "firmware/pi_memory.h"
#include "firmware/cyclic_mist.h"
#include "firmware/humidity_emergency.h"

namespace AutomaticLimits {
constexpr float CO2_KP = 0.04f;
constexpr float CO2_TI_SECONDS = 600;
constexpr float HUMIDITY_KP = 1.5f;
constexpr float HUMIDITY_TI_SECONDS = 900;
constexpr uint8_t FAN_MIN_PERCENT = 0;
constexpr uint8_t FAN_MAX_PERCENT = 80;
constexpr uint8_t FAN_FAULT_PERCENT = 10;
constexpr uint8_t CYCLIC_MIST_FAN_PERCENT = 50;
constexpr uint8_t FOGGER_MAX_PERCENT = 100;
constexpr uint8_t FAN_STALL_CHECK_PERCENT = 10;
constexpr uint32_t FAN_START_GRACE_MS = 5000;
constexpr uint32_t FAN_STALL_TIMEOUT_MS = 5000;
constexpr uint32_t CO2_MAX_AGE_MS = 15000;
constexpr uint32_t HUMIDITY_MAX_AGE_MS = 135000;
constexpr uint32_t FOGGER_PULSE_MS = 100;
constexpr bool FOGGER_ENABLED = true;
constexpr bool STARTUP_TEST_ENABLED = true;
}

struct ControlInput {
  uint32_t co2At = 0;
  uint32_t humidityAt = 0;
  float co2 = 0;
  float humidity = 0;
  float scdHumidity = 0;
  bool co2Valid = false;
  bool humidityValid = false;
  bool scdHumidityValid = false;
  bool hardwareReady = false;
  bool rpmValid = false;
  uint32_t rpm = 0;
};

class AutomaticControl {
 public:
  void setEnabled(bool enabled, uint32_t now);
  void releaseToManual();
  void resetIntegrals();
  PiMemory memory() const { return {co2Pi_.terms().i, humidityPi_.terms().i}; }
  bool restoreMemory(const PiMemory& memory);
  void refreshMeasurements() { co2Seen_ = humiditySeen_ = false; }
  uint32_t memoryRevision() const { return memoryRevision_; }
  void setMemorySaved(bool saved) { memorySaved_ = saved; }
  bool memorySaved() const { return memorySaved_; }
  bool configureCyclicMist(const CyclicMistSettings& settings, uint32_t now) {
    if (settings.enabled && (!enabled_ || fault_) && !cyclicMist_.settings().enabled) return false;
    return cyclicMist_.configure(settings, now);
  }
  void restoreCyclicMist(const CyclicMistSettings& settings, uint32_t now) {
    cyclicMist_.configure(settings, now);
  }
  const CyclicMist& cyclicMist() const { return cyclicMist_; }
  void waitForCyclicMistClock() { cyclicMist_.waitForClock(); }
  void restoreCyclicMistPhase(uint32_t now, uint32_t elapsedMs) {
    cyclicMist_.restorePhase(now, elapsedMs);
  }

  void resumeIfIdle(uint32_t now, const ControlInput& input, bool manualActive,
                    bool networkAvailable, bool maintenance);
  void stop(const char* reason);
  void poll(uint32_t now, const ControlInput& input, const ControlSettings& settings,
            bool networkAvailable, bool maintenance);
  bool humidityEmergency() const { return humidityEmergency_.active(); }
  float effectiveCo2Target(float configured) const {
    return humidityEmergency() ? HumidityEmergency::CO2_TARGET_PPM : configured;
  }
  bool cyclicMisting() const { return !humidityEmergency() && cyclicMist_.misting(); }
  bool enabled() const { return enabled_; }
  bool ownsOutputs() const { return ownsOutputs_; }
  bool fault() const { return fault_; }
  uint32_t resetCount() const { return resetCount_; }
  const char* reason() const { return reason_; }
  uint8_t fanPercent() const { return fanPercent_; }
  uint8_t foggerPercent() const { return foggerPercent_; }
  bool foggerOn(uint32_t now) const;
  uint32_t foggerPeriodMs() const;
  const PiTerms& co2Terms() const { return co2Pi_.terms(); }
  const PiTerms& humidityTerms() const { return humidityPi_.terms(); }

 private:
  void resetRuntimeState();
  bool fanStalled(uint32_t now, const ControlInput& input);
  void fail(const char* reason, bool hardwareReady);
  void pauseForCo2();
  void updateFan(uint32_t now, const ControlInput& input, const ControlSettings& settings);
  void updateFogger(uint32_t now, const ControlInput& input, const ControlSettings& settings);
  void inhibitFogger(const char* reason);
  CyclicMist cyclicMist_;
  HumidityEmergency humidityEmergency_;
  PiController co2Pi_{AutomaticLimits::CO2_KP, AutomaticLimits::CO2_TI_SECONDS};
  PiController humidityPi_{AutomaticLimits::HUMIDITY_KP, AutomaticLimits::HUMIDITY_TI_SECONDS};
  bool enabled_ = false;
  bool ownsOutputs_ = false;
  bool fault_ = false;
  bool fanDemand_ = false;
  bool fanMissing_ = false;
  uint32_t fanMissingAt_ = 0;
  bool co2Seen_ = false;
  bool humiditySeen_ = false;
  bool co2Available_ = false;
  bool co2Interrupted_ = false;
  float lastValidCo2_ = 0;
  uint32_t lastValidCo2At_ = 0;
  uint32_t co2At_ = 0;
  uint32_t co2ResumedAt_ = 0;
  uint32_t humidityAt_ = 0;
  uint32_t humidityResumedAt_ = 0;
  uint32_t fanStartedAt_ = 0;
  uint32_t cycleStartedAt_ = 0;
  uint8_t fanPercent_ = 0;
  uint8_t foggerPercent_ = 0;
  uint32_t resetCount_ = 0;
  uint32_t memoryRevision_ = 0;
  bool memorySaved_ = false;
  const char* reason_ = "automatic_off";
};
