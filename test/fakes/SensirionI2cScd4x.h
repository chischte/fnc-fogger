#pragma once
#include "Wire.h"
constexpr uint8_t SCD41_I2C_ADDR_62 = 0x62;
class SensirionI2cScd4x {
 public:
  void begin(TwoWire& bus, uint8_t) { bus_ = bus.index; }
  int16_t wakeUp() { return status(); }
  int16_t stopPeriodicMeasurement() {
    if (status()) return status();
    fakeScd.measuring = false;
    return 0;
  }
  int16_t getSerialNumber(uint64_t& serial) {
    serial = fakeScd.serial;
    return status();
  }
  int16_t setTemperatureOffset(float offset) {
    fakeScd.offset = offset;
    return status();
  }
  int16_t getTemperatureOffset(float& offset) {
    offset = fakeScd.offset;
    return status();
  }
  int16_t setSensorAltitude(uint16_t) { return status(); }
  int16_t setAutomaticSelfCalibrationEnabled(bool) { return status(); }
  int16_t startPeriodicMeasurement() {
    if (status()) return status();
    fakeScd.measuring = true;
    ++fakeScd.starts;
    return 0;
  }
  int16_t getDataReadyStatus(bool& ready) {
    ready = fakeScd.measuring;
    return status();
  }
  int16_t readMeasurement(uint16_t& co2, float& temperature, float& humidity) {
    if (fakeScd.requiresReinit) return 1;
    co2 = 800;
    temperature = 25;
    humidity = 90;
    return status();
  }
 private:
  int16_t status() const { return fakeScd.present && bus_ == fakeScd.bus ? 0 : 1; }
  int bus_ = 0;
};
