# Control concept

This specifies future firmware; PI tuning is not yet established.

## CO2 to supply air

Control error = measured CO2 minus CO2 setpoint. A positive error increases
fan demand. Only the CO2 PI determines fan speed. At sufficiently low CO2,
it may request no air exchange and stop the fan. When running, constrain the
output to the experimentally established reliable minimum and configured
maximum; apply anti-windup using the actual constrained output.

ESP32 directly drives the Noctua NF-A4x10 24V PWM using non-inverted 3.3 V
push-pull PWM at 25 kHz. GPIO5 reads tach using the internal pull-up; no
external tach resistor is planned. Tach detects a stopped fan after a startup
grace period. The viewer displays measured tach RPM, never RPM inferred from PI output.

Supply air can lower CO2 only if its concentration is lower and an exhaust
path exists. Without a CO2 source, active increase is impossible. The setpoint
is therefore achievable only within physical limits.

Update the CO2 PI only with fresh valid readings. Initially plan a five-second
measurement interval for SCD41 standard operation; account for sensor and
chamber lag during tuning. Source: [SCD4x datasheet](https://sensirion.com/resource/datasheet/scd4x).
Use automatic self-calibration only when its fresh-air conditions are satisfied.

## Relative humidity to fogger

The humidity PI and fogger control must never request or increase fan speed.
The fogger may operate only when measured fan speed reaches the experimentally
established reliable minimum. When the CO2 PI requests no air exchange because
CO2 is sufficiently low, the fogger stays off regardless of humidity demand.
Immediately switch the fogger off below minimum fan speed. Account for this
interlock in humidity-PI anti-windup.

Control error = humidity setpoint minus measured humidity. Positive error
increases output between 0 and 100%. GPIO6 drives an IRLB8721 low-side switch
for the 5 V fogger supply (gate to GPIO6, drain to fogger negative, source to
GND; HIGH requests ON, LOW = OFF).

The fogger uses a fixed **200 ms ON time** and variable OFF time. For demand
p with 0 < p < 100: `off_time = 0.2 s * (100 / p - 1)`.
At 50%, alternate 200 ms ON / 200 ms OFF; at 10%, use 200 ms ON / 1.8 s OFF.
Do not switch fogger power at 25 kHz.

The fixed ON time was reduced from 2 s to 200 ms after the practical test on
2026-11-09. At 0%, stay off. At 100%, continuous operation requires explicit
support by the module. Protection shutdowns and the fan interlock act
immediately, including during an ON pulse. Timing must be nonblocking.

Acquire SHT45 readings at a fixed configurable interval. Update the PI only
with fresh valid readings and actual elapsed time. Ventilation also affects
humidity; tune controllers separately first, then together. Initially keep
D at zero; add it only if demonstrated useful, with a filtered measurement derivative.

## Fault and startup states

| Event | Planned response |
| --- | --- |
| Boot/reset, no valid readings yet | Request fogger OFF; without gate pull-down, OFF during reset is not guaranteed; initially run fan at full speed |
| SHT45 invalid or stale | Fogger OFF immediately; hold/reset humidity integrator |
| SCD41 invalid or stale | Configured fan fault speed (initially 100%); fogger OFF |
| Fan stopped despite speed demand | Report fault; fogger OFF |
| No water | Dry-run protection switches fogger OFF |
| Configured humidity upper limit exceeded | Fogger OFF independently of PI |

Define timeouts relative to sensor intervals. Restart only with valid readings
and cleared fault cause, using bounded, bumpless output. Fault states must stay visible.

## Pending experiment after fan installation

- [ ] With the real air path installed, determine the PWM command and measured speed at which the fan reliably starts from rest. Repeat multiple starts.
- [ ] Separately determine the lowest reliably sustained speed of an already running fan. Record startup and operating limits with margin.
- [ ] Verify that fogger enable requires tach-confirmed minimum speed and that stopped/slow fan conditions switch the fogger off.

## Firmware structure

Keep sensor access, hardware-independent PI logic, fogger pulse scheduling,
fan/load-switch drivers and state monitoring separate. Application connects
them through explicit dependencies. Use monotonic, nonblocking timing;
networking and UI remain separate modules.

Before hardware release, check reset outputs, sensor loss, fan stall, dry-run
protection, PWM polarity and minimum switching times. Tune PI only with the
actual chamber volume, air path and fogger.

## WiFi OTA updates

Sensor/OTA provisioning is prepared in the `esp32c3_supermini` build profile:
initial installation via USB, then targeted WiFi updates. See
[device management](device-management.md). Authentication and integration with
the planned actuator controller remain unimplemented.
The XZG buck continues providing 5 V during OTA; USB is unnecessary.

For the future actuator controller: before writing firmware, switch fogger off, hold both PI integrators and set
fan to the defined fault speed (initially 100%). After successful upload,
restart, initialize outputs and resume control only after valid readings.
Report aborted updates and control recovery. USB remains the recovery route.

Switching at 3.3 V successfully tested (2026-11-09, fogger module supplied at
5 V). Without gate pull-down, reset behaviour remains undefined; see
[electrical limits](hardware.md#limits-of-the-requested-resistor-free-variant).
