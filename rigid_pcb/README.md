# SmartPaddle Rigid PCB Study

This directory contains a first rigid-PCB architecture study for SmartPaddle.

## Architecture

- Drone-frame-like rigid carrier in the OpenSCAD sweet-zone.
- ESP32-C6-WROOM-1 and IM948 are embedded into board cutouts.
- The carrier uses plated castellated half-hole pads along the module cutout edges.
- Four PZT front-end areas are placed near the PZT positions along the radial direction.
- Each PZT front-end keeps the 1M discharge resistor and BAT54S clamp close to the PZT.
- Handle-side LED, button, battery, USB D+/D- are still wire-connected by large solder pads.

## Current Electrical Intent

- `VBAT_IN`: protected 10440 battery positive before soft switch.
- `VBAT`: soft-switched battery rail for IM948 and external WS2812 power.
- `VCC`: local 3.3V rail for ESP32-C6 and PZT clamp reference.
- `LED_DATA`: ESP32 GPIO output before the 330R series resistor.
- `LED_DIN`: external WS2812 DIN solder pad after the 330R resistor.
- `BTN_SW`: external single button line.
- `USER_BTN`: ESP32 button sense.
- `PWR_LATCH`: ESP32 soft-power latch control.
- `BOOT` and `EN`: local test pads for first flashing and recovery.

## Thickness Estimate

Recommended first rigid-board thickness: `0.8 mm`.

Approximate assembled height:

- FR4 board: `0.8 mm`
- ESP32-C6-WROOM-1: about `3.1 mm`
- solder/adhesive/mechanical allowance: `0.3-0.6 mm`
- recommended enclosure pocket depth at ESP32: `4.3-4.8 mm`

If the board is changed to `1.0 mm`, use about `4.6-5.0 mm` pocket depth.

## Weight Estimate

The current outline is a skeleton-style carrier with a center spine, four PZT ears, and module cutouts.

For FR4 density around `1.85 g/cm^3`:

- `0.8 mm` skeleton study outline after ESP32/IM948 cutouts: about `10 g`.
- A full paddle-sized rigid board would be much heavier and is not recommended as the default architecture.

The preferred production direction is a central rigid board plus narrow arms or separate small PZT front-end islands.

## Additional Purchasing List

| Part | Suggested spec | Qty |
| --- | --- | ---: |
| P-MOSFET | AO3401, SOT-23 | 1 |
| N-MOSFET | 2N7002 or BSS138, SOT-23 | 1 |
| 3.3V LDO | AP2112K-3.3, SOT-23-5, 600mA | 1 |
| Diode | 1N4148, SOD-323/SOD-523 | 1-2 |
| Resistor | 100k, 0603 | 3 |
| Resistor | 330R, 0603 | 1 |
| Capacitor | 10uF, 0603/0805, >=6.3V | 2 |
| Capacitor | 100nF, 0603 | 1 |
| Wire | 28-32AWG silicone wire | as needed |
| Adhesive | electronics silicone/UV glue/hot glue | as needed |

## Status

`generate_kicad.py` creates the current rigid-PCB mechanical/electrical placement study.

Current KiCad DRC status:

- 26 copper-to-edge warnings remain by design because the ESP32 and IM948 plated castellated pads are centered on the module cutout edges.
- 58 unconnected items remain because routing is intentionally disabled in this structural study.

Next PCB work:

- decide whether the embedded module half-holes should stay as plated slots/half-holes or become wider solder shelves,
- route power, USB/UART, LED, button, and PZT nets on the skeleton carrier,
- add fab notes for castellated internal cutouts before manufacturing.
