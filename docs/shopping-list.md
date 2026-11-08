# Einkaufsliste – gewählter Aufbau

| Menge | Bauteil | Verwendung |
| --- | --- | --- |
| 1 | XZG DC/DC-Buck, abgebildete kompakte Ausführung | 24 V auf 5,0 V für ESP32 |
| 1 | [Noctua NF-A4x10 24V PWM](https://www.galaxus.ch/de/s1/product/noctua-nf-a4x10-24v-pwm-40-mm-1x-pc-luefter-40864061) | Direkt mit 24 V versorgt; PWM an GPIO4 |
| 1 | IRLB8721, vorhanden | Fogger-Low-Side-Schalter, Gate direkt an GPIO6 |
| nach Bedarf | Leitungen, Klemmen, Sicherung, Isolation | Versorgung und Montage |
| nach Bedarf | Dupont-Kabel | Sensor- und Signalleitungen |

Ein Buck-Modul versorgt den Controller; Lüfter und Fogger bleiben direkt am 24-V-Zweig. Die konkrete Buck-Variante muss 24 V am Eingang und 5,0 V am Ausgang unterstützen; Ausgang vor Anschluss messen. Keine Gate-Widerstände in der gewünschten Variante; deren elektrische Grenzen stehen in [hardware.md](hardware.md#grenzen-der-gewünschten-widerstandslosen-variante).

ESP32-C3 SuperMini-Devboard, SCD41- und SHT45-Breakouts sowie vollständiges 24-V-Fogger-Modul ergänzen, soweit noch nicht vorhanden. Geregelte 24-V-Versorgung ist vorhanden. Fogger-Modell, Trockenlaufschutz, Laststrom und Schaltspitzen vor Hardwarefreigabe dokumentieren.
