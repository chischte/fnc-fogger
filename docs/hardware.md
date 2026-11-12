# Hardware for fnc-fogger wiring diagram, revision 07

Updated 2026-11-12. Wiring reference for C3 firmware 3.4.3; verify the actual assembly before use.

The [fnc-fogger wiring diagram, revision 07](fnc-fogger-wiring.svg) is the
authoritative reference for the planned assembly. Tables and notes below supplement it.

## Power supply

Use a regulated 24 V DC supply with common ground and one XZG DC/DC buck:

| Source | Destination |
| --- | --- |
| Supply +24 V | Noctua pin 2 and XZG buck IN+ |
| Supply GND | Noctua pin 1, IRLB8721 source, ESP32 GND, XZG buck IN- / OUT- |
| XZG buck OUT+ = 5.0 V | ESP32-C3 SuperMini 5V and fogger positive |

Use the pictured compact XZG buck (black PCB, 4R7 inductor). The product title
lists multiple output voltages, so the exact variant/setting is uncertain.
Use the 5 V variant or setting and measure 5.0 V before connecting. Do not
change unidentified solder bridges. IN+/IN- and OUT+/OUT- are functional
labels; check physical positions on the delivered module. Check the board's
appropriate 5 V input; never apply 5 V to 3V3. Route load currents directly
back to the supply, not through ESP32/sensor wiring. Size wiring and fuses for
load and inrush current. The 24 V and GND nets are drawn without crossings.

## Proposed GPIO assignments

| Function | GPIO | Connection/configuration |
| --- | --- | --- |
| I2C SDA | 0 | SCD41 and SHT45 SDA |
| I2C SCL | 1 | SCD41 and SHT45 SCL |
| FAN_PWM | 10 | Direct to Noctua pin 4; 3.3 V push-pull, 25 kHz |
| FAN_TACH | 7 | Noctua pin 3; input with internal pull-up to 3.3 V |
| FOG_EN | 3 | Direct to IRLB8721 gate, pin 1; LOW = OFF, HIGH requests ON |

