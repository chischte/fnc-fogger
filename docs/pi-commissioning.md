# PI commissioning · 12 November 2026

## Current revision 3.5.2: humidity PI enabled

On explicit user request, the fogger is enabled for **90% corrected SHT45 RH**.
CO₂ remains at 2,000 ppm, Kp=0.02 and Ti=300 s; normal fan range remains 12–80%,
fault fallback 10%, and startup tests remain skipped.

Humidity starts gently at **Kp=1 % duty per percentage point RH**, **Ti=600 s
(10 min)**, with **20% maximum automatic duty**. These are initial trial settings,
not a fitted tuning result. For constant 3 percentage points error, P=3%; with
no saturation/interlock, the integral grows another 3% over 600 s. It is not a
600-second delay or ON duration. Integration occurs only on fresh SHT45 timestamps
(about every 65 s), with actual elapsed time and anti-windup.

Humidity input now matches the viewer: `min(100, raw RH + humidity_offset_rh)`.
The prior automatic input used raw RH, which would otherwise regulate one
percentage point above the displayed target with the configured +1% correction.

**Existing airflow policy is unchanged**: humidity cannot start/increase the fan.
Fogger needs a CO₂ fan demand and confirmed tach at least 250 rpm. No CO₂ demand,
lost/slow fan, missing/stale humidity, Wi-Fi loss, OTA or faults inhibit fogging.
The humidity integral resets while inhibited. At 95% RH or target+0.5% RH the
fogger stops. Condensation-related CO₂ errors remain a commissioning concern.

Automatic fogger output uses a fixed **100 ms ON** impulse and variable OFF:
`period_ms = 100 * 100 / rounded_duty_percent`. At 5%: 100 ms ON / 1,900 ms OFF;
at 1%: 100 ms ON / 9,900 ms OFF; at 20%: 100 ms ON / 400 ms OFF. Zero stays OFF.
This avoids attempting ineffective 10–50 ms pulses for small PI demands. The
scheduler is nonblocking and interlocks interrupt an ON pulse immediately.
Manual Mode retains its existing one-second variable-ON duty and 0–100% range;
the 20% cap applies to automatic control, not manual testing.

Telemetry reports actual pulse times and explicit `fogger.duty_percent`.
The independent logger now prefers that explicit duty over reconstructing it
from rounded pulse times. Native tests exercise actual GPIO ON/OFF, 100-ms pulse
boundaries, fresh/held RH integration, caps, airflow/no-CO₂ gating, humidity
limits, stale inputs and Wi-Fi stop.

Under each viewer PI graph, the current device-reported **Kp and Ti in minutes**
are shown. This replaces the initially requested Ki decimal representation at
the user's follow-up request. CO₂ is displayed per 100 ppm: Kp=2 %/100 ppm,
Ti=5 min; humidity: Kp=1 %/%RH, Ti=10 min. This is a display conversion only;
the CO₂ controller continues to use Kp=0.02 %/ppm internally.
Ki remains implicitly Kp/Ti inside the controller. Missing parameters display
`--`; no hard-coded displayed tuning values. Reopen an already running viewer
to load the labels. Firmware 3.5.2 build `42a70ff1b9e7` was verified by OTA on
`b81f3f27f4e0`; both PIs were explicitly activated with fresh CO₂ data, target
RH=90% and target CO₂=2,000 ppm. Other devices were not updated.

## Previous revision 3.5.1: gentler ventilation

User-requested CO₂ setpoint is now **2,000 ppm**. Minimum running fan output
is **12%**, maximum remains 80%; stall threshold is provisionally 250 rpm
with the existing 5 s grace. No separate manual speed test is performed for
this revision. **Startup test pulses are skipped** to avoid adding a full-speed
ventilation impulse to the chamber measurement. Actual 12% RPM will be evaluated
from the regular PI run, not by injecting a test disturbance.

After the user reported an aggressive response, the live 3.5.0 snapshot showed
3,901 ppm / 2,000 ppm target, P=95.05%, I=7.15%, limited output=80%. This snapshot
has about 1,900 ppm error; it does not establish the reported 70% at 500 ppm.
For the next experimental iteration, **Kp=0.02 %/ppm replaces 0.05; Ti remains 300 s**, as explicitly
requested in the follow-up. A 500 ppm error contributes 10% P; the running floor is 12%.
Because Ki=Kp/Ti, reducing Kp also reduces the integral gain by a factor of 2.5
even though Ti is unchanged. PI activation after the update starts with zero integral. These remain
trial settings, not a proven optimum. Fogger remains locked OFF.

