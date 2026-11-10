#pragma once

#include <Arduino.h>

#include "firmware/control_settings_store.h"
#include "firmware/startup_test.h"
#include "firmware/manual_control.h"

bool parseControlSettings(const String& body, ControlSettings& settings);
bool parseManualSettings(const String& body, bool& active, uint8_t& fan, uint8_t& fogger, bool& renew);
String buildControlJson(const ControlSettingsStore& store, const ActuatorStatus* actuators = nullptr, const ManualControl* manual = nullptr);
