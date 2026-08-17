# Tail-board functional-island workbench

This directory is a **placement/routing workbench only**.  It is not a
manufacturing design and must not be used to generate Gerbers.  The production
board remains `../default/default.kicad_pcb` and is intentionally not modified
by the workbench scripts.

`functional-groups.kicad_pcb` retains the production Edge.Cuts while parking
all 33 footprints outside that outline.  Each footprint belongs to exactly one
named `PCB_GROUP`; only electrical connections whose endpoints are inside the
same group are routed here.  Cross-group connections stay as ratsnest lines so
the islands can later be moved without pretending that their final board-level
topology has been chosen.

The workbench was frozen from saved tail-board snapshot SHA-256
`bf3debd22961eb797a6e2e488d365b77627f230a493b4901b5f8fab4fd6f97ef`.

## Group contract

| Group | Footprints | Internal nets to complete inside the island |
|---|---|---|
| G1 USB-C / CC / ESD | J1 R1 R2 U2 | `GND`, `cc1`, `cc2`, `usb_dp_conn`, `usb_dn_conn`, `vbus` |
| G2 USB input limiter | U5 R9 C10 | `GND`, `vbus`, `vbus_ilim` |
| G3 IP5305 power core | U3 L1 C3 C4 C5 C6 R7 | `GND`, `bat_p`, `pmic_led23`, `sw_node`, `vbus_limited`, `vin_damp_mid`, `vout_5v_raw` |
| G4 system 5 V limiter | U4 R8 C7 C8 C9 | `GND`, `system_ilim`, `vout_5v`, `vout_5v_raw` |
| G5 PMIC key / status | SW1 D2 R4 R5 R6 LED1 | `GND`, `user_btn`, `pmic_key_isolated`, `led_stat_a` |
| G6 RGB buffer / pixel | U1 D1 R3 C1 C2 | `GND`, `led_ahct_y`, `led_din`, `v5_sw_return` |
| G7 power / battery interfaces | J2 J4 | `GND`, `bat_p` |
| G8 signal interface | J3 | none |

Two easy-to-miss facts are part of this contract:

* `pmic_led23` is a real G3 local connection between U3 pads 3 and 4 and must
  be shorted locally; it is not an intentionally open pair.
* G7 is not route-free.  J2.3 and J4.1 form the local `bat_p` connection, and
  J2.2 and J4.2 form the local `GND` connection.  When G3 is later integrated,
  its `bat_p` power path must join this local battery bus at J4 or at a short
  nearby T-junction.  Do **not** daisy-chain the high-current path through J2.3
  and then run a long continuation to U3.  J2 remains an interface branch, not
  the series current path.

## Placement and routing decisions

The workbench was compacted with a measured objective: minimize each island's
combined footprint-courtyard and copper axis-aligned envelope while preserving
the electrical topology, minimum 0.25 mm same-side courtyard gap, original
trace widths, connector service direction, USB matching, and strict
pad-external vias.  This is a constraint-checked local packing optimum, not a
claim of a mathematical global optimum for arbitrary PCB routing.

* U3 and L1 have BAT/SW pins in matching order.  `sw_node` is a short,
  0.60 mm, same-layer route with no via.
* C3, C4 and C6 point both their functional pad and their ground-return pad
  toward the IP5305/U3 exposed-pad loop.  C7 shares `F.Cu` with U4, and C1
  shares `B.Cu` with U1.
* High-current island routes use 0.60 mm copper.  G7 BAT/GND are both 0.60 mm.
  Ordinary power uses 0.40 mm and signals use 0.20 mm.
* G1 USB D+/D- use 0.20 mm copper and pad-external 0.60/0.30 mm dogbone vias;
  their total copper lengths differ by 0.10 mm.  The J1.A4 VBUS branch has a
  3.05 mm local 0.20 mm escape before joining the 0.60 mm trunk.  This is a
  short branch of the receptacle's four parallel VBUS contacts, not the sole
  input-current trunk.  Attempts to widen it without moving the present G1
  footprints crossed CC1, so the DRC-clean branch was retained explicitly.
* There are no via-in-pad features.  The final audit checks actual KiCad copper
  shapes rather than bounding boxes.
* No copper zones are present.  A continuous global ground plane and stitching
  vias are board-level work to do only after the islands return inside the real
  outline.