Viewer setpoints now autosave after **3 seconds without another edit**, with no
Save button. Changes during an in-flight request are retained and submitted
later; offline drafts wait for reconnection. Failed requests retry after 5 s
while connected. Returning to already persisted values avoids an extra write.
Only device-confirmed targets feed the displayed difference and the controller.
Repeated identical settings requests do not reset the running PI.
Restart the viewer once to load this UI behavior. Unsent edits cannot be saved
if the viewer process is closed before transmission.

### Missing CO₂ sample and fallback correction

The first recorded 3.5.0 fault is `automatic_co2_invalid`. Sensor sequence 526
contains no valid CO₂; sequence 527 already contains a valid 2,529 ppm and
subsequent samples are valid. 3.5.0 latched the fault on a single invalid cycle,
reset PI terms to zero and applied an independent 80% fallback. Hence the
reported combination of sum=0% and about 3,990–4,110 rpm. The stored invalid
sample cannot distinguish an I²C read failure from data not being ready.
It is not evidence of a permanently failed sensor.

3.5.1 holds the last valid CO₂ value and its original timestamp for **less than
15 seconds**, keeping the integral unchanged on held samples. A valid sample
within that window resumes normal updates. At 15 s without valid data, the
fault latches. The user explicitly selected **10% fallback PWM**, independently
of the normal 12–80% PI range. Other recoverable control faults also use 10%;
hardware-unavailable output remains zero. The fault still requires an explicit
PI restart after clearing the cause. While building the fix, the target's
already latched 80% fallback was replaced by an explicitly commanded 10% fan,
with fogger zero, and will return to PI after the update.

Viewer fault intervals show gaps rather than a misleading zero PI trace.
The title shows actual PWM and tach RPM with a fault marker; PI output fields
are unavailable while the independent fallback owns the output.

## Original test: ventilation only, firmware 3.5.0

Target: **Primus Popinus @ in production**, `B8:1F:3F:27:F4:E0`.
CO₂ setpoint **2,500 ppm**, explicitly requested for the chamber with casing.
The independent humidity PI is implemented but disabled for this first test.
**Fogger outputs are locked OFF, including manual commands and startup pulses.**
The gate driver always requests LOW; nonzero fogger commands return HTTP 422.
The other lance is not updated by this commissioning operation.

| Item | Initial setting | Reason |
|---|---|---|
| CO₂ error | measured CO₂ minus setpoint | Ventilation can lower CO₂ only |
| CO₂ Kp | 0.05 percentage points PWM / ppm | 500 ppm error gives 25% P demand |
| CO₂ Ti | 300 s | Provisional slow integral action, not a fitted process model |
| Fan start | above setpoint + 50 ppm (above 2,550 ppm) | Avoid switching at every small fluctuation |
| Fan stop | at/below setpoint (2,500 ppm) | No ventilation solely for humidity |
| Running fan range | 15–80% PWM | User's start margin; measured 80% is maximum acceptable noise |
| Minimum tach | 400 rpm, after 5 s startup grace | Provisional stall threshold below measured 15% speed |
| Fogger | disabled | User requested ventilation-only tests |
| Humidity Kp / Ti | 2 % duty / %RH, 600 s | Prepared initial proposal, inactive |
| Future fogger limit | 20% duty, 1 s cycle | Initial test cap, inactive |

At rest, fan demand is zero even when humidity is low. Once CO₂ crosses the
start threshold, PI output is constrained to 15–80%; at the setpoint the fan
stops and the integral is reset. This stop/start band and minimum fan output
can cause cycling; stable continuous operation is not yet demonstrated.
No feedforward/base ventilation or RPM control loop is active.

## What the measurements establish

The user's fan series: 10% ≈ 300 rpm, 20% ≈ 1,000, 30% ≈ 1,800,
40% ≈ 2,370, 50% ≈ 2,900, 60% ≈ 3,060, 70% ≈ 3,420,
80% ≈ 3,900, 90% ≈ 4,300, 100% ≈ 4,410.
60% was judged very quiet, 80% the maximum acceptable noise.

An actual start from rest after OTA at **15%** produced about **630–720 rpm**
after the initial acceleration. The last three samples were 660 rpm.
This verifies this start in this setup, not all possible loads or repeated starts.

Earlier logged manual operation at fan 22%, fogger 53% showed humidity around
92% and CO₂ around 600 ppm. It does not identify chamber gain, dead time or a
CO₂ source step. High CO₂ during dense mist was previously reported and is
not treated as a valid tuning response. Thus Kp/Ti above are provisional
engineering starting values, not calculated optimum gains from these readings.

## Timing, interlocks and telemetry

The PI uses conditional integration against output limits (anti-windup), and
updates only on a new sensor timestamp with actual elapsed time. CO₂ normally
updates every 5 s; SHT45 humidity is held between approximately 65 s samples.
A future humidity loop cannot demand a fan start or increase fan demand; its
integrator resets while airflow is unavailable. It requires valid tach at least
400 rpm, valid humidity, and stays off at 95% RH or setpoint + 0.5% RH.
The current fogger lock takes precedence over all those rules.

