#include "firmware/humidity_calibration.h"
#include <math.h>

namespace {
constexpr uint32_t RUNNING_SAVE_INTERVAL_MS = 60000;
constexpr uint32_t RUNNING_SAVE_RETRY_MS = 1000;

bool validHumidity(float value) {
  return isfinite(value) && value >= 0 && value <= 100;
}

bool adjustOffset(float raw, bool valid, float& referenceRaw, float& offset) {
  if (!valid || !validHumidity(raw) || raw + offset <= 100) return false;
  referenceRaw = raw;
  offset = 100 - raw;
  return true;
}
}

void HumidityCalibration::start(uint32_t now) {
  startedAt_ = lastRiseAt_ = now;
  hasHumidity_ = false;
  running_ = true;
  status_ = "running";
}

void HumidityCalibration::observeHumidity(uint32_t now, float humidity, bool valid) {
  if (!running_) return;
  if (!valid || !validHumidity(humidity)) {
    hasHumidity_ = false;
    lastRiseAt_ = now;
    return;
  }
  if (!hasHumidity_ || humidity >= riseReferenceRh_ + MINIMUM_RISE_RH) {
    riseReferenceRh_ = humidity;
    lastRiseAt_ = now;
    hasHumidity_ = true;
  }
}

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
  pendingSave_ = saveFailed_ = false;
  running_ = false;
  status_ = "complete";
  return true;
}

bool HumidityCalibration::runningCalibration(uint32_t now, float shtRaw, bool shtValid,
                                             float scdRaw, bool scdValid) {
  if (running_) return false;
  const bool shtChanged = adjustOffset(shtRaw, shtValid, reference_.shtRaw, reference_.shtOffset);
  const bool scdChanged = adjustOffset(scdRaw, scdValid, reference_.scdRaw, reference_.scdOffset);
  const bool changed = shtChanged || scdChanged;
  if (changed) {
    reference_.kind = HumidityReferenceKind::runningCalibration;
    reference_.durationMs = 0;
    pendingSave_ = true;
  }
  checkpointRunning(now);
  return changed;
}

void HumidityCalibration::checkpointRunning(uint32_t now, bool force) {
  if (!pendingSave_) return;
  const uint32_t interval = force ? RUNNING_SAVE_RETRY_MS : RUNNING_SAVE_INTERVAL_MS;
  if (saveAttempted_ && now - lastSaveAttemptAt_ < interval) return;
  saveAttempted_ = true;
  lastSaveAttemptAt_ = now;
  HumidityReference next = reference_;
  ++next.revision;
  saveFailed_ = !saveHumidityReference(next);
  if (saveFailed_) return;
  reference_ = next;
  pendingSave_ = false;
}

