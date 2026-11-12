# WLAN-Sendeleistungstest · 12. November 2026

Gerät: **B8:1F:3F:27:F4:E0**, Primus Popinus @ in production.
Firmware **3.4.6**, Build `d0d914c9a9cb`, USB COM9, IP `192.168.31.220`.
Beim ersten Durchlauf wurde die andere Lanze nicht verändert. Der anschließend
beauftragte Vergleich auf der zweiten Lanze ist unten dokumentiert.

## Gemeinsamer Standard

Auf Benutzerwunsch gilt **8,5 dBm für alle Geräte mit dieser Firmware**.
Quelle: `include/config.h`, `Config::WIFI_TX_POWER_QDBM = 34` (Viertel-dBm).
Keine gerätespezifische NVS-Einstellung. Temporäre USB-Vergleiche werden durch
Neustart verworfen; `wifi power default` stellt ebenfalls 8,5 dBm wieder her.
OTA-Datei: `firmware/fnc-fogger-firmware_3.4.6.bin`.

## Messverfahren und Grenzen

Gleicher Aufbau nahe am Router, Kanal 1. Pro Stufe wurde die WLAN-Anmeldung
mit `wifi reconnect` erneut ausgelöst, danach 25 Sekunden lang `/api/current`
abgefragt (1 s Timeout, mindestens 0,6 s Pause). Ein Durchlauf je Stufe,
aufsteigende Reihenfolge, kein Langzeit- oder Reichweitentest. Der unabhängige
Logger lief währenddessen weiter. Fehlversuche enthalten die absichtliche
Neuanmeldung; unterschiedliche Antwortzeiten führen zu unterschiedlichen
Anfragezahlen. Die tatsächliche Treibervorgabe wurde über USB zurückgelesen.
Sie ist eine Leistungsobergrenze, keine Messung der abgestrahlten Leistung.
RSSI beschreibt den Empfang vom Router und bewertet die ESP-Sendeleistung
nicht direkt. Antwortzeiten werden als Median angegeben.

| Vorgabe / zurückgelesen (dBm) | HTTP erfolgreich / gesamt | Erste HTTP-Antwort nach Neuanmeldung (s) | HTTP-Median (ms) | RSSI-Median (dBm) |
|---|---:|---:|---:|---:|
| 2 / 2 | 31 / 32 | 1.8 | 94.0 | -37.0 |
| 5 / 5 | 34 / 34 | 0.12 | 70.5 | -33.0 |
| 7 / 7 | 30 / 32 | 1.86 | 78.0 | -32.0 |
| 8.5 / 8.5 | 34 / 34 | 0.11 | 70.5 | -32.0 |
| 11 / 11 | 34 / 34 | 0.14 | 78.0 | -31.0 |
| 13 / 13 | 32 / 33 | 1.88 | 78.0 | -31 |
| 14 / 14 | 32 / 33 | 1.84 | 63.0 | -38 |
| 15 / 15 | 34 / 34 | 0.12 | 78.0 | -38.0 |
| 16.5 / 16.5 | 30 / 31 | 1.88 | 141.0 | -41 |
| 18 / 18 | 1 / 16 | 20.55 | 485.0 | -42.0 |
| 20 / 20 | 0 / 15 | — | — | — |

8,5 dBm funktionierte mit 34/34 Antworten; 18 dBm lieferte nur eine Antwort,
20 dBm keine. Nach Rückkehr zu 8,5 dBm war das Gerät wieder verbunden.
Die niedrigere Leistung ist damit ein gemessener Workaround für diesen Aufbau.
Die Messung beweist weder eine bestimmte Hardwareursache noch, dass 8,5 dBm
für jeden Standort optimal ist. Der anschließende Vergleich auf der anderen Lanze folgt unten.

## Verfügbare Stufen

