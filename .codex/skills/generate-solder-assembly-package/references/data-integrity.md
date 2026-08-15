# Assembly-package data integrity

## Source precedence

Use facts in this order:

1. Exact bytes of the selected `.kicad_pcb` snapshot for position, side, rotation, footprint, Pad 1 and nets.
2. BOM from the same revision for quantity, manufacturer part number, and approved substitutions.
3. Exact received-part datasheet or supplier drawing for physical marking, polarity, mating direction, and Pin 1 identification.
4. Legacy guide only for visual style and vocabulary.

Never combine sources when their revision or SHA relationship is unknown.

## Status meanings

- `[OK]`: the specific claim is directly supported by a current source. State the evidence in CSV/manifest.
- `[CHECK]`: the PCB establishes placement but not the received part's physical marking, substitution, polarity, wire identity, or connector mechanics.

All PCB positions may be `[OK]` while the overall package remains `[CHECK]` because the physical board revision or received parts are unverified.

## Conservative orientation rules

- Resistor and verified non-polar ceramic capacitor footprints: either direction.
- DNP: leave unpopulated unless a separate approved rework instruction exists.
- Test point: inspect only; do not invent a component.
- LED: claim A/K mapping only if the footprint description or approved source explicitly provides it.
- Diode, MOS, IC, module, connector, and loose sensor wire: show PCB Pad 1/net facts, then keep physical orientation `[CHECK]` until an exact part source proves it.
- A multi-diode package counts as one BOM placement, even if it contains multiple junctions.

## Required cross-checks

- Record PCB SHA256 before extraction and after final rendering; fail if different.
- Require unique reference designators.
- Require finite X/Y/rotation and an explicit side for every footprint.
- Count top, bottom, DNP, inspect-only, `[OK]`, and `[CHECK]` items.
- Verify every map callout resolves to exactly one extracted reference.
- Compare any legacy checklist count; if different, label it stale and do not merge it.
- Treat an empty or missing current BOM as a release warning.

## Safety language

Do not invent continuity thresholds, current limits, rail tolerances, or first-power-on acceptance values. Refer to the approved electrical test specification, or mark the value `[CHECK]` when none exists.