Routing was deliberately hybrid rather than delegated blindly to one tool:

* G2, G3 and G4 were routed one net at a time with KiCadRoutingTools, followed
  by connectivity and native KiCad DRC checks.
* G1 keeps the previously validated pin-aware USB/dogbone routing.  Two
  independent compaction attempts showed that pushing R1/R2 into the
  J1-to-U2 gap creates real CC/VBUS/GND and flipped USB-pair conflicts when the
  proposed replacement's VBUS escape is kept at least 0.30 mm and all vias
  remain outside pads.  The smaller failing candidate was rejected instead of
  replacing the already documented, DRC-clean 0.20 mm A4 branch exception with
  an unverified layout.
* G5, G6 and G7 use hand-planned pin-aware copper because their cross-layer
  dogbones and connector mating direction require explicit control.

### Compactness result

The table uses the full audit's combined courtyard+copper AABB, so long copper
escapes and vias count against compactness instead of measuring footprints
alone.

| Group | Previous area | Current area | Reduction |
|---|---:|---:|---:|
| G1 USB-C / CC / ESD | 143.694 mm² | 143.694 mm² | retained safe lower bound |
| G2 USB input limiter | 39.183 mm² | 32.578 mm² | 16.9% |
| G3 IP5305 power core | 205.506 mm² | 134.130 mm² | 34.7% |
| G4 system 5 V limiter | 69.572 mm² | 54.120 mm² | 22.2% |
| G5 PMIC key / status | 63.886 mm² | 36.615 mm² | 42.7% |
| G6 RGB buffer / pixel | 62.315 mm² | 34.946 mm² | 43.9% |
| G7 power / battery interfaces | 154.929 mm² | 153.608 mm² | 0.9% (service-space bound) |
| G8 signal interface | 82.269 mm² | 82.269 mm² | single footprint |

Across the seven routed groups the combined envelope falls from 739.085 to
589.691 mm² (20.2%).  G7 intentionally stops at a small geometric gain:
J4's rotation permits two direct 0.60 mm, same-layer, zero-via BAT/GND routes
while leaving J2's mating and wire-exit half-plane unobstructed.

## Rebuilding and merging

`../../scripts/build_functional_group_workbench.py` deterministically rebuilds
the blank island placement.  Re-running it removes all workbench copper, so do
not run it over a routed workbench unless that reset is intentional.

Validated group-only route boards can be merged by net name with
`../../scripts/merge_functional_group_routes.py`.  The merger refuses the
production `layouts/default` directory, verifies the exact footprint poses and
group membership, requires the complete internal-net inventory above, copies
only tracks/vias, adds them to the selected `PCB_GROUP`, and proves that all 33
footprints, drawings/Edge.Cuts, zones, and pre-existing copper are unchanged.
It writes a new file by default:

```sh
KIPY="/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3"
"$KIPY" ../../scripts/merge_functional_group_routes.py \
  G2 /path/to/validated/G2-routed.kicad_pcb \
  --workbench functional-groups.kicad_pcb \
  --output /tmp/functional-groups-with-G2.kicad_pcb
```

Only use `--in-place` with an output path identical to the workbench after the
group route has passed its reduced-board KiCad DRC and any extra engineering
checks (for example, the explicit no-via-in-pad rule for G1/G5/G6).

## Current validated state

The routed workbench contains 207 track segments and 11 vias.  G1 through G7
have all of their in-group pads connected; G8 is a single interface connector
and correctly contains no local copper.  Each routed island passed KiCad DRC in
an isolated test outline before merging.

Run the full workbench contract audit with KiCad's Python:

```sh
KIPY="/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3"
"$KIPY" ../../scripts/audit_functional_group_workbench.py \
  --board functional-groups.kicad_pcb
```

The audit requires 33 footprints in eight mutually exclusive groups, checks
that every track/via belongs to exactly one correct group, verifies all local
pad connectivity, rejects cross-group copper and zones, and enforces strict
no-via-in-pad.  Whole-workbench KiCad DRC is intentionally not authoritative:
the island copper sits outside the retained production Edge.Cuts, and the
remaining cross-island nets are intentionally unrouted.

Do not generate Gerbers, drill/placement files, or an order package from this
directory.
