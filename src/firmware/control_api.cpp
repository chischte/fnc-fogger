#include "firmware/control_api.h"

#include <stdlib.h>

namespace {
bool parseNumber(const String& text, float& result) {
  if (!text.length()) {
    return false;
  }
  char* end = nullptr;
  result = strtof(text.c_str(), &end);
  return end != text.c_str() && *end == '\0' && isfinite(result);
}

String piJson(const PiTerms& terms) {
  return "{\"p\":" + String(terms.p, 2) + ",\"i\":" + String(terms.i, 2) +
         ",\"sum\":" + String(terms.sum, 2) + "}";
}
}  // namespace

bool parseControlSettings(const String& body, ControlSettings& settings) {
  const int separator = body.indexOf('&');
  if (separator < 0 || body.indexOf('&', separator + 1) >= 0) {
    return false;
  }
  bool co2Found = false;
  bool humidityFound = false;
  const String fields[] = {body.substring(0, separator), body.substring(separator + 1)};
  for (const String& field : fields) {
    if (field.startsWith("co2_ppm=")) {
      co2Found = parseNumber(field.substring(8), settings.co2Ppm);
    } else if (field.startsWith("humidity_rh=")) {
      humidityFound = parseNumber(field.substring(12), settings.humidityRh);
    } else {
      return false;
    }
  }
  return co2Found && humidityFound && settings.valid();
}

bool parseManualSettings(const String& body, bool& active, uint8_t& fan, uint8_t& fogger, bool& renew) {
  bool modeFound = false, fanFound = false, foggerFound = false;
  int start = 0;
  while (start < static_cast<int>(body.length())) {
    const int end = body.indexOf('&', start);
    const String field = end < 0 ? body.substring(start) : body.substring(start, end);
    float value;
    if (field == "mode=manual" || field == "mode=off" || field == "mode=renew") {
      if (modeFound) return false;
      active = field != "mode=off";
      renew = field == "mode=renew";
      modeFound = true;
    } else if (field.startsWith("fan_percent=")) {
      if (fanFound || !parseNumber(field.substring(12), value) || value < 0 || value > 100 || value != floorf(value)) return false;
      fan = static_cast<uint8_t>(value);
      fanFound = true;
    } else if (field.startsWith("fogger_percent=")) {
      if (foggerFound || !parseNumber(field.substring(15), value) || value < 0 || value > 100 || value != floorf(value)) return false;
      fogger = static_cast<uint8_t>(value);
      foggerFound = true;
    } else {
      return false;
    }
    if (end < 0) break;
    start = end + 1;
    if (start == static_cast<int>(body.length())) return false;
  }
  return modeFound && fanFound && foggerFound && (active || (!fan && !fogger));
}

