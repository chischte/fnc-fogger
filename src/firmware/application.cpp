#include "firmware/application.h"

#include <Arduino.h>
#include "firmware/esp32_hardware.h"

#include "firmware/time_utils.h"
#include "firmware/cyclic_mist_store.h"

namespace {
constexpr uint32_t PI_CHECKPOINT_MS = 30000;
constexpr uint32_t PI_SAVE_RETRY_MS = 1000;
constexpr uint32_t SERIAL_BAUD_RATE = 115200;
constexpr uint32_t SERIAL_WAIT_TIMEOUT_MS = 2000;
constexpr uint32_t SERIAL_POLL_INTERVAL_MS = 10;
}  // namespace

Application::Application()
    : firmwareUpdater_(storage_),
      measurements_(sensors_, storage_),
      webServer_(measurements_, storage_, firmwareUpdater_, controlSettings_
#if defined(CONFIG_IDF_TARGET_ESP32C3)
                 , &actuators_.status(), &actuators_.manualControl(), &automatic_, &calibration_
#endif
                 ) {}

void Application::begin() {
#if defined(CONFIG_IDF_TARGET_ESP32C3)
  actuators_.begin(millis());
#endif
  beginSerial();
  storage_.begin();
  beginEsp32Hardware();
  const uint32_t now = millis();
  calibration_.begin();
  sensors_.setHumidityOffsets(calibration_.reference().shtOffset, calibration_.reference().scdOffset);
  sensors_.begin(now);
  measurements_.begin(now);
  controlSettings_.begin();
#if defined(CONFIG_IDF_TARGET_ESP32C3)
  PiMemory memory;
  if (loadPiMemory(memory)) {
    automatic_.restoreMemory(memory);
    automatic_.setMemorySaved(true);
  }
  lastPiSaveAttemptAt_ = now - PI_SAVE_RETRY_MS;
  CyclicMistSettings cyclic;
  if (loadCyclicMistSettings(cyclic)) automatic_.restoreCyclicMist(cyclic, now);
  cyclicMistClock_.begin(automatic_);
#endif
  webServer_.begin(now);
}

void Application::poll() {
  const uint32_t now = millis();
  sensors_.setHumidityOffsets(calibration_.reference().shtOffset, calibration_.reference().scdOffset);
  measurements_.poll(now);
  webServer_.poll(now);
#if defined(CONFIG_IDF_TARGET_ESP32C3)
  const uint32_t controlNow = millis();
  const bool networkAvailable = webServer_.manualNetworkAvailable();
  const bool maintenance = webServer_.firmwareUpdateInProgress();
  pollCalibration(controlNow, networkAvailable, maintenance);
  pollRunningCalibration(controlNow, maintenance);
  const Measurement& measurement = measurements_.current();
  const ActuatorStatus& status = actuators_.status();
  ControlInput input;
  input.co2At = measurement.uptimeMs;
  input.humidityAt = measurement.shtReadUptimeMs;
  input.co2 = measurement.co2;
  input.humidity = min(100.0f, measurement.humidity + calibration_.reference().shtOffset);
  input.scdHumidity = measurement.scdHumidity;
  input.co2Valid = measurement.co2Valid;
  input.humidityValid = measurement.humidityValid;
  input.scdHumidityValid = measurement.scdHumidityValid;
  input.hardwareReady = status.hardwareReady;
  input.rpmValid = status.rpmValid;
  input.rpm = status.rpm;
  automatic_.resumeIfIdle(controlNow, input, actuators_.manualControl().active(),
                          networkAvailable, maintenance);
  automatic_.poll(controlNow, input, controlSettings_.settings(), networkAvailable, maintenance);
  cyclicMistClock_.poll(automatic_, controlNow);
  actuators_.poll(controlNow, maintenance, networkAvailable, &automatic_);
  checkpointPi(controlNow, maintenance);
#endif
}

void Application::checkpointPi(uint32_t now, bool force) {
#if defined(CONFIG_IDF_TARGET_ESP32C3)
  const uint32_t revision = automatic_.memoryRevision();
  if (!force && revision == savedPiRevision_ && !hasElapsed(now, lastPiSaveAt_, PI_CHECKPOINT_MS)) return;
  if (!hasElapsed(now, lastPiSaveAttemptAt_, PI_SAVE_RETRY_MS)) return;
  lastPiSaveAttemptAt_ = now;
  const bool saved = savePiMemory(automatic_.memory());
  automatic_.setMemorySaved(saved);
  if (!saved) {
    Serial.println("PI memory could not be saved; retry pending");
    return;
  }
  lastPiSaveAt_ = now;
  savedPiRevision_ = revision;
#endif
}

void Application::pollRunningCalibration(uint32_t now, bool maintenance) {
#if defined(CONFIG_IDF_TARGET_ESP32C3)
  if (maintenance) {
    calibration_.checkpointRunning(now, true);
    return;
  }
  const Measurement& sample = measurements_.current();
  const bool shtValid = sample.humidityValid && !sample.shtHeated && !sample.shtCooling &&
      now - sample.shtReadUptimeMs < AutomaticLimits::HUMIDITY_MAX_AGE_MS;
  const bool scdValid = sample.scdHumidityValid &&
      now - sample.uptimeMs < AutomaticLimits::CO2_MAX_AGE_MS;
  if (calibration_.runningCalibration(now, sample.humidity, shtValid, sample.scdHumidity, scdValid)) {
    sensors_.setHumidityOffsets(calibration_.reference().shtOffset, calibration_.reference().scdOffset);
    automatic_.refreshMeasurements();
  }
#endif
}

void Application::pollCalibration(uint32_t now, bool networkAvailable, bool maintenance) {
#if defined(CONFIG_IDF_TARGET_ESP32C3)
  if (!calibration_.running()) return;
  ManualControl& manual = actuators_.manualControl();
  if (!networkAvailable || maintenance || !manual.active() ||
      manual.fanPercent() != 50 || manual.foggerPercent() != 100) {
    calibration_.cancel("interrupted");
    manual.stop();
    return;
  }
  if (!calibration_.due(now)) return;
  const Measurement& sample = measurements_.current();
  const bool valid = sample.humidityValid && sample.scdHumidityValid &&
      now - sample.shtReadUptimeMs < AutomaticLimits::HUMIDITY_MAX_AGE_MS &&
      now - sample.uptimeMs < AutomaticLimits::CO2_MAX_AGE_MS;
  if (!valid || !calibration_.capture(sample.humidity, sample.scdHumidity,
                                     HumidityCalibration::DURATION_MS)) {
    calibration_.cancel("failed");
  }
  manual.stop();
  automatic_.setEnabled(true, now);
#endif
}

void Application::beginSerial() {
  Serial.begin(SERIAL_BAUD_RATE);
  const uint32_t startedAt = millis();
  while (!Serial &&
         !hasElapsed(millis(), startedAt, SERIAL_WAIT_TIMEOUT_MS)) {
    delay(SERIAL_POLL_INTERVAL_MS);
  }
}
