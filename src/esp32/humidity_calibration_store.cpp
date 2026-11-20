#include "firmware/humidity_calibration.h"
#include <Preferences.h>
#include <math.h>

namespace {
constexpr char STORAGE_NAMESPACE[] = "humidity-ref";
constexpr char REFERENCE_KEY[] = "reference";
struct LegacyReference {
  uint32_t version;
  uint32_t revision;
  float shtRaw;
  float scdRaw;
  float shtOffset;
  float scdOffset;
  uint32_t durationMs;
};
}

bool loadHumidityReference(HumidityReference& reference) {
  Preferences storage;
  if (!storage.begin(STORAGE_NAMESPACE, false)) return false;
  HumidityReference loaded;
  bool read = false;
  if (storage.getBytesLength(REFERENCE_KEY) == sizeof(LegacyReference)) {
    LegacyReference legacy = {};
    read = storage.getBytes(REFERENCE_KEY, &legacy, sizeof(legacy)) == sizeof(legacy) && legacy.version == 1;
    if (read) {
      loaded.revision = legacy.revision;
      loaded.shtRaw = legacy.shtRaw;
      loaded.scdRaw = legacy.scdRaw;
      loaded.shtOffset = legacy.shtOffset;
      loaded.scdOffset = legacy.scdOffset;
      loaded.durationMs = legacy.durationMs;
    }
  } else if (storage.getBytesLength(REFERENCE_KEY) == sizeof(loaded)) {
    read = storage.getBytes(REFERENCE_KEY, &loaded, sizeof(loaded)) == sizeof(loaded);
  }
  storage.end();
  if (!read || loaded.version != 2 || !isfinite(loaded.shtOffset) ||
      !isfinite(loaded.scdOffset) ||
      (loaded.kind != HumidityReferenceKind::assumedSaturation &&
       loaded.kind != HumidityReferenceKind::runningCalibration)) return false;
  reference = loaded;
  return true;
}

bool saveHumidityReference(const HumidityReference& reference) {
  Preferences storage;
  if (!storage.begin(STORAGE_NAMESPACE, false)) return false;
  const bool saved = storage.putBytes(REFERENCE_KEY, &reference, sizeof(reference)) == sizeof(reference);
  storage.end();
  return saved;
}
