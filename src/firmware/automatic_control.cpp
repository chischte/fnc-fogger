#include "firmware/automatic_control.h"

using namespace AutomaticLimits;

void AutomaticControl::reset() {
  co2Pi_.reset();
  humidityPi_.reset();
  fanDemand_ = false;
  co2Seen_ = false;
  humiditySeen_ = false;
  co2Available_ = false;
  fanPercent_ = 0;
  foggerPercent_ = 0;
  fault_ = false;
}

void AutomaticControl::setEnabled(bool enabled, uint32_t now) {
  reset();
  enabled_ = enabled;
  ownsOutputs_ = true;
  cycleStartedAt_ = now;
  reason_ = enabled ? "automatic_waiting" : "automatic_off";
}

void AutomaticControl::releaseToManual() {
  reset();
  enabled_ = false;
  ownsOutputs_ = false;
  reason_ = "automatic_off";
}

void AutomaticControl::stop(const char* reason) {
  setEnabled(false, 0);
  reason_ = reason;
}

void AutomaticControl::fail(const char* reason, bool hardwareReady) {
  reset();
  fault_ = true;
  fanPercent_ = hardwareReady ? FAN_FAULT_PERCENT : 0;
  reason_ = reason;
}

void AutomaticControl::poll(uint32_t now, const ControlInput& input,
                            const ControlSettings& settings, bool networkAvailable,
                            bool maintenance) {
  if (!enabled_) return;
  if (maintenance || !networkAvailable) {
    stop(maintenance ? "automatic_update" : "automatic_wifi_lost");
    return;
  }
  if (fault_) return;
  if (!input.hardwareReady) {
    fail("automatic_hardware_error", false);
    return;
  }
  ControlInput effective = input;
  if (input.co2Valid && isfinite(input.co2) && input.co2 >= 0 &&
      now - input.co2At < CO2_MAX_AGE_MS) {
    co2Available_ = true;
    lastValidCo2_ = input.co2;
    lastValidCo2At_ = input.co2At;
  } else if (co2Available_ && now - lastValidCo2At_ < CO2_MAX_AGE_MS) {
    // Reuse the timestamp too: held samples must not advance the integral.
    effective.co2 = lastValidCo2_;
    effective.co2At = lastValidCo2At_;
    effective.co2Valid = true;
  } else {
    fail("automatic_co2_invalid", true);
    return;
  }
  if (!settings.valid()) {
    fail("automatic_co2_invalid", true);
    return;
  }
  if (input.scdHumidityValid && input.scdHumidity >= HUMIDITY_LIMIT_RH) {
    fail("automatic_co2_condensation_risk", true);
    return;
  }
  updateFan(now, effective, settings);
  if (fanDemand_ && now - fanStartedAt_ >= FAN_START_GRACE_MS &&
      (!input.rpmValid || input.rpm < FAN_MIN_RPM)) {
    fail("automatic_fan_stalled", true);
    return;
  }
  updateFogger(now, input, settings);
}

void AutomaticControl::updateFan(uint32_t now, const ControlInput& input,
                                 const ControlSettings& settings) {
  const float error = input.co2 - settings.co2Ppm;
  if (!fanDemand_ && error > CO2_HYSTERESIS_PPM) {
    fanDemand_ = true;
    fanStartedAt_ = now;
  } else if (fanDemand_ && error <= 0) {
    fanDemand_ = false;
  }
  if (!fanDemand_) {
    fanPercent_ = 0;
    co2Pi_.reset();
    co2Seen_ = false;
    return;
  }
  if (!co2Seen_ || input.co2At != co2At_) {
    const float seconds = co2Seen_ ? (input.co2At - co2At_) / 1000.0f : 0;
    const float output = co2Pi_.update(error, seconds, FAN_MIN_PERCENT, FAN_MAX_PERCENT);
    fanPercent_ = static_cast<uint8_t>(output + 0.5f);
    co2Seen_ = true;
    co2At_ = input.co2At;
  }
}

void AutomaticControl::inhibitFogger(const char* reason) {
  foggerPercent_ = 0;
  humidityPi_.reset();
  humiditySeen_ = false;
  reason_ = reason;
}

void AutomaticControl::updateFogger(uint32_t now, const ControlInput& input,
                                    const ControlSettings& settings) {
  if (!FOGGER_ENABLED) {
    inhibitFogger(fanDemand_ ? "automatic_ventilation_only" : "automatic_no_co2_demand");
    return;
  }
  if (!fanDemand_) {
    inhibitFogger("automatic_no_co2_demand");
    return;
  }
  if (!input.rpmValid || input.rpm < FAN_MIN_RPM) {
    inhibitFogger("automatic_waiting_for_fan");
    return;
  }
  if (!input.humidityValid || !isfinite(input.humidity) || input.humidity < 0 ||
      input.humidity > 100 || now - input.humidityAt >= HUMIDITY_MAX_AGE_MS) {
    inhibitFogger("automatic_humidity_invalid");
    return;
  }
  if (input.humidity >= HUMIDITY_LIMIT_RH ||
      input.humidity >= settings.humidityRh + HUMIDITY_OVERSHOOT_RH) {
    inhibitFogger("automatic_humidity_limit");
    return;
  }
  reason_ = "automatic_running";
  if (!humiditySeen_ || input.humidityAt != humidityAt_) {
    const float seconds = humiditySeen_ ? (input.humidityAt - humidityAt_) / 1000.0f : 0;
    const float output = humidityPi_.update(settings.humidityRh - input.humidity,
                                          seconds, 0, FOGGER_MAX_PERCENT);
    const uint8_t percent = static_cast<uint8_t>(output + 0.5f);
    if (percent != foggerPercent_) cycleStartedAt_ = now;
    foggerPercent_ = percent;
    humidityAt_ = input.humidityAt;
    humiditySeen_ = true;
  }
}

bool AutomaticControl::foggerOn(uint32_t now) const {
  return enabled_ && !fault_ && foggerPercent_ > 0 &&
      (now - cycleStartedAt_) % foggerPeriodMs() < FOGGER_PULSE_MS;
}

uint32_t AutomaticControl::foggerPeriodMs() const {
  return foggerPercent_ > 0 ? FOGGER_PULSE_MS * 100 / foggerPercent_ : 0;
}
