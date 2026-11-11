#include "firmware/control_settings_store.h"

#include <Preferences.h>

namespace {
constexpr char STORAGE_NAMESPACE[] = "lance-control";
constexpr char SETTINGS_KEY[] = "setpoints";
constexpr uint32_t SETTINGS_VERSION = 1;

struct StoredSettings {
  uint32_t version;
  ControlSettings values;
};
}  // namespace

void ControlSettingsStore::begin() {
  Preferences storage;
  available_ = storage.begin(STORAGE_NAMESPACE, false);
  if (!available_) {
    return;
  }
  StoredSettings stored = {};
  const bool loaded = storage.getBytesLength(SETTINGS_KEY) == sizeof(stored) &&
      storage.getBytes(SETTINGS_KEY, &stored, sizeof(stored)) == sizeof(stored);
  storage.end();
  if (loaded && stored.version == SETTINGS_VERSION && stored.values.valid()) {
    settings_ = stored.values;
    persisted_ = true;
  }
}

bool ControlSettingsStore::save(const ControlSettings& settings) {
  if (!available_ || !settings.valid()) {
    return false;
  }
  if (persisted_ && settings == settings_) {
    return true;
  }
  Preferences storage;
  if (!storage.begin(STORAGE_NAMESPACE, false)) {
    return false;
  }
  // One NVS blob commits the two setpoints together, including across power loss.
  const StoredSettings stored = {SETTINGS_VERSION, settings};
  const bool saved = storage.putBytes(SETTINGS_KEY, &stored, sizeof(stored)) ==
                     sizeof(stored);
  storage.end();
  if (!saved) {
    return false;
  }
  settings_ = settings;
  persisted_ = true;
  return true;
}
