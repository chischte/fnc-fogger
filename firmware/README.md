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

Vorbereiteter Stand: **3.4.6**, MOSFET-Gate **GPIO3**, FAN PWM GPIO10 und
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
