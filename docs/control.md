# Control concept

This specifies future firmware; PI tuning is not yet established.

## Manual Mode, firmware 3.4.0

Open the viewer's Command Mode, then select Manual Mode. Entry sets both
outputs to zero. Fan [%] controls GPIO5 PWM duty from 0 to 100, rather than
closed-loop RPM; actual measured RPM remains visible in the CO2 graph title.
Fogger [%] controls a one-second time-proportioned cycle: 25% means 250 ms ON
and 750 ms OFF, 0% stays OFF, 100% stays ON. Each output has its own On/Off button.
Slider changes apply immediately to
enabled outputs; disabled outputs retain their local slider setting for the next
On press. Pending slider commands are coalesced to the latest position.
Stop All sends both outputs to zero; Exit Manual also stops both outputs.
PI stays disabled throughout. The manual test permits independent outputs,
including fogger operation without tach-confirmed airflow, for commissioning.
There is no water-level detection: supply water when testing the fogger.

Manual commands take over from the startup test and never resume it in the
same boot. Values exist only in device RAM and are not restored after reset.
The existing startup sequence still runs after a new boot until manual takeover.
The viewer renews confirmed manual commands while connected. After 30 seconds
without renewal, the firmware stops both outputs. A connection failure or a
stale client lease requires an explicit On action again; reconnect alone does not resume outputs.
OTA reception also stops both outputs. Timing is serviced without blocking;
late application polls can extend an individual fogger pulse.

`POST /api/control/manual` accepts a form with `mode=manual|off|renew`,
`fan_percent=0..100` and `fogger_percent=0..100` (whole percentages).
Mode off requires both values zero. Renew extends only an existing, unexpired
command with identical values; it cannot restart outputs after a device reboot.
The response and `/api/current` expose
`control.manual` with supported/active/fan_percent/fogger_percent/lease_ms;
`control.enabled=false` confirms that PI is disabled. Old firmware leaves
the manual controls unavailable. No manual output values are stored in SQLite
or NVS. This section is the reference for manual-mode behavior; code lives in
`manual_control`, `startup_actuators`, `control_api`, `viewer_manual`, and
`lance_collection`.

Verified on `b81f3f288aec`: firmware `3.4.0-esp32c3`, build `08564d7a1454`,
boot `2464235409`. Manual entry, renewal and exit confirmed with both outputs
at zero and PI disabled. Out-of-range commands and renewal after exit returned
HTTP 422. Final fan PWM 0%, measured RPM 0, fogger OFF. Nonzero operation is
left to the user's manual tests. All 93 host tests passed, including driver
PWM/gate output, duty timing, timeout, renewal, and direct viewer controls.

### Gate pin revision, firmware 3.4.1

The gate moves from GPIO3 to GPIO21 at the user's request. Manual controls,
fan GPIO5 and tach GPIO6 remain as above. GPIO21 can emit UART0 ROM boot
messages before the firmware requests LOW; a passive gate pull-down does
not suppress actively driven UART pulses. See hardware.md for the limitation.
Firmware is prepared for this new wiring; installation is deferred while the
previously overheated controller and wiring are being checked.

### Gate pin revision, firmware 3.4.2

The gate returns to GPIO3, avoiding GPIO21's UART0 TX boot output. Fan PWM
remains GPIO5, tach remains GPIO6, and startup/manual behavior is unchanged.
The firmware is prepared, not installed. Move the physical gate connection
to GPIO3 before installing this version. Check the previously overheated
controller and wiring before powering the assembly.

## Implemented commissioning mode, firmware 3.3.2

The C3 now drives fan PWM on GPIO5 at 25 kHz, counts falling tach edges on
GPIO6 with the internal 3.3 V pull-up, and switches the fogger gate on GPIO3 in firmware 3.4.2
(GPIO21 in 3.4.1; GPIO3 in the original 3.3.x/3.4.0 releases).
Noctua specifies two tach pulses per revolution; RPM is calculated from the
actual pulse count and elapsed time in one-second windows.

On each restart, after the initial delay, the fan runs once for 3 seconds at
100%. Simultaneously the fogger pulses 100 ms ON / 100 ms OFF until the fan
returns to 0%. Both outputs then remain OFF. After a one-second pause the
test is marked complete. Nominally there are 15 fogger pulses; delayed polling
can reduce the count and extend individual phases. The fan deadline always
takes precedence over starting another fogger pulse. Rotor inertia means the
fan may continue turning after PWM reaches 0%.

The user explicitly allowed these startup-only fogger pulses without
tach-confirmed airflow or valid sensor readings and confirmed water readiness
on 10 November 2026. There is no electronic water-level check. This exception
does not enable humidity/CO2 control or waive the future control interlocks.
The startup test repeats after every reset, including an OTA restart.
OTA reception aborts the current test and requests fogger OFF and fan 100%;
the test does not resume until a new boot. PWM initialization failure prevents
fogger operation. Reset-time OFF still requires the external gate pull-down.

Telemetry under `control` reports `fan.rpm`, `fan.pwm_percent`, `fogger.on`,
and `startup_test.active/complete/completed_pulses/completed_fan_pulses`.
`completed_pulses` counts fogger pulses; the separate fan counter counts fan pulses. `enabled=false` refers
to the PI controller, not to the commissioning outputs. The viewer displays
the measured RPM in Command Mode and identifies commissioning separately.
Observed on `b81f3f288aec`: three completed pulses, fogger subsequently OFF,
fan at 100%, measured RPM 5160–5190, stable boot ID `1896208148`.
The user visually confirmed both original 3.3.0 startup tests successful.
The previous firmware 3.3.1 used three 2-second fan pulses and five 200 ms fogger pulses.
OTA verified on `b81f3f288aec`, build `3f3017286313`, boot ID `1965666641`:
startup complete, five fogger pulses and three fan pulses, fogger OFF afterward,
fan 100% with measured 5220 RPM. CO2, temperature and humidity readings valid.

Firmware 3.3.2 OTA was verified on `b81f3f288aec`, build `2a06017b4fb6`.
Subsequent HTTP status reads timed out, so completion and post-test tach RPM
could not yet be confirmed on the physical device. All 87 host tests passed,
including simultaneous timing, shutdown, delayed polling and OTA abort.

Sources: [Noctua PWM/tach specifications](https://www.noctua.at/pub/media/wysiwyg/Noctua_PWM_specifications_white_paper.pdf).

## CO2 to supply air

Control error = measured CO2 minus CO2 setpoint. A positive error increases
fan demand. Only the CO2 PI determines fan speed. At sufficiently low CO2,
it may request no air exchange and stop the fan. When running, constrain the
output to the experimentally established reliable minimum and configured
maximum; apply anti-windup using the actual constrained output.

ESP32 directly drives the Noctua NF-A4x10 24V PWM using non-inverted 3.3 V
push-pull PWM at 25 kHz. GPIO6 reads tach using the internal pull-up; no
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
increases output between 0 and 100%. GPIO3 drives an IRLB8721 low-side switch
for the 5 V fogger supply (gate to GPIO3, drain to fogger negative, source to
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
