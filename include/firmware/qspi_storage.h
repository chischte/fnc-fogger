#pragma once

#include <Arduino.h>
#include <cstdio>

#include "firmware/measurement.h"

class BacklogReader {
 public:
  bool begin(bool storageReady, bool currentOnly = false);
  size_t read(uint8_t* buffer, size_t capacity);
  bool isFinished() const;
  void close();

 private:
  bool openNextFile();

  FILE* file_ = nullptr;
  uint8_t nextFileIndex_ = 0;
  bool finished_ = true;
};

class QspiStorage {
 public:
  void begin();
  uint32_t nextBootId();
  void append(const Measurement& measurement, uint32_t bootId);

  bool isDataReady() const;
  bool isOtaReady() const;

 private:
  void rotateLogIfNeeded();

  bool dataReady_ = false;
  bool otaReady_ = false;
};
