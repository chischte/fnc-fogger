# Diagramm-Änderungshistorie

Aktueller [Anschlussplan](../fnc-fogger-layout-v4.png).
Pinbelegung und elektrische Grenzen stehen in [Hardware](../hardware.md).
Zurück zur [Dokumentationsübersicht](../README.md).

## Aktueller Stand

ESP32-C3 SuperMini mit SDA GPIO0, SCL GPIO1, Fan PWM GPIO5, Fan TACH GPIO6
und MOSFET-Gate GPIO21. Die Controller-Grafik zeigt die Kontakte direkt am
Board; sie ist eine Pinpositions-Illustration, keine exakte Fotografie.
GPIO21 kann vor dem Firmwarestart UART0-Bootsignale ausgeben.

Der Fan liegt an 24 V, ESP32 und Fogger an Buck OUT+ mit 5 V. Buck IN− und
OUT− sind im verwendeten Modul intern verbunden und im Plan entsprechend
dargestellt. Sensorleitungen: 3,3 V rot, GND schwarz, SDA blau, SCL gelb.
Der optionale SHTC3 ist gestrichelt am gemeinsamen Sensorbus dargestellt.

## Wesentliche Bildänderungen

| Zeitpunkt | Änderung |
| --- | --- |
| Oktober 2026 | ESP32-C3 SuperMini und kompakter XZG-Buck ersetzen frühere Darstellungen |
| 8. November 2026 | Optionaler SHTC3 am selben I²C-Bus ergänzt |
| 9. November 2026 | Fogger auf 5 V, getrennte 24-V-/GND-Netze, englische Beschriftung, Noctua-Kabelfarben |
| 9. November 2026 | Controller-Pintabelle durch direkte Board-Beschriftung ersetzt; PWM GPIO5 und TACH GPIO6 |
| 10. November 2026 | Buck IN−/OUT− direkt verbunden und redundanter GND-Abzweig entfernt |
| 10. November 2026 | Sensorbusfarben rot/schwarz/blau/gelb und Gate auf GPIO21 angepasst |

Die Grafik wurde mit dem eingebauten Bildgenerator bearbeitet und visuell
geprüft. Beschriftungen zum Regelungskonzept können geplantes Verhalten
zeigen; der tatsächlich implementierte Betrieb steht in [Steuerung](../control.md).

## Wofür die Prompt-Dateien dienten

Bei unseren KI-Bildgenerierungen und Bildkorrekturen wurden separate TXT-Dateien
angelegt, um die jeweilige Änderungsanweisung zu protokollieren. Sie wurden
nicht vom Firmware-Build, Logger, Viewer oder den Tests erzeugt oder gelesen.
Sie waren keine ausführbaren Dateien und keine notwendige Quelle für das
fertige PNG. Sie wurden auf Wunsch gelöscht. Frühere Inhalte sind in Git
vorhanden; künftig werden im Projekt keine separaten Prompt-TXT-Dateien für
Bildänderungen angelegt.
