#pragma once

#include <Arduino.h>

class NetworkDiscovery {
 public:
  void poll(bool connected, uint32_t now);

 private:
  bool started_ = false;
  bool attempted_ = false;
  uint32_t lastAttemptAt_ = 0;
};
