#pragma once

#include <Arduino.h>

class I2cDiagnostics {
 public:
  static constexpr uint8_t FIRST_ADDRESS = 0x08;
  static constexpr uint8_t LAST_ADDRESS = 0x77;

  void start();
  void poll(uint32_t now);
  bool started() const { return started_; }
  bool running() const { return running_; }
  bool complete() const { return started_ && !running_; }
  uint8_t status(uint8_t address) const { return statuses_[address - FIRST_ADDRESS]; }

 private:
  uint8_t statuses_[LAST_ADDRESS - FIRST_ADDRESS + 1] = {};
  uint8_t nextAddress_ = FIRST_ADDRESS;
  uint32_t lastProbeAt_ = 0;
  bool started_ = false;
  bool running_ = false;
};
