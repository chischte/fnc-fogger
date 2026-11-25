# Geräteverwaltung und OTA

Stand: 11. November 2026. Aktuell werden ausschließlich ESP32-C3 SuperMinis eingesetzt.
Das Standardprofil `esp32c3_supermini` bereitet ESP32-C3 SuperMinis mit
4 MiB Flash für Sensorbetrieb und WLAN-Updates vor. Die reale Flashgröße muss
bei der ersten USB-Einrichtung bestätigt werden. Die bestehende S3-Lanze wurde
nicht aktualisiert. Der erste Mini wurde inzwischen erfolgreich eingerichtet;
siehe [USB-/OTA-Test des ersten Minis](archive/esp32c3-mini-01-test-2026-11-09.md).
Auch der [zweite Mini, fogger 01](archive/esp32c3-mini-02-test-2026-11-09.md), ist
inzwischen per USB eingerichtet und OTA-getestet. Beide sind in der Geräteverwaltung gespeichert.

## Geräteübersicht im Viewer

Device Overview zeigt je registriertem Gerät eine Diagrammspalte mit dem
Titel `Name @ Location` und drei Kurven: korrigierte SHT45-Feuchte, SCD41-CO₂
und SHT45-Temperatur. Alle Spalten verwenden dasselbe aktuelle 30-Minuten-Fenster
in Schweizer Ortszeit. Die Y-Achsen bleiben fest: 85–100 %RH, 0–15.000 ppm und
20–30 °C. Zusatzsensoren, gepunktete/gestrichelte Kurven, Messwertkarten,
PI-Anzeigen, Zoom und Command Mode gehören nur zum vollständigen Viewer.

Die Übersicht startet im Dark Mode; der Button schaltet zwischen dunkel und
hell um und zeigt jeweils den Zielmodus (Light Mode oder Dark Mode). Ein manueller
Refresh-Button entfällt; die Geräteerkennung läuft automatisch. Full Screen beziehungsweise F11 schaltet Vollbild, Escape verlässt es.
Bei vielen Geräten lassen sich die Spalten horizontal scrollen. Ein Klick auf
eines der drei Diagramme öffnet genau dieses Gerät. Die verfügbaren Aktionen
Update Firmware und Remove Offline Device stehen zentriert nebeneinander unter
den Diagrammen, gleich breit und ohne reservierte Leerflächen.
Update Firmware ist nur sichtbar, wenn im lokalen `firmware/`-Ordner eine
validierte BIN mit passendem Hardwareprofil und höherer Versionsnummer liegt.
Gleiche Version mit anderer Buildkennung zählt nicht als neuer. Unbekannte
Geräteversionen erhalten erst nach Erkennung ein Angebot. Bei einem offline
Gerät bleibt ein vorhandenes neueres Update sichtbar, aber deaktiviert.
Remove Offline Device erscheint nur nach bestätigter Offline-Erkennung; während
einer Suche oder eines Updates bleibt die sichtbare Schaltfläche deaktiviert.
Der Firmwarekatalog wird bei den regelmäßigen Suchläufen alle 15 Sekunden neu gelesen.

Während eines Firmwareupdates sind Navigation,
Titelbearbeitung und weitere Geräteaktionen gesperrt. Der vollständige
Viewer bleibt unverändert verfügbar.

Die Diagramme lesen nur die jeweilige SQLite-Messdatei und aktualisieren sich
alle zehn Sekunden. Der Datenabruf läuft außerhalb des UI-Threads und ist auf
die jüngsten 5.000 Datensätze je Gerät begrenzt. Fehlende Sensorwerte werden
nicht durch andere Sensoren ersetzt. Ohne Messungen im Zeitfenster erscheint
`No recent measurements`; ein Datenbankfehler erscheint als `history unavailable`.
Offline-Geräte bleiben mit ihren Metadaten sichtbar. Die Übersicht zeichnet
selbst nichts auf und sendet keine Aktorbefehle. Der Hintergrundlogger bleibt
für die Aufzeichnung zuständig.

Die frühere Tabelle entfällt. Der zentrierte Spaltenkopf besteht aus:

