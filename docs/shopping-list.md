# Shopping list: selected assembly

| Quantity | Part | Purpose |
| --- | --- | --- |
| 1 | XZG DC/DC buck, pictured compact variant | 24 V to 5.0 V for ESP32 and fogger |
| 1 | [Noctua NF-A4x10 24V PWM](https://www.noctua.at/en/products/nf-a4x10-24v-pwm/specifications) | Direct 24 V supply; PWM to GPIO10 |
| 1 | IRLB8721, already available | Fogger low-side switch; gate directly to GPIO3 |
| As needed | Wires, terminals, fuse, insulation | Power and assembly |
| As needed | Dupont cables | Sensor and signal wiring |

One buck powers controller and fogger at 5 V; only fan and buck input stay
on the 24 V net. The actual buck must support 24 V input and 5.0 V output;
measure output before connecting. No gate resistors in the requested variant;
see [electrical limits](hardware.md#limits-of-the-requested-resistor-free-variant).

Add ESP32-C3 SuperMini, SCD41 and SHT45 breakouts, and a complete 5 V fogger
module if not already available. A regulated 24 V supply is available.
Document fogger model, dry-run protection, load current and switching spikes
before hardware approval.
