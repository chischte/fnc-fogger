# Independent background logger

Implemented 11 November 2026. The viewer no longer owns measurement recording.
`python -m logger.background` records every non-removed device registered in
`logger/data/lances.db`, each into its assigned SQLite database. New devices
registered through Device Selection are picked up within ten seconds. Each
device has its own worker, so an offline device does not stop other devices.
Closing or switching the viewer does not stop recording. Viewer live telemetry
and manual command renewal remain scoped to its own process; the background
logger never sends actuator commands or renews manual operation.

## Windows startup and monitoring

Run `powershell -File install_logger_autostart.ps1` from this project once.
The installer creates two tasks for the current user, with ordinary privileges:

- `fnc-fogger-logger`: starts at user login; runs without a console; retries
  failed process exits every minute, up to 999 attempts; no execution time
  limit; allowed on battery; duplicate task starts are ignored.
- `fnc-fogger-logger-watchdog`: checks every two minutes. A stopped task or
  heartbeat older than 90 seconds causes a restart. Per-device worker crashes
  are also restarted by the Python supervisor within ten seconds.

This is login autostart, not an unattended service before login. Windows must
be awake and connected. No power or sleep settings are changed by installation.
The installer backs up and disables the obsolete `fastnchip-sensor-logger`
task only when it points at the old `fnc-sensors/logger/logger.py` path.
Its XML backup is in `logger/data/recovery/legacy-logger-task.xml`.

`start_logger.ps1` starts recording alone; `start_monitoring.ps1` starts the
logger and viewer. Opening the viewer directly also ensures the logger has
started, preferring the scheduled task. A process-held OS file lock prevents
duplicate writers for one data directory, including command-line starts. The
lock is automatically released if its process crashes. Start or stop tasks in
Windows Task Scheduler. To intentionally stop recording for maintenance,
disable the watchdog first; otherwise it will restart the main task.

## Health and diagnostics

- `logger/data/background-status.json`: refreshed every ten seconds, including
  PID, per-device connection state, last successful sample, boot/sequence,
  last recovery and errors. A fresh supervisor heartbeat does not mean every
  device is online: inspect its individual device entry.
- `logger/data/background.log`: rotating log, four 1-MiB backups.
- `Get-ScheduledTask -TaskName fnc-fogger-logger*`: task states.
- `Get-ScheduledTaskInfo -TaskName fnc-fogger-logger`: last result.

Network and device errors are retried without terminating other workers.
The device ID returned by `/api/current` must match the assigned device before
any measurement is written. Removed devices stop being polled; their histories
remain intact.

## Recovery and time axis

Live samples are requested approximately every five seconds. The logger loads
`/api/backlog` at startup, after reconnects, boot changes and sequence gaps.
Recovery attempts are throttled to at most once a minute per device. A failed
recovery does not discard the current live sample and is retried. Existing
`UNIQUE(boot_id, sequence)` keys make replays idempotent.

The `measurement_clocks` table stores an estimated wall-clock boot time per
boot ID. It uses the earliest stored sample for an already known boot, or a
live sample and device uptime for a new boot. Recovered rows retain their
actual receive time in `received_at`; their estimated original measurement
time goes in `device_time`. The viewer uses this time on its chart. Accuracy
depends on reception latency, PC clock and device oscillator drift: this is
not an RTC or NTP clock on the ESP32. Old boots with no known clock anchor are
not assigned fabricated times; they are skipped with a warning.

The C3's flash is a bounded rotating buffer, not unlimited history. A long
Windows shutdown, sleep or network outage can exceed its retention window.
The inspected device held roughly 50 minutes at the time of the incident.
Already overwritten hours cannot be reconstructed. Saved raw snapshots in
`logger/data/recovery/` allow a later import while their boot clock is known.
The legacy single-device logger is not used for the new multi-device daemon.

## Validation

Automated tests cover independent recording without a viewer, device identity,
recovery timestamps and deduplication, retry after recovery failure, exclusive
process locking, registry changes, heartbeat freshness, and a viewer client
that does not write a measurements table. Runtime installation and recovery
results are recorded below after deployment.

Deployed 11 November 2026: both scheduled tasks installed for user michi;
the obsolete fnc-sensors task backed up and disabled. Runtime verified logger
online for b81f3f27ca14 while b81f3f288aec remained offline without blocking
recording. Restored 587 missing rows from the saved snapshot and 17 more from
the live device buffer. Verified a real watchdog restart (PID 11180 to 17244)
after stopping the main task; recovery remained idempotent (zero duplicate rows).
101 automated tests passed before installation.

Final live verification: with no viewer process running, the standalone logger
advanced device 27ca14 from sequence 17042 / 2901 rows to sequence 17043 /
2902 rows. The updated viewer was then relaunched. Startup recovery can take
several seconds before the first newly observed row; an initial fixed-duration
check was too early, so the final check waited for a real sequence advance.
The final code passed all 101 tests.

Grafische Übersicht: [Mehrgeräte-Architektur](architecture.md).
