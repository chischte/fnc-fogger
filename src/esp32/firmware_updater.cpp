#include "firmware/firmware_updater.h"

#include <Update.h>
#include "firmware/identity.h"

FirmwareUpdater::FirmwareUpdater(QspiStorage&) {}

bool FirmwareUpdater::beginUpload() {
  cancelUpload();
  writtenBytes_ = 0;
  expectedFileSize_ = 0;
  profileMatchBytes_ = 0;
  profileMatched_ = false;
  uploadFailed_ = !Update.begin(UPDATE_SIZE_UNKNOWN);
  return !uploadFailed_;
}

bool FirmwareUpdater::write(const uint8_t* data, size_t length) {
  if (uploadFailed_ || !expectedFileSize_) {
    return false;
  }
  const size_t count = min(length, expectedFileSize_ - writtenBytes_);
  for (size_t index = 0; index < count && !profileMatched_; ++index) {
    const char value = static_cast<char>(data[index]);
    if (value == FirmwareIdentity::PROFILE_MARKER[profileMatchBytes_]) {
      ++profileMatchBytes_;
      profileMatched_ = profileMatchBytes_ == sizeof(FirmwareIdentity::PROFILE_MARKER) - 1;
    } else {
      profileMatchBytes_ = value == FirmwareIdentity::PROFILE_MARKER[0] ? 1 : 0;
    }
  }
  if (count && Update.write(const_cast<uint8_t*>(data), count) != count) {
    uploadFailed_ = true;
    return false;
  }
  writtenBytes_ += count;
  return true;
}

FirmwareUpdateResult FirmwareUpdater::finishAndInstall() {
  if (uploadFailed_ || !expectedFileSize_ || writtenBytes_ != expectedFileSize_) {
    cancelUpload();
    return {400, "Incomplete or invalid firmware upload.", false};
  }
  if (!profileMatched_) {
    cancelUpload();
    return {422, "Firmware hardware profile missing or incompatible.", false};
  }
  if (!Update.end(true)) {
    return {422, "Firmware verification failed: " + String(Update.errorString()), false};
  }
  return {200, "Firmware verified; restarting.", true};
}

void FirmwareUpdater::cancelUpload() {
  if (Update.isRunning()) {
    Update.abort();
  }
}

void FirmwareUpdater::restart() {
  delay(500);
  ESP.restart();
}
