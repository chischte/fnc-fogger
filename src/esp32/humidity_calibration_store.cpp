#include "firmware/humidity_calibration.h"
#include <Preferences.h>

namespace {
constexpr char STORAGE_NAMESPACE[] = "humidity-ref";
constexpr char REFERENCE_KEY[] = "reference";
}

bool loadHumidityReference(HumidityReference& reference) {
  Preferences storage;
  if (!storage.begin(STORAGE_NAMESPACE, false)) return false;
  HumidityReference loaded;
  const bool read = storage.getBytesLength(REFERENCE_KEY) == sizeof(loaded) &&
      storage.getBytes(REFERENCE_KEY, &loaded, sizeof(loaded)) == sizeof(loaded);
  storage.end();
  if (!read || loaded.version != 1 || !isfinite(loaded.shtOffset) ||
      !isfinite(loaded.scdOffset)) return false;
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
