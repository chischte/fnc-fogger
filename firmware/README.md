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
