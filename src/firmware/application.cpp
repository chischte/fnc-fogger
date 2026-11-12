#include "firmware/application.h"

#include <Arduino.h>
#include "firmware/esp32_hardware.h"

#include "firmware/time_utils.h"

namespace {
constexpr uint32_t SERIAL_BAUD_RATE = 115200;
constexpr uint32_t SERIAL_WAIT_TIMEOUT_MS = 2000;
constexpr uint32_t SERIAL_POLL_INTERVAL_MS = 10;
}  // namespace

Application::Application()
    : firmwareUpdater_(storage_),
      measurements_(sensors_, storage_),
      webServer_(measurements_, storage_, firmwareUpdater_, controlSettings_
#if defined(CONFIG_IDF_TARGET_ESP32C3)
                 , &actuators_.status(), &actuators_.manualControl(), &automatic_
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
  sensors_.begin(now);
  measurements_.begin(now);
  controlSettings_.begin();
  webServer_.begin(now);
}

void Application::poll() {
  const uint32_t now = millis();
  measurements_.poll(now);
  webServer_.poll(now);
#if defined(CONFIG_IDF_TARGET_ESP32C3)
  const uint32_t controlNow = millis();
  const bool networkAvailable = webServer_.manualNetworkAvailable();
  const bool maintenance = webServer_.firmwareUpdateInProgress();
  const Measurement& measurement = measurements_.current();
  const ActuatorStatus& status = actuators_.status();
  ControlInput input;
  input.co2At = measurement.uptimeMs;
  input.humidityAt = measurement.shtReadUptimeMs;
  input.co2 = measurement.co2;
  input.humidity = min(100.0f, measurement.humidity + measurement.humidityOffset);
  input.scdHumidity = measurement.scdHumidity;
  input.co2Valid = measurement.co2Valid;
  input.humidityValid = measurement.humidityValid;
  input.scdHumidityValid = measurement.scdHumidityValid;
  input.hardwareReady = status.hardwareReady;
  input.rpmValid = status.rpmValid;
  input.rpm = status.rpm;
  automatic_.poll(controlNow, input, controlSettings_.settings(), networkAvailable, maintenance);
  actuators_.poll(controlNow, maintenance, networkAvailable, &automatic_);
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