GPIO numbers are not physical connector positions. Check availability on the
actual ESP32-C3 SuperMini. Explicitly configure I2C SDA GPIO0 / SCL GPIO1.
Leave GPIO8 (board LED) and GPIO9 (BOOT) unused; both are boot configuration
pins. Fan tach GPIO7 and PWM GPIO10 are not strapping pins. USB uses GPIO18/19
and remains available. See
[Espressif boot-mode selection](https://docs.espressif.com/projects/esptool/en/latest/esp32c3/advanced-topics/boot-mode-selection.html).

The current actuator assignment is gate GPIO3, fan PWM GPIO10, fan tach GPIO7
(C3 firmware 3.4.3; 3.4.2 used PWM GPIO5 / tach GPIO6). Firmware 3.4.1 used GPIO21, which is also UART0 TX;
3.3.x/3.4.0 used GPIO3. The current assignment avoids the UART0 TX boot output.
The firmware requests GPIO3 LOW at actuator initialization. During reset or
before initialization, a gate-source pull-down is still needed for a defined
OFF state. No eFuses or strapping pins are changed.
The SVG wiring plan matches this GPIO3 assignment. Its component artwork is
illustrative; connector order and physical pinout must be checked on the modules.
See [Espressif's boot and pin documentation](https://documentation.espressif.com/esp32-c3_datasheet_en.html).

Pin reference: [Apache NuttX: ESP32-C3 SuperMini](https://nuttx.incubator.apache.org/docs/latest/platforms/risc-v/esp32c3/boards/esp32c3-supermini/index.html).

## Sensors

| ESP32 signal | SCD41 breakout | SHT45 breakout |
| --- | --- | --- |
| 3V3 | Appropriate 3.3 V supply input | Appropriate 3.3 V supply input |
| GND | GND | GND |
| GPIO0 | SDA | SDA |
| GPIO1 | SCL | SCL |

An optional **SHTC3 (I2C address `0x70`)** measures ambient humidity and temperature
on the same bus:

| SHTC3 signal | Connection |
| --- | --- |
| 3V3 | 3.3 V sensor supply |
| GND | Common ground |
| SDA | GPIO0, parallel to SCD41 and SHT45 |
| SCL | GPIO1, parallel to SCD41 and SHT45 |

These are signal assignments; check physical pin order on the module.
SHTC3 is optional and measures ambient conditions.

Addresses: SCD41 `0x62`, SHT45 `0x44`. No multiplexer needed. Keep I2C wiring
short, initially at 100 kHz. Breakout pull-ups must connect to 3.3 V. Omitting
the optional tach resistor does not remove the need for I2C pull-ups; add them
if absent on the breakouts.

At 3.3 V, SCD41 requires up to 205 mA peak in addition to other board loads.
Check regulator headroom. Mount sensors in representative chamber air,
protected from direct mist and condensation. Only SHT45 humidity feeds the humidity PI.

Sources: [SCD4x datasheet](https://sensirion.com/resource/datasheet/scd4x),
[SHT4x datasheet](https://sensirion.com/resource/datasheet/sht4x).

## Noctua NF-A4x10 24V PWM

| Fan pin | Signal / usual wire colour | Connection |
| --- | --- | --- |
| 1 | GND / black | Common ground |
| 2 | +24 V / yellow | Direct to supply +24 V |
| 3 | TACH / green | GPIO7 with internal 3.3 V pull-up |
| 4 | PWM / blue | Direct to GPIO10 |

Check pin numbering against the connector, not an assumed viewing direction.
The fan receives continuous 24 V; only its PWM input is driven with 3.3 V at
25 kHz. 100% HIGH means maximum speed. No buck or load MOSFET in the fan path.
Tach provides two open-collector pulses per revolution; check signal quality
with the internal pull-up on the assembly. With no PWM signal, the fan runs
at full speed.

Sources: [Noctua microcontroller guide](https://www.noctua.at/en/support/faqs/microcontroller-guide-pwm-setup-and-rpm-monitoring),
[NF-A4x10 24V PWM](https://www.noctua.at/en/products/nf-a4x10-24v-pwm/specifications).

## Fogger with IRLB8721

Requested direct drive without gate series resistor or gate-source pull-down.
Switching at 3.3 V successfully tested (2026-11-09, fogger module supplied at 5 V).

### Pinout and exact connections

TO-220 front view: marking towards you, metal tab behind, legs pointing down.
Left to right: **1 Gate, 2 Drain, 3 Source**. The metal tab is also drain and
must remain insulated from GND/enclosure.

```text
             IRLB8721
         Marking towards you
          +------------+
          |  IRLB8721  |
          +--+--+--+---+
             1  2  3
             G  D  S
             |  |  +-------- Supply GND / ESP32 GND
GPIO3 --------+  |
                +----------- Fogger negative
Buck OUT+ 5 V -------------- Fogger positive
```

| Terminal | Connection |
| --- | --- |
| Gate, pin 1 left | Direct to ESP32 GPIO3 |
| Drain, pin 2 middle | Fogger negative |
| Source, pin 3 right | Supply negative and ESP32 GND |
| Fogger positive | XZG buck OUT+ (5.0 V) |
| Metal tab | Drain; same potential as fogger negative |

**Do not also connect fogger negative to GND:** that would bypass the MOSFET.
Use a complete 5 V ultrasonic module with its own driver, not a bare piezo element.

### Limits of the requested resistor-free variant

- Switching at 3.3 V successfully tested: on 2026-11-09 the user confirmed clean switching of the 5 V fogger module. This records the tested assembly.
- Without gate-source pull-down, the gate can remain charged or undefined during reset, boot or ESP32 disconnection. Software LOW and an internal GPIO pull-down do not guarantee OFF then. Do not approve unattended operation in that state.
- Without gate series resistance, GPIO charging currents and ringing are not externally limited; keep wires short and check the real assembly.
- Fogger uses 5 V from the buck; fan remains directly on 24 V. Only fan and buck input connect to the 24 V net.

Set GPIO3 LOW early. HIGH requests ON; LOW switches off with a powered,
actively driven GPIO. Fixed ON time is 200 ms, OFF time varies (50%: 200 ms
ON / 200 ms OFF); no 25 kHz fogger PWM. Check minimum run times, restart
behaviour and independent dry-run protection for the actual module.

Source: [Infineon IRLB8721 datasheet, pinout and ratings](https://www.infineon.com/assets/row/public/documents/24/49/infineon-irlb8721-datasheet-en.pdf).

## Upload and OTA

Firmware 3.3.0 implements startup-only fan/fogger tests and measured tach RPM;
the PI actuator controller is not implemented. See [commissioning mode](control.md).
The `esp32c3_supermini`
profile now prepares sensor operation and WiFi OTA with a 4 MiB partition layout.
See [device management and USB provisioning](device-management.md).
The XZG buck keeps the ESP32 supplied with 5 V.
Initial installation and recovery use USB; disconnect external 5 V unless
the board supports simultaneous supplies.

During updates request fogger OFF and set the defined fan fault speed.
The resistor-free gate circuit does not guarantee OFF during the subsequent
reset. Resume control only after valid sensor readings.

## Wi-Fi transmit power

Firmware 3.4.6 sets **8.5 dBm on every device**, defined by
`Config::WIFI_TX_POWER_QDBM = 34` in `include/config.h`. No per-device NVS override.
USB allows temporary comparisons; reboot restores this default. The C3 driver
supports effective ceilings of 2, 5, 7, 8.5, 11, 13, 14, 15, 16.5, 18 and 20 dBm.
This is a configured ceiling, not a measurement of radiated power.
See [Espressif API](https://docs.espressif.com/projects/esp-idf/en/v4.4.7/esp32c3/api-reference/network/esp_wifi.html)
and [measured comparison](wifi-power-test-2026-11-12.md).