1. `name @ location` in etwas größerer Schrift und Kleinschreibung;
2. `online` oder `last seen ...`.

Unter den Diagrammen, über den Aktionsbuttons, stehen die kopierbare MAC-Adresse
und Firmware im Format `<MAC> | Firmware <version>` mit je
einem Leerzeichen um den Trennstrich. Die vertikalen Diagrammabstände sind kompakt;
der Abstand zur Infozeile darunter ist reduziert.

Last seen erscheint nur bei offline-Geräten. Die Adresse wird nicht als Link
angezeigt; sie bleibt für Geräteerkennung und Updates intern gespeichert.
Die Kleinschreibung verändert keine gespeicherten Namen oder Locations.
Alle drei Diagramme zeigen ihre Zeitbeschriftungen. Die große
Seitenüberschrift entfällt. Light Mode beziehungsweise Dark Mode und Full Screen stehen unten
horizontal zentriert direkt über den Statusmeldungen. Der Fenstertitel bleibt
`Device Overview`; der Rücksprungbutton im Viewer heißt `device overview`.

Start: `python logger/viewer.py`.

Der Startbildschirm zeigt Name, Standort, `online` beziehungsweise `last seen`, Firmwareversion,
letzte Erreichbarkeit offline und Geräte-ID. Hardwareprofil und Buildkennung
bleiben intern für die Updateprüfung gespeichert. Die Firmwareanzeige lässt
den Hardwarezusatz weg, beispielsweise `3.2.1` statt `3.2.1-esp32c3`.
Die Geräte-ID erscheint als WLAN-MAC mit Großbuchstaben und Doppelpunkten;
sie ist als schreibgeschützter Text markierbar. Ein Klick kopiert die gesamte
angezeigte MAC-Adresse in die Zwischenablage.
Intern bleibt sie unverändert ohne Doppelpunkte gespeichert. Das ändert weder
Gerätezuordnung noch Messdaten oder Updates. Bei `Last seen` steht für heute
nur die lokale Uhrzeit, für andere Tage zusätzlich das Datum.
Beschrifte jedes Gerät mit Name und kurzer ID, z. B.
`Lanze 02 – 445566`. Namen und Standorte sind frei wählbar; die ID bleibt
bei einem IP-Wechsel gleich. Ein Ersatzcontroller bekommt eine neue ID.

Ein einfacher Klick auf `Name @ Location` verwandelt den Titel direkt in
zwei Eingabefelder. Enter oder ein Klick außerhalb speichert beide Werte;
der Wechsel zwischen den beiden Feldern speichert noch nicht. Escape
verwirft die Änderung. Ein Aktualisierungslauf überschreibt keine laufende
Eingabe. Separate Benennungsfelder oder ein Save-Button sind nicht vorhanden.


Die Suche läuft alle 15 Sekunden, solange die Geräteauswahl geöffnet ist.
mDNS findet neue Geräte; bekannte Geräte werden ebenfalls über ihre gespeicherte
Adresse abgefragt. Online bedeutet eine erfolgreiche HTTP-Statusabfrage im
letzten Suchlauf, nicht lediglich eine mDNS-Ankündigung. Bei sieben nicht
erreichbaren Geräten kann ein Suchlauf wegen der Netzwerk-Timeouts länger
dauern. Offline-Einträge behalten ihren zuletzt bestätigten Firmwarestand.
Der Viewer ist kein ständig laufender Überwachungsdienst, wenn er geschlossen ist.

Nicht mehr verwendete Offline-Geräte lassen sich über `Remove Offline Device`
nach einer Rückfrage aus der Liste entfernen. Die Schaltfläche ist erst nach
einem erfolgreichen Suchlauf verfügbar und während einer Suche oder eines
Firmwareupdates deaktiviert. Messdateien, Updateverlauf und die interne
Zuordnung der Messdaten bleiben erhalten. Meldet sich das Gerät später wieder
im Netzwerk, erscheint es mit seinem bisherigen Namen und seiner Historie erneut.

## Wo die Informationen gespeichert werden

