---
name: generate-solder-assembly-package
description: Learn the established SmartPaddle solder-guide visual language from legacy output, then create a fresh printable bench-side soldering and assembly package from the current KiCad PCB/BOM. Use when the user says the board has arrived, asks for a soldering map, assembly drawing, placement guide, printable assembly package, top/bottom component guide, or wants the old SmartPaddle output style reproduced for a newer PCB revision; Chinese triggers include “板子到了/到手了”, “生成焊接图”, “焊接装配包”, “装配定位图”, and “照着焊的图”.
---

# Generate SmartPaddle solder assembly package

Create the package as an AI-authored visual artifact, not from a fixed page template. Keep data extraction deterministic and visual composition adaptive.

## Required workflow

1. Use the PDF skill for PDF creation and render verification.
2. Read [visual-language.md](references/visual-language.md) completely.
3. Read [data-integrity.md](references/data-integrity.md) completely.
4. Inspect the legacy PDF and PNGs visually before designing anything. Do not rely only on text extraction or the old generator source.
5. Run the fact extractor against the exact PCB selected for the package:

   ```bash
   python3 .codex/skills/generate-solder-assembly-package/scripts/extract_pcb_assembly_facts.py \
     --pcb pcb/layouts/default/default.kicad_pcb \
     --out tmp/pdfs/smartpaddle-assembly-facts.json
   ```

6. Compare the extracted footprint count and SHA with any BOM or legacy checklist. Never merge mismatched revisions silently.
7. Form a short visual brief from the inspected legacy artifacts. Preserve their bench-map character while adapting to the current component density.
8. Author one-off rendering code under `tmp/pdfs/smartpaddle-ai-assembly/`. The code may use ReportLab, Matplotlib, SVG, or another suitable vector workflow. Do not add a permanent fixed-layout generator to the repository.
9. Write final artifacts under `output/pdf/smartpaddle-ai-assembly/`:
   - a printable PDF;
   - an auditable component/status CSV;
   - a source manifest containing PCB SHA256;
   - a contact-sheet PNG.
10. Render every PDF page to PNG, inspect every page, revise, and repeat until labels are legible and no text is clipped or overlapping.

## Non-negotiable content

Include:

- top and bottom views, with the bottom view explicitly mirrored as seen from the board bottom;
- board outline as the dominant visual anchor;
- direct leaders from each component center to its reference, value, package or soldering meaning;
- polarity/Pin 1 guidance only when supported by evidence;
- compact `[OK]` and `[CHECK]` markers integrated into callouts;
- installation order;
- pre-solder and post-solder checklists;
- exact PCB SHA and revision warnings.

## Hard constraints

- Never edit the PCB, schematic, firmware, netlist, routing, fab outputs, or legacy assembly artifacts.
- Never use legacy positions or polarity notes as current-board facts.
- Never guess a component position, side, orientation, pin mapping, or polarity.
- Never make tables, dashboards, large warning cards, or audit forms the primary visual experience.
- Never shrink the PCB to a small illustration surrounded by whitespace.
- Keep the first pages usable beside a soldering mat without consulting the CSV.
- Stop and mark `[CHECK]` when received-part identity, physical marking, or board revision cannot be proven.

## Completion gate

Deliver only after:

- the current PCB hash is unchanged from extraction through final render;
- every footprint appears exactly once in the maps or is explicitly listed as DNP/inspect-only;
- the page set visually matches the legacy bench-map language;
- all rendered pages pass manual visual inspection at print-equivalent size;
- uncertain orientation claims remain visibly unresolved rather than inferred.
