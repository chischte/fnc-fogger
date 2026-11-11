# Hardware migration, 2026-10-24

> Historischer Bericht. Der beschriebene Stand kann vom heutigen Projekt abweichen.
> Aktuelle Anleitungen: [Dokumentationsübersicht](../README.md).

Through commit `e215ccc`, the project used Arduino Portenta Machine Control.
The local tag `portenta-machine-control-final` marks the complete previous
state with PT100 and Portenta OTA.

Since firmware `3.0.0-esp32s3`, ESP32-S3-DEV-KIT-N8R8 is the default target:
8 MiB flash, 8 MiB Octal PSRAM. SHT45 and SCD41 share one I2C bus.

| Wire | Connection |
| --- | --- |
| Blue / SDA | GPIO8 |
| Yellow / SCL | GPIO9 |
| Red / VCC | 3V3 |
| Black / GND | GND |

This table describes the actual Grove cable, in black/red/blue/yellow order.
Blue replaces the usual white SDA wire. The original image's colour assignment
did not match this cable and was corrected during the hardware test.

I2C operates at 100 kHz. PT100, RTD driver and RTD diagnostics are removed.
API field `outertemp` remains `null` for existing loggers; `valid.outertemp`
is false. Historical Python logger data remains readable.

The measurement buffer uses LittleFS rather than Portenta QSPI. Two 2 MiB app
partitions support OTA; 4032 KiB remains for LittleFS. Two rotating measurement
files are limited to about 1.5 MiB each. Mount failure formats the data
partition; SQLite remains the long-term store.

Initial USB installation: `pio run -e esp32s3 -t upload --upload-port COMx`.
Store WiFi credentials in `../wifi-credentials.h` as before. Then open
`http://<device-ip>/update` and upload only `.pio/build/esp32s3/firmware.bin`
(no merged/factory BIN or Portenta file). Alternatively run
`./upload_firmware.ps1 -DeviceUrl http://<device-hostname> -DeviceId <12-digit-device-id>`.
The current managed updater also checks the hardware profile and confirms
the running firmware after restart; see [device management](../device-management.md).
The ESP32 Update library validates the image and activates the other app
partition only on success. Aborting leaves the current firmware running.
The update page still has no login and is intended for trusted local WiFi.

Portenta builds remain explicitly available through `-e portenta_h7_m7`, now
also without PT100. The complete old firmware is preserved in the Git tag.
