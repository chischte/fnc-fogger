#include "firmware/cyclic_mist_store.h"

#include <Preferences.h>

namespace {
constexpr char STORAGE_NAMESPACE[] = "cyclic-mist";
constexpr char SETTINGS_KEY[] = "settings";
constexpr uint32_t STORAGE_VERSION = 1;
struct StoredSettings {
  uint32_t version;
  CyclicMistSettings values;
};
}

bool loadCyclicMistSettings(CyclicMistSettings& settings) {
  Preferences storage;
  if (!storage.begin(STORAGE_NAMESPACE, false)) return false;
  StoredSettings loaded = {};
  const bool read = storage.getBytesLength(SETTINGS_KEY) == sizeof(loaded) &&
      storage.getBytes(SETTINGS_KEY, &loaded, sizeof(loaded)) == sizeof(loaded);
  storage.end();
  if (!read || loaded.version != STORAGE_VERSION) return false;
  // Preserve older enabled schedules while raising their pause to the new minimum.
  if (loaded.values.pauseMinutes >= 1 && loaded.values.pauseMinutes < 10) {
    loaded.values.pauseMinutes = 10;
  }
  if (!loaded.values.valid()) return false;
  settings = loaded.values;
  return true;
}

bool saveCyclicMistSettings(const CyclicMistSettings& settings) {
  if (!settings.valid()) return false;
  Preferences storage;
  if (!storage.begin(STORAGE_NAMESPACE, false)) return false;
  const StoredSettings stored = {STORAGE_VERSION, settings};
  const bool saved = storage.putBytes(SETTINGS_KEY, &stored, sizeof(stored)) == sizeof(stored);
  storage.end();
  return saved;
}

bool loadCyclicMistStart(uint32_t& unixSeconds) {
  Preferences storage;
  if (!storage.begin(STORAGE_NAMESPACE, true)) return false;
  uint32_t value = 0;
  const bool read = storage.getBytesLength("last-start") == sizeof(value) &&
      storage.getBytes("last-start", &value, sizeof(value)) == sizeof(value);
  storage.end();
  if (!read || value == 0) return false;
  unixSeconds = value;
  return true;
}

bool saveCyclicMistStart(uint32_t unixSeconds) {
  if (unixSeconds == 0) return false;
  Preferences storage;
  if (!storage.begin(STORAGE_NAMESPACE, false)) return false;
  const bool saved = storage.putBytes("last-start", &unixSeconds, sizeof(unixSeconds)) == sizeof(unixSeconds);
  storage.end();
  return saved;
}
