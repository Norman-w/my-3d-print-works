# SmartPaddle solder-guide visual language

## Mandatory visual references

Inspect these files before creating a new package:

- `output/assembly/smartpaddle_solder_guide_v3.pdf`
- `output/assembly/smartpaddle_solder_guide_v3_overview.png`
- `output/assembly/smartpaddle_solder_guide_overview.png`
- `output/assembly/board_base.svg`

If they are missing, search `output/assembly/` for the closest solder/assembly guide. If no visual reference exists, stop and ask for one; do not invent a new house style.

Use `tmp/pdfs/make_solder_guide.py` only to understand provenance or label vocabulary. Do not treat its hard-coded labels, revision string, coordinates, polarity notes, or page ranges as current facts.

## What to learn from the legacy package

- A4 portrait pages feel like annotated engineering maps, not reports.
- The board outline occupies most of the printable area.
- The full-board overview immediately matches the physical paddle silhouette.
- Zone pages enlarge the PCB region itself; they do not merely enlarge a table.
- Thin colored leaders connect exact component centers to short Chinese callouts.
- Callouts say what to solder, not merely a database value.
- Color encodes part family consistently:
  - resistor: burnt orange;
  - capacitor: blue;
  - diode: purple;
  - MOS: ochre/gold;
  - LDO/IC: green;
  - module: dark navy;
  - switch: brown;
  - LED: magenta;
  - pad/wire/mechanical: neutral gray.
- Grid, axes, board orientation, and region names help users transfer the diagram to the real board.
- Labels remain close enough to follow with a finger or probe.

## Improve without changing the character

- Prevent the legacy overview's edge labels from clipping.
- Split dense current-board regions into additional portrait zoom pages instead of reducing type size.
- Use at least 7.5 pt for secondary label text and 9 pt where practical.
- Keep `[OK]` / `[CHECK]` short and subordinate to the solder instruction.
- Show Pad 1 with a small red marker when it is useful; do not fill the page with numbered pads.
- Put detailed evidence, source audit, and long tables after the bench-map pages or in separate CSV/manifest files.
- Make bottom-side pages visually unmistakable and state that the view is mirrored.

## Rejected visual direction

Do not reproduce the rejected package found under `output/pdf/assembly-package/` as the main visual design. In particular, avoid:

- landscape dashboard pages;
- oversized status cards and compliance language;
- the PCB reduced to a small central schematic;
- left/right stacks of uniform UI cards;
- large empty areas caused by rigid table pagination;
- English-heavy assembly instructions;
- forcing the user to cross-reference a table to understand a map.

Those artifacts may be inspected only as evidence of what not to do or as a source-audit example.

## Page hierarchy

Prefer this hierarchy, adapting page count to density:

1. Full-board top overview.
2. PZT corner/edge zooms grouped logically.
3. Main island zooms split until every callout is readable.
4. Handle, switches, and top connector zoom.
5. Bottom-side overview and connector zoom.
6. Concise installation order and printable checklists.
7. Optional evidence appendix; CSV and manifest remain separate files.
