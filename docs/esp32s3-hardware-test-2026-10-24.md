# ESP32-S3 hardware test, 2026-10-24

**Final result: ESP32-S3 operates successfully.** Both sensors return valid
readings, WiFi and flash buffering work. OTA including restart and operation
without USB on an external 5 V supply were verified. The sensor errors below
were resolved after correcting swapped wires; they record the preceding investigation.

Device: ESP32-S3 revision v0.2, MAC `14:c1:9f:5c:c8:b4`.
COM4 is USB Serial/JTAG; COM5 is the CH343 connection on the same board.
Firmware: `3.0.0-esp32s3`. Test WiFi address: `192.168.31.211`.

## Successfully verified

- USB upload using esptool, including flash hash verification.
- Startup and PSRAM detection (8386295 usable bytes, 8 MB chip).
- WiFi connection, home page and update page (HTTP 200).
- `/api/current`, `/api/measurement`, including JSON history.
- LittleFS measurement buffer, NDJSON delivery and persistence across restarts.
- Real OTA of the app BIN: HTTP 200, automatic software restart, new boot ID and reconnection.
- OTA using `upload_firmware.ps1 -DeviceUrl http://192.168.31.211`.
- Invalid OTA image rejected with HTTP 422; no restart; flash buffer remains available.
- All 38 automated tests passed.

The first OTA test exposed a restart race condition, which was fixed: if the
client closes immediately after receiving the response, a verified update is
still activated. The subsequent test confirmed software restart and new boot ID.

## Initial sensor check unsuccessful

The user reported connected sensors. Startup diagnostics at 100 kHz:

```text
I2C SDA=8 SCL=9
I2C idle SDA=1 SCL=1
SHT45 I2C address 0x44 status=5
SCD41 I2C address 0x62 status=5
```

In the local ESP32 Wire driver, status 5 is `ESP_ERR_TIMEOUT`. Neither sensor
returned valid readings. Firmware kept searching; API returned NULL with false
validity flags. Real CO2, temperature, humidity and SHT45 heater-cycle checks
were therefore still pending. Lines were HIGH at startup; no permanently LOW
bus was observed. Supply, wiring and pull-ups required physical checks; no
specific cause was proven yet.

## Retry: SHT45 alone with shorter cable

The user disconnected SCD41 and connected SHT45 directly with a shorter cable.
API and serial diagnostics again showed `SHT45 I2C address 0x44 status=5`.
After a complete interval (`uptime_ms=77195`, `sht_read_uptime_ms=72587`,
sequence 16), `boxtemp` and `humidity` stayed NULL with both flags false.
ESP32 remained reachable under the same boot ID during final observation.
No SHT45 heater cycle could be demonstrated without a valid initial reading.
The missing SCD41 signal was expected in this assembly. Shortening the cable
and disconnecting the second sensor had not resolved SHT45 communication.

## Retry after improving power supply

After the user's supply improvement, HTTP API observation showed the boot ID
change from `2388127005` to `2211524122`; a restart occurred without the test
triggering reset. Cause was undetermined. After the next SHT45 acceptance time
(`uptime_ms=74577`, `sht_read_uptime_ms=74577`, sequence 15), temperature and
humidity remained NULL with false flags. LittleFS stayed ready and HTTP
responded. Successful sensor acquisition was still unproven.

## Retry after correcting swapped wires

I2C worked after reconnection: SCD41 serial `0A8815073B72` returned valid CO2
and humidity, for example 533 ppm and 44.35 %RH at sequence 68. Read-back SCD41
temperature was 29.47 degrees C, configured offset 2.2 degrees C. Readings
continued over consecutive five-second intervals with boot ID `1364144317`.

SHT45 remained invalid at its next regular acceptance
(`sht_read_uptime_ms=339192`, sequence 68): `boxtemp` and `humidity` were NULL.
Both modules' connections still needed clarification; the responding sensor
was clearly SCD41. NDJSON from the current flash buffer was queried again.

## Successful SHT45 acquisition after further wiring correction

Both sensors returned valid readings simultaneously for the first time:
sequence 159, boot ID `1364144317`, `sht_read_uptime_ms=794192`.
SHT45: 23.52 degrees C, 50.91 %RH. SCD41: 288 ppm CO2, 23.30 degrees C,
43.85 %RH. SHT45 values came from a fresh scheduled reading, not an old repeat.
Valid SHT45 data was also confirmed in current LittleFS NDJSON. The complete
heater/cooldown cycle was not yet separately verified.

## Repeated measurement including heater/cooldown timing

Both remained valid at sequence 185: SHT45 24.63 degrees C, 46.04 %RH raw,
47.04 %RH with +1 percentage point offset; SCD41 493 ppm, 26.62 degrees C,
45.15 %RH. SHT45 timestamp increased from 859192 to 924192 ms (65 s).
Firmware reported `sht_heater_elapsed_ms=60010`, indicating at least 60 s
cooldown. This is firmware timing evidence, not an independent electrical
heater-power measurement. Boot ID unchanged, flash ready, SCD error count 0.

## Successful external-supply operation without USB

User-reported supply: 5 V on the 5 V pin, USB disconnected. Device reachable
at `192.168.31.211`; ARP confirmed MAC `14:c1:9f:5c:c8:b4`.
Final check before commit: boot ID `2924729219`, sequence 33, uptime 162187 ms,
SCD errors 0, LittleFS ready. SHT45: 24.40 degrees C and 41.71 %RH raw,
42.71 %RH corrected; SCD41: 337 ppm, 24.51 degrees C, 46.63 %RH.
All available readings were valid. SHT45 cooldown was 60010 ms.
ESP32-S3 therefore operated successfully without USB on the external supply.
