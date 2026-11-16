#pragma once

#include <Arduino.h>

#include "firmware/control_settings_store.h"
#include "firmware/sensor_diagnostics.h"
#include "firmware/startup_test.h"
#include "firmware/manual_control.h"
#include "firmware/automatic_control.h"
#include "firmware/humidity_calibration.h"

bool parsePiMemory(const String& body, PiMemory& memory);
bool parseCyclicMistSettings(const String& body, CyclicMistSettings& settings);
bool parseUnixSeconds(const String& text, uint32_t& result);
bool parseControlSettings(const String& body, ControlSettings& settings);
bool parseHumidityReference(const String& body, float& sht, float& scd);
bool parseManualSettings(const String& body, bool& active, uint8_t& fan, uint8_t& fogger, bool& renew);
String buildControlJson(const ControlSettingsStore& store, const ActuatorStatus* actuators = nullptr,
                        const ManualControl* manual = nullptr, const AutomaticControl* automatic = nullptr,
                        const HumidityCalibration* calibration = nullptr,
                        const SensorDiagnostics* diagnostics = nullptr);
