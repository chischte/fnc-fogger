#pragma once

#include <Arduino.h>

#include "firmware/control_settings_store.h"

bool parseControlSettings(const String& body, ControlSettings& settings);
String buildControlJson(const ControlSettingsStore& store);