2 · 5 · 7 · 8,5 · 11 · 13 · 14 · 15 · 16,5 · 18 · 20 dBm.
Der ESP32-C3-Treiber quantisiert Zwischenwerte auf diese Stufen.
[Espressif: esp_wifi_set_max_tx_power, ESP-IDF 4.4.7](https://docs.espressif.com/projects/esp-idf/en/v4.4.7/esp32c3/api-reference/network/esp_wifi.html#_CPPv425esp_wifi_set_max_tx_power6int8_t).
USB verwendet den Dezimalpunkt, beispielsweise `wifi power 8.5`.

## Verifikation

Build erfolgreich; alle 113 Hosttests erfolgreich. USB-Installation nur im
vorhandenen aktiven App-Slot `0x190000`, Flash-Hash durch esptool bestätigt.
Zugangsdaten, NVS und Messpuffer wurden nicht überschrieben. Vollständige
Sicherung vor den Diagnose-Updates liegt lokal im ignorierten Recovery-Ordner.
Rohmessungen: `logger/data/recovery/usb-b81f3f27f4e0-20261112/power-comparison.json`
und `power-comparison-serial.txt` (nicht im Git).

Anschlie?ender MCU-Neustart best?tigte automatisch `tx_power_qdbm=34` und
Firmware/Build per HTTP. Nach 10 s Startfenster: **33/33 HTTP-Antworten**
in den verbleibenden rund 30 s. Ung?ltige/zu lange USB-Kommandos wurden
abgelehnt, ebenso ein Scan bei bestehender Verbindung.

## Wiederholung: Lanze @ Big Mama

Auf Benutzerwunsch wurde der identische Vergleich anschließend auf
**B8:1F:3F:27:CA:14** wiederholt. USB COM7, IP `192.168.31.108`.
Benutzerbestätigung: nur Sensoren angeschlossen, keine Aktoren.
Vorher Firmware 3.2.1; vollständige 4-MiB-Sicherung erstellt und mit SHA256
protokolliert. OTA-Auswahl im Backup: Sequenz 3 aktiv, daher App0 `0x10000`.
Nur dieser App-Slot wurde mit derselben Firmware 3.4.6 / Build `d0d914c9a9cb`
beschrieben; esptool bestätigte den Flash-Hash, HTTP anschließend die Identität.
NVS, Messpuffer, Bootloader und Partitionstabelle blieben erhalten.

Messverfahren wie oben: elf Stufen, jeweils WLAN-Neuanmeldung und 25 s
HTTP-Abfragen. Alle Stufen wurden mit der angeforderten Leistung zurückgelesen.
Der Empfang lag hier um −50 bis −52 dBm. Aufbauten und Empfangsbedingungen
beider Geräte sind damit nicht identisch; ein direkter Hardwarevergleich
würde gleiche Position, Versorgung und angeschlossene Verbraucher erfordern.

| Vorgabe / zurückgelesen (dBm) | HTTP erfolgreich / gesamt | Erste HTTP-Antwort (s) | HTTP-Median (ms) | RSSI-Median (dBm) |
|---|---:|---:|---:|---:|
| 2 / 2 | 29 / 31 | 0.19 | 109.0 | -51 |
| 5 / 5 | 30 / 31 | 1.86 | 125.0 | -51 |
| 7 / 7 | 32 / 33 | 1.88 | 78.0 | -51 |
| 8.5 / 8.5 | 28 / 31 | 1.77 | 78.0 | -51 |
| 11 / 11 | 32 / 33 | 1.84 | 63.0 | -51 |
| 13 / 13 | 28 / 31 | 1.84 | 78.0 | -50 |
| 14 / 14 | 31 / 32 | 1.83 | 94.0 | -51.5 |
| 15 / 15 | 32 / 33 | 1.86 | 70.5 | -50 |
| 16.5 / 16.5 | 34 / 34 | 0.14 | 78.0 | -50.0 |
| 18 / 18 | 28 / 31 | 1.75 | 62.0 | -51 |
| 20 / 20 | 31 / 32 | 1.84 | 94.0 | -50.5 |

Diese Lanze war auf allen elf Stufen erreichbar. Insbesondere 20 dBm
funktionierten hier mit 31/32 Antworten, während das erste Gerät bei 20 dBm
0/15 Antworten lieferte. 8,5 dBm lieferten hier 28/31 Antworten, 16,5 dBm
34/34. Einzelne HTTP-Fehler können aus Neuanmeldung, Anwendungs-/Netzwerklast
oder Funkproblemen stammen und sind kein direkter WLAN-Paketverlustzähler.
Die kurze Einzelmessung begründet keine belastbare Rangfolge zwischen den
funktionierenden Stufen. 8,5 dBm bleibt wie gewünscht gemeinsamer Standard.

Rohdaten und Flash-Sicherung liegen lokal unter
`logger/data/recovery/usb-b81f3f27ca14-20261112/` (ignoriert, nicht im Git).
Nach dem Vergleich wurde 8,5 dBm wiederhergestellt und die Verbindung bestätigt.

Abschließender MCU-Neustart: automatischer Wechsel auf `tx_power_qdbm=34`,
**32/32 HTTP-Antworten** nach 10 s Startfenster im restlichen ca. 30-s-Test.
Der unabhängige Logger bestätigte danach Firmware 3.4.6 / Build `d0d914c9a9cb`
und eine neue `last_seen`-Zeit für die zweite Lanze.
