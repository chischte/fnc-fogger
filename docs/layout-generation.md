# Image generation

## Current: draft 04

Revised on 2026-10-24 using the built-in image_gen tool: ESP32-C3 SuperMini
replaces ESP32-S3; a compact XZG buck replaces LM2596. No power-supply picture
or chamber-interior label. I2C uses GPIO0/GPIO1; GPIO4/5/6 serve fan and fogger.
The exact buck variant is unclear from its product title; measure its 5 V
output before connecting.

Output: `fnc-fogger-layout-v4.png`. Historical generation instructions:
[layout-v4-prompt.txt](layout-v4-prompt.txt). The wiring diagram is authoritative;
`hardware.md` supplements it with tables and notes.

Visual review prompted corrections to the controller illustration and buck
input ground wiring. The buck terminals are schematic; verify actual positions.
The orange net serves only fan and buck IN+ at 24 V. ESP32 and fogger use
buck OUT+ at 5 V. See `hardware.md` for the complete nets.

## Optional ambient sensor, 2026-11-08

An OPTIONAL SHTC3 was added with dashed border and branches. It measures
ambient humidity and temperature, connected in parallel to 3.3 V, GND,
SDA GPIO0 and SCL GPIO1; I2C address `0x70`. The filename remains the project reference.

## Fogger test and 5 V supply, 2026-11-09

Switching at 3.3 V successfully tested with the fogger supplied at 5 V.
Fogger positive moves to buck OUT+ (5 V); Noctua remains directly on 24 V.
Fixed fogger ON time is now 200 ms; at 50%, OFF time is also 200 ms. The warning
about undefined reset state without gate pull-down remains. Edited using the
built-in image_gen tool; [edit prompt](layout-fogger-5v-prompt.txt).

The power section was then redrawn without any crossing between +24 V and
GND: the short orange fan branch goes up; the ground distribution stays below.
The previous crossing bridge was ambiguous.
[Correction prompt](layout-power-no-crossing-prompt.txt).

## English translation, 2026-11-09

All diagram labels translated to English using the built-in image_gen tool.
Wiring, pin assignments, the optional SHTC3 and the separated power nets remain
unchanged. [Translation prompt](layout-english-prompt.txt).

## I2C cable colors, 2026-11-09

The four sensor-bus rows in the controller pin table now use the cable colors
confirmed by the user, with the subsequent SDA revision: 3V3 red, GND black,
GPIO0/SDA blue, GPIO1/SCL yellow.
Text is black on red and yellow, and white on black and blue for legibility.
Edited with the built-in image_gen tool. The remaining diagram and the
schematic wire-color legend are unchanged.

## Noctua harness colors, 2026-11-09

Panel 4 fan leads and numbered circles follow the manufacturer's
[NF-A4x10 24V PWM specifications](https://www.noctua.at/en/products/nf-a4x10-24v-pwm/specifications):
1 black = GND, 2 yellow = +24 V, 3 green = RPM/TACH (GPIO5),
4 blue = PWM (GPIO4). Circle 2 uses black lettering; circles 1, 3 and 4
use white lettering. The schematic net colors outside the fan panel remain
unchanged. Edited using the built-in image_gen tool.

## Actuator GPIO reassignment, 2026-11-09

The current assignment supersedes the earlier GPIO4/5/6 mapping above:
FAN_PWM GPIO5, FAN_TACH GPIO6, MOSFET gate GPIO3. Updated the three controller
table rows, the two Noctua connection labels and the gate signal box using
the built-in image_gen tool. Wire colors and sensor pins remain unchanged.
The initially requested GPIO21 gate was replaced by GPIO3 with user approval
because GPIO21 is UART0 TX and may output boot messages before firmware starts.
Firmware 3.2.1-esp32c3 prepares this mapping; device installation is separate.

## Direct board callouts

Replaced the controller connection table with direct colored leaders to a
simplified component-side SuperMini illustration, USB-C at the bottom.
Exactly eight contacts are shown on each side. Used pins are prominent and
unused pins are gray. Left top-to-bottom: GPIO0, GPIO1, GPIO2, GPIO3, GPIO4,
3V3, GND, 5V. Right top-to-bottom: GPIO21, GPIO20, GPIO10, GPIO9, GPIO8,
GPIO7, GPIO6, GPIO5. Checked against the
[Apache NuttX SuperMini header reference](https://nuttx.apache.org/docs/latest/platforms/risc-v/esp32c3/boards/esp32c3-supermini/index.html).
This is a pin-location illustration, not an exact photograph of the PCB.
Edited using the built-in image_gen tool and visually checked for contact
count, signal assignment and readable contrasting labels.

## Buck internal common ground, 2026-11-10

Edited panel 1 with the built-in image_gen tool following the user's marked
reference: a black line now joins buck IN- and OUT- directly beneath the
module, representing their internal connection on the installed buck.
Removed the redundant lower distributor branch and label Buck OUT- (GND).
The three branches to ESP32 GND, fan pin 1 and MOSFET source remain.
Visually checked the connection and branch removal. The project reference
remains `fnc-fogger-layout-v4.png`.
[Exact edit specification](layout-buck-common-ground-prompt.txt).

## Sensor-bus cable colors, 2026-11-10

Panel 3 now uses red for 3V3, black for GND, blue for SDA GPIO0 and yellow
for SCL GPIO1, including all three sensors and the dashed optional branches.
SCL text stays dark for readability. Generated with the built-in image_gen
tool, visually corrected and checked branch by branch. Only the edited
sensor-wire region was transferred into the existing diagram so the other
panels remain unchanged.
[Edit specification](layout-i2c-net-colors-prompt.txt).

## Gate GPIO21, 2026-11-10

At the user's request, GPIO21 now drives the MOSFET gate instead of GPIO3.
Panel 2 marks the right top contact GPIO21 / GATE in purple; left fourth GPIO3
is gray and unused. Panel 5 gate command label is GPIO21. Other functional
assignments remain unchanged. Edited with built-in image_gen and visually
checked. [Edit specification](layout-gate-gpio21-prompt.txt).
Firmware 3.4.1 and hardware.md document the new mapping and UART0 ROM boot
output limitation. No eFuse changes or physical device upload were performed.