| Datei / Ort | Inhalt |
| --- | --- |
| `logger/data/lances.db`, Tabelle `lances` | Geräte-ID, Adresse/Port, Name, Standort, Messdaten-Zuordnung, zuletzt bestätigte Firmware, Hardwareprofil, Buildkennung und `last_seen` in UTC |
| Dieselbe Datenbank, Tabelle `firmware_updates` | Updateverlauf aus Viewer und Uploadskript: Ziel-ID, Zeitpunkt in UTC, Zielversion, Buildkennung, Hardwareprofil, SHA256, Phase und Fehlerdetails |
| `logger/data/devices/<device-id>.db` | Messwerte je Gerät; die bereits zugeordnete historische `measurements.db` bleibt erhalten |
| `include/firmware/identity.h` | Firmwareversionen und Hardwareprofilnamen im Quellcode |
| `tools/build_identity.py` | Erzeugt eine 12-stellige Kennung aus Firmwarequellen, Projektkonfiguration, Partitionstabellen, Buildskript und Zielprofil |
| `firmware/fnc-fogger-firmware_<version>.bin` | Zum Hochladen exportierte Anwendung für ESP32-C3 SuperMinis; Profil und Buildkennung bleiben intern gespeichert |
| Gleichnamige `.json` in `firmware/` | Manifest mit Profil, Version, Buildkennung, Dateigröße und SHA256 der konkreten BIN-Datei |
| `.pio/build/<profil>/firmware.bin` und `.json` | Interne PlatformIO-Builddateien; die OTA-Kopie liegt im Projektroot unter `firmware/` |
| `platformio.ini` | Getrennte Buildprofile für ESP32-S3 und ESP32-C3 SuperMini |
| `include/config.h` | Profilabhängige Pinbelegung und Speicherlimits |
| `partitions_esp32s3.csv`, `partitions_esp32c3.csv` | Flashaufteilung pro Hardwareprofil |
| Controller, `/api/current` | Tatsächlich laufende Version, Profil, Buildkennung, Geräte-ID und Boot-ID; Grundlage für Status und Updatebestätigung |
| Controller, NVS | Individuelle Regelungs-Sollwerte; werden durch normale OTA-Updates nicht ersetzt |

Die Viewer-Datenbanken sind lokale Laufzeitdaten und werden nicht in Git
gespeichert. Sichere den gesamten Ordner `logger/data`, um Namen, Historie
und Gerätezuordnung zu erhalten. Vor der erstmaligen Migration einer bereits
genutzten Datenbank den Viewer schließen und eine Kopie anlegen.
Die Schemaergänzung erfolgt automatisch beim nächsten Start und erhält
bestehende Namen und Messdatenzuordnungen. Der Viewer zeigt Zeitangaben lokal an.

Firmwareversion und Buildkennung beschreiben den laufenden Stand. Die SHA256
im Manifest und Updateprotokoll identifiziert zusätzlich die genaue Datei.
Interne Buildausgaben werden beim nächsten Build ersetzt; die benannten
Exporte anderer Versionen in `firmware/` bleiben erhalten. Ein erneuter Build
derselben Version ersetzt deren BIN und JSON. BIN und JSON gemeinsam archivieren.

## Gezielt aktualisieren

1. Im Viewer die gewünschte Online-Lanze auswählen.
2. `Update selected firmware` anklicken und die passende `firmware.bin` wählen.
3. Name, Standort, ID, Adresse, Profil und Versionswechsel prüfen und bestätigen.
4. Upload, Neustart und abschließende Bestätigung abwarten.

Der Viewer bleibt während des Uploads bedienbar, lässt aber keine zweite
Installation und kein Schließen oder Öffnen von Diagrammen zu. Updates werden
einzeln ausgeführt. Zunächst ein Testgerät aktualisieren und prüfen, danach
weitere Geräte. Es gibt kein unbeabsichtigtes Update an alle Geräte.

Alternativ im Projektverzeichnis:

```powershell
./upload_firmware.ps1 -DeviceUrl http://fnc-fogger-445566.local -DeviceId 112233445566 -Environment esp32c3_supermini
```

