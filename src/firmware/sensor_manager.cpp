#include "firmware/sensor_manager.h"

#include <SensirionErrors.h>

#include "config.h"
#include "firmware/esp32_hardware.h"
#include "firmware/time_utils.h"

namespace {
constexpr uint32_t RESTART_INTERVAL_MS = 30000;
constexpr uint32_t SCD_REINIT_MS = 30;
constexpr uint8_t SCD_ADDRESS = 0x62;
constexpr uint16_t SCD_STOP = 0x3F86;
constexpr uint16_t SCD_REINIT = 0x3646;

bool sendScdCommand(uint16_t command) {
  Wire.beginTransmission(SCD_ADDRESS);
  Wire.write(static_cast<uint8_t>(command >> 8));
  Wire.write(static_cast<uint8_t>(command));
  return Wire.endTransmission() == 0;
}

void printScdError(const char* operation, int16_t error) {
  char message[96];
  errorToString(error, message, sizeof(message));
  Serial.print(operation);
  Serial.print(": ");
  Serial.println(message);
}
}  // namespace

void SensorManager::begin(uint32_t now) {
  sht45_.begin(now);
  shtc3_.begin(now);
  shtReading_.readAt = now - Config::SHT45_READ_INTERVAL_MS;
  startInitialization(now, false);
}

void SensorManager::poll(uint32_t now) {
  sht45_.poll(now);
  diagnostics_.heaterActive = sht45_.heaterActive();
  if (sht45_.lastHeaterStartMs()) diagnostics_.lastHeaterStartMs = sht45_.lastHeaterStartMs();
  shtc3_.poll(now);
  if (ready_) {
    // A replacement can acknowledge I2C while still being in idle mode.
    if (hasElapsed(now, lastScdMeasurementAt_,
                   Config::SCD_MEASUREMENT_TIMEOUT_MS)) {
      Serial.println("SCD4x measurement timeout; searching again");
      startInitialization(now);
    }
    return;
  }
  if (initializationState_ != InitializationState::idle) {
    continueInitialization(now);
    return;
  }
  if (hasElapsed(now, lastInitializationAt_,
                 Config::SENSOR_RETRY_INTERVAL_MS)) {
    startInitialization(now);
  }
}

void SensorManager::read(Measurement& measurement, uint32_t now) {
  readScd(measurement, now);
  readSht(measurement, now);
  const bool ambientValid = shtc3_.read(measurement.ambientTemperature,
                                       measurement.ambientHumidity, now);
  measurement.ambientTemperatureValid = ambientValid;
  measurement.ambientHumidityValid = ambientValid;
}

void SensorManager::readSht(Measurement& measurement, uint32_t now) {
  const uint32_t interval = shtRecovering_ ? Config::SENSOR_RETRY_INTERVAL_MS : Config::SHT45_READ_INTERVAL_MS;
  if (hasElapsed(now, shtReading_.readAt, interval)) {
    shtReading_.readAt = now;
    shtReading_.valid = sht45_.read(shtReading_.temperature, shtReading_.humidity, now);
    shtReading_.heaterElapsedMs = shtReading_.valid ? sht45_.heaterElapsedMs() : -1;
    diagnostics_.sht45.observe(shtReading_.valid, now);
    if (shtReading_.valid) shtRecovering_ = false;
    else if (!shtRecovering_ || hasElapsed(now, lastShtRestartAt_, RESTART_INTERVAL_MS)) restartSht(now);
  }
  // Keep the last scheduled reading during heating; preserve its original timestamp.
  measurement.shtReadUptimeMs = shtReading_.readAt;
  measurement.boxTemperature = shtReading_.temperature;
  measurement.humidity = shtReading_.humidity;
  measurement.boxTemperatureValid = shtReading_.valid;
  measurement.humidityValid = shtReading_.valid;
  // Valid SHT45 readings already exclude heating/cooldown. A reference offset
  // applies to every valid reading, including readings before the first heater cycle.
  measurement.humidityOffset = shtOffset_;
  measurement.scdHumidityOffset = scdOffset_;
  measurement.shtHeaterElapsedMs = shtReading_.heaterElapsedMs;
}

bool SensorManager::isReady() const {
  return ready_;
}

uint16_t SensorManager::errorCount() const {
  return errorCount_;
}

void SensorManager::restartSht(uint32_t now) {
  ++diagnostics_.sht45.restarts;
  lastShtRestartAt_ = now;
  shtRecovering_ = true;
  sht45_.restart(now);
}

void SensorManager::recoverBus(uint32_t now) {
  if (busRestarted_ && !hasElapsed(now, lastBusRestartAt_, RESTART_INTERVAL_MS)) return;
  busRestarted_ = true;
  lastBusRestartAt_ = now;
  ++diagnostics_.busRestarts;
  restartSensorBus();
  restartSht(now);
  shtc3_.begin(now);
  shtReading_.valid = false;
}

