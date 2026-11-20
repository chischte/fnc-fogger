#include "firmware/humidity_calibration.h"
#include <math.h>
extern "C" { int _fltused = 0; }
#define assert(condition) do { if (!(condition)) return __LINE__; } while (false)
bool writable = true;
unsigned saves = 0;
bool loadHumidityReference(HumidityReference&) { return false; }
bool saveHumidityReference(const HumidityReference&) { ++saves; return writable; }
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
  HumidityCalibration automatic;
  assert(automatic.capture(94, 98));
  const unsigned manualSaves = saves;
  assert(!automatic.runningCalibration(1000, 94, true, 98, true));
  assert(saves == manualSaves);
  assert(automatic.runningCalibration(2000, 96, true, 98, true));
  assert(automatic.reference().shtOffset == 4 && automatic.reference().scdOffset == 2);
  assert(automatic.reference().kind == HumidityReferenceKind::runningCalibration);
  assert(automatic.reference().revision == 2 && !automatic.pendingSave());
  assert(!automatic.runningCalibration(3000, 50, true, 50, true));
  assert(automatic.reference().shtOffset == 4 && automatic.reference().scdOffset == 2);
  assert(!automatic.runningCalibration(4000, 99, false, 99, false));
  assert(!automatic.runningCalibration(5000, NAN, true, 101, true));
  assert(automatic.runningCalibration(6000, 99, false, 99, true));
  assert(automatic.reference().shtOffset == 4 && automatic.reference().scdOffset == 1);
  assert(automatic.pendingSave() && automatic.reference().revision == 2);
  const unsigned batchedSaves = saves;
  automatic.checkpointRunning(61999);
  assert(saves == batchedSaves && automatic.pendingSave());
  writable = false;
  automatic.checkpointRunning(62000);
  assert(automatic.saveFailed() && automatic.pendingSave());
  assert(automatic.reference().revision == 2 && automatic.reference().scdOffset == 1);
  writable = true;
  automatic.checkpointRunning(63000, true);
  assert(!automatic.pendingSave() && !automatic.saveFailed());
  assert(automatic.reference().revision == 3);
  automatic.start(64000);
  assert(!automatic.runningCalibration(65000, 100, true, 100, true));
  assert(automatic.reference().shtOffset == 4 && automatic.reference().scdOffset == 1);
  automatic.cancel("cancelled");
  assert(automatic.runningCalibration(66000, 100, true, 100, true));
  assert(automatic.reference().shtOffset == 0 && automatic.reference().scdOffset == 0);
  return 0;
}
