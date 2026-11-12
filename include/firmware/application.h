#pragma once

#include "firmware/firmware_updater.h"
#include "firmware/measurement_controller.h"
#include "firmware/qspi_storage.h"
#include "firmware/sensor_manager.h"
#include "firmware/web_server.h"
#if defined(CONFIG_IDF_TARGET_ESP32C3)
#include "firmware/startup_actuators.h"
#endif

class Application {
 public:
  Application();

  void begin();
  void poll();

 private:
  void beginSerial();

  QspiStorage storage_;
  SensorManager sensors_;
  FirmwareUpdater firmwareUpdater_;
  MeasurementController measurements_;
  ControlSettingsStore controlSettings_;
#if defined(CONFIG_IDF_TARGET_ESP32C3)
  StartupActuators actuators_;
  AutomaticControl automatic_;
#endif
  WebServer webServer_;
};
