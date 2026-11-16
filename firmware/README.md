# Firmwaredateien für OTA

Dieser Ordner enthält die zum Hochladen vorbereiteten Firmwaredateien.
Nach einem Firmwarebuild exportiert das Buildskript BIN und JSON-Manifest
automatisch hierher. Die internen PlatformIO-Builddateien bleiben unter `.pio/build`.

Dateinamen: `fnc-fogger-firmware_<version>.bin`, zum Beispiel
`fnc-fogger-firmware_3.2.1.bin`. Aktuell werden nur ESP32-C3 SuperMinis eingesetzt;
`pio run` und das Uploadskript verwenden deshalb standardmäßig dieses Profil.
Das gleichnamige JSON enthält die Dateigröße, Prüfsumme und Firmwaredaten.
Im Viewer das gewünschte Gerät auswählen, `Update Firmware` öffnen
und die passende BIN-Datei auswählen. Die Dateiauswahl startet in diesem Ordner.

Hardwareprofil und Buildkennung bleiben im Image und JSON für die
Kompatibilitätsprüfung erhalten. Der Dateiname enthält diese Angaben nicht.
Ein erneuter Build derselben Version ersetzt BIN und JSON dieser Version.
Andere Versionsnummern bleiben als eigene Dateien erhalten.

Alte Dateinamen sind unter `archive/` abgelegt. Ausdrückliche Builds für
frühere Hardwareprofile werden unter `legacy/<profil>/` exportiert.

Die Dateien werden lokal aufbewahrt und nicht in Git eingecheckt. Sie können
eingebaute WLAN-Zugangsdaten enthalten. Ältere Builds bleiben erhalten und
werden nicht automatisch installiert.

Aktueller Teststand: **3.5.2**, MOSFET-Gate **GPIO3**, FAN PWM GPIO10 und
FAN TACH GPIO7. Vor der Installation die Lüftersignale entsprechend umlegen.
GPIO8 und GPIO9 bleiben als Boot-Konfigurationspins frei.
Der [SVG-Anschlussplan](../docs/fnc-fogger-wiring.svg) und die
[Pinbelegung](../docs/hardware.md) zeigen GPIO3. Kein automatischer Upload.

Firmware 3.4.4 ergänzt die passive USB-WLAN-Diagnose: Bei Statusänderungen und
alle zehn Sekunden erscheinen `[wifi]`-Zeilen mit Status und letztem
Verbindungsabbruchgrund, bei Verbindung zusätzlich IP, RSSI und Kanal.
SSID und Passwort werden nicht ausgegeben. Pinbelegung und Verbindungslogik
bleiben gegenüber 3.4.3 unverändert. Eine Installation erfolgt nicht automatisch.

Firmware 3.4.5 erweitert die Diagnose um USB-Kommandos (115200 Baud, Zeilenende):
`wifi status`, `wifi scan`, `wifi power low`, `wifi power default`.
Der Scan sucht nur das konfigurierte WLAN und meldet RSSI, Kanal, numerischen
Sicherheitsmodus und BSSID ohne SSID/Passwort. Er ist nur im nicht verbundenen
Zustand erlaubt; reguläre Verbindungsversuche pausieren während des asynchronen
Scans. `wifi power low` testet 8,5 dBm, `wifi power default` stellt den zuvor
ausgelesenen Wert wieder her. Die Sendeleistungsänderung ist vorerst nur im RAM
und wird durch Neustart verworfen. Keine Aktorbefehle über diese USB-Konsole.

Firmware 3.4.6 setzt für alle Geräte fest **8,5 dBm** als WLAN-Sendeleistung
(`Config::WIFI_TX_POWER_QDBM = 34`). Keine gerätespezifische NVS-Vorgabe.
USB: `wifi power default` stellt 8,5 dBm wieder her; `wifi power <dBm>` erlaubt
vorübergehend 2, 5, 7, 8.5, 11, 13, 14, 15, 16.5, 18 und 20 dBm.
`wifi reconnect` wiederholt die WLAN-Anmeldung ohne MCU-Neustart oder Aktor-Test.
Neustart stellt immer den Firmware-Standard wieder her. Der Scan pausiert auch
Arduino-Auto-Reconnect und ist bei bestehender Verbindung nicht erlaubt.

Firmware 3.4.7: Manual Mode has no command timeout (`lease_ms=0`). Closing the
viewer does not stop outputs. Device Wi-Fi loss stops both outputs, including
brief disconnects; reconnect does not restart them. Manual values are not
restored on reboot. Explicit Off and firmware-update shutdown remain available.
Pin mapping and the global 8.5 dBm Wi-Fi default are unchanged.

Firmware 3.5.0: CO₂ PI ventilation commissioning, fan 15–80%, explicit Start PI /
Stop PI in Command Mode. Humidity PI is prepared but **fogger outputs are locked
OFF**, including manual commands and startup pulses. Wi-Fi loss, update or reboot
stops PI; it does not resume automatically. Parameters and measured limits:
[PI commissioning](../docs/pi-commissioning.md). Installed only on the chamber
device `B8:1F:3F:27:F4:E0`, with CO₂ setpoint 2,500 ppm.

