#pragma once

#include <Arduino.h>
#include <SensirionI2cScd4x.h>
#include <Wire.h>

#include "firmware/measurement.h"
#include "firmware/sensor_diagnostics.h"
#include "firmware/sht45_sensor.h"
#include "firmware/shtc3_sensor.h"

class SensorManager {
 public:
  void begin(uint32_t now);
  void poll(uint32_t now);
  void read(Measurement& measurement, uint32_t now);
  void setHumidityOffsets(float sht, float scd) { shtOffset_ = sht; scdOffset_ = scd; }

  bool isReady() const;
  uint16_t errorCount() const;
  const SensorDiagnostics& diagnostics() const { return diagnostics_; }

 private:
  enum class InitializationState {
    idle,
    waitingAfterWake,
    waitingAfterStop,
    waitingAfterReinit,
  };

  void startInitialization(uint32_t now, bool recovery = true);
  void restartSht(uint32_t now);
  void recoverBus(uint32_t now);
  void continueInitialization(uint32_t now);
  void finishInitialization(uint32_t now);
  void scheduleRetry(uint32_t now);
  void readSht(Measurement& measurement, uint32_t now);
  void readScd(Measurement& measurement, uint32_t now);
  void recordScdError(const char* operation, int16_t error, uint32_t now);

  struct ShtReading {
    float temperature = NAN;
    float humidity = NAN;
    int32_t heaterElapsedMs = -1;
    uint32_t readAt = 0;
    bool valid = false;
  };
  SensorDiagnostics diagnostics_;
  uint32_t lastShtRestartAt_ = 0;
  uint32_t lastBusRestartAt_ = 0;
  bool shtRecovering_ = false;
  bool busRestarted_ = false;
  ShtReading shtReading_;
  Sht45Sensor sht45_;
  Shtc3Sensor shtc3_{Wire};
  SensirionI2cScd4x scd4x_;
  InitializationState initializationState_ = InitializationState::idle;
  uint32_t stateStartedAt_ = 0;
  uint32_t lastInitializationAt_ = 0;
  uint32_t lastScdMeasurementAt_ = 0;
  uint64_t scdSerialNumber_ = 0;
  uint16_t errorCount_ = 0;
  bool ready_ = false;
  float scdTemperatureOffset_ = NAN;
  float shtOffset_ = 1;
  float scdOffset_ = 0;
};
