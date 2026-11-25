# Diagramm-Änderungshistorie

Aktueller [Anschlussplan](../fnc-fogger-wiring.svg).
Pinbelegung und elektrische Grenzen stehen in [Hardware](../hardware.md).
Zurück zur [Dokumentationsübersicht](../README.md).

## Aktueller Stand

ESP32-C3 SuperMini mit SDA GPIO0, SCL GPIO1, Fan PWM GPIO10, Fan TACH GPIO7
und MOSFET-Gate GPIO3 (Firmware 3.4.3). Die Controller-Grafik zeigt die Kontakte direkt am
Board; sie ist eine Pinpositions-Illustration, keine exakte Fotografie.
Die aktuelle Revision 08 ist ein SVG: Beschriftungen, Leitungen und
Pinzuordnungen sind editierbare Vektorelemente. Die Bauteilbilder wurden
separat in hoher Auflösung neu generiert und sind
als Rastergrafiken eingebettet. Es sind fotorealistische Illustrationen, keine
verifizierten Produktfotos. Die Pinzuordnungen stammen aus der Firmware und
der Hardwaredokumentation, nicht aus KI-generierten Leiterbahnen.

Fan und Fogger liegen an 24 V, der ESP32 an Buck OUT+ mit 5 V. Buck IN− und
OUT− sind im verwendeten Modul intern verbunden und im Plan entsprechend
dargestellt. Sensorleitungen: 3,3 V rot, GND schwarz, SDA blau, SCL gelb.
Der optionale SHTC3 ist gestrichelt am gemeinsamen Sensorbus dargestellt.
Die vier Sensorabgänge sind schematisch nach Qwiic geordnet: GND schwarz,
3V3 rot, SDA blau, SCL gelb. Das ist keine verifizierte Lötpad-Reihenfolge
der dargestellten Breakouts; dafür gelten die Beschriftungen der realen Module.

## Wesentliche Bildänderungen

| Zeitpunkt | Änderung |
| --- | --- |
| Oktober 2026 | ESP32-C3 SuperMini und kompakter XZG-Buck ersetzen frühere Darstellungen |
| 8. November 2026 | Optionaler SHTC3 am selben I²C-Bus ergänzt |
| 9. November 2026 | Fogger auf 5 V, getrennte 24-V-/GND-Netze, englische Beschriftung, Noctua-Kabelfarben |
| 9. November 2026 | Controller-Pintabelle durch direkte Board-Beschriftung ersetzt; PWM GPIO5 und TACH GPIO6 |
| 10. November 2026 | Buck IN−/OUT− direkt verbunden und redundanter GND-Abzweig entfernt |
| 10. November 2026 | Sensorbusfarben rot/schwarz/blau/gelb und Gate auf GPIO21 angepasst |
| 11. November 2026 | SVG-Neuaufbau mit eingebetteten Bauteilbildern; Gate GPIO3 und implementierten Firmwarefunktionen |
| 11. November 2026 | Revision 06: neue hochauflösende Bauteilillustrationen, eingerahmte Pin-Felder, bereinigte Abstände und Hinweise |

| 12. November 2026 | Revision 07: Fan PWM GPIO10, Fan TACH GPIO7, kompakter Buck und überarbeitete Lüftergrafik |

| 23. November 2026 | Revision 08: Fogger mit integriertem Treiber an 24 V, 5-V-Abzweig entfernt und Startup-Kommentar gelöscht |

## Bearbeiten und reproduzieren

Quelle: [tools/build_wiring_diagram.py](../../tools/build_wiring_diagram.py).
Aus dem Projektverzeichnis ausführen:

```powershell
python tools/build_wiring_diagram.py
```

Der Generator benötigt nur die Python-Standardbibliothek. Er zeichnet Texte,
Leitungen und Markierungen als SVG. Die neuen Komponentenbilder und ihre
Ausschnitt-Metadaten liegen in `docs/diagrams/components/`. Die PNG- und WebP-Dateien
sind in hoher Qualität bei voller Bildauflösung kodiert; es erfolgt keine erneute KI-Bearbeitung beim Build.
`docs/fnc-fogger-layout-v4.png` bleibt als historische Fassung erhalten. Das erzeugte SVG ist eigenständig und
benötigt beim Anzeigen keine externen Bilddateien. Koordinaten und Ausschnitte
sind Illustrationen; die tatsächlichen Module bleiben zu prüfen.

Künftige Pinänderungen erfolgen im Generator. Bauteilfotos können später durch
bessere Originalaufnahmen ersetzt werden, ohne Texte und Leitungen neu zu zeichnen.

## Wofür die Prompt-Dateien dienten

Bei unseren KI-Bildgenerierungen und Bildkorrekturen wurden separate TXT-Dateien
angelegt, um die jeweilige Änderungsanweisung zu protokollieren. Sie wurden
nicht vom Firmware-Build, Logger, Viewer oder den Tests erzeugt oder gelesen.
Sie waren keine ausführbaren Dateien und keine notwendige Quelle für das
fertige PNG. Sie wurden auf Wunsch gelöscht. Frühere Inhalte sind in Git
vorhanden; künftig werden im Projekt keine separaten Prompt-TXT-Dateien für
Bildänderungen angelegt.
