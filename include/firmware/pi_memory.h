#pragma once

struct PiMemory {
  constexpr PiMemory(float co2Value = 0, float humidityValue = 0)
      : co2(co2Value), humidity(humidityValue) {}
  float co2;
  float humidity;
  bool operator==(const PiMemory& other) const {
    return co2 == other.co2 && humidity == other.humidity;
  }
};

bool loadPiMemory(PiMemory& memory);
bool savePiMemory(const PiMemory& memory);
