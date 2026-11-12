#include "firmware/humidity_calibration.h"
#include <math.h>

bool HumidityCalibration::capture(float shtRaw, float scdRaw, uint32_t durationMs) {
  if (!isfinite(shtRaw) || !isfinite(scdRaw) || shtRaw < 0 || shtRaw > 100 ||
      scdRaw < 0 || scdRaw > 100) return false;
  HumidityReference next;
  next.revision = reference_.revision + 1;
  next.shtRaw = shtRaw;
  next.scdRaw = scdRaw;
  next.shtOffset = 100 - shtRaw;
  next.scdOffset = 100 - scdRaw;
  next.durationMs = durationMs;
  if (!saveHumidityReference(next)) return false;
  reference_ = next;
  running_ = false;
  status_ = "complete";
  return true;
}

