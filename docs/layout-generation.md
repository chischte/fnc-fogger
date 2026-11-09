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
