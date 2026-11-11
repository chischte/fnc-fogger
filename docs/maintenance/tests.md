# Tests und vorhandene Testergebnisse

Stand: 11. November 2026, nach Portenta-Cleanup und Geräteübersicht.

## 1. Ausführbare Softwaretests: behalten

Das sind **Prüfprogramme, keine alten Ergebnisdateien**. Sie laufen nicht im
normalen Logger-/Viewer-/Firmwarebetrieb. Ein Löschen spart kaum Platz,
verhindert aber, dass wir spätere Änderungen auf dieselben Fehler prüfen.
Alle 17 Gruppen prüfen weiterhin verwendete ESP32-, Logger- oder Viewer-Funktionen.
Ich empfehle, diese Gruppen zu behalten. Es wurde keine Testgruppe gelöscht.

Letzter Durchlauf nach dem Cleanup: **113 Tests, alle bestanden**; keine Gruppe
übersprungen. Beide verbleibenden Firmwareprofile (`esp32c3_supermini` und
`esp32s3`) wurden nach dem Cleanup erfolgreich gebaut. Es wurde keine
Firmware auf ein Gerät geladen.

Der Sensor-Wiederanschlusstest wurde vom früheren zweiten
Portenta-Bus auf den tatsächlich genutzten ESP32-Bus umgestellt. Die zweite
Bussuche selbst wurde als Portenta-Code entfernt.

Befehl: `python -m unittest discover -s test -p "test_*.py"`.
Die C++-Prüfungen benötigen hier Windows mit Clang/LLD. Sie verwenden
Fake-Hardware und ersetzen keinen realen elektrischen Hardwaretest.

| Testdatei | Testmethoden | Zweck |
| --- | ---: | --- |
| [test_device_overview.py](../../test/test_device_overview.py) | 7 | Nur-Lese-Abfragen, Gerätetrennung, Hauptlinien und feste Skalen, Diagrammklicks, Dark Mode/Vollbild, OTA-Sperre und sieben Gerätespalten. |
| [test_background_logger.py](../../test/test_background_logger.py) | 8 | Daueraufzeichnung ohne Viewer, Puffernachladung, Messzeitpunkte, Geräte-ID, Prozesssperre und Heartbeat. |
| [test_control.py](../../test/test_control.py) | 12 | Sollwertübertragung, Bestätigung, Live-Telemetrie, Reglerdiagramme und Wertedarstellung. |
| [test_control_settings.py](../../test/test_control_settings.py) | 1 | Sollwerte nach Neustart, NVS-Fehler, Wertebereiche und Speicherung als zusammengehöriges Paar. |
| [test_esp32_ota.py](../../test/test_esp32_ota.py) | 1 | Echte ESP32-Updater-Logik gegen Fake-Flash: Schreibfehler, Profilprüfung, Abschluss und Neustart. |
| [test_firmware_management.py](../../test/test_firmware_management.py) | 9 | Falsche Geräte-/Chipzuordnung verhindern, Firmware-Metadaten und OTA-Neustartbestätigung. |
| [test_i2c_diagnostics.py](../../test/test_i2c_diagnostics.py) | 1 | I²C-Scan, gefundene Adressen und nicht blockierender Ablauf. |
| [test_lance_selection.py](../../test/test_lance_selection.py) | 19 | Geräteverwaltung, Datenbankzuordnung, Titelbearbeitung, Entfernen pro Spalte, Firmware-Zielauswahl, Zwischenablage, Navigation und Viewer ohne Messdatenschreibzugriff. |
| [test_logger.py](../../test/test_logger.py) | 12 | SQLite-Schema, Deduplizierung, Messwertfelder sowie Import/Export und historische Datenverträglichkeit. |
| [test_manual_control.py](../../test/test_manual_control.py) | 6 | Manual Mode, direkte Reglerwerte, getrennte Schalter, Stop All, Befehlsbestätigung und Verbindungsverlust. |
| [test_sensor_recovery.py](../../test/test_sensor_recovery.py) | 1 | Echter SCD41/SHT45/SHTC3-Code mit Fake-Sensoren: Ausfall, Wiederanschluss, CRC, Heizung und Abkühlzeit. |
| [test_startup_actuators.py](../../test/test_startup_actuators.py) | 1 | GPIO-Ausgänge, Starttest, PWM/Tacho, manuelle Pulsung, Timeout, Wiederanlauf-Schutz und OTA-Stopp. |
| [test_viewer_cache.py](../../test/test_viewer_cache.py) | 4 | SQLite-/CSV-Lesen, inkrementeller Cache und nachträglich eintreffende Messungen. |
| [test_viewer_refresh.py](../../test/test_viewer_refresh.py) | 3 | Darstellungsaktualisierung und unnötige Neuberechnungen vermeiden. |
| [test_viewer_sensors.py](../../test/test_viewer_sensors.py) | 8 | Fehlende Werte, SHTC3-/PT100-Abgrenzung und Temperatur-/Feuchteanzeigen. |
| [test_viewer_stepper.py](../../test/test_viewer_stepper.py) | 7 | CO2-/Feuchte-Eingaben, Plus/Minus, Grenzen, unveränderte gespeicherte Werte. |
| [test_viewer_window.py](../../test/test_viewer_window.py) | 13 | Fenster, Taskleiste, Größenänderung und Verknüpfung mit Windows-Fensterfunktionen. |

