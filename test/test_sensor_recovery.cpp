#define assert(condition) do { if (!(condition)) return __LINE__; } while (false)
#ifdef _WIN32
extern "C" { int _fltused = 0; }
#endif
#include "config.h"
#include "firmware/sensor_manager.h"

bool restartSensorBus() { return true; }

void finishInitialization(SensorManager& sensor, uint32_t started) {
  sensor.poll(started + Config::SCD_WAKE_DELAY_MS);
  sensor.poll(started + Config::SCD_WAKE_DELAY_MS + Config::SCD_STOP_DELAY_MS);
  sensor.poll(started + Config::SCD_WAKE_DELAY_MS + Config::SCD_STOP_DELAY_MS + 30);
}

int main() {
  {
    Shtc3Sensor ambient(Wire);
    ambient.begin(0);
    float temperature = NAN;
    float humidity = NAN;
    assert(!ambient.read(temperature, humidity, 0));
    fakeShtc3.present = true;
    ambient.poll(5000);
    assert(fakeShtc3.lastCommand == 0x3517);
    ambient.poll(5001);
    assert(fakeShtc3.lastCommand == 0x7866);
    ambient.poll(5013);
    assert(!ambient.read(temperature, humidity, 5013));
    ambient.poll(5014);
    assert(ambient.read(temperature, humidity, 5014));
    assert(temperature > 24.99f && temperature < 25.01f);
    assert(humidity == 50.0f);
    assert(fakeShtc3.lastCommand == 0xB098);
    fakeShtc3.corrupt = true;
    ambient.poll(10000);
    ambient.poll(10001);
    ambient.poll(10014);
    assert(!ambient.read(temperature, humidity, 10014));
    fakeShtc3.corrupt = false;
    fakeShtc3.shortResponse = true;
    ambient.poll(15000);
    ambient.poll(15001);
    ambient.poll(15014);
    assert(!ambient.read(temperature, humidity, 15014));
    fakeShtc3.shortResponse = false;
    fakeShtc3.present = false;
    ambient.poll(20000);
    assert(!ambient.read(temperature, humidity, 20000));
    fakeShtc3.present = true;
    ambient.poll(25000);
    ambient.poll(25001);
    ambient.poll(25014);
    assert(ambient.read(temperature, humidity, 25014));
    assert(!ambient.read(temperature, humidity, 35014));
    fakeShtc3 = FakeShtc3{};
  }
  SensorManager sensor;
  sensor.begin(0);
  finishInitialization(sensor, 0);
  assert(sensor.isReady());
  Measurement original;
  sensor.read(original, 6000);
  assert(original.co2Valid && original.scdSerialNumber == 1);

  // A quick swap can produce no I2C errors: the new sensor acknowledges in idle.
  fakeScd.serial = 2;
  fakeScd.measuring = false;
  Measurement missing;
  sensor.read(missing, 11000);
  assert(!missing.co2Valid);
  sensor.poll(6000 + Config::SCD_MEASUREMENT_TIMEOUT_MS - 1);
  assert(sensor.isReady());
  const uint32_t recovery = 6000 + Config::SCD_MEASUREMENT_TIMEOUT_MS;
  sensor.poll(recovery);
  assert(!sensor.isReady());
  finishInitialization(sensor, recovery);
  Measurement replacement;
  sensor.read(replacement, recovery + 6000);
  assert(replacement.co2Valid && replacement.scdSerialNumber == 2);
  assert(replacement.scdTemperatureOffset == Config::SCD41_TEMPERATURE_OFFSET_C);
  assert(fakeScd.starts == 2);

  // Recover a disconnected SCD41 on the same configured ESP32 I2C bus.
  fakeScd.present = false;
  uint32_t now = recovery + 11000;
  for (int i = 0; i < Config::SCD_MAX_CONSECUTIVE_ERRORS; ++i) {
    Measurement disconnected;
    sensor.read(disconnected, now);
    assert(!disconnected.co2Valid);
    now += 5000;
  }
  assert(!sensor.isReady());
  fakeScd.present = true;
  fakeScd.bus = 0;
  fakeScd.serial = 3;
  fakeScd.measuring = false;
  const uint32_t started = now - 5000;
  finishInitialization(sensor, started);
  Measurement reconnected;
  sensor.read(reconnected, now + 6000);
  assert(reconnected.co2Valid && reconnected.scdSerialNumber == 3);

  SensorManager combined;
  fakeSht = FakeSht{};
  fakeScd = FakeScdState{};
  combined.begin(0);
  finishInitialization(combined, 0);
  Measurement both;
  combined.read(both, 1000);
  assert(both.boxTemperatureValid && both.humidityValid);
  assert(both.boxTemperature > 24.9f && both.boxTemperature < 25.1f);
  assert(both.humidity > 93.9f && both.humidity < 94.1f);
  assert(both.scdHumidityValid && both.scdHumidity == 90);
  fakeSht.present = false;
  combined.poll(5000);
  Measurement held;
  combined.read(held, 5000);
  assert(held.humidityValid && held.humidity == both.humidity);
  assert(held.shtReadUptimeMs == both.shtReadUptimeMs);
  assert(held.co2Valid);
  // At the next scheduled SHT read, a failure replaces the held value.
  combined.poll(66000);
  Measurement disconnectedSht;
  combined.read(disconnectedSht, 66000);
  assert(!disconnectedSht.humidityValid);

  fakeSht = FakeSht{};
  Sht45Sensor raw;
  raw.begin(0);
  raw.poll(10);
  float rawTemperature = NAN;
  float rawHumidity = NAN;
  fakeSht.corrupt = true;
  raw.poll(5000);
  raw.poll(5010);
  assert(!raw.read(rawTemperature, rawHumidity, 5010));
  fakeSht.corrupt = false;
  fakeSht.shortResponse = true;
  raw.poll(10000);
  raw.poll(10010);
  assert(!raw.read(rawTemperature, rawHumidity, 10010));
  fakeSht.shortResponse = false;
  fakeSht.bus = 0;
  fakeSht.humidity = 65535;
  raw.poll(15000);
  raw.poll(15010);
  assert(raw.read(rawTemperature, rawHumidity, 15010) && rawHumidity == 100);
  assert(!raw.read(rawTemperature, rawHumidity, 25010));
  if (!Config::SHT45_HEATER_ENABLED) {
    fakeSht = FakeSht{};
    fakeScd = FakeScdState{};
    SensorManager unheated;
    unheated.begin(0);
    const uint32_t duration = 3 * Config::SHT45_READ_INTERVAL_MS;
    for (uint32_t time = 10; time <= duration; time += 10) {
      unheated.poll(time);
      if (time < 8000 || (time - 8000) % Config::MEASUREMENT_INTERVAL_MS != 0) continue;
      Measurement sample;
      unheated.read(sample, time);
      assert(sample.boxTemperatureValid && sample.humidityValid);
      assert(sample.humidityOffset == 0.0f);
      assert(sample.shtHeaterElapsedMs == -1);
      assert(!sample.shtHeated && !sample.shtCooling);
    }
    assert(fakeSht.heaterCommands == 0);
    return 0;
  }
  // Readout requests a heater pulse; no heated/early cooldown sample is published.
  fakeSht = FakeSht{};
  Sht45Sensor heater;
  heater.begin(0);
  heater.poll(10);
  float temperature = NAN;
  float humidity = NAN;
  const uint32_t interval = Config::SHT45_HEATER_INTERVAL_MS;
  assert(heater.read(temperature, humidity, 1000));
  for (uint32_t time = 5000; time < interval; time += 5000) {
    heater.poll(time);
    heater.poll(time + 10);
  }
  assert(fakeSht.heaterCommands == 0);
  assert(heater.read(temperature, humidity, interval));
  assert(heater.heaterElapsedMs() == -1);
  heater.poll(interval);
  assert(fakeSht.heaterCommands == 1);
  fakeSht.temperature = 48000;
  heater.poll(interval + 1110);
  assert(!heater.read(temperature, humidity, interval + 1110));
  heater.poll(interval + 61109);
  assert(fakeSht.lastCommand == 0x39);
  fakeSht.temperature = 26214;
  heater.poll(interval + 61110);
  assert(fakeSht.lastCommand == 0xFD);
  heater.poll(interval + 61120);
  assert(heater.read(temperature, humidity, 2 * interval));
  assert(heater.heaterElapsedMs() == 60010);
  assert(!heater.heatedReading() && !heater.coolingReading());
  heater.poll(2 * interval);
  assert(fakeSht.heaterCommands == 2);
  // Continuous operation also beyond the old six-pulse test limit.
  for (uint32_t cycle = 2; cycle <= 8; ++cycle) {
    const uint32_t started = cycle * interval;
    heater.poll(started + 1110);
    heater.poll(started + 61110);
    heater.poll(started + 61120);
    assert(heater.read(temperature, humidity, started + interval));
    heater.poll(started + interval);
  }
  assert(fakeSht.heaterCommands == 9);
  // CRC failures remain invalid and cannot immediately reheat the sensor.
  fakeSht.corrupt = true;
  heater.poll(9 * interval + 1110);
  assert(!heater.read(temperature, humidity, 9 * interval + 1110));
  heater.poll(9 * interval + 5000);
  assert(fakeSht.heaterCommands == 9);
  // Exercise the real acquisition cadence with both sensors and correction metadata.
  fakeSht = FakeSht{};
  fakeScd = FakeScdState{};
  SensorManager regular;
  regular.setHumidityOffsets(6.23f, 1.35f);
  regular.begin(0);
  uint32_t previousReadAt = 0;
  float previousHumidity = NAN;
  uint16_t shtUpdates = 0;
  uint16_t fastUpdates = 0;
  for (uint32_t time = 10; time <= 10 * interval; time += 10) {
    regular.poll(time);
    if (time < 8000 || (time - 8000) % Config::MEASUREMENT_INTERVAL_MS != 0) continue;
    Measurement sample;
    regular.read(sample, time);
    assert(sample.humidityValid && sample.boxTemperatureValid && sample.co2Valid);
    assert(!sample.shtHeated && !sample.shtCooling);
    ++fastUpdates;
    if (sample.shtReadUptimeMs != previousReadAt) {
      if (previousReadAt) assert(sample.shtReadUptimeMs - previousReadAt == interval);
      previousReadAt = sample.shtReadUptimeMs;
      previousHumidity = sample.humidity;
      ++shtUpdates;
    } else {
      assert(sample.humidity == previousHumidity);
    }
    if (sample.shtReadUptimeMs <= interval + 8000) {
      assert(sample.humidityOffset == 6.23f && sample.shtHeaterElapsedMs == -1);
    } else {
      assert(sample.humidityOffset == 6.23f);
      assert(sample.shtHeaterElapsedMs >= 60000 && sample.shtHeaterElapsedMs < 65000);
    }
    assert(sample.scdHumidityOffset == 1.35f);
  }
  assert(shtUpdates == 10 && fastUpdates > 120);

  // A delayed acquisition must keep the correction after the cooldown window.
  fakeSht = FakeSht{};
  fakeScd = FakeScdState{};
  SensorManager delayed;
  delayed.begin(0);
  const uint32_t firstReadAt = 8000;
  const uint32_t skippedReadAt = firstReadAt + 2 * interval;
  bool checkedDelayedOffset = false;
  for (uint32_t time = 10; time <= firstReadAt + 4 * interval; time += 10) {
    delayed.poll(time);
    if (time < firstReadAt ||
        (time - firstReadAt) % Config::MEASUREMENT_INTERVAL_MS != 0 ||
        time == skippedReadAt) continue;
    Measurement sample;
    delayed.read(sample, time);
    if (time >= skippedReadAt + Config::MEASUREMENT_INTERVAL_MS) {
      assert(sample.humidityValid);
      assert(sample.humidityOffset == Config::SHT45_HUMIDITY_OFFSET_RH);
    }
    if (sample.shtHeaterElapsedMs >= static_cast<int32_t>(interval)) {
      checkedDelayedOffset = true;
    }
  }
  assert(checkedDelayedOffset);
  fakeSht = FakeSht{};
  fakeScd = FakeScdState{};
  SensorManager restarting;
  restarting.begin(0);
  finishInitialization(restarting, 0);
  Measurement firstGood;
  restarting.read(firstGood, 6000);
  fakeSht.requiresReset = true;
  for (uint32_t time = 6010; time <= 71000; time += 10) {
    restarting.poll(time);
    if (time % 5000 == 0) { Measurement sample; restarting.read(sample, time); }
  }
  Measurement firstFailure;
  restarting.read(firstFailure, 71000);
  assert(!firstFailure.humidityValid && fakeSht.resets == 1);
  assert(restarting.diagnostics().sht45.outages == 1);
  for (uint32_t time = 71010; time <= 76000; time += 10) restarting.poll(time);
  Measurement recoveredSht;
  restarting.read(recoveredSht, 76000);
  assert(recoveredSht.humidityValid);
  assert(restarting.diagnostics().sht45.outages == 1 && !restarting.diagnostics().sht45.failed);
  assert(restarting.diagnostics().sht45.lastRecoveryMs == 76000);
  fakeScd.requiresReinit = true;
  uint32_t failedAt = 81000;
  for (int index = 0; index < Config::SCD_MAX_CONSECUTIVE_ERRORS; ++index) {
    Measurement failed;
    restarting.read(failed, failedAt);
    failedAt += 5000;
  }
  assert(restarting.diagnostics().co2.outages >= 1);
  const uint32_t outageCount = restarting.diagnostics().co2.outages;
  assert(restarting.diagnostics().co2.restarts >= 1);
  finishInitialization(restarting, failedAt - 5000);
  Measurement recoveredCo2;
  restarting.read(recoveredCo2, failedAt + 6000);
  assert(recoveredCo2.co2Valid && !fakeScd.requiresReinit);
  assert(restarting.diagnostics().co2.outages == outageCount && !restarting.diagnostics().co2.failed);
  SensorFailure episode;
  episode.observe(false, 1);
  episode.observe(false, 2);
  assert(episode.outages == 1);
  episode.observe(true, 3);
  episode.observe(false, 4);
  assert(episode.outages == 2 && episode.lastFailureMs == 4 && episode.lastRecoveryMs == 3);
  return 0;
}