Das Beispiel enthält eine fiktive ID. Adresse und ID müssen zum tatsächlichen
Gerät gehören. Es gibt keine Standard-IP mehr. Das Skript fragt vor dem
Upload nach; `-Yes` überspringt nur diese Rückfrage, keine Geräteprüfungen.
Viewer und Skript prüfen Chiptyp und Metadaten der Datei sowie ID und Profil
des Zielgeräts. Vorbereitete Firmware lehnt beim OTA zusätzlich eine Datei
ohne passenden Profilmarker ab. Die Updatebibliothek prüft das ESP-Image.
Die Profilkennung dient dem Schutz vor Verwechslungen, nicht als digitale Signatur.

Erfolg wird erst bestätigt, wenn dieselbe Geräte-ID mit neuem Boot und dem
erwarteten Profil, Versionsstand und Build wieder antwortet. Ein HTTP-Erfolg
allein genügt nicht. Bei fehlender Bestätigung bleibt der Vorgang im Protokoll
als `unconfirmed` stehen; vor einem erneuten Versuch Gerät prüfen.
Ein automatisches Boot-Rollback ist nicht eingerichtet.

Die bestehende S3-Firmware vor 3.2.0 liefert noch keine Geräte-ID im HTTP-Status.
Für deren einmalige Umstellung akzeptieren Viewer/Skript ausschließlich den
zur ID passenden mDNS-Namen und einen S3-Firmwarestand. Die Identitätsprüfung
dieses ersten Updates ist damit eingeschränkt. Danach gilt die strikte ID-Prüfung.
Bis zur Umstellung können Hardwareprofil und Build bei alten Geräten als
`Unknown` beziehungsweise `-` erscheinen; die bestehende Firmwareversion ist
bereits über die bisherige API sichtbar.
Die bestehende Lanze muss für die Vorbereitung der Minis nicht aktualisiert werden.

Die geräteeigene Seite `http://<gerät>/update` zeigt ebenfalls Gerätekennung,
Hardware und Firmware, prüft das gewählte Image und kontrolliert den Neustart.
Updates über diese Seite werden nicht in der PC-Datenbank protokolliert;
beim nächsten Viewer-Suchlauf wird der laufende Stand übernommen.
OTA ist weiterhin für ein vertrauenswürdiges lokales WLAN vorgesehen.

## Die ersten beiden C3 SuperMinis einrichten

Die erste Installation erfolgt je Gerät per USB. OTA setzt die Anwendung,
WLAN-Zugangsdaten und die passende Partitionstabelle auf dem Gerät voraus.

1. Prüfen, dass es ESP32-C3 SuperMinis mit 4 MiB Flash sind. Zunächst nur
   einen Mini per USB anschließen; den bestehenden S3 nicht neu flashen.
2. Die bestehende `../wifi-credentials.h` wird auch für die Minis verwendet.
   Vorlage: `include/wifi-credentials.example.h`. Zugangsdaten nicht committen.
3. Bauen: `pio run -e esp32c3_supermini`.
4. Port bestimmen: `pio device list`.
5. Vollständige Erstinstallation: `pio run -e esp32c3_supermini -t upload --upload-port COMx`.
   Hierfür nicht nur die OTA-BIN einzeln schreiben. Falls nötig BOOT gedrückt
   halten, RESET kurz drücken und BOOT loslassen; anschließend Port erneut prüfen.
6. Neustarten. Mit `pio device monitor --port COMx --baud 115200` den Start
   kontrollieren. Native USB kann nach dem Flashen einen anderen Port bekommen.
7. Im Viewer `Refresh` ausführen, Geräte-ID notieren, Namen `Lanze 02` und
   Standort vergeben und Gerät entsprechend beschriften.
8. Über den Viewer ein OTA derselben vorbereiteten C3-Datei ausführen.
   Gleiche Version ist für diesen Test erlaubt; die geänderte Boot-ID bestätigt
   den Neustart. Erst nach erfolgreicher Rückmeldung ist OTA am Gerät verifiziert.
9. Den zweiten Mini einzeln genauso einrichten, als `Lanze 03` benennen und
   dessen eigene Geräte-ID kontrollieren. Der tatsächlich gewählte Name für
   den zweiten Mini ist `fogger 01`. Beide später gemeinsam einschalten
   und getrennte Einträge sowie getrennte Updateziele prüfen.

