#include "firmware/humidity_calibration.h"
extern "C" { int _fltused = 0; }
#define assert(condition) do { if (!(condition)) return __LINE__; } while (false)
bool writable = true;
bool loadHumidityReference(HumidityReference&) { return false; }
bool saveHumidityReference(const HumidityReference&) { return writable; }
int main() {
  HumidityCalibration calibration;
  assert(calibration.capture(94, 98));
  assert(calibration.reference().shtOffset == 6 && calibration.reference().scdOffset == 2);
  assert(calibration.capture(95, 99));
  assert(calibration.reference().shtOffset == 5 && calibration.reference().revision == 2);
  calibration.start(1000);
  assert(calibration.running() && !calibration.due(900999));
  assert(calibration.remaining(900999) == 1 && calibration.due(901000));
  assert(!calibration.capture(-1, 98));
  writable = false;
  assert(!calibration.capture(96, 99));
  assert(calibration.reference().shtOffset == 5 && calibration.reference().revision == 2);
  calibration.cancel("failed");
  assert(!calibration.running());
  calibration.start(0xFFFFFF00U);
  assert(calibration.due(0xFFFFFF00U + HumidityCalibration::DURATION_MS));
  writable = true;
  assert(calibration.capture(96, 99, HumidityCalibration::DURATION_MS));
  assert(!calibration.running() && calibration.reference().durationMs == 900000);
  return 0;
}
