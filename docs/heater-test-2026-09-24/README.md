# SHT45 cooldown test, 2026-09-24

Firmware 2.0.11, boot ID 1971548083. Six nominal 200 mW, 1 s heater pulses,
120 s apart, from 01:19:21 to 01:29:22 (Europe/Zurich). Heating then stopped
automatically; follow-up continued until about 01:45. All heating and cooldown
readings remain recorded.

## Result

Temperature largely recovered after about 90 s in this assembly. Humidity
showed a much longer recovery. Complete humidity stabilization after 60 or
90 s was not demonstrated. The small 90-to-110 s difference underestimates
longer recovery.

### Comparison across six cycles

Difference from each cycle's reading about 110 s after the stored heater
peak; median over six cycles. This is relative comparison, not absolute calibration.

| Wait | Temperature difference | Humidity difference |
| --- | ---: | ---: |
| 30 s | +0.11 degrees C | -1.01 percentage points |
| 45 s | +0.06 degrees C | -0.52 percentage points |
| 60 s | +0.04 degrees C | -0.31 percentage points |
| 90 s | +0.01 degrees C | -0.12 percentage points |

### After the last heater pulse

| Time since heater peak | SHT45 temperature | SHT45 humidity | SCD41 humidity |
| --- | ---: | ---: | ---: |
| 60 s | 24.98 degrees C | 84.95 %RH | 81.43 %RH |
| 90 s | 24.93 degrees C | 85.12 %RH | 81.40 %RH |
| 110 s | 24.95 degrees C | 85.25 %RH | 81.42 %RH |
| 180 s | 24.95 degrees C | 85.50 %RH | 81.41 %RH |
| 300 s | 24.90 degrees C | 85.81 %RH | 81.43 %RH |
| 600 s | 24.87 degrees C | 86.14 %RH | 81.55 %RH |
| 900 s | 24.87 degrees C | 86.51 %RH | 81.59 %RH |

## Interpretation and recommendation

- Temperature: provisionally wait 90 s for the tested assembly.
- Humidity: do not treat 60/90 s as fully stable. Provisionally wait at least five minutes and monitor rate of change, for example less than 0.1 percentage point per minute over two minutes. This is a proposed criterion, not a manufacturer guarantee. The observed curves may require about 10-15 minutes.
- Humidity still rose 0.70 percentage point between five and 15 minutes. Five minutes alone therefore does not guarantee equilibrium. Without an independent reference, slow real ambient changes or humidity-offset changes cannot be excluded.
- SCD41 humidity stayed comparatively steady (about 81.4-81.6 %RH), but is not a calibrated reference. Inbox PT100 was also recorded.
- Results apply to this installation near 25 degrees C and 85 %RH, not automatically to other temperatures, airflows or condensation conditions.

## Data and operating state

All six heater peaks and 60/90/110 s comparison points are saved. One missing
logger record (sequence 212) follows the five-minute comparison phase and does
not affect these comparisons. Sequence 1 is also missing before the first
pulse. Times refer to the stored heated reading; five-second acquisition means
approximate waits rather than millisecond-accurate times since heater shutdown.

Heating stops automatically after six pulses. Restarting the test firmware
starts another trial limited to six pulses. Normal recording of all sensors
continues. Valid readings are still not discarded because of heating.

- [Measurement CSV](measurements.csv)
- [Complete analysis JSON](summary.json)
- [Chart](cooldown.png)

Manufacturer reference: [Sensirion: Using the Integrated Heater of SHT4x in High-Humidity Environments](https://sensirion.com/media/documents/A88858C9/629626D4/Application_Note_Creep_Mitigation_SHT4x.pdf).
The one-minute interval there is an example for a particular assembly; thermal
and humidity recovery must be established on the actual device.
