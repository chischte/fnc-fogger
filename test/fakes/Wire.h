#pragma once
#include <stdint.h>
struct FakeScdState {
  bool present = true;
  bool measuring = false;
  int bus = 0;
  int starts = 0;
  bool requiresReinit = false;
  uint64_t serial = 1;
  float offset = 0;
};
inline FakeScdState fakeScd;

struct FakeSht {
  bool present = true;
  int bus = 0;
  uint8_t lastCommand = 0;
  int heaterCommands = 0;
  int resets = 0;
  bool requiresReset = false;
  bool corrupt = false;
  bool shortResponse = false;
  uint16_t temperature = 26214;
  uint16_t humidity = 52428;
};
inline FakeSht fakeSht;
struct FakeShtc3 {
  bool present = false;
  bool corrupt = false;
  bool shortResponse = false;
  uint16_t temperature = 26214;
  uint16_t humidity = 32768;
  uint16_t lastCommand = 0;
  uint32_t measurementCommands = 0;
};
inline FakeShtc3 fakeShtc3;
struct TwoWire {
  int index;
  int cursor = 0;
  void begin() {}
  void setClock(uint32_t) {}
  uint8_t address = 0;
  uint16_t command = 0;
  void beginTransmission(uint8_t value) { address = value; command = 0; }
  void write(uint8_t value) { command = (command << 8) | value; }
  int endTransmission() {
    if (address == 0x62) {
      if (!fakeScd.present || fakeScd.bus != index) return 1;
      if (command == 0x3F86) fakeScd.measuring = false;
      if (command == 0x3646) fakeScd.requiresReinit = false;
      return 0;
    }
    if (address == 0x70) {
      fakeShtc3.lastCommand = command;
      if (command == 0x7866) ++fakeShtc3.measurementCommands;
      return fakeShtc3.present ? 0 : 1;
    }
    if (!fakeSht.present || fakeSht.bus != index) return 1;
    fakeSht.lastCommand = command;
    if (command == 0x39) ++fakeSht.heaterCommands;
    if (command == 0x94) { ++fakeSht.resets; fakeSht.requiresReset = false; }
    if (fakeSht.requiresReset) return 1;
    return 0;
  }
  uint8_t requestFrom(uint8_t value, uint8_t) {
    address = value;
    cursor = 0;
    if (address == 0x70) return fakeShtc3.present && !fakeShtc3.shortResponse ? 6 : 0;
    return fakeSht.present && !fakeSht.shortResponse ? 6 : 0;
  }
  int read() {
    const int position = cursor++;
    const bool ambient = address == 0x70;
    const uint16_t word = ambient
        ? (position < 3 ? fakeShtc3.temperature : fakeShtc3.humidity)
        : (position < 3 ? fakeSht.temperature : fakeSht.humidity);
    if (position % 3 == 0) return word >> 8;
    if (position % 3 == 1) return word & 0xFF;
    uint8_t crc = 0xFF;
    for (int i = 0; i < 2; ++i) {
      crc ^= i == 0 ? word >> 8 : word & 0xFF;
      for (int bit = 0; bit < 8; ++bit) {
        crc = crc & 0x80 ? (crc << 1) ^ 0x31 : crc << 1;
      }
    }
    return (ambient ? fakeShtc3.corrupt : fakeSht.corrupt) ? crc ^ 1 : crc;
  }
};
inline TwoWire Wire{0};
