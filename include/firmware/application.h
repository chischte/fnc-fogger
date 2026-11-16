#pragma once

#include "firmware/firmware_updater.h"
#include "firmware/measurement_controller.h"
#include "firmware/qspi_storage.h"
#include "firmware/sensor_manager.h"
#include "firmware/web_server.h"
#if defined(CONFIG_IDF_TARGET_ESP32C3)
#include "firmware/startup_actuators.h"
#include "firmware/cyclic_mist_clock.h"
#endif

class Application {
 public:
  Application();

  void begin();
  void poll();

 private:
  void beginSerial();
  void checkpointPi(uint32_t now, bool force);
  void pollCalibration(uint32_t now, bool networkAvailable, bool maintenance);

  QspiStorage storage_;
  SensorManager sensors_;
  FirmwareUpdater firmwareUpdater_;
  MeasurementController measurements_;
  ControlSettingsStore controlSettings_;
  HumidityCalibration calibration_;
#if defined(CONFIG_IDF_TARGET_ESP32C3)
  StartupActuators actuators_;
  AutomaticControl automatic_;
  CyclicMistClock cyclicMistClock_;
  uint32_t lastPiSaveAt_ = 0;
  uint32_t lastPiSaveAttemptAt_ = 0;
  uint32_t savedPiRevision_ = 0;
#endif
  WebServer webServer_;
};
