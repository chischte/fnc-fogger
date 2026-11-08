# Hardware zum fnc-fogger-Anschlussplan - Entwurf 04

Stand: 24.10.2026. Anschlussentwurf, keine ausführbare Firmware und keine Hardwarefreigabe.

Massgebende Referenz fuer den geplanten Projektaufbau ist der
[fnc-fogger-Anschlussplan - Entwurf 04](fnc-fogger-layout-v4.png).
Die folgenden Tabellen und Hinweise ergaenzen diesen Plan.

## Stromversorgung

Geregeltes 24-V-DC-Netzteil mit gemeinsamer Masse verwenden. Nur ein XZG DC/DC-Buck bleibt:

| Quelle | Ziel |
| --- | --- |
| Netzteil +24 V | Noctua Pin 2, Fogger-Plus und XZG DC/DC-Buck IN+ |
| Netzteil GND | Noctua Pin 1, IRLB8721 Source, ESP32 GND, XZG DC/DC-Buck IN− / OUT− |
| XZG DC/DC-Buck OUT+ = 5,0 V | ESP32-C3 SuperMini 5V |

Abgebildetes kompaktes XZG-DC/DC-Buck-Modul verwenden (schwarze Platine, 4R7-Drossel). Der Angebotstitel nennt mehrere Ausgangsspannungen; die konkrete Variante und deren Einstellung sind damit nicht eindeutig bestimmt. Für diesen Aufbau die 5-V-Variante bzw. 5-V-Einstellung verwenden und vor Anschluss mit dem Multimeter 5,0 V am Ausgang prüfen. Keine unbekannten Lötbrücken verändern. Die Klemmenbezeichnungen IN+/IN− und OUT+/OUT− sind funktional; ihre Position am gelieferten Modul prüfen. Geeigneten 5-V-Eingang am konkreten Devboard prüfen; keine 5 V auf 3V3 legen. Lastströme direkt zum Netzteil zurückführen, nicht durch ESP32- oder Sensorleitungen. Leitungen und Sicherung nach Last und Einschaltstrom auslegen.

## GPIO-Vorschlag

| Funktion | GPIO | Anschluss / Konfiguration |
| --- | --- | --- |
| I²C SDA | 0 | SDA von SCD41 und SHT45 |
| I²C SCL | 1 | SCL von SCD41 und SHT45 |
| FAN_PWM | 4 | Direkt an Noctua Pin 4; 3,3-V-Push-Pull, 25 kHz |
| FAN_TACH | 5 | Noctua Pin 3; Eingang mit internem Pull-up nach 3,3 V |
| FOG_EN | 6 | Direkt an IRLB8721 Gate, Pin 1; LOW = AUS, HIGH fordert EIN an |

GPIO-Nummern sind keine physischen Steckplatznummern. Verfügbarkeit am konkreten ESP32-C3 SuperMini-Board prüfen. I²C in der Firmware explizit auf SDA GPIO0 und SCL GPIO1 konfigurieren. GPIO8 (Board-LED) und GPIO9 (BOOT) bleiben frei; beide sind Boot-Konfigurationspins. USB verwendet GPIO18/19 und bleibt verfügbar.

