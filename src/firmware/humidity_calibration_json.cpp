#include "firmware/humidity_calibration.h"
#include <Arduino.h>

String HumidityCalibration::json(uint32_t now) const {
  String json = "{\"supported\":true,\"assumed_reference_rh\":100,\"revision\":" + String(reference_.revision);
  json += ",\"running\":" + String(running_ ? "true" : "false");
  json += ",\"remaining_ms\":" + String(remaining(now));
  json += ",\"status\":\"" + String(status_) + "\"";
  json += ",\"running_calibration_enabled\":true";
  json += ",\"running_calibration_pending\":" + String(pendingSave_ ? "true" : "false");
  json += ",\"running_calibration_save_failed\":" + String(saveFailed_ ? "true" : "false");
  json += ",\"reference_kind\":\"";
  json += reference_.kind == HumidityReferenceKind::runningCalibration ? "running_calibration" : "assumed_saturation";
  json += "\"";
  json += ",\"sht_raw_rh\":" + String(reference_.shtRaw, 2);
  json += ",\"scd_raw_rh\":" + String(reference_.scdRaw, 2);
  json += ",\"sht_offset_rh\":" + String(reference_.shtOffset, 2);
  json += ",\"scd_offset_rh\":" + String(reference_.scdOffset, 2);
  json += ",\"duration_ms\":" + String(reference_.durationMs) + "}";
  return json;
}
