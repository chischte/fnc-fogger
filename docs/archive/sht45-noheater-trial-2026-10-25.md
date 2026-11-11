# SHT45 comparison without heater

> Historischer Bericht. Der beschriebene Stand kann vom heutigen Projekt abweichen.
> Aktuelle Anleitungen: [Dokumentationsübersicht](../README.md).

Trial started at 2026-10-25T01:34:26+02:00 (Europe/Zurich).
Firmware `3.1.1-esp32s3-noheater`, installed by OTA on `192.168.31.211`.

Before the change (firmware 3.1.0):

- SHT45: 22.67 degrees C; SHTC3: 21.80 degrees C; Inbox minus Ambient: +0.87 degrees C.
- SHT45: 39.91 %RH raw, 40.91 %RH with the previous heater-related humidity offset.
- Stored time between heater cycle and SHT45 reading: 60010 ms.

The trial sets `SHT45_HEATER_ENABLED = false`. Measurement and acceptance
intervals stay unchanged (SHT45 accepted every 65 s). Without the heater cycle,
no heater-related humidity offset applies: `humidity_offset_rh = 0`,
`sht_heater_elapsed_ms = null`. No temperature offset is applied.
SHTC3 and SCD41 continue unchanged.

A new boot ID separates the trial from previous data. Firmware identification
also marks the trial in the live API. Thermal results immediately after the
change are not conclusive; consider residual heat and changing ambient conditions.

## End of trial

After operating without the heater, the user reported a zero temperature
difference. At the user's request, firmware `3.1.2-esp32s3` restored the previous
heater cycle. This is an observation on the current assembly, not an absolute
calibration of either sensor.

After restoration, firmware 3.1.2 and new boot ID 3910737168 were confirmed.
Before the first heater pulse: SHT45 21.31 degrees C, SHTC3 21.26 degrees C,
difference +0.05 degrees C.
