# SmartPaddle Rigid PCB Study

This directory contains a first rigid-PCB architecture study for SmartPaddle.

## Architecture

- Central rigid electronics island in the OpenSCAD sweet-zone.
- ESP32-C6-WROOM-1 and IM948 stay in the center.
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

The current conservative outline is intentionally large so all copper remains on FR4 during the first electrical study. It should be lightened into narrow arms after DRC/routing review.

For FR4 density around `1.85 g/cm^3`:

- `0.8 mm` full conservative study outline: roughly tens of grams, depending on final arm cutouts.
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

`generate_kicad.py` creates the first placement/routing study, but this layout is not yet production-ready. The current route needs cleanup before commit/PR:

- reduce outline into true arms,
- reroute low-speed handle wires away from USB and latch paths,
- keep the PZT signal routes away from the 3.3V clamp bus,
- rerun KiCad DRC to zero violations.
