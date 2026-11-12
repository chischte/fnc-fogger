#pragma once

#include <math.h>

struct ControlSettings {
  static constexpr float MAX_CO2_PPM = 20000.0f;
  static constexpr float MIN_HUMIDITY_RH = 70.0f;
  static constexpr float MAX_HUMIDITY_RH = 99.0f;
  float co2Ppm = 1000.0f;
  float humidityRh = 90.0f;

  bool valid() const {
    return isfinite(co2Ppm) && co2Ppm >= 0.0f && co2Ppm <= MAX_CO2_PPM &&
           isfinite(humidityRh) && humidityRh >= MIN_HUMIDITY_RH &&
           humidityRh <= MAX_HUMIDITY_RH;
  }

  bool operator==(const ControlSettings& other) const {
    return co2Ppm == other.co2Ppm && humidityRh == other.humidityRh;
  }
};
