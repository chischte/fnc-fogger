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

String buildControlJson(const ControlSettingsStore& store) {
  const ControlSettings& settings = store.settings();
  String json = "{\"version\":1,\"settings_supported\":";
  json += store.available() ? "true" : "false";
  json += ",\"persisted\":";
  json += store.persisted() ? "true" : "false";
  json += ",\"setpoints\":{\"co2_ppm\":" + String(settings.co2Ppm, 1);
  json += ",\"humidity_rh\":" + String(settings.humidityRh, 1) + "}";
  // Actuators and PI tuning are not installed on the current measurement lance.
  json += ",\"enabled\":false,\"reason\":\"not_configured\"";
  json += ",\"humidity\":{\"p\":null,\"i\":null,\"sum\":null}";
  json += ",\"co2\":{\"p\":null,\"i\":null,\"sum\":null}";
  json += ",\"fan\":{\"rpm\":null}";
  json += ",\"fogger\":{\"on_time_s\":null,\"off_time_s\":null}}";
  return json;
}