Das C3-Profil verwendet SDA GPIO0 und SCL GPIO1, keine PSRAM und zwei
1536-KiB-OTA-Slots. LittleFS erhält 960 KiB; die beiden rotierenden Messdateien
sind auf je 256 KiB begrenzt. Das S3-Profil und seine 8-MiB-Flashaufteilung bleiben
getrennt erhalten. Der Plattform-Basistyp ist `esp32-c3-devkitm-1`, angepasst
für native USB-Kommunikation und die SuperMini-Pinbelegung.

Diese Firmware bereitet Sensoren, Geräteverwaltung und OTA vor. Die geplante
Lüfter-/Neblerregelung ist noch nicht implementiert. GPIO3 wird beim C3-Start
auf LOW gesetzt; ein externer Gate-Pulldown gemäß Hardwaredokumentation bleibt
für Reset/Boot erforderlich. Erste USB-/OTA-Tests ohne angeschlossene Aktoren
durchführen. Fehlende Sensoren verhindern den WLAN-/OTA-Betrieb nicht.

Technische Grundlagen: [PlatformIO C3-Profil](https://docs.platformio.org/en/latest/boards/espressif32/esp32-c3-devkitm-1.html)
und [Espressif OTA-Partitionen](https://docs.espressif.com/projects/esp-idf/en/release-v4.4/esp32c3/api-reference/system/ota.html).

## Prüfung dieser Vorbereitung

### I2C-Diagnose ab C3-Firmware 3.2.2

`GET /api/i2c` startet beim ersten Aufruf einen Scan und liefert dessen Status.
`POST /api/i2c/scan` startet einen neuen Scan, sofern keiner läuft. Die Firmware
prüft GPIO0/SDA und GPIO1/SCL mit einer Adresse pro Poll im Bereich 0x08–0x77,
ohne Befehlsdaten an unbekannte Geräte zu schreiben. `addresses` enthält die
bestätigten Adressen als Dezimalzahlen. `sht45_probe_status` ist der rohe
Wire-Status für 0x44: 0 = ACK, 2 = Adress-NACK, 255 = noch nicht geprüft.
Ein ACK bestätigt die Erreichbarkeit einer Adresse, nicht den Sensortyp.

Am 10. November 2026 wurde 3.2.2 gezielt auf `b81f3f288aec` installiert und
der Neustart bestätigt. Zwei abgeschlossene Scans fanden ausschließlich
0x62 (SCD41). 0x44 meldete beide Male Status 2, also kein ACK. Es wurde kein
zweiter I2C-Teilnehmer gefunden; der SHT45 lieferte weiterhin keine Werte.
Die Firmwaredatei liegt unter `firmware/fnc-fogger-firmware_3.2.2.bin`.

Nach Austausch des Feuchtesensors am selben Tag antworten 0x44 und 0x62.
Die SHT45-Probe meldet Status 0 (ACK); Temperatur und Feuchte sind gültig
(beobachtet 29,01 °C und 48,66 %RH). Der zuvor verwendete Sensor beziehungsweise
dessen Modul ist damit als Fehlerursache naheliegend; ein interner Defekt wurde
nicht separat geprüft.

Die spätere Pinänderung ist ab C3-Firmware `3.2.1-esp32c3` vorbereitet:
MOSFET-Gate GPIO3, FAN PWM GPIO5, FAN TACH GPIO6. Die USB-/OTA-Testprotokolle
der beiden Minis beschreiben den damals installierten Stand 3.2.0 und bleiben
historisch unverändert. Die Pinänderung ist damit noch nicht auf den Geräten
installiert. Lüfter-PWM und Tacho sind als Pinzuordnung vorbereitet; die
Aktorenregelung ist weiterhin nicht implementiert.

- Beide Profile mit PlatformIO erfolgreich gebaut: `esp32s3` und `esp32c3_supermini`.
- BIN-Metadaten und SHA256 stimmen mit den erzeugten JSON-Manifesten überein.
- Automatische Tests prüfen die Datenbankmigration, Firmwareanzeige für
  Offline-Geräte, falsche Geräte-ID, unpassendes Chip-/Hardwareprofil,
  Profilprüfung im ESP-Updater und Neustartbestätigung.
- Die USB-Erkennung zeigte am 9. November 2026 keinen angeschlossenen ESP32.
  Erstinstallation, tatsächliche Flashgröße, WLAN und OTA an beiden Minis
  waren zu diesem Zeitpunkt noch auf Hardware zu prüfen. Anschließend wurde
  der [erste Mini erfolgreich per USB und OTA getestet](archive/esp32c3-mini-01-test-2026-11-09.md).
  Auch der [zweite Mini, fogger 01](archive/esp32c3-mini-02-test-2026-11-09.md), ist nun
  erfolgreich getestet. Die S3-Lanze wurde nicht aktualisiert.

## Gate assignment revision, 2026-11-10

Firmware 3.4.1 supersedes the historical GPIO3 gate assignment above with
GPIO21. FAN PWM remains GPIO5, FAN TACH remains GPIO6; I2C remains GPIO0/1.
GPIO21 is UART0 TX; ROM boot output can precede firmware initialization.
No eFuse or strapping changes were made. See hardware.md for boot limitations.
Do not install this firmware until the physical gate wiring matches GPIO21
and the previously overheated board and possible short circuit are checked.

## Independent recording, 2026-11-11

All registered non-removed devices are now recorded by the background process,
independently of Viewer/Device Selection lifetime. Device histories keep their
existing assignments. Windows login autostart, restart settings, watchdog,
health files and buffer recovery are described in
[background-logger.md](background-logger.md). Manual command renewal remains
viewer-scoped; the recording daemon does not control actuators.

## Gate assignment revision, firmware 3.4.2

The prepared C3 firmware returns the MOSFET gate to GPIO3. PWM GPIO5, tach
GPIO6 and I2C GPIO0/1 remain unchanged. Firmware 3.4.1's GPIO21 assignment
above is historical. No device has been updated by this change. Match the
physical gate wiring to GPIO3 before installing 3.4.2, and check the previously
overheated controller and wiring before use.

## Neuer C3 per USB eingerichtet, 11. November 2026

Gerät `B8:1F:3F:27:F4:E0` wurde auf COM9 als ESP32-C3, Revision 0.4, mit
4 MiB Flash bestätigt und per USB mit `3.4.2-esp32c3`, Build `619163873d9a`,
eingerichtet. Flash-Prüfsummen wurden verifiziert. WLAN und Geräteidentität
wurden unter `fnc-fogger-27f4e0.local` (bei Einrichtung `192.168.31.220`)
bestätigt. Die OTA-Uploadseite `/update` antwortet mit HTTP 200.

Das Gerät ist in der Geräteverwaltung registriert; seine eigene Messdatei ist
`logger/data/devices/b81f3f27f4e0.db`. Name und Location bleiben frei wählbar.
Weitere OTA-Updates führt der Benutzer selbst über Update Firmware im Viewer
aus. Bei dieser Einrichtung wurde kein OTA-Upload durchgeführt. Pinbelegung:
Gate GPIO3, FAN PWM GPIO5, FAN TACH GPIO6, SDA GPIO0 und SCL GPIO1.

## Lüfter-Pinbelegung, Firmware 3.4.3, 12. November 2026

Vorbereitete C3-Belegung: FAN PWM GPIO10, FAN TACH GPIO7, MOSFET-Gate GPIO3,
SDA GPIO0 und SCL GPIO1. Die ältere Firmware 3.4.2 verwendet weiterhin
PWM GPIO5 und TACH GPIO6. Vor dem Update die Lüfter-Signalleitungen passend
umlegen. GPIO8 und GPIO9 bleiben frei; Details in
[Hardware](hardware.md#proposed-gpio-assignments).

OTA-Datei: `firmware/fnc-fogger-firmware_3.4.3.bin`. Kein automatischer Upload;
die Installation erfolgt gezielt über Update Firmware am gewünschten Gerät.

## USB-WLAN-Diagnose, Firmware 3.4.4, 12. November 2026

Die serielle Ausgabe mit 115200 Baud enthält `[wifi]`-Zeilen bei Status- oder
Fehlergrundänderung und spätestens alle zehn Sekunden. Gemeldet werden der
Arduino-WLAN-Status und der letzte ESP-IDF-Verbindungsabbruchgrund, jeweils
mit Klartext und numerischem Code. Bei bestehender Verbindung kommen lokale
IP-Adresse, RSSI und Kanal dazu. Der letzte Abbruchgrund ist historisch und
kann auch nach erfolgreicher Wiederverbindung noch angezeigt werden.
WLAN-SSID und Passwort werden nicht ausgegeben. Es gibt keine neuen
Aktorbefehle oder Änderungen an Wiederverbindung, Sensorabtastung und
GPIO7/10-Belegung. WLAN-Ereignisse speichern nur den Fehlercode; die
USB-Ausgabe erfolgt im normalen Hauptloop.

Die bislang installierte Firmware 3.4.2 von `B8:1F:3F:27:F4:E0` bietet keinen
USB-Statusbefehl. Für diese Diagnose ist eine ausdrücklich freigegebene
USB-Installation der vorbereiteten Datei
`firmware/fnc-fogger-firmware_3.4.4.bin` nötig. Vor dem Flashen wird eine
Gerätesicherung angelegt; ein vollständiges Löschen des Flashs ist nicht
Teil dieser Diagnose.

### USB-Installation und Befund für B8:1F:3F:27:F4:E0

Am 12. November 2026 auf COM9 als ESP32-C3 Revision 0.4 mit 4 MiB Flash
bestätigt. Nach ausdrücklicher Freigabe wurde der vollständige Flash vorab
unter `logger/data/recovery/usb-b81f3f27f4e0-20261112/` gesichert; die
SHA256 und Partitionstabelle stehen im zugehörigen JSON. Die vorherige
Firmware war 3.4.2, Build `619163873d9a`. Die gültige OTA-Auswahl verweist
mit Sequenz 2 auf app1 bei `0x190000`.

Installiert wurde ausschließlich in app1: Firmware 3.4.4, Build
`f42a2df8927c`, 928752 Byte. Esptool bestätigte den Flash-Hash. Bootloader,
Partitionstabelle, app0, NVS, OTA-Auswahl und LittleFS wurden nicht beschrieben.
Die Firmware läuft nach Neustart und liefert Sensorwerte sowie USB-Diagnose.
Die Geräteverwaltung enthält den per USB bestätigten Firmwarestand; die
letzte WLAN-Erreichbarkeit wurde dadurch nicht vorgetäuscht oder aktualisiert.

USB-Befund: wiederholt `connect_failed (4)` mit
`authentication_failed (202)` und `authentication_expired (2)`;
anfangs auch `access_point_not_found (201)`. Das Gerät war während der
Prüfung weiterhin nicht per mDNS/HTTP erreichbar. Der Befund grenzt den
Fehler auf die WLAN-Anmeldung ein, beweist jedoch kein falsches Passwort.
Router-Zugriffssperren, Authentifizierungsmodus und Funkverhalten sind noch
zu prüfen. Lüfter war bei der Diagnose nicht angeschlossen.

### Weiterführende USB-Diagnose, Firmware 3.4.5

Nach laut Benutzer unauffälliger Router-Zugriffssperre wird die Diagnose um
`wifi status`, `wifi scan`, `wifi power low` und `wifi power default` erweitert.
Kommandos werden zeilenweise mit begrenztem Puffer und Bytebudget verarbeitet.
Ein zu langes Kommando wird vollständig verworfen. Der gezielte WLAN-Scan
läuft asynchron und pausiert die regulären Verbindungsversuche; bei bestehender
Verbindung wird er abgelehnt. Ausgabe: RSSI, Kanal, Authentifizierungsmodus
als ESP-IDF-Code und BSSID der passenden Access Points, keine SSID/Passwörter.
Der Sendeleistungstest mit 8,5 dBm ist eine bislang unbestätigte Hypothese;
vorher/nachher werden Status und tatsächlich angewendete Leistung verglichen.
Die ursprüngliche Leistung lässt sich wiederherstellen, Neustart verwirft den
Test. Zugangsdaten, Routerkonfiguration und Aktorausgänge werden nicht geändert.

### Erfolgreicher Leistungstest und gemeinsamer Firmware-Standard

Mit 3.4.5 und unveränderten Zugangsdaten meldete das Zielgerät zunächst
weiterhin Authentifizierungsfehler bei tatsächlich ausgelesenen 20 dBm
(`tx_power_qdbm=80`). Nach ausschließlich vorübergehender Umstellung auf
8,5 dBm (`tx_power_qdbm=34`) verband es sich mit `192.168.31.220`, Kanal 1,
RSSI ungefähr −38 bis −39 dBm. HTTP und mDNS bestätigten Firmware 3.4.5,
Build `20c133c6be1d`. Der unabhängige Logger nahm die Aufzeichnung automatisch
wieder auf. Der aktive Scan war davor fehlgeschlagen und ergab keine nutzbaren
Empfangsdaten; aus ihm wird keine Ursache abgeleitet. Das Experiment belegt
die erfolgreiche Verbindung bei reduzierter Sendeleistung, keine bestimmte
Hardware- oder Routerfehlfunktion.

Firmware 3.4.6 setzt auf Benutzerwunsch **8,5 dBm für alle Geräte** in
`include/config.h` (`WIFI_TX_POWER_QDBM = 34`). Keine gerätespezifische NVS-Vorgabe.
USB-Kommandos `wifi power <dBm>` ändern die Leistung nur bis zum Neustart;
`wifi power default` stellt 8,5 dBm wieder her. Stufen: 2, 5, 7, 8.5, 11, 13,
14, 15, 16.5, 18, 20 dBm. `wifi reconnect` wiederholt nur die WLAN-Anmeldung.
Der Status enthält den Sicherheitsmodus (`auth`); der Scan pausiert zusätzlich
Arduino-Auto-Reconnect.

Ergebnisse und Installationsstand: [WLAN-Leistungstest](wifi-power-test-2026-11-12.md).


## Neuer Controller b81f3f2905f4, 24./25. November 2026

ESP32-C3 (Revision v0.4), 4 MiB Flash, per USB an COM11 identifiziert.
Vollständige Erstinstallation mit Bootloader, Partitionstabelle,
OTA-Auswahl und Firmware `3.6.16-esp32c3`, Build `47a0ae64619f`.
Quellfingerprint, SHA-256 und geschriebene Flashbereiche wurden geprüft.
Ein anschließendes OTA derselben Firmware bestätigte Geräte-ID,
Hardwareprofil, Firmware, Build und neue Boot-ID.

WLAN-Adresse bei Einrichtung: `192.168.31.89`,
mDNS: `fnc-fogger-2905f4.local`, Anzeigename: `Secondi a Nessuno`.
In der lokalen Geräteverwaltung ist `actuators_installed` aktiviert,
damit der Viewer das Control Panel anzeigt.

Aktueller Installationsstand am 25. November 2026:
`3.6.21-esp32c3`, Build `57871d832342`, per OTA installiert und mit
neuer Boot-ID verifiziert. Alle 178 Tests und der C3-Build bestanden.
Manual Mode und PI verwenden gemeinsam 100-ms-EIN-Pulse mit
stellwertabhängiger Pause; bei 100% dauerhaft EIN. Es gibt keine
Unterscheidung nach Fogger-Typ mehr. Die vorübergehenden manuellen
Messzähler wurden entfernt; vorhandene SQLite-Messdaten bleiben erhalten.
Die anderen Controller wurden bei diesem Update nicht geflasht.

Beim Sensorvergleich am selben Anschluss lieferte SCD41 `77AFEF073BA5`
gültige CO2-Werte. Ein anderes Modul antwortete nicht unter `0x62`,
während der SHT45 unter `0x44` erreichbar blieb. Sensor-outages-Zähler
gelten seit dem letzten Controllerstart; Sensor-Erholung, Sensor-Neustart,
Reset PI und Exit Error Mode setzen sie nicht zurück.

Die vorhandene Git-Version `2.56.1.windows.1` aus GitKraken 12.7.0 wurde
zum Benutzer-PATH hinzugefügt; danach war der PlatformIO-Build erfolgreich.
Bereits laufende Anwendungen benötigen für den neuen PATH einen Neustart.
