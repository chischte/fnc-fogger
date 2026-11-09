# Regelungskonzept

Dies ist eine Spezifikation für die spätere Firmware; PID-Werte sind noch nicht abgestimmt.

## CO₂ → Zuluft

Regelfehler = CO₂-Istwert − CO₂-Sollwert. Positiver Fehler erhöht den Lüfter-Stellwert. Begrenzung auf die erprobte Mindestlüftung bis 100 %, Anti-Windup auf Basis des tatsächlich begrenzten Ausgangs. Der ESP32 setzt diesen Stellwert direkt und ohne Invertierung in 3,3-V-Push-Pull-PWM mit 25 kHz für den Noctua NF-A4x10 24V PWM um. GPIO5 erfasst das Tachosignal mit internem Pull-up; ein externer Tacho-Widerstand ist nicht vorgesehen. Tacho dient zur Erkennung von Stillstand nach Ablauf einer Anlaufzeit.

Zuluft kann CO₂ nur senken, wenn ihre Konzentration niedriger ist und ein Abluftweg vorhanden ist. Ohne CO₂-Quelle ist eine aktive Erhöhung nicht möglich. Deshalb ist der Sollwert nur innerhalb der physikalisch erreichbaren Grenzen haltbar.

Den CO₂-Regler nur mit einem neuen gültigen Messwert aktualisieren. Für den geplanten SCD41-Standardbetrieb zunächst 5-s-Messtakt vorsehen; die Sensor- und Kammerträgheit beim Tuning berücksichtigen. Quelle: [SCD4x-Datenblatt](https://sensirion.com/resource/datasheet/scd4x). Automatische Selbstkalibrierung nur verwenden, wenn deren Frischluftbedingungen erfüllt sind.

## Relative Feuchte → Fogger

Die Lüfterdrehzahl wird ausschließlich vom CO₂-PI-Regler bestimmt. Der
Feuchte-PI-Regler und die Fogger-Steuerung dürfen keine Lüfterdrehzahl
anfordern oder erhöhen. Der Fogger darf nur laufen, wenn die gemessene
Lüfterdrehzahl mindestens die experimentell bestimmte zuverlässige
Mindestdrehzahl erreicht. Fordert der CO₂-Regler wegen ausreichend niedriger
CO₂-Konzentration keinen Luftaustausch an, bleibt der Fogger unabhängig vom
Feuchtebedarf aus. Bei Unterschreiten der Mindestdrehzahl wird der Fogger
sofort ausgeschaltet. Diese Freigabesperre muss beim Anti-Windup des
Feuchte-PI-Reglers berücksichtigt werden.

Regelfehler = rF-Sollwert − rF-Istwert. Positiver Fehler erhöht den PID-Ausgang zwischen 0 und 100 %. GPIO6 schaltet über den IRLB8721 als Low-Side-Schalter die 24-V-Fogger-Versorgung (Gate an GPIO6, Drain an Fogger-Minus, Source an GND; HIGH fordert EIN an, LOW = AUS). Der Ausgang wird in einem konfigurierbaren Zeitfenster in eine EIN-Dauer übersetzt: t_ein = Stellwert / 100 × Fensterdauer. Kein 25-kHz-Schalten der Fogger-Versorgung.

Fensterdauer und Mindest-EIN-/AUS-Zeiten erst nach Auswahl des Foggers festlegen. Kurze Anforderungen unterhalb der Mindestlaufzeit gezielt unterdrücken oder über Fenster akkumulieren; die gewählte Strategie muss mit dem Anti-Windup abgestimmt werden. Bei 0 % bleibt der Fogger aus; 100 % darf nur bei freigegebenem Dauerbetrieb dauerhaft einschalten. Schutzabschaltungen wirken sofort, auch während einer Mindestlaufzeit.

SHT45-Werte in festem, konfigurierbarem Takt erfassen; PID nur mit frischen gültigen Werten und tatsächlichem Zeitabstand berechnen. Lüftung beeinflusst auch die Feuchte. Beide Regler zuerst einzeln, danach gemeinsam abstimmen. Zunächst D-Anteil auf null setzen; später nur bei belegtem Nutzen ergänzen, mit gefilterter Ableitung des Messwerts.

## Fehler- und Startzustände

| Ereignis | Vorgesehene Reaktion |
| --- | --- |
| Boot/Reset, noch keine gültigen Messungen | Fogger AUS anfordern; ohne Gate-Pulldown ist AUS beim Reset nicht garantiert; Lüfter zunächst volle Drehzahl |
| SHT45 ungültig oder veraltet | Fogger sofort AUS; Feuchteintegrator anhalten/zurücksetzen |
| SCD41 ungültig oder veraltet | Lüfter auf konfigurierte Fehlerdrehzahl (zunächst 100 %), Fogger AUS |
| Lüfterstillstand bei angeforderter Drehzahl | Fehler melden, Fogger AUS |
| Wasser fehlt | Fogger durch Trockenlaufschutz AUS |
| Konfigurierte Feuchteobergrenze überschritten | Fogger AUS unabhängig vom PID |

Zeitüberschreitungen relativ zum Sensortakt definieren. Wiederanlauf erst nach gültigen Messungen und beseitigter Fehlerursache mit begrenztem, sprungarmem Ausgang. Fehlerzustände müssen sichtbar bleiben.

## Offener Versuch nach Einbau des Lüfters

- [ ] Sobald der Lüfter installiert ist: mit dem tatsächlichen Luftweg prüfen,
  ab welcher PWM-Vorgabe und gemessenen Drehzahl er aus dem Stillstand
  zuverlässig anläuft. Mehrere Starts wiederholen.
- [ ] Separat die kleinste zuverlässig gehaltene Drehzahl bei bereits
  laufendem Lüfter bestimmen. Anlauf- und Betriebsgrenze mit Reserve festhalten.
- [ ] Fogger-Freigabe erst bei per Tacho bestätigter Mindestdrehzahl prüfen;
  bei Stillstand oder zu geringer Drehzahl muss der Fogger ausschalten.

## Firmware-Struktur

Sensorzugriff, hardwareunabhängiger PID, Fogger-Zeitfenstersteuerung, Lüfter-/Lastschalter-Treiber und Zustandsüberwachung getrennt halten. Anwendung verbindet die Module mit expliziten Abhängigkeiten. Zeitsteuerung monoton und ohne blockierende Wartezeiten; Netzwerk und UI später als separate Module ergänzen.

Vor Hardwarefreigabe: Reset-Ausgänge, Sensorverlust, Lüfterstillstand, Trockenlauf, PWM-Polarität sowie minimale Schaltzeiten prüfen. PID erst mit dem realen Luftvolumen, Luftweg und Fogger abstimmen.

## WLAN-OTA-Updates

Erstinstallation per USB, danach Firmware-Updates über WLAN mit Authentifizierung und geeigneter OTA-Partitionierung. Noch nicht implementiert. Der XZG DC/DC-Buck liefert während des OTA-Uploads weiterhin 5 V; USB ist dafür nicht nötig.

Vor dem Schreiben der Firmware Fogger ausschalten, beide PID-Integratoren anhalten und Lüfter auf definierte Fehlerdrehzahl (zunächst 100 %) setzen. Nach erfolgreichem Upload neu starten, Ausgangszustände setzen und erst nach gültigen Sensorwerten in die Regelung wechseln. Bei Abbruch Zustand melden und Wiederanlauf kontrollieren. USB bleibt als Wiederherstellungsweg verfügbar.

Die direkte IRLB8721-Ansteuerung bei 3,3 V ohne Widerstände ist nicht hardwareseitig freigegeben. Reset-Verhalten und vollständiges Durchschalten sind nicht garantiert; siehe [elektrische Grenzen](hardware.md#grenzen-der-gewünschten-widerstandslosen-variante).
