# Dateiprüfung und Aufräumen

Stand: 11. November 2026. Geprüft wurden die vorhandenen Dateien, Git-Dateiliste, Verweise in README/Dokumentation und die Build-Konfiguration. Portenta-spezifische Programmdateien und die Prompt-TXT-Dateien wurden auf ausdrücklichen Wunsch entfernt. Messdaten und die übrigen Testberichte bleiben erhalten; die vier ausdrücklich ausgewählten historischen Berichte wurden entfernt.

## Ohne fachlichen Datenverlust regenerierbar

| Datei/Ordner | Einschätzung |
| --- | --- |
| `.pio/` | Build-Produkte und lokale PlatformIO-Buildabhängigkeiten. Bei beendetem Build und Upload löschbar; nächster Build benötigt Zeit und eventuell Downloads. Zuvor benötigte Firmware-BINs separat behalten. |
| `**/__pycache__/`, `*.pyc` | Python-Cache. Löschbar, wird automatisch neu erstellt. |
| `.vscode/.browse.c_cpp.db*`, `.vscode/ipch/` | Falls vorhanden: Editor-Indizes, können bei geschlossenem Editor neu aufgebaut werden. |

Diese Dateien sind bereits überwiegend durch `.gitignore` ausgeschlossen. Sie wurden nicht gelöscht und sind keine Ursache der unübersichtlichen Dokumentation.

## Prompt-Dateien: für den Betrieb nicht benötigt

Die folgenden sieben Prompt-Dateien wurden auf Wunsch gelöscht (vorher unter `docs/diagrams/prompts/`):

- `layout-v4-prompt.txt`
- `layout-fogger-5v-prompt.txt`
- `layout-power-no-crossing-prompt.txt`
- `layout-english-prompt.txt`
- `layout-buck-common-ground-prompt.txt`
- `layout-i2c-net-colors-prompt.txt`
- `layout-gate-gpio21-prompt.txt`

Die Dateien wurden bei KI-Bildgenerierungen und Bildkorrekturen als Protokoll
der jeweiligen Bildanweisung angelegt. Kein Build- oder Laufzeitprozess liest
sie. Sie sind keine ausführbaren Tests und keine notwendige Quelle für das
fertige PNG. Die Bild-Änderungshistorie bleibt ohne Prompt-Verweise bestehen;
frühere Prompt-Inhalte sind über Git abrufbar.

`docs/layout-generation.md` wurde nach `docs/diagrams/README.md` verschoben. Das aktuelle Bild `docs/fnc-fogger-layout-v4.png` bleibt an seinem bekannten Ort und wird weiterhin von README und Hardwaredokumentation verwendet.

## Historische Unterlagen: verbleibendes Archiv

Unter `docs/archive/` liegen nun:

- `control-preparation.md`
- `esp32c3-mini-01-test-2026-11-09.md`
- `esp32c3-mini-02-test-2026-11-09.md`
- `hardware-migration-esp32s3.md`
- `sht45-noheater-trial-2026-10-25.md`
- `heater-test-2026-09-24/` mit README, CSV, PNG und JSON

Diese Unterlagen bleiben auf Wunsch erhalten. Entfernt wurden der alte Viewer-Ausfallbericht, die PT100-Untersuchung sowie der frühere S3-Hardware- und mDNS-Testbericht. Deren frühere Fassungen liegen in Git. Die Dokumentationsverweise wurden angepasst.

## Alte Firmware-BINs: nur bewusst entfernen

Die Versionen 3.2.2 und 3.3.0–3.3.2 unter `firmware/` sind frühere Zwischenstände und keine Laufzeitabhängigkeit des PC-Loggers. Löschen würde jedoch diese lokalen Rückfallversionen entfernen. Nicht jeder historische uncommittete Quellstand ist exakt aus Git reproduzierbar.

Behalten: 3.2.1 als zuletzt bestätigter Stand der Lanze 27:CA:14, 3.4.0 als zuletzt bestätigter Stand von 28:8A:EC und 3.4.1 als vorbereiteter Stand für Gate GPIO21. Alle `.bin`/`.json`-Paare zusammen behandeln. Die Daten in `firmware/archive/` wurden nicht verändert.

