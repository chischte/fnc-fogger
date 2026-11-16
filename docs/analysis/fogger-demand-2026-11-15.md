# Fogger demand during settled humidity control

Device: Primus Popinus @ Lilith, B8:1F:3F:27:F4:E0.

[PNG](fogger-demand-2026-11-15.png) | [Vector SVG](fogger-demand-2026-11-15.svg) | [PDF](fogger-demand-2026-11-15.pdf) | [Phase means CSV](fogger-demand-2026-11-15.csv)

## Method

- Uses the available actuator recording from 12 November 2026 onward. Sensor
  recording starts earlier, but cannot establish earlier actuator demand.
- All dates/times are Europe/Zurich. Both membranes were replaced on
  14 November at approximately 04:20, according to the user. One old membrane
  was completely inoperative; failure onset is unknown.
- Sensor readings are joined to actuator observations by boot ID and measurement
  sequence. Humidity is the SHT45 value plus the recorded calibration offset,
  clipped to 0-100% as in the viewer.
- Only enabled, fault-free normal automatic control with the fogger enabled is
  considered. Manual control, cyclic mist, startup and sensor/fan fault states
  are excluded.
- Eligible runs must remain within +/-2 percentage points of their own recorded
  humidity target for at least 15 continuous minutes. A gap longer than 15 s,
  a boot, a target change or the membrane change breaks a run. The entire run
  is included once it qualifies retrospectively. This is an RH tolerance test,
  not proof that the PI integral or water-output rate has reached equilibrium.
- Means in the CSV are weighted by observed time, capped at 15 s per sample.
  The figure shows one-minute means within each eligible run and never bridges
  excluded runs. The final observation is not extrapolated.
- Dotted yellow lines show recorded PI output caps. Percentages are electrical
  output commands, not measured atomization performance, watts or airflow.

## Interpretation limits

Changing targets, PI gains/caps, ventilation demand, inlet conditions and wick
condition prevent a controlled membrane-efficiency comparison. A higher duty
at similar RH can indicate lower effective mist delivery, but does not isolate
membrane wear. The early post-replacement comparison contains only about
25 eligible minutes. Wick trimming and the outlet opening change from stage
3 to stage 5 have no precise timestamps here and are not marked speculatively.

## Reproduce

Run `python tools/plot_fogger_demand.py` from the repository root. The script
reads the device SQLite database in read-only mode and regenerates the
artifacts with the newest recorded observations.

## Phase means

| Phase | Eligible h | Fogger % | Fan % | RH % | Target % |
|---|---:|---:|---:|---:|---:|
| 12.11. alte Membranen | 2.91 | 18.3 | 72.4 | 96.1 | 97.0 |
| 13.11. alte Membranen | 14.44 | 32.7 | 31.3 | 98.5 | 98.8 |
| 14.11. 00:00-04:20 alt | 1.06 | 44.0 | 33.7 | 98.5 | 99.0 |
| 14.11. 04:20-12:00 neu | 0.41 | 16.3 | 59.0 | 97.9 | 99.0 |
| 14.11. 12:00-18:00 neu | 4.49 | 32.7 | 78.7 | 98.9 | 99.0 |
| 14.11. 18:00-24:00 neu | 5.02 | 32.5 | 49.0 | 99.1 | 99.0 |
| 15.11. neue Membranen | 3.87 | 39.9 | 27.9 | 99.1 | 99.0 |
