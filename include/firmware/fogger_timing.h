#pragma once

#include <stdint.h>

namespace FoggerTiming {
constexpr uint32_t PULSE_MS = 100;
constexpr uint8_t FULL_PERCENT = 100;

inline uint32_t periodMs(uint8_t percent) {
  return percent > 0 ? PULSE_MS * FULL_PERCENT / percent : 0;
}
}  // namespace FoggerTiming
