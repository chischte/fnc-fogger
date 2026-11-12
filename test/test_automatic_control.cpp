#include "firmware/automatic_control.h"
#include "firmware/startup_actuators.h"

extern "C" { int _fltused = 0; }

#define assert(condition) do { if (!(condition)) return __LINE__; } while (false)

int main() {
  PiController pi(2, 10);
  assert(pi.update(20, 10, 0, 20) == 20);
  assert(pi.terms().i == 0);  // No accumulation against the upper limit.
  assert(pi.update(5, 1, 0, 20) == 11);
  assert(pi.update(-20, 10, 0, 20) == 0);
  assert(pi.terms().i == 1);  // No negative windup at the lower limit.

  ControlSettings settings;
  settings.co2Ppm = 2500;
  ControlInput input;
  input.hardwareReady = true;
  input.co2Valid = true;
  input.humidityValid = true;
  input.co2 = 600;
  input.humidity = 91;
  input.co2At = input.humidityAt = 1000;
  input.rpmValid = true;
  input.rpm = 650;
  AutomaticControl control;
  assert(!control.enabled() && !control.ownsOutputs());
  control.setEnabled(true, 1000);
  control.poll(1000, input, settings, true, false);
  assert(control.enabled() && control.fanPercent() == 0 && !control.foggerOn(1000));

  input.co2 = 2540;
  input.co2At = 2000;
  control.poll(2000, input, settings, true, false);
  assert(control.fanPercent() == 0);
  input.co2 = 2600;
  input.co2At = 3000;
  control.poll(3000, input, settings, true, false);
  assert(control.fanPercent() == 2 && control.foggerPercent() == 0);
  const float integral = control.co2Terms().i;
  control.poll(4000, input, settings, true, false);
  assert(control.co2Terms().i == integral);  // Integrate a sensor sample only once.
  input.co2At = 8000;
  control.poll(8000, input, settings, true, false);
  assert(control.co2Terms().i > integral);
  input.co2 = 10000;
  input.co2At = 13000;
  control.poll(13000, input, settings, true, false);
  assert(control.fanPercent() == 80 && !control.foggerOn(13000));

  // Startup pulses remain disabled; automatic high-humidity state keeps fogger off.
  StartupActuators hardware;
  hardware.begin(0);
  hardware.poll(1000, false);
  assert(pinValues[3] == LOW && !hardware.status().foggerOn && pwmDuty == 0);
  hardware.poll(13000, false, true, &control);
  assert(pwmDuty == 80*255/100 && pinValues[3] == LOW);

  input.co2 = 2400;
  input.co2At = 18000;
  control.poll(18000, input, settings, true, false);
  assert(control.fanPercent() == 0 && control.co2Terms().i == 0);
  input.co2 = 3000;
  input.co2At = 19000;
  control.poll(19000, input, settings, true, false);
  control.poll(19001, input, settings, false, false);
  assert(!control.enabled() && control.fanPercent() == 0);
  control.poll(19002, input, settings, true, false);
  assert(!control.enabled());

  control.setEnabled(true, 20000);
  input.co2At = 20000;
  control.poll(20000, input, settings, true, false);
  input.co2At = 25000;
  input.rpm = 0;
  control.poll(25000, input, settings, true, false);
  assert(control.fault() && control.fanPercent() == 10 && !control.foggerOn(25000));
  input.rpm = 1000;
  control.poll(25001, input, settings, true, false);
  assert(control.fault());  // No silent fault restart.
  control.setEnabled(true, 30000);
  input.co2At = 10000;
  control.poll(30000, input, settings, true, false);
  assert(control.fault());

  control.setEnabled(true, 40000);
  input.co2At = 40000;
  input.scdHumidityValid = true;
  input.scdHumidity = 96;
  control.poll(40000, input, settings, true, false);
  assert(control.fault() && control.foggerPercent() == 0);
  input.scdHumidity = 80;
  control.setEnabled(true, 40001);
  control.poll(40001, input, settings, true, true);
  assert(!control.enabled() && control.fanPercent() == 0);

  control.setEnabled(true, 0xFFFFFF00U);
  input.co2At = 0xFFFFFF00U;
  control.poll(0xFFFFFF00U, input, settings, true, false);
  input.co2At += 5000;
  control.poll(input.co2At, input, settings, true, false);
  assert(!control.fault() && control.enabled());
  control.releaseToManual();
  assert(!control.enabled() && !control.ownsOutputs());

  control.setEnabled(true, 100000);
  input.co2 = 3000;
  input.co2At = 100000;
  input.co2Valid = true;
  control.poll(100000, input, settings, true, false);
  const uint8_t heldFan = control.fanPercent();
  const float heldIntegral = control.co2Terms().i;
  input.co2Valid = false;
  input.co2At = 105000;
  control.poll(105000, input, settings, true, false);
  assert(!control.fault() && control.fanPercent() == heldFan);
  assert(control.co2Terms().i == heldIntegral);
  input.co2At = 110000;
  input.co2Valid = true;
  control.poll(110000, input, settings, true, false);
  assert(!control.fault());
  input.co2Valid = false;
  control.poll(124999, input, settings, true, false);
  assert(!control.fault());
  control.poll(125000, input, settings, true, false);
  assert(control.fault() && control.fanPercent() == 10);
  input.co2Valid = true;
  input.co2At = 125001;
  control.poll(125001, input, settings, true, false);
  assert(control.fault());

  AutomaticControl humidity;
  input.co2 = 3000;
  input.co2Valid = input.humidityValid = input.rpmValid = true;
  input.co2At = input.humidityAt = 200000;
  input.humidity = 85;
  input.rpm = 650;
  humidity.setEnabled(true, 200000);
  humidity.poll(200000, input, settings, true, false);
  assert(humidity.foggerPercent() == 5 && humidity.humidityTerms().i == 0);
  assert(humidity.foggerPeriodMs() == 2000);
  assert(humidity.foggerOn(200000) && humidity.foggerOn(200099));
  assert(!humidity.foggerOn(200100) && !humidity.foggerOn(201999));
  assert(humidity.foggerOn(202000));
  hardware.poll(200000, false, true, &humidity);
  assert(pinValues[3] == HIGH);
  hardware.poll(200100, false, true, &humidity);
  assert(pinValues[3] == LOW);
  input.co2At = 205000;
  humidity.poll(205000, input, settings, true, false);
  assert(humidity.humidityTerms().i == 0);  // Held RH must not accumulate I.
  input.co2At = input.humidityAt = 265000;
  humidity.poll(265000, input, settings, true, false);
  assert(humidity.humidityTerms().i > 0.54f && humidity.humidityTerms().i < 0.55f);
  assert(humidity.foggerPercent() == 6);
  input.co2 = 1000;
  input.co2At = 270000;
  humidity.poll(270000, input, settings, true, false);
  assert(humidity.fanPercent() == 0 && humidity.foggerPercent() > 0);
  assert(humidity.humidityTerms().i > 0);  // Rotation still permits fogging at zero PWM.
  input.rpm = 0;
  humidity.poll(270001, input, settings, true, false);
  assert(humidity.foggerPercent() == 0 && humidity.humidityTerms().i == 0);
  input.co2 = 3000;
  input.co2At = 275000;
  input.rpm = 0;
  humidity.poll(275000, input, settings, true, false);
  assert(humidity.foggerPercent() == 0 && !humidity.fault());
  input.rpm = 650;
  input.humidityValid = false;
  input.co2At = 276000;
  humidity.poll(276000, input, settings, true, false);
  assert(humidity.foggerPercent() == 0);
  input.humidityValid = true;
  input.humidity = 90.6f;
  input.co2At = input.humidityAt = 277000;
  humidity.poll(277000, input, settings, true, false);
  assert(humidity.foggerPercent() == 0 && humidity.humidityTerms().i == 0);
  input.humidity = 95;
  input.co2At = input.humidityAt = 278000;
  humidity.poll(278000, input, settings, true, false);
  assert(humidity.foggerPercent() == 0);
  input.humidity = 40;
  input.co2At = input.humidityAt = 280000;
  humidity.poll(280000, input, settings, true, false);
  assert(humidity.foggerPercent() == 20 && humidity.humidityTerms().i == 0);
  input.co2At = 415000;
  humidity.poll(415000, input, settings, true, false);
  assert(humidity.foggerPercent() == 0 && !humidity.fault());
  humidity.poll(415001, input, settings, false, false);
  assert(!humidity.enabled() && !humidity.foggerOn(415001));
  // Retain accumulated demand at the setpoint and unwind below it.
  AutomaticControl smooth;
  input.co2 = 3000;
  input.humidity = 85;
  input.co2At = input.humidityAt = 500000;
  smooth.setEnabled(true, 500000);
  smooth.poll(500000, input, settings, true, false);
  input.co2At = input.humidityAt = 800000;
  smooth.poll(800000, input, settings, true, false);
  assert(smooth.co2Terms().i == 10);
  smooth.resetIntegrals();
  assert(smooth.enabled() && !smooth.fault() && smooth.resetCount() == 1);
  assert(smooth.co2Terms().i == 0 && smooth.humidityTerms().i == 0);
  assert(smooth.co2Terms().p == 10 && smooth.co2Terms().sum == 10);
  input.co2At = 800001;
  smooth.poll(800001, input, settings, true, false);
  input.co2At = 1100001;
  input.humidityAt = 1100001;
  smooth.poll(1100001, input, settings, true, false);
  assert(smooth.co2Terms().i == 10);
  // Reset timing for the remaining independent rundown scenario.
  smooth.setEnabled(true, 500000);
  input.co2At = input.humidityAt = 500000;
  smooth.poll(500000, input, settings, true, false);
  input.co2At = input.humidityAt = 800000;
  smooth.poll(800000, input, settings, true, false);
  input.co2 = 2500;
  input.co2At = 805000;
  smooth.poll(805000, input, settings, true, false);
  assert(smooth.co2Terms().sum == 10 && smooth.fanPercent() == 10);
  assert(smooth.foggerPercent() > 0);
  input.co2 = 2400;
  input.co2At = 810000;
  smooth.poll(810000, input, settings, true, false);
  assert(smooth.co2Terms().i < 10 && smooth.co2Terms().i > 9);
  assert(smooth.fanPercent() == 8 && smooth.foggerPercent() > 0);
  input.co2 = 1900;
  input.co2At = 815000;
  smooth.poll(815000, input, settings, true, false);
  assert(smooth.co2Terms().sum == 0 && smooth.fanPercent() == 0);
  assert(smooth.foggerPercent() > 0 && !smooth.fault());
  input.rpm = 30;
  smooth.poll(815001, input, settings, true, false);
  assert(smooth.foggerPercent() > 0);  // No minimum RPM threshold.
  input.rpm = 0;
  smooth.poll(815002, input, settings, true, false);
  assert(smooth.foggerPercent() == 0);
  input.co2 = 2540;
  input.co2At = 820000;
  smooth.poll(820000, input, settings, true, false);
  assert(smooth.fanPercent() == 0);
  input.co2 = 2560;
  input.co2At = 825000;
  smooth.poll(825000, input, settings, true, false);
  assert(smooth.fanPercent() == 1);
  input.co2At = 831000;
  smooth.poll(831000, input, settings, true, false);
  assert(!smooth.fault() && smooth.fanPercent() == 1);
  input.rpmValid = false;
  smooth.poll(831001, input, settings, true, false);
  assert(smooth.foggerPercent() == 0);
  AutomaticControl idle;
  input.co2Valid = false;
  idle.resumeIfIdle(831001, input, false, true, false);
  assert(!idle.enabled());
  input.co2Valid = true;
  idle.resumeIfIdle(831001, input, true, true, false);
  assert(!idle.enabled());
  idle.resumeIfIdle(831001, input, false, false, false);
  assert(!idle.enabled());
  idle.resumeIfIdle(831001, input, false, true, true);
  assert(!idle.enabled());
  idle.resumeIfIdle(831001, input, false, true, false);
  assert(idle.enabled());
  idle.poll(831001, input, settings, false, false);
  assert(!idle.enabled());
  idle.resumeIfIdle(831002, input, false, true, false);
  assert(idle.enabled());
  input.co2Valid = false;
  idle.poll(900000, input, settings, true, false);
  assert(idle.fault());
  idle.resetIntegrals();
  idle.resumeIfIdle(900000, input, false, true, false);
  assert(idle.fault());  // Reset and automatic default must not clear faults.
  return 0;
}