Bei `test_*.cpp` stehen viele konkrete Prüfungen innerhalb einer einzelnen
Testmethode des zugehörigen Python-Starts. Die C++-Dateien und Ordner
`test/*_fakes/`, `test/fakes/` enthalten Prüfcode bzw. simulierte Hardware.
Sie sind keine Ergebnisablage und dürfen nicht unabhängig von den zugehörigen
Testgruppen entfernt werden.

## 2. Wo sind die Softwaretestergebnisse abgelegt?

Der Testlauf schreibt seine genaue Ausgabe normalerweise nur ins Terminal.
Ein vollständiger zentraler HTML-/JUnit-Testbericht wurde bisher nicht
versioniert. Frühere kurze Ergebnisnotizen stehen in
[Hintergrundlogger](../background-logger.md), [Steuerung](../control.md) und
[Geräteverwaltung](../device-management.md). Diese Datei fasst jetzt die
Testgruppen und den aktuellen Gesamtausgang zusammen.

Ein Satz wie „101 Tests bestanden“ ist kein Ersatz für die Testprogramme:
Er belegt nur einen früheren Durchlauf und prüft keine zukünftigen Änderungen.

## 3. Historische Hardwareversuche und Berichte: behalten

Diese Dateien werden im Betrieb nicht eingelesen. Ein Löschen beeinflusst
Firmware, Logger und Viewer nicht, entfernt aber den jeweiligen Nachweis.
Die folgende Auswahl bleibt auf Wunsch erhalten. Entfernt wurden der alte
Viewer-Ausfallbericht, die PT100-Untersuchung sowie der frühere S3-Hardware-
und mDNS-Testbericht. Frühere Fassungen sind über Git verfügbar.

| Archivdatei / Ordner | Inhalt | Bereits anderweitig zusammengefasst? | Einschätzung |
| --- | --- | --- | --- |
| [esp32c3-mini-01-test-2026-11-09.md](../archive/esp32c3-mini-01-test-2026-11-09.md) | Erste USB-/OTA-Inbetriebnahme von 27:CA:14, Flashdaten und Versionsnachweis | Erfolg kurz in der Geräteverwaltung; Details nur im Bericht | Als Inbetriebnahmenachweis behalten, sonst optional |
| [esp32c3-mini-02-test-2026-11-09.md](../archive/esp32c3-mini-02-test-2026-11-09.md) | Zweiter C3, USB/OTA und Geräteidentität | Erfolg kurz in der Geräteverwaltung; Details nur im Bericht | Wie Mini 01 |
| [sht45-noheater-trial-2026-10-25.md](../archive/sht45-noheater-trial-2026-10-25.md) | Temperaturvergleich mit ausgeschalteter SHT45-Heizung und Rückkehr zum Heizzyklus | Kein gleichwertiger vollständiger Bericht andernorts | Behalten: weiterhin relevanter Sensortyp |
| [heater-test-2026-09-24/README.md](../archive/heater-test-2026-09-24/README.md) | Zusammenfassung des Heiz-/Abkühlversuchs mit sechs Zyklen | Diese README ist bereits die verständliche Zusammenfassung | README möglichst behalten |
| [heater-test-2026-09-24/measurements.csv](../archive/heater-test-2026-09-24/measurements.csv) | Originalmesswerte dieses Versuchs | Nur Auszüge/Statistiken in README und JSON | Wichtigste Rohdaten; nicht als Duplikat ansehen |
| [heater-test-2026-09-24/summary.json](../archive/heater-test-2026-09-24/summary.json) | Detaillierte berechnete Auswertung des Versuchs | Kernaussagen in README, nicht alle Detailwerte | Optional, wenn README und CSV ausreichen |
| [heater-test-2026-09-24/cooldown.png](../archive/heater-test-2026-09-24/cooldown.png) | Grafische Darstellung der Abkühlung | Gleiche Daten teilweise als Tabelle in README/CSV | Am ehesten verzichtbares abgeleitetes Ergebnisbild |

Die Dateien `hardware-migration-esp32s3.md` und `control-preparation.md` sind
zusätzliche historische Entwicklungsnotizen, keine ausführbaren Tests. Sie
bleiben ebenfalls erhalten.

Die Verweise auf die vier entfernten Berichte wurden bereinigt. Alle
ausführbaren Tests und die übrigen historischen Versuchsdaten bleiben erhalten.

## 4. Portenta und Prompt-Dateien

Portenta-Buildziele, sieben Portenta-Hilfs-/Implementierungsdateien und sieben
Prompt-TXT-Dateien wurden auf Wunsch entfernt. Details stehen in der
[Dateiprüfung](file-review.md). Die frühere Historie liegt in Git. Das fertige
Anschlussbild und seine kurze [Änderungshistorie](../diagrams/README.md) bleiben.
