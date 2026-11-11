#pragma once

#include <Arduino.h>
#include "firmware/qspi_storage.h"

struct FirmwareUpdateResult {
  uint16_t httpStatus;
  String message;
  bool restartRequired;
};

class FirmwareUpdater {
 public:
  explicit FirmwareUpdater(QspiStorage& storage);
  bool beginUpload();
  void setExpectedSize(size_t size) { expectedFileSize_ = size; }
  bool write(const uint8_t* data, size_t length);
  FirmwareUpdateResult finishAndInstall();
  void cancelUpload();
  void restart();

 private:
  size_t expectedFileSize_ = 0;
  size_t writtenBytes_ = 0;
  bool uploadFailed_ = false;
  size_t profileMatchBytes_ = 0;
  bool profileMatched_ = false;
};