## Portenta-Cleanup durchgeführt

Entfernt wurden die PlatformIO-Ziele `portenta_h7_m7` und `qspi_formatter` sowie:

- `disable_portenta_touch.py`
- `make_ota.py`
- `tools/bin2ota.py`
- `tools/lzss.py`
- `src/qspi_formatter.cpp`
- `src/firmware/qspi_storage.cpp` (Portenta-Implementierung)
- `src/firmware/firmware_updater.cpp` (Portenta-Implementierung)

Alle sieben Dateien waren bereits in Git versioniert. Die ESP32-Implementierungen
unter `src/esp32/` und die gemeinsamen öffentlichen Schnittstellen bleiben.
Entfernt wurden außerdem mbed-/Portenta-Felder, der Portenta-Firmwarezweig und
die zweite I²C-Bussuche. Das ESP32-S3-Profil samt Partitionstabelle bleibt als
Legacy-Ziel erhalten; dessen Entfernung wurde nicht beauftragt.

`logger/backup.py` bleibt erhalten: Es kann von einem externen Windows-Task
verwendet werden und sichert derzeit nur die alte `measurements.db`. Die neue
Mehrgeräte-Backup-Abdeckung muss separat geprüft/modernisiert werden.

## Weiterhin benötigt beziehungsweise wertvoll

- `logger/logger.py`: trotz altem CLI-Startmodus wichtig; der neue Hintergrundlogger verwendet daraus Datenbankschema, Normalisierung und HTTP-Helfer.
- `logger/background.py`, `measurement_recording.py`, `process_lock.py`, `background_process.py`: aktuelle Daueraufzeichnung.
- `start_logger.ps1`, `start_monitoring.ps1`, `check_logger.ps1`, `install_logger_autostart.ps1`: Start und Windows-Überwachung.
- `include/`, `src/`, `test/`, `tools/build_identity.py`, `platformio.ini`, Partitionstabellen: Firmware, Tests und Build.
- `assets/monitoring-eye.*`: tatsächlich verwendete Fenster-/Taskleistensymbole.
- `screenshot_viewer.jpg`: historischer Viewer-Screenshot; nach Kürzung des Haupt-README nicht mehr eingebunden. Technisch entbehrlich, noch nicht gelöscht.
- `.vscode/extensions.json`: optionale Editor-Empfehlungen, keine Laufzeitabhängigkeit; klein und absichtlich vorhanden.
- `logger/data/lances.db`, `logger/data/devices/`, `logger/data/measurements.db`, Mess-CSV und `logger/data/recovery/`: Gerätezuordnung, Messhistorien und Sicherungen. Nicht zur Bereinigung löschen.
- SQLite-Dateien `*-wal` und `*-shm`: bei laufenden Prozessen niemals als vermeintlichen Cache löschen; im WAL können noch nicht in die Hauptdatei übernommene Messungen liegen.
- `wifi-credentials.h` (normalerweise eine Ebene oberhalb des Projekts): lokale WLAN-Zugangsdaten, nicht versioniert; für einen neuen Firmware-Build benötigt.
- `.git/`: Versionshistorie, keine Bereinigungsdatei.

## Ergebnis

Direkt unter `docs/` stehen jetzt nur die sechs aktuellen Fachanleitungen, diese [Dokumentationsübersicht](../README.md) und der Anschlussplan. Historie und Wartungsübersicht liegen getrennt. Portenta-Code und Prompt-Dateien wurden wie oben beschrieben entfernt; der laufende Logger und seine Windows-Aufgaben wurden nicht verändert. Alle ausführbaren Tests und die übrigen historischen Unterlagen und Versuchsdaten bleiben erhalten.

Validierung: 101 Softwaretests bestanden, beide ESP32-Profile erfolgreich gebaut,
alle lokalen Dokumentationslinks geprüft. Keine Gerätefirmware installiert.
