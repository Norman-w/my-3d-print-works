# SmartPaddle tail in-board packing candidate

> **Candidate only — not for fabrication, ordering, or power-up.**

This directory contains the first mechanically anchored placement candidate
derived from `layouts/functional-groups/functional-groups.kicad_pcb`.  It does
not replace or modify `layouts/default/default.kicad_pcb`.

## Result

- All 33 footprints are back inside the real tail-board integration layout.
- The real 96-point `Edge.Cuts` is byte-semantically identical to both the
  validated functional-group source and the current production board.
- Hard shell anchors are restored exactly:
  - J1 `(-6.858008, -0.381) / -90°`
  - SW1 `(-1.651, -5.461) / -90°`
  - D1 `(2.454994, -3.783996) / -90°`
  - LED1 `(-5.9435, -6.35) / 0°`
  - J2 `(-11.3, -0.6) / -90°`
  - J3 `(6.3, -5.8) / 180°`
  - J4 `(-2.794, -7.0) / 90°`
- G2, G3 and G4 retain their validated rigid local copper unchanged in
  meaning and connectivity: 37, 31 and 51 track objects respectively, with no
  vias.  G8 has no honest internal net and therefore contains no local copper.
- KiCad DRC on the accepted candidate reports **0 rule errors**, 23 known
  warnings, and 53 intentionally remaining unconnected items.
- Strict no-via-in-pad audit passes, and the current production PCB SHA-256
  remains `bf3debd22961eb797a6e2e488d365b77627f230a493b4901b5f8fab4fd6f97ef`.

The packing contract used a hard insertion region of `Edge.Cuts − 0.50 mm`
and a conservative ordinary component/copper target of `Edge.Cuts − 0.70 mm`.
The latter has area 444.702 mm² and bounding box
`(-14.168,-9.812)..(14.168,8.108)`.  J2/J3 are documented connector exceptions:
their mated 51021 housings intentionally use generated shell pockets and must
retain their service/exit envelopes.

## Why four groups were decomposed

Rigid-island packing is geometrically impossible.  A conservative search on
only G3, G7 and G8 (four right-angle rotations, 0.5 mm grid) found 1261, 856
and 1564 individually legal poses.  It tested 14,254 non-overlapping G7+G3
combinations and found **zero** positions that could also accept G8.  This was
already optimistic because it ignored J2/J3 mated-housing service volume.

Accordingly, G1/G5/G6/G7 were split at their required mechanical anchors and
repacked.  Their reduced-board auto-routes were tested, but rejected after
full-board DRC because they had been generated without all other groups as
obstacles.  The combined trial produced 115 rule errors (including shorts and
crossings); none of that copper is present in the accepted candidate.

## Remaining electrical work

Accepted local copper is deliberately absent for G1, G5, G6 and G7.  The DRC
still lists 53 unconnected pairs across these and cross-group networks.  The
affected net names are:

`GND`, `bat_p`, `cc1`, `cc2`, `led_ahct_y`, `led_data`, `led_din`,
`led_stat_a`, `pmic_key`, `pmic_key_isolated`, `pmic_led1`, `pmic_led23`,
`usb_dn`, `usb_dn_conn`, `usb_dp`, `usb_dp_conn`, `user_btn`,
`v5_sw_return`, `vbus`, `vbus_limited`, `vout_5v`, `vout_5v_raw`.

Before this candidate can be promoted, those nets require obstacle-aware
integrated routing, then full mechanical Step6/handle-groove and mated-housing
validation, whole-board DRC with zero unconnected items, and a separate release
review.  This directory intentionally contains no zones, Gerbers, drill files,
manufacturing ZIP, BOM, CPL, or fabrication output.

Rejected integrated-routing trials were removed from this directory and moved
to the recoverable quarantine directory
`/private/tmp/smartpaddle-inboard-rejected-routes-20260816/`.

## Files and repeatable checks

- `in-board-candidate.kicad_pcb` — accepted placement/safe-local-copper candidate
- `build_in_board_candidate.py` — deterministic candidate builder
- `audit_in_board_candidate.py` — read-only invariant and partial-connectivity gate
- `drc-final.json` — final KiCad DRC evidence for the accepted candidate
- `preview/` — top, bottom, and 2D layout previews

Run the read-only audit with KiCad's bundled Python:

```sh
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 \
  pcb-tail/layouts/in-board-candidate/audit_in_board_candidate.py
```
