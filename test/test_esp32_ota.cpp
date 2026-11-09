#include <Update.h>
#include "firmware/firmware_updater.h"
#define assert(condition) do { if (!(condition)) return __LINE__; } while (false)
int main() {
  QspiStorage storage;
  FirmwareUpdater updater(storage);
  static const char image[] = "\xE9" "FNC_FW|esp32s3|3.2.0-esp32s3|0123456789ab|END";
  const auto* payload = reinterpret_cast<const uint8_t*>(image);
  const size_t imageSize = sizeof(image) - 1;

  // Multipart trailers must never reach the flash writer, even across chunks.
  assert(updater.beginUpload());
  updater.setExpectedSize(imageSize);
  assert(updater.write(payload, 10));
  assert(updater.write(payload + 10, sizeof(image) - 10));
  assert(updater.write(payload, 2));
  assert(Update.bytes == imageSize);
  auto result = updater.finishAndInstall();
  assert(result.httpStatus == 200 && result.restartRequired && Update.installed);

  assert(updater.beginUpload());
  updater.setExpectedSize(8);
  assert(updater.write(payload, 3));
  result = updater.finishAndInstall();
  assert(result.httpStatus == 400 && !result.restartRequired && !Update.installed);
  assert(!Update.running);

  assert(updater.beginUpload());
  updater.setExpectedSize(8);
  Update.rejectWrite = true;
  assert(!updater.write(payload, 8));
  result = updater.finishAndInstall();
  assert(!result.restartRequired && !Update.running);
  Update.rejectWrite = false;

  assert(updater.beginUpload());
  updater.setExpectedSize(imageSize);
  assert(updater.write(payload, imageSize));
  Update.rejectImage = true;
  result = updater.finishAndInstall();
  assert(result.httpStatus == 422 && !result.restartRequired && !Update.installed);
  Update.rejectImage = false;

  // The device also rejects incompatible images when bypassing the PC tool.
  static const char wrongImage[] = "\xE9" "FNC_FW|esp32c3_supermini|3.2.0|0123456789ab|END";
  assert(updater.beginUpload());
  updater.setExpectedSize(sizeof(wrongImage) - 1);
  assert(updater.write(reinterpret_cast<const uint8_t*>(wrongImage), sizeof(wrongImage) - 1));
  result = updater.finishAndInstall();
  assert(result.httpStatus == 422 && !result.restartRequired && !Update.installed);
  assert(!Update.running);

  assert(updater.beginUpload());
  updater.setExpectedSize(8);
  assert(updater.write(payload, 8));
  result = updater.finishAndInstall();
  assert(result.httpStatus == 422 && !result.restartRequired);

  assert(updater.beginUpload());
  updater.cancelUpload();
  assert(!Update.running && !ESP.restarted);
  return 0;
}
