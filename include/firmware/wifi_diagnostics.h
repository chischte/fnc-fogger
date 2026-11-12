#pragma once

#include <atomic>
#include <stddef.h>
#include <stdint.h>

class WifiDiagnostics {
 public:
  void begin();
  void poll(uint32_t now);
  bool scanActive() const;

 private:
  enum class ScanState { idle, waiting, running };

  void readCommands(uint32_t now);
  void executeCommand(uint32_t now);
  void requestScan(uint32_t now);
  void pollScan(uint32_t now);
  void finishScan(int16_t count);
  void setPower(const char* value);
  void applyConfiguredPower(uint32_t now);
  void report(uint8_t status, uint8_t reason);

  // Wi-Fi events arrive on a different task; USB output stays on the main loop.
  std::atomic<uint8_t> disconnectReason_{0};
  uint8_t reportedStatus_ = 255;
  uint8_t reportedReason_ = 255;
  uint32_t lastReportAt_ = 0;
  char command_[32] = {};
  size_t commandLength_ = 0;
  bool commandOverflow_ = false;
  ScanState scanState_ = ScanState::idle;
  uint32_t scanRequestedAt_ = 0;
  bool configuredPowerApplied_ = false;
  uint32_t lastPowerAttemptAt_ = 0;
  bool originalAutoReconnect_ = false;
};
