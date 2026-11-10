#pragma once

#include <Arduino.h>
#include "firmware/startup_test.h"
#include "firmware/manual_control.h"

class StartupActuators {
 public:
  void begin(uint32_t now);
  void poll(uint32_t now, bool maintenance);
  ManualControl& manualControl() { return manual_; }
  const ActuatorStatus& status() const { return status_; }

 private:
  static void IRAM_ATTR onTachPulse(void* instance);
  void updateRpm(uint32_t now);
  void applyOutputs(uint32_t now);

  ManualControl manual_;
  bool manualTookOver_ = false;
  StartupTest startup_;
  ActuatorStatus status_;
  portMUX_TYPE tachMux_ = portMUX_INITIALIZER_UNLOCKED;
  volatile uint32_t tachPulses_ = 0;
  uint32_t previousPulses_ = 0;
  uint32_t lastRpmAt_ = 0;
  uint8_t appliedFanPercent_ = 255;
  bool appliedFoggerOn_ = false;
};