Firmware 3.5.1: fan minimum 12%, CO₂ Kp 0.02 %/ppm, Ti unchanged at 300 s. Startup tests
are skipped to avoid perturbing chamber measurements. Fogger remains locked OFF.
The chamber setpoint is now 2,000 ppm. Viewer setpoints autosave after 3 s idle;
restart the viewer to load the new UI. See the current PI commissioning revision.

3.5.1 also bridges missing CO₂ samples using the last valid value for less than
15 s without integrating held samples. Longer outages latch the user-selected
10% fan fallback (not the PI sum). Hardware-unavailable output stays zero.
The viewer labels fallback separately, with actual PWM and RPM and gaps in PI
traces. Valid data alone does not automatically clear a latched fault.

Firmware 3.5.2 enables humidity PI: corrected SHT45 target 90% RH, Kp=1,
Ti=600 s, automatic fogger cap 20%, fixed 100-ms ON pulses with variable OFF.
Fogger still requires CO₂-requested ventilation and valid fan tach. CO₂ tuning
and skipped startup tests remain unchanged. See [current commissioning](../docs/pi-commissioning.md).
The viewer displays Kp and readable Ti under each PI graph; restart it to load
these UI changes. Manual output behavior is unchanged.

## Revision 3.5.3

Der CO2-PI behält beim Erreichen des Sollwerts seinen I-Anteil. Unterhalb
des Sollwerts nimmt die Stellleistung kontinuierlich ab. Positive Anforderungen
werden mit mindestens 12% Lüfterleistung umgesetzt; erst bei berechneten 0%
stoppt der Lüfter und sperrt den Fogger. Neustart weiterhin oberhalb Sollwert
plus 50 ppm. Kp, Ti und alle übrigen Grenzen bleiben unverändert.

## Revision 3.5.4

Die Mindestleistung von 12% entfällt. Der Lüfter folgt dem CO2-PI von 0–80%.
Der Fogger darf bei gültiger gemessener Drehzahl über 0 rpm weiterregeln,
auch während des Auslaufens bei 0% PWM. Bei 0 rpm oder ungültigem Tachosignal
wird er gesperrt. Unter 10% PWM gilt ein stehender Lüfter als erwartbar;
ab 10% bleibt die Stillstandserkennung nach fünf Sekunden aktiv.

## Revision 3.5.5

PI ist außerhalb des manuellen Modus automatisch aktiv, auch nach Neustart
und WLAN-Rückkehr, sobald gültige CO2-Messwerte vorliegen. „Reset PI“ im Viewer
setzt die angesammelten I-Anteile zurück; Kp, Ti und Sollwerte bleiben erhalten.
Fehlersperren bleiben bestehen. Nach behobenem Fehler kann ein bewusster Wechsel
in den manuellen Modus und zurück die Regelung neu starten.

## Revision 3.5.6

15-Minuten-Feuchteabgleich im Manual Mode: Lüfter 50%, Fogger 100%, danach
beide absolute Offsets zur angenommenen 100-%-Referenz dauerhaft in NVS speichern
und zu PI zurückkehren. Abbruch/WLAN-Ausfall speichert keine neuen Offsets.
Maximaler automatischer Feuchte-Sollwert 99%. Rohwerte und die SCD41-Schutzprüfung
bleiben unverändert; sichtbarer Nebel ist keine gesicherte Kalibrierreferenz.

## Revision 3.5.7

Bei normaler Lüfterpause bleibt der Fogger-I-Anteil erhalten; der Ausgang ist
gesperrt. Beim Wiederanlauf wird P aus der aktuellen Feuchte berechnet und
ohne nachträgliche Integration der Pause weitergeregelt. Sensorfehler,
Überfeuchte und Reset PI setzen weiterhin zurück. Parameter bleiben unverändert.

## 3.5.8

Automatic fogger output now permits 0-50%; fan remains 0-80%. Both PI loops
run continuously through normal setpoint crossings and zero output, keeping
signed P and nonnegative I terms. I is bounded to 0 through each channel's maximum;
positive accumulation into upper output saturation remains inhibited. Normal
RH overshoot no longer resets humidity PI. Sensor, fan and condensation
fault handling is unchanged. Manual and calibration output limits are unchanged.

## 3.5.9

Removes the SCD41 humidity condensation fault and limits humidity setpoints to
98% of the calibrated SHT45 reading. Automatic fogger maximum remains 50%.
Calibration offsets, PI anti-windup and sensor/network/fan handling are unchanged.

## 3.5.10

Retunes both PI channels with stronger P and unchanged integral gains:

- CO2: Kp: 4 %/100 ppm | Ki: 0.4 %/(100 ppm·min) | Ti: 10 min
- Humidity: Kp: 1.5 %/%RH | Ki: 0.1 %/(%RH·min) | Ti: 15 min

Limits, anti-windup, setpoints and calibration are unchanged from 3.5.9.

## 3.6.0