Pinbelegungsreferenz: [Apache NuttX: ESP32-C3 SuperMini](https://nuttx.incubator.apache.org/docs/latest/platforms/risc-v/esp32c3/boards/esp32c3-supermini/index.html).
## Sensoren

| Signal vom ESP32 | SCD41-Breakout | SHT45-Breakout |
| --- | --- | --- |
| 3V3 | Geeigneter 3,3-V-Versorgungseingang | Geeigneter 3,3-V-Versorgungseingang |
| GND | GND | GND |
| GPIO0 | SDA | SDA |
| GPIO1 | SCL | SCL |

Optional kann ein **SHTC3 (I2C-Adresse `0x70`)** fuer Aussenfeuchte und
Aussentemperatur am gleichen Bus angeschlossen werden:

| SHTC3-Signal | Verbindung |
| --- | --- |
| 3V3 | 3,3-V-Sensorversorgung |
| GND | Gemeinsame Masse |
| SDA | GPIO0, parallel zu SCD41 und SHT45 |
| SCL | GPIO1, parallel zu SCD41 und SHT45 |

Die Angaben beschreiben die Signale; die physische Pinreihenfolge am Modul
pruefen. Der SHTC3 ist optional und dient der Aussenmessung.

Adressen: SCD41 0x62, SHT45 0x44. Kein Multiplexer erforderlich. Kurze I²C-Leitungen, zunächst 100 kHz. Vorhandene I²C-Pull-ups der Breakouts müssen nach 3,3 V führen. Das Weglassen des optionalen Tacho-Widerstands betrifft nicht die erforderlichen I²C-Pull-ups: bei Breakouts ohne diese ist der Busaufbau zu ergänzen.

SCD41 benötigt bei 3,3 V bis 205 mA Spitzenstrom zusätzlich zur übrigen Boardlast. Reglerreserve des gewählten Devboards prüfen. Sensoren repräsentativ in der Innenluft, vor direktem Nebel und Kondensation geschützt, montieren. Nur SHT45-Feuchte geht in den Feuchte-PID ein.

Quellen: [SCD4x-Datenblatt](https://sensirion.com/resource/datasheet/scd4x), [SHT4x-Datenblatt](https://sensirion.com/resource/datasheet/sht4x).

## Noctua NF-A4x10 24V PWM

| Lüfter-Pin | Signal / übliche Kabelfarbe | Anschluss |
| --- | --- | --- |
| 1 | GND / schwarz | Gemeinsame Masse |
| 2 | +24 V / gelb | Direkt an Netzteil +24 V |
| 3 | TACH / grün | GPIO5 mit internem 3,3-V-Pull-up |
| 4 | PWM / blau | Direkt an GPIO4 |

Pinzählung anhand des Steckers prüfen, nicht aus einer beliebigen Blickrichtung ableiten. Der Lüfter erhält dauerhaft 24 V; nur seine separate PWM-Leitung wird mit 3,3 V und 25 kHz angesteuert. 100 % HIGH entspricht maximaler Drehzahl. Kein XZG DC/DC-Buck und kein Last-MOSFET im Lüfterzweig. Tacho liefert zwei Open-Collector-Pulse pro Umdrehung; Signalqualität mit internem Pull-up am Aufbau prüfen. Ohne PWM-Signal läuft der Lüfter mit voller Drehzahl.

Quellen: [Noctua Mikrocontroller-Anleitung](https://www.noctua.at/en/support/faqs/microcontroller-guide-pwm-setup-and-rpm-monitoring), [NF-A4x10 24V PWM](https://www.noctua.at/en/products/nf-a4x10-24v-pwm/specifications).

## Fogger mit IRLB8721

Gewünschte Direktansteuerung ohne Gate-Vorwiderstand und ohne Gate-Source-Pulldown. Diese Variante ist elektrisch nicht als zuverlässige 3,3-V-Schaltung freigegeben.

### Pinbelegung und exakter Anschluss

TO-220 von vorne betrachten: Beschriftung zu dir, Metalllasche hinten, Beine nach unten. Von links nach rechts: **1 Gate, 2 Drain, 3 Source**. Die Metalllasche ist ebenfalls Drain und muss gegen GND/Gehäuse isoliert bleiben.

```text
             IRLB8721
        Beschriftung zu dir
          ┌───────────┐
          │ IRLB8721  │
          └──┬──┬──┬──┘
             1  2  3
             G  D  S
             │  │  └──────── Netzteil GND / ESP32 GND
GPIO6 ───────┘  │
                └─────────── Fogger −
Netzteil +24 V ───────────── Fogger +
```

| Anschluss | Verbindung |
| --- | --- |
| Gate, Pin 1 links | Direkt an ESP32 GPIO6 |
| Drain, Pin 2 Mitte | Fogger-Minus |
| Source, Pin 3 rechts | Netzteil-Minus und ESP32 GND |
| Fogger-Plus | Direkt an Netzteil +24 V |
| Metalllasche | Drain; gleiches Potential wie Fogger-Minus |

**Fogger-Minus nicht zusätzlich an GND anschliessen:** Das würde den MOSFET überbrücken. Ein vollständiges 24-V-Ultraschallmodul mit eigener Treiberelektronik verwenden, keinen nackten Piezo.

### Grenzen der gewünschten widerstandslosen Variante

- Das Datenblatt spezifiziert den Einschaltwiderstand ab 4,5 V Gatespannung, nicht bei 3,3 V. Die Gate-Schwellenspannung bedeutet noch kein vollständiges Durchschalten. Laststrom, Spannungsabfall Drain–Source und Erwärmung müssen geprüft werden; für garantierten Betrieb ist eine geeignete Treiberstufe oder ein bei 3,3 V spezifizierter MOSFET nötig.
- Ohne Gate-Source-Pulldown kann das Gate bei Reset, Boot oder abgetrenntem ESP32 geladen bzw. undefiniert bleiben. Software-LOW und ein interner GPIO-Pulldown garantieren dann keinen AUS-Zustand. Unbeaufsichtigten Betrieb damit nicht freigeben.
- Ohne Gate-Vorwiderstand sind GPIO-Ladeströme und Ringing nicht extern begrenzt; kurze Leitungen und Prüfung am realen Aufbau erforderlich.
- IRLB8721 hat nur 30 V maximale Drain–Source-Spannung. Bei 24 V Versorgung bleiben 6 V Reserve. Netzteiltoleranz und Schaltspitzen müssen darunter bleiben; erforderliche Schutzbeschaltung hängt vom konkreten Fogger und der Verkabelung ab.

GPIO6 früh auf LOW setzen. HIGH fordert EIN an, LOW schaltet bei versorgtem, aktiv treibendem GPIO aus. Nur langsame EIN/AUS-Zeitfenster; kein 25-kHz-PWM am Fogger. Mindestlaufzeiten, Wiederanlauf und unabhängigen Trockenlaufschutz des konkreten Foggers prüfen.

Quelle: [Infineon IRLB8721-Datenblatt, Pinbelegung und Grenzwerte](https://www.infineon.com/assets/row/public/documents/24/49/infineon-irlb8721-datasheet-en.pdf).

## Upload und OTA

Firmware ist noch nicht implementiert. OTA über WLAN benötigt passende Firmware und Flash-Partitionen. Der verbleibende XZG DC/DC-Buck versorgt das ESP32-Board dabei weiter mit 5 V. Erstinstallation und Wiederherstellung per USB; externe 5 V dabei trennen, solange das Board keine gleichzeitige Einspeisung erlaubt.

Während Updates Fogger AUS anfordern und Lüfter auf definierte Fehlerdrehzahl setzen. Die widerstandslose Gate-Schaltung garantiert beim anschliessenden Reset keinen AUS-Zustand. Erst nach gültigen Sensorwerten regeln.
