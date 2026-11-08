# Bildgenerierung

## Aktuell: Entwurf 04

Am 24.10.2026 mit dem integrierten image_gen-Tool überarbeitet: ESP32-C3 SuperMini statt ESP32-S3, kompaktes XZG-DC/DC-Buck-Modul statt LM2596, kein Netzteilbild und kein Vermerk „Innen“. I²C verwendet GPIO0/GPIO1; GPIO4/5/6 bleiben für Lüfter und Fogger. Die konkrete Buck-Ausführung ist anhand des Angebotstitels nicht eindeutig; 5-V-Ausgang vor Anschluss prüfen.

Ergebnis: `fnc-fogger-layout-v4.png`. Vollständiger verwendeter Prompt: [layout-v4-prompt.txt](layout-v4-prompt.txt). Der fnc-fogger-Anschlussplan ist fuer das Projekt massgebend; hardware.md ergaenzt ihn mit Anschlusstabellen und Hinweisen.

Bei der Bildprüfung wurde eine Korrektur der Controller-Abbildung und der Masseleitung am Buck-Eingang veranlasst. Der Korrekturprompt steht ebenfalls in layout-v4-prompt.txt. Die Buck-Anschlüsse sind schematisch, ihre tatsächliche Lage ist am Modul zu prüfen.

Die untere orange Anschlussliste in Feld 1 ist eine funktionale Aufzählung der +24-V-Abgänge, kein eigenständiger Versorgungseingang. Alle drei Abgänge sind mit dem oberen +24-V-Eingang zu verbinden; hardware.md beschreibt die Netze vollständig.

## Optionaler Aussensensor (08.11.2026)

Im Sensorfeld wurde der SHTC3 fuer Aussenfeuchte und Aussentemperatur
als OPTIONAL mit gestricheltem Rahmen und gestrichelten Abzweigen ergaenzt.
Anschluss parallel an 3,3 V, GND, SDA GPIO0 und SCL GPIO1; I2C-Adresse 0x70.
Der bestehende Dateiname bleibt die massgebende Projektreferenz.