void SensorManager::startInitialization(uint32_t now, bool recovery) {
  if (recovery) {
    diagnostics_.co2.observe(false, now);
    ++diagnostics_.co2.restarts;
    recoverBus(now);
  }
  ready_ = false;
  scdTemperatureOffset_ = NAN;
  scdSerialNumber_ = 0;

  Wire.setClock(Config::I2C_CLOCK_HZ);
  scd4x_.begin(Wire, SCD41_I2C_ADDR_62);
  scd4x_.wakeUp();
  stateStartedAt_ = now;
  initializationState_ = InitializationState::waitingAfterWake;
}

void SensorManager::continueInitialization(uint32_t now) {
  if (initializationState_ == InitializationState::waitingAfterWake &&
      hasElapsed(now, stateStartedAt_, Config::SCD_WAKE_DELAY_MS)) {
    sendScdCommand(SCD_STOP);
    stateStartedAt_ = now;
    initializationState_ = InitializationState::waitingAfterStop;
    return;
  }
  if (initializationState_ == InitializationState::waitingAfterStop &&
      hasElapsed(now, stateStartedAt_, Config::SCD_STOP_DELAY_MS)) {
    if (!sendScdCommand(SCD_REINIT)) { scheduleRetry(now); return; }
    stateStartedAt_ = now;
    initializationState_ = InitializationState::waitingAfterReinit;
    return;
  }
  if (initializationState_ == InitializationState::waitingAfterReinit &&
      hasElapsed(now, stateStartedAt_, SCD_REINIT_MS)) {
    finishInitialization(now);
  }
}

void SensorManager::finishInitialization(uint32_t now) {
  uint64_t serialNumber = 0;
  if (scd4x_.getSerialNumber(serialNumber)) {
    scheduleRetry(now);
    return;
  }

  int16_t error = scd4x_.setTemperatureOffset(
      Config::SCD41_TEMPERATURE_OFFSET_C);
  if (error) {
    printScdError("offset", error);
    scheduleRetry(now);
    return;
  }
  error = scd4x_.getTemperatureOffset(scdTemperatureOffset_);
  if (error) {
    printScdError("read offset", error);
    scheduleRetry(now);
    return;
  }
  error = scd4x_.setSensorAltitude(Config::SCD41_ALTITUDE_M);
  if (error) {
    printScdError("altitude", error);
  }
  error = scd4x_.setAutomaticSelfCalibrationEnabled(
      Config::SCD41_ASC_ENABLED);
  if (error) {
    printScdError("ASC", error);
  }
  if (scd4x_.startPeriodicMeasurement()) {
    scheduleRetry(now);
    return;
  }

  ready_ = true;
  lastScdMeasurementAt_ = now;
  scdSerialNumber_ = serialNumber;
  errorCount_ = 0;
  initializationState_ = InitializationState::idle;
  Serial.println("SCD4x: Wire");
}

void SensorManager::scheduleRetry(uint32_t now) {
  initializationState_ = InitializationState::idle;
  lastInitializationAt_ = now;
  Serial.println("SCD4x unavailable; retry scheduled");
}

void SensorManager::readScd(Measurement& measurement, uint32_t now) {
  if (!ready_) {
    return;
  }

  bool dataReady = false;
  int16_t error = scd4x_.getDataReadyStatus(dataReady);
  if (!error && dataReady) {
    error = scd4x_.readMeasurement(measurement.co2, measurement.scdTemperature,
                                   measurement.scdHumidity);
  }
  if (error) {
    recordScdError("read", error, now);
    return;
  }
  if (!dataReady || !measurement.co2) {
    return;
  }

  measurement.co2Valid = true;
  diagnostics_.co2.observe(true, now);
  lastScdMeasurementAt_ = now;
  measurement.scdSerialNumber = scdSerialNumber_;
  measurement.scdTemperatureOffset = scdTemperatureOffset_;
  measurement.scdHumidityValid = isfinite(measurement.scdHumidity) &&
      measurement.scdHumidity >= Config::HUMIDITY_MIN_RH &&
      measurement.scdHumidity <= Config::HUMIDITY_MAX_RH;
  errorCount_ = 0;
}

void SensorManager::recordScdError(const char* operation, int16_t error,
                                   uint32_t now) {
  diagnostics_.co2.observe(false, now);
  printScdError(operation, error);
  ++errorCount_;
  if (errorCount_ < Config::SCD_MAX_CONSECUTIVE_ERRORS) {
    return;
  }
  startInitialization(now);
}