String buildControlJson(const ControlSettingsStore& store, const ActuatorStatus* actuators,
                        const ManualControl* manual, const AutomaticControl* automatic) {
  const ControlSettings& settings = store.settings();
  String json = "{\"version\":1,\"settings_supported\":";
  json += store.available() ? "true" : "false";
  json += ",\"persisted\":";
  json += store.persisted() ? "true" : "false";
  json += ",\"setpoints\":{\"co2_ppm\":" + String(settings.co2Ppm, 1);
  json += ",\"humidity_rh\":" + String(settings.humidityRh, 1) + "}";
  const char* reason = "not_configured";
  if (actuators) {
    reason = !actuators->hardwareReady ? "hardware_error" :
             actuators->aborted ? "startup_test_aborted" :
             actuators->startupActive ? "startup_test" : "startup_test_complete";
  }
  if (manual && manual->active()) reason = "manual";
  else if (manual && manual->interrupted()) reason = "manual_wifi_lost";
  if (automatic && automatic->ownsOutputs()) reason = automatic->reason();
  json += ",\"manual\":{\"supported\":";
  json += manual && actuators && actuators->hardwareReady ? "true" : "false";
  json += ",\"active\":";
  json += manual && manual->active() ? "true" : "false";
  json += ",\"fan_percent\":" + String(manual ? manual->fanPercent() : 0);
  json += ",\"fogger_percent\":" + String(manual ? manual->foggerPercent() : 0);
  json += ",\"lease_ms\":" + String(ManualControl::LEASE_MS) + "}";
  const bool automaticActive = automatic && automatic->enabled();
  json += ",\"automatic_supported\":";
  json += automatic ? "true" : "false";
  json += ",\"fogger_enabled\":";
  json += AutomaticLimits::FOGGER_ENABLED ? "true" : "false";
  json += ",\"parameters\":{\"co2_kp\":" + String(AutomaticLimits::CO2_KP, 3);
  json += ",\"co2_ti_s\":" + String(AutomaticLimits::CO2_TI_SECONDS, 0);
  json += ",\"humidity_kp\":" + String(AutomaticLimits::HUMIDITY_KP, 3);
  json += ",\"humidity_ti_s\":" + String(AutomaticLimits::HUMIDITY_TI_SECONDS, 0);
  json += ",\"fan_min_percent\":" + String(AutomaticLimits::FAN_MIN_PERCENT);
  json += ",\"fan_max_percent\":" + String(AutomaticLimits::FAN_MAX_PERCENT);
  json += ",\"fan_fault_percent\":" + String(AutomaticLimits::FAN_FAULT_PERCENT);
  json += ",\"fogger_max_percent\":" + String(AutomaticLimits::FOGGER_MAX_PERCENT) + "}";
  json += ",\"enabled\":";
  json += automaticActive ? "true" : "false";
  json += ",\"fault\":";
  json += automatic && automatic->fault() ? "true" : "false";
  json += ",\"reason\":\"";
  json += reason;
  json += '"';
  json += ",\"humidity\":";
  json += automaticActive ? piJson(automatic->humidityTerms()) : "{\"p\":null,\"i\":null,\"sum\":null}";
  json += ",\"co2\":";
  json += automaticActive ? piJson(automatic->co2Terms()) : "{\"p\":null,\"i\":null,\"sum\":null}";
  json += ",\"fan\":{\"rpm\":";
  json += actuators && actuators->rpmValid ? String(actuators->rpm) : String("null");
  json += ",\"pwm_percent\":";
  json += actuators ? String(actuators->fanPercent) : String("null");
  json += "},\"fogger\":{\"on\":";
  json += actuators && actuators->foggerOn ? "true" : "false";
  const bool manualActive = manual && manual->active();
  const bool testing = actuators && actuators->startupActive;
  json += ",\"duty_percent\":";
  json += automaticActive ? String(automatic->foggerPercent()) :
      manualActive ? String(manual->foggerPercent()) : testing ? String("null") : String("0");
  json += ",\"on_time_s\":";
  json += automaticActive ? String(automatic->foggerPercent() > 0 ?
      AutomaticLimits::FOGGER_PULSE_MS / 1000.0f : 0.0f, 2) :
      manualActive ? String(manual->foggerPercent() / 100.0f, 2) :
      actuators && actuators->foggerTestActive ? String(StartupTest::FOGGER_PULSE_MS / 1000.0f, 1) : String("0.0");
  json += ",\"off_time_s\":";
  json += automaticActive ? (automatic->foggerPercent() > 0 ?
      String((automatic->foggerPeriodMs() - AutomaticLimits::FOGGER_PULSE_MS) / 1000.0f, 3) : String("null")) :
      manualActive ? String(1.0f - manual->foggerPercent() / 100.0f, 2) :
      actuators && actuators->foggerTestActive ? String(StartupTest::FOGGER_PAUSE_MS / 1000.0f, 1) : String("null");
  json += "},\"startup_test\":{\"active\":";
  json += testing ? "true" : "false";
  json += ",\"complete\":";
  json += actuators && actuators->startupComplete ? "true" : "false";
  json += ",\"completed_pulses\":";
  json += actuators ? String(actuators->completedPulses) : String("0");
  json += ",\"completed_fan_pulses\":";
  json += actuators ? String(actuators->completedFanPulses) : String("0");
  json += "}}";
  return json;
}
