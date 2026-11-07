#pragma once

#include "firmware/control_settings.h"

class ControlSettingsStore {
 public:
  void begin();
  bool save(const ControlSettings& settings);
  const ControlSettings& settings() const { return settings_; }
  bool available() const { return available_; }
  bool persisted() const { return persisted_; }

 private:
  ControlSettings settings_;
  bool available_ = false;
  bool persisted_ = false;
};
