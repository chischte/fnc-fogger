#pragma once

#include <stdint.h>
#include "firmware/control_settings.h"
#include "firmware/pi_controller.h"

namespace AutomaticLimits {
constexpr float CO2_KP = 0.02f;
constexpr float CO2_TI_SECONDS = 300;
constexpr float HUMIDITY_KP = 1;
constexpr float HUMIDITY_TI_SECONDS = 600;
constexpr float CO2_HYSTERESIS_PPM = 50;
constexpr uint8_t FAN_MIN_PERCENT = 0;
constexpr uint8_t FAN_MAX_PERCENT = 80;
constexpr uint8_t FAN_FAULT_PERCENT = 10;
constexpr uint8_t FOGGER_MAX_PERCENT = 20;
constexpr uint8_t FAN_STALL_CHECK_PERCENT = 10;
constexpr uint32_t FAN_START_GRACE_MS = 5000;
constexpr uint32_t CO2_MAX_AGE_MS = 15000;
constexpr uint32_t HUMIDITY_MAX_AGE_MS = 135000;
constexpr float HUMIDITY_LIMIT_RH = 95;
constexpr float HUMIDITY_OVERSHOOT_RH = 0.5f;
constexpr uint32_t FOGGER_PULSE_MS = 100;
constexpr bool FOGGER_ENABLED = true;
constexpr bool STARTUP_TEST_ENABLED = false;
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
  void resumeIfIdle(uint32_t now, const ControlInput& input, bool manualActive,
                    bool networkAvailable, bool maintenance);
  void stop(const char* reason);
  void poll(uint32_t now, const ControlInput& input, const ControlSettings& settings,
            bool networkAvailable, bool maintenance);
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
  void reset();
  void fail(const char* reason, bool hardwareReady);
  void updateFan(uint32_t now, const ControlInput& input, const ControlSettings& settings);
  void updateFogger(uint32_t now, const ControlInput& input, const ControlSettings& settings);
  void inhibitFogger(const char* reason);
  PiController co2Pi_{AutomaticLimits::CO2_KP, AutomaticLimits::CO2_TI_SECONDS};
  PiController humidityPi_{AutomaticLimits::HUMIDITY_KP, AutomaticLimits::HUMIDITY_TI_SECONDS};
  bool enabled_ = false;
  bool ownsOutputs_ = false;
  bool fault_ = false;
  bool fanDemand_ = false;
  bool co2Seen_ = false;
  bool humiditySeen_ = false;
  bool co2Available_ = false;
  float lastValidCo2_ = 0;
  uint32_t lastValidCo2At_ = 0;
  uint32_t co2At_ = 0;
  uint32_t humidityAt_ = 0;
  uint32_t humidityResumedAt_ = 0;
  uint32_t fanStartedAt_ = 0;
  uint32_t cycleStartedAt_ = 0;
  uint8_t fanPercent_ = 0;
  uint8_t foggerPercent_ = 0;
  uint32_t resetCount_ = 0;
  const char* reason_ = "automatic_off";
};