Adds device-side Cyclic Mist with persistent On/Off state, 1-10 minute mist
time and 1-10/15-60 minute pause settings. Mist phases override fogger output
to continuous 100% while holding humidity PI. Normal humidity PI resumes in
the pause; CO2 PI continues. Saved cycles survive reboot and continue during
Wi-Fi loss. Manual mode/calibration temporarily take priority. Defaults Off.
Maximum calibrated humidity setpoint increases from 98% to 99%.

## 3.6.1

Adds ON=0 as a persistable disabled Cyclic Mist duration. Positive ON durations
1-10 minutes enable the cycle in the viewer; the separate toggle is removed.
The compact timing row has its own frame directly below the main controls.

## 3.6.2

Cyclic Mist now holds both PI loops during ON, with fixed fan 50% and fogger
100%. Both resume with retained I after ON, excluding mist time from integration.
OFF is 10-60 minutes in steps of 5; older shorter pauses migrate to 10.

## Cyclic Mist per hour (firmware 3.6.3)

The viewer offers one ON-time stepper: 0 (disabled) or 1-10 minutes per hour.
The pause is calculated as 60 minus the ON time, so 5 minutes means 5 minutes
of mist followed by 55 minutes of normal PI operation. Settings changes retain
both PI integrals and all PI gains. A changed schedule starts a new mist phase.
The API also retains support for legacy independent pause values; firmware 3.6.3
accepts integer pauses from 10 to 60 minutes. Existing saved schedules are
unchanged until the hourly setting is explicitly submitted. A firmware install
requires a reboot and therefore resets volatile PI state; do not install while
that state must be preserved.

## Firmware 3.6.4: humidity emergency and startup test

During automatic operation, a continuous valid, fresh calibrated humidity deficit
strictly greater than 10 percentage points for strictly more than 30 minutes
latches a humidity emergency. Invalid/stale humidity, recovery to the threshold,
or interrupted automatic operation clears the pending timer. Missing observation
intervals of 135 seconds or more do not count as continuous evidence.

The effective CO2 target becomes 5,000 ppm, with unchanged PI gains and limits.
The configured CO2 setpoint stays saved. Both cyclic-mist output overrides are
suspended while latched, so they cannot force the fan to 50%; normal humidity PI
continues subject to the existing sensor/RPM checks. The saved mist schedule is
retained. This is inferred humidification failure, not confirmed empty water.

The latch survives humidity recovery, setpoint edits and Reset PI. Restarting the
device or entering Manual Mode releases it; returning to PI starts a fresh
30-minute observation. Existing sensor and fan fault handling retains priority.

The API includes `humidity_emergency.active` and `co2_target_ppm`; the independent
logger records these in `control_samples.control_json`. Viewer warnings are bold
red. CO2 SET/DIF and recorded setpoint graphs use the effective target while the
editable Control Panel keeps the configured target.

Startup testing is enabled again: 1-second initial delay, one 3-second fan pulse
at 100%, concurrent fogger pulses of 100 ms ON / 100 ms OFF, then a 1-second pause.
An OTA installation restarts the device and resets volatile PI state.

Firmware **3.6.6** adds automatic SHT45/SCD41 sensor recovery, bounded I2C
peripheral restarts, outage/restart counters and heater timing diagnostics.
CO2 sensor interruptions now resume automatically with preserved PI integrals;
fan and hardware faults remain latched. See [control documentation](../docs/control.md).

Firmware **3.6.7** preserves PI integrals across mode/fault/setpoint transitions
and restores them from NVS after reboot/OTA or compiled Kp/Ti changes. Normal
checkpoints are 30 seconds apart; mode changes and OTA force a checkpoint.
Only explicit Reset PI clears the persisted integrals. Initial migration from
3.6.6 requires capturing and restoring live integrals once; see [control documentation](../docs/control.md).

## Firmware 3.6.8: automatic fogger maximum 60%

Automatic humidity PI output and its integral ceiling are increased from 50% to 60%.
Existing PI integrals and tuning are retained. Cyclic mist and manual output still permit 100%.

## Firmware 3.6.9: retain cyclic mist timing across restarts

The device persists the UTC start of each cyclic mist period in NVS. After a
restart it skips the interrupted mist phase and waits until the next period is
due, rather than starting another mist immediately. Changes to the mist duration
preserve the period origin and both PI integrals. An overdue period starts once;
missed periods are not replayed.

Clock recovery is nonblocking, using NTP or the logger/viewer X-Unix-Time header.
Until a valid clock is available, cyclic mist waits; ordinary PI control continues.
Without an earlier saved start, the initial wait is one full period. The migration
endpoint POST /api/control/cyclic-mist-phase accepts last_start_unix to restore a
known earlier start from recorded telemetry. This does not change PI memory.

## Firmware 3.6.10: automatic fogger maximum 100%

Automatic humidity PI output and its integral ceiling now allow 0-100%.
At 100%, the fogger remains continuously on. Fan maximum remains 80%.
Existing PI integrals, tuning, setpoints and the persisted cyclic mist origin are retained.
