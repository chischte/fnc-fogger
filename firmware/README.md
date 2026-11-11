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

Vorbereiteter Stand: **3.4.2**, MOSFET-Gate **GPIO3**, FAN PWM GPIO5 und
FAN TACH GPIO6. Vor der Installation die Gate-Leitung an GPIO3 anschließen.
Der [SVG-Anschlussplan](../docs/fnc-fogger-wiring.svg) und die
[Pinbelegung](../docs/hardware.md) zeigen GPIO3. Kein automatischer Upload.
