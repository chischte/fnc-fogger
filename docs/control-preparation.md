# Command mode and persistent setpoints

## Current scope

The present lance only measures. Firmware 3.1.4 adds persistent setpoints and
a telemetry contract; it does not configure GPIOs, operate actuators or run
a PI controller. The viewer does not simulate regulator values.

Settings ownership is independent of networking: `Application` initializes
`ControlSettingsStore` before starting the HTTP/WiFi service. A future local
controller can consume this store without depending on the viewer or network.
Hardware drivers, PI logic and their tuning still need to be implemented for
the actual fan and nebulizer. This preparation alone does not control a chamber.

## HTTP interface

`GET /api/control` returns the control object. `/api/current` and
`/api/measurement` also include it under `control`:

```json
{
  "version": 1,
  "settings_supported": true,
  "persisted": true,
  "setpoints": {"co2_ppm": 1200.0, "humidity_rh": 92.0},
  "enabled": false,
  "reason": "not_configured",
  "humidity": {"p": null, "i": null, "sum": null},
  "co2": {"p": null, "i": null, "sum": null}
}
```

`POST /api/control/setpoints`, content type
`application/x-www-form-urlencoded`, accepts exactly two fields:

```text
co2_ppm=1200.0&humidity_rh=92.0
```

Ranges are 0–20000 ppm CO2 and 70–100 %RH. The viewer uses minus/plus
buttons with read-only values: CO2 steps of 500 ppm through 5000 ppm, then
1000 ppm through 20000 ppm; humidity steps of 1 %RH from 70 through 100.
Previously saved off-grid values are displayed unchanged until edited;
minus/plus selects the nearest lower/higher allowed value.
With no device settings available, the editor offers draft values of 1000 ppm
and 90 %RH so minus/plus can still be used. These are explicitly labelled as
unsaved defaults; Save remains disabled until compatible firmware is online.
Defaults are 1000 ppm and 90 %RH; they are labelled as factory values
until explicitly saved. These defaults are not a recommendation for a process.
Both fields must be valid. No change is applied if validation or persistence
fails. Success returns the full control object after NVS commit. Invalid
bodies receive 400/422; unavailable or failed persistence receives 503.
Portenta currently reports `settings_supported=false` and rejects writes.

The NVS namespace is `lance-control`, key `setpoints`, containing version 1
and the two floats in one blob. ESP32 NVS supplies the commit mechanism;
invalid or incompatible data falls back to defaults with `persisted=false`.
The integrator state and live PI terms are deliberately not persisted.

Future firmware should publish valid live P/I/sum percentages and
`enabled=true` only when the corresponding hardware and controller are ready.
The current API publishes null terms; it must not claim an output is operating.

## Viewer data and synchronization

Command-mode graph titles show current fogger ON/OFF durations in seconds
and the fan's measured RPM. The control object provides `fan.rpm` from the
tach input and `fogger.on_time_s` / `fogger.off_time_s` from the pulse
scheduler. These are current configured pulse durations, not countdowns;
they are never inferred from PI percentages. Missing, invalid or offline
values display as `—`. Current measurement-only firmware publishes null
for all three fields until the tach driver and actuator scheduler exist.
The planned fixed ON duration is 0.2 s (200 ms); at 50 % the OFF duration
is also 0.2 s. The scheduler itself is not implemented yet.

The table `control_setpoints` in each lance's measurement DB contains only
the last device-confirmed setpoints and their confirmation timestamp. The
device is authoritative. On connection, persisted device settings replace
the PC cache. Unpersisted defaults are displayed but do not replace the cache.

Commands use the selected lance's mDNS URL and run on its collector thread.
The viewer only reports success after a matching durable acknowledgement
and successful local persistence. A lost response is reported as unconfirmed;
subsequent polling reconciles the actual device settings. Failed commands
are not retried automatically. Offline or unsupported firmware disables Save.
An external change does not overwrite unsent text in the editor.

PI telemetry stays in a bounded deque, deduplicated by boot ID/sequence.
A new boot clears it; changing lance or closing the view discards it.
The measured humidity, CO2 and temperature history continues using SQLite.

## Verification

Host tests cover setpoint limits, nonfinite values, cached settings after
restart, bounded/deduplicated in-memory telemetry, per-boot clearing,
failed/unconfirmed commands, matching durable acknowledgements, switching
between one and two columns, and the setpoint text size.

The real firmware storage implementation is compiled against fake NVS to
test restoration after reconstructing the application, validation, failed
writes retaining the previous pair, version fallback and avoiding redundant
writes. This does not replace a physical power-interruption test.

`pio run -e esp32s3` builds the firmware. No physical power failure, WiFi
outage or actuator behavior was tested for this preparation. Firmware must
be uploaded before the present lance can accept setpoints.
