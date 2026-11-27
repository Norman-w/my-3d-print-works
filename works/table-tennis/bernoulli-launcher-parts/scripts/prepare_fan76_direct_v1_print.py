#!/usr/bin/env python3
"""Arrange the five clean fan76 direct meshes; no slicing or printer contact.

The wider bayonet body has its own layout. This reuses only the mesh packaging
and native preset preservation code, not fan41's geometry or lug audit.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from prepare_fan_tee_v5_print import ROOT, TEMPLATE, build

LAYOUT = [("connector", (76., 150.)), ("nozzle15", (156., 60.)),
          ("nozzle20", (216., 60.)), ("nozzle25", (156., 150.)),
          ("nozzle30", (216., 150.))]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for role, _ in LAYOUT:
        ap.add_argument("--"+role, type=Path, required=True)
    ap.add_argument("--out", type=Path, default=ROOT/"output/fan76-direct-longtravel-v1-20261007/print")
    ap.add_argument("--template", type=Path, default=TEMPLATE)
    args = ap.parse_args()
    report = build({role: getattr(args, role) for role, _ in LAYOUT},
                   args.out.resolve(), args.template.resolve(), layout=LAYOUT,
                   package_stem="fan76-direct-v1",
                   plate_name="fan76-direct-v1 - body and 15-20-25-30 mm")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
