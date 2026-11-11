#include "firmware/startup_actuators.h"
#include "config.h"

#define assert(condition) do { if (!(condition)) return __LINE__; } while (false)

int main() {
  StartupTest test;
  test.begin(0);
  test.poll(999);
  assert(!test.status().foggerOn && test.status().fanPercent == 0);
  for (uint32_t now = 1000; now <= 5000; now += 10) {
    test.poll(now);
    const uint32_t elapsed = now - 1000;
    const bool foggerOn = elapsed < 3000 && elapsed % 200 < 100;
    const uint8_t fanPercent = elapsed < 3000 ? 100 : 0;
    assert(test.status().foggerOn == foggerOn);
    assert(test.status().fanPercent == fanPercent);
  }
  assert(test.status().startupComplete && !test.status().startupActive);
  assert(test.status().completedFanPulses == 1);
  assert(test.status().completedPulses == 15);
  test.poll(50000);
  assert(!test.status().foggerOn && test.status().completedPulses == 15);

  // A delayed poll must stop the fogger at the fan deadline, without replay.
  test.begin(0);
  test.poll(1000);
  test.poll(4500);
  assert(!test.status().foggerOn && test.status().fanPercent == 0);
  assert(test.status().completedPulses == 1);
  test.poll(5500);
  assert(test.status().startupComplete);

  test.begin(0xFFFFFF00U);
  test.poll(0xFFFFFF00U + 1000U);
  assert(test.status().foggerOn);
  test.abort();
  test.poll(100000);
  assert(!test.status().foggerOn && test.status().aborted && test.status().fanPercent == 100);

  StartupActuators hardware;
  static_assert(Config::FOGGER_ENABLE_PIN == 3, "Gate must use GPIO3");
  hardware.begin(0);
  assert(hardware.status().hardwareReady && pwmPin == 5);
  assert(pinModes[6] == INPUT_PULLUP && pinValues[3] == LOW);
  hardware.poll(1000, false);
  assert(pinValues[3] == HIGH && pwmDuty == 255);
  for (unsigned pulse = 0; pulse < 100; ++pulse) tachHandler(tachInstance);
  hardware.poll(1500, false);
  hardware.poll(2000, false);
  assert(hardware.status().rpmValid && hardware.status().rpm == 3000);
  hardware.poll(2100, true);
  assert(pinValues[3] == LOW && pwmDuty == 0 && hardware.status().aborted);
  hardware.poll(10000, false);
  assert(pinValues[3] == LOW && hardware.status().rpm == 0);

  auto& manual = hardware.manualControl();
  assert(!manual.renew(0, 0, 10000));
  assert(manual.set(true, 40, 25, 11000));
  assert(!manual.renew(100, 100, 11000));
  assert(manual.renew(40, 25, 11000));
  hardware.poll(11000, false);
  assert(hardware.status().fanPercent == 40 && pinValues[3] == HIGH);
  hardware.poll(11250, false);
  assert(pinValues[3] == LOW);
  hardware.poll(12000, false);
  assert(pinValues[3] == HIGH);
  assert(manual.set(true, 100, 100, 12001));
  hardware.poll(12999, false);
  assert(pinValues[3] == HIGH && pwmDuty == 255);
  assert(manual.set(true, 0, 0, 13000));
  hardware.poll(13000, false);
  assert(pinValues[3] == LOW && pwmDuty == 0);
  assert(!manual.set(true, 101, 50, 13000));
  assert(!manual.set(false, 50, 0, 13000));
  assert(manual.set(true, 50, 100, 14000));
  hardware.poll(44000, false);
  assert(manual.expired() && pinValues[3] == LOW && pwmDuty == 0);
  assert(!manual.renew(50, 100, 44001));
  assert(manual.set(true, 100, 100, 45000));
  hardware.poll(45000, true);
  assert(!manual.active() && pinValues[3] == LOW && pwmDuty == 0);
  assert(manual.set(true, 50, 50, 0xFFFFFF00U));
  hardware.poll(0xFFFFFF00U + 30000U, false);
  assert(manual.expired() && pinValues[3] == LOW && pwmDuty == 0);

  pwmAvailable = false;
  StartupActuators failed;
  failed.begin(0);
  failed.poll(1000, false);
  assert(!failed.status().hardwareReady && pinValues[3] == LOW);
  assert(failed.status().aborted && !failed.status().foggerOn);
  return 0;
}
