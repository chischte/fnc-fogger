# Hardware for fnc-fogger wiring diagram, draft 04

Updated 2026-11-09. Wiring proposal, not executable actuator firmware or hardware approval.

The [fnc-fogger wiring diagram, draft 04](fnc-fogger-layout-v4.png) is the
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
| FAN_PWM | 5 | Direct to Noctua pin 4; 3.3 V push-pull, 25 kHz |
| FAN_TACH | 6 | Noctua pin 3; input with internal pull-up to 3.3 V |
| FOG_EN | 3 | Direct to IRLB8721 gate, pin 1; LOW = OFF, HIGH requests ON |

GPIO numbers are not physical connector positions. Check availability on the
actual ESP32-C3 SuperMini. Explicitly configure I2C SDA GPIO0 / SCL GPIO1.
Leave GPIO8 (board LED) and GPIO9 (BOOT) unused; both are boot configuration
pins. USB uses GPIO18/19 and remains available.

The current actuator assignment is gate GPIO3, fan PWM GPIO5, fan tach GPIO6
(C3 firmware 3.2.1 and later). GPIO21 was considered for the gate but rejected:
it is UART0 TX and may output boot messages before application initialization.
See [Espressif's boot and pin documentation](https://documentation.espressif.com/esp32-c3_datasheet_en.html).
An external gate-source pull-down is still required for a defined OFF state
while GPIO3 is high-impedance during reset.

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
| 3 | TACH / green | GPIO6 with internal 3.3 V pull-up |
| 4 | PWM / blue | Direct to GPIO5 |

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
GPIO3 -------+  |
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

The planned actuator controller is not implemented. The `esp32c3_supermini`
profile now prepares sensor operation and WiFi OTA with a 4 MiB partition layout.
See [device management and USB provisioning](device-management.md).
The XZG buck keeps the ESP32 supplied with 5 V.
Initial installation and recovery use USB; disconnect external 5 V unless
the board supports simultaneous supplies.

During updates request fogger OFF and set the defined fan fault speed.
The resistor-free gate circuit does not guarantee OFF during the subsequent
reset. Resume control only after valid sensor readings.
