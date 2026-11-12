#include <Preferences.h>
#include "firmware/control_settings_store.h"

extern "C" { int _fltused = 0; }

#define assert(condition) do { if (!(condition)) return __LINE__; } while (false)

int main() {
  ControlSettings humidityLimit;
  humidityLimit.humidityRh = 98;
  assert(humidityLimit.valid());
  humidityLimit.humidityRh = 99;
  assert(!humidityLimit.valid());

  ControlSettingsStore first;
  first.begin();
  assert(first.available() && !first.persisted());
  const ControlSettings selected = {1500.0f, 93.0f};
  assert(first.save(selected));
  assert(first.persisted() && first.settings() == selected);
  assert(first.save(selected) && Preferences::writes == 1);

  // A fresh application instance restores both values without WiFi or a PC.
  ControlSettingsStore restarted;
  restarted.begin();
  assert(restarted.persisted() && restarted.settings() == selected);

  Preferences::failWrite = true;
  assert(!restarted.save({2000.0f, 95.0f}));
  assert(restarted.settings() == selected);
  ControlSettingsStore afterFailedWrite;
  afterFailedWrite.begin();
  assert(afterFailedWrite.settings() == selected);
  Preferences::failWrite = false;

  assert(!restarted.save({-1.0f, 93.0f}));
  assert(!restarted.save({1500.0f, 101.0f}));
  assert(!restarted.save({1500.0f, 69.0f}));
  assert(!restarted.save({20001.0f, 93.0f}));
  assert(!restarted.save({NAN, 93.0f}));
  assert(Preferences::writes == 1);

  Preferences::bytes[0] = 99;
  ControlSettingsStore incompatible;
  incompatible.begin();
  assert(!incompatible.persisted());
  assert(incompatible.settings().co2Ppm == 1000.0f);

  Preferences::failOpen = true;
  ControlSettingsStore unavailable;
  unavailable.begin();
  assert(!unavailable.available() && !unavailable.save(selected));
  return 0;
}