Invalid CO₂, a sample age of at least 15 s, actuator failure or a fan stall
latches a fault.
Fault fan output is 80% when hardware is available; fogger stays OFF.
SCD41-reported humidity ≥95% also latches a CO₂-reliability fault. That check
is a heuristic guard, not a condensation detector: readings below 95% can still
be affected by droplets. Faults require explicit Stop PI / Start PI after repair.
Wi-Fi loss or OTA stops PI and both outputs; reconnection does not resume PI.
Reboot starts with PI disabled and discards manual outputs. The normal fan
startup test remains, while all fogger test pulses are suppressed in this build.
Closing the viewer does not stop firmware control.

API: POST `/api/control/automatic` with `enabled=1` or `enabled=0`.
Viewer Command Mode provides **Start PI / Stop PI**. Manual Mode takes over
explicitly and disables PI. Opening a viewer sends no start command. Humidity
plot says it is disabled during ventilation commissioning; CO₂ plot shows
actual P, I and limited output. Zero-output lines are drawn above the zero axis.
`/api/current` includes parameters, fault/reason and actuator state. Existing
`control_samples` stores them in `control_json`, with RPM, PWM, mode and setpoints
as dedicated columns; sensor and control timestamps remain separate.

Implementation: `pi_controller` (arithmetic), `automatic_control` (policy),
`startup_actuators` (GPIO arbitration), `application` (sensor/network inputs),
`control_api` / `web_server` (commands), and `viewer_automatic` (viewer button).

## Deployment and tuning status

3.5.0 build `73c411136131` installed by checked OTA on the target and verified
with a new boot ID and HTTP identity. The 2,500 ppm setting was confirmed in
persistent storage before and after installation. The fan-start test was
followed by explicit PI activation. Initial CO₂ was below target, so fan PWM
returned to zero and fogger remained OFF. Actual settling around 2,500 ppm
requires the chamber concentration to rise sufficiently first.

Monitor a full rise and ventilation cycle before adjusting gains. Compare
overshoot, time to return, fan demand and repeated start/stop cycles in the
recorded data. Do not compensate for mist-corrupted CO₂ by changing PI gains.
No unattended auto-tuning or synthetic CO₂ readings are used.

References: [MathWorks: conditional integration anti-windup](https://www.mathworks.com/help/simulink/slref/anti-windup-control-using-a-pid-controller.html),
[Sensirion SCD4x operating conditions](https://sensirion.com/en/media/documents/E0F04247/631EF271/CD_DS_SCD40_SCD41_Datasheet_D1.pdf).

Verification: firmware build succeeded; **123 automated tests passed**. Native
checks cover actual PI saturation/anti-windup, fresh-sample-only integration,
15–80% limits, start/stop band, GPIO fogger lock, stall/stale/condensation faults,
Wi-Fi/OTA shutdown, no automatic restart and timestamp wraparound. Viewer tests
cover explicit command confirmation, manual/automatic arbitration and the
humidity-disabled notice. An Agg rendering with recorded live telemetry verified
visible CO₂ zero lines, Stop PI and the disabled humidity graph.

First live observation: 18 HTTP snapshots over about 90 s, CO₂ approximately
1,220–1,240 ppm, PI enabled, fan PWM/RPM zero, fogger OFF throughout. SQLite
`control_samples` contains the active PI telemetry. This confirms operation
below the start threshold, not closed-loop settling at 2,500 ppm.

## Deployment of revision 3.5.1

Build `672aff201922`, image SHA256
`61e5c9f98ee9ae7ac30d5aceaf793f37cd973bb60d7c19ce59ecb10552f2ed37`,
installed by verified OTA on `b81f3f27f4e0`. HTTP confirmed Kp=0.02, Ti=300 s,
fan minimum=12%, maximum=80%, fault output=10%, setpoint=2,000 ppm, fogger locked
OFF and zero completed startup pulses. PI was explicitly restarted after a fresh
valid CO₂ reading. No separate manual speed test was injected. Device and logger
show resumed PI operation with the new parameters; 12% RPM is not claimed as
measured until a normal controller demand requests it.

**128 automated tests passed**, covering debounce/latest edits, edits during
pending saves, offline retention/retry, no unnecessary NVS request on unchanged
values, missing-sample hold without integral updates, timeout at 15 s, 10% fault
output, fault display separation and skipped startup pulses. The updated Command
Mode was rendered and inspected without a Save button. Viewer restart is needed
to activate autosave and the revised fault/PWM display in an already open window.
