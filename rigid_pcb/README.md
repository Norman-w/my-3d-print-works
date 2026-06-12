# SmartPaddle Rigid PCB Study

This directory contains a first rigid-PCB architecture study for SmartPaddle.

## Architecture

- Drone-frame-like rigid carrier in the OpenSCAD sweet-zone: 42×42mm central electronics island, four narrow radial arms, four PZT front-end docks, and one short handle tail.
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

The current outline is a skeleton-style carrier generated from the same 2D profile used by `enclosure/paddle_shell.scad`: a 42×42mm central electronics island, four narrow radial arms that match the PZT slot directions, four wider PZT docks, one short handle tail ending just past the handle-neck screw, and module cutouts.

For FR4 density around `1.85 g/cm^3`:

- `0.8 mm` skeleton study outline after ESP32/IM948 cutouts: about `4.4 g`.
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

## Incremental KiCad Workflow

Do not use the old full-board generator as the normal edit loop once manual
placement/routing starts.  The preferred flow is incremental:

1. Open or create a `.kicad_pcb` once.
2. Run only the update script for the layer of intent that changed.
3. Run `ato build --keep-designators --keep-net-names` after electrical logic changes.
4. Manually place parts and route in KiCad against the refreshed references.

Scripts:

| Script | Owns | Preserves |
| --- | --- | --- |
| `scripts/update_reference_lines.py` | `Dwgs.User` and `Eco1.User` reference geometry: SCAD backing, PCB profile reference, PZT circles, screw/keepout guides | footprints, tracks, zones, Edge.Cuts |
| `scripts/update_cutouts.py` | `Edge.Cuts`: board outline, ESP32/IMU cutouts, screw holes | footprints, tracks, zones, reference layers |
| `scripts/update_generated_pads.py` | legacy pre-atopile PZT placeholder creation, disabled unless `--legacy-create` is passed | normal atopile workflow |
| `scripts/normalize_kicad_for_atopile.py` | generated footprint metadata needed by atopile/KiCad decoders | placement, pads, tracks |
| `scripts/place_atopile_scaffold.py` | initial placement for footprints with `atopile_address`; default only moves obvious atopile grid placements | manually moved footprints |
| `scripts/update_board_layers.py` | convenience runner for the scripts above | manual placement/routing, except the owned layers listed above |

Run with KiCad's bundled Python:

```sh
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 rigid_pcb/scripts/update_reference_lines.py
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 rigid_pcb/scripts/update_cutouts.py
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 rigid_pcb/scripts/normalize_kicad_for_atopile.py
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 rigid_pcb/scripts/place_atopile_scaffold.py
```

Or run the complete mechanical/pad refresh:

```sh
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 rigid_pcb/scripts/update_board_layers.py --board rigid_pcb/layouts/default/default.kicad_pcb
```

Add `--force-placement` only when you intentionally want to re-apply scaffold
placement to footprints you may have already moved by hand.

### Electrical Logic

Electrical connectivity now starts in `main.ato`, with `ato.yaml` pointing the
default build at `main.ato:SmartPaddleRigid`.

Use:

```sh
cd rigid_pcb
ato validate main.ato
ato build --keep-designators --keep-net-names
```

`main.ato` currently defines the logical nets and physical components for:

- ESP32-C6 embedded module cutout,
- IM948 embedded module cutout,
- four PZT docks and their local clamp/front-end pads,
- tail harness pads for battery, LED, button, and USB,
- the soft power latch/regulator interface,
- LED data conditioning interface.

`ato build --keep-designators --keep-net-names` now reads and updates the KiCad
9 PCB successfully. The ESP32-C6 and IM948 embedded module cutouts are physical
atopile components backed by local footprints in `layouts/lib/footprints.pretty`.
Treat footprints with `atopile_address` as the electrical source-of-truth
instances. Legacy Python-created placeholders are no longer part of the normal
flow.

The scripts intentionally avoid routing.  After they run, KiCad still owns:

- component placement decisions for any existing footprint reference,
- all tracks, vias, zones, and DRC cleanup,
- schematic/netlist synchronization from atopile or KiCad.

`generate_kicad.py` is now best treated as an initialization/research script.
It can recreate a full study board, but it is not the safe path after manual
KiCad edits exist.

## Status

The current branch still contains the routed study board from earlier
experiments.  The new incremental scripts are intended to replace that loop:
refresh mechanical references/cutouts, then place and route manually in KiCad.

Next PCB work:

- decide whether the embedded module half-holes should stay as plated slots/half-holes or become wider solder shelves,
- route power, USB/UART, LED, button, and PZT nets manually against the updated references,
- add fab notes for castellated internal cutouts before manufacturing.
