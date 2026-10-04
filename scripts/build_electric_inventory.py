#!/usr/bin/env python3
"""Select the non-Bowden feeder and spin parts for the new electric layout.

This is a source/instance inventory, not a motor mount or print release.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))
from launcher_final_assembly import inventory as baseline_inventory  # noqa: E402
from spin_head_geometry import PARTS as SPIN_PARTS  # noqa: E402


def digest(path: str) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def main() -> int:
    baseline = [row for row in baseline_inventory() if row["role"] == "printed"]
    assert len(baseline) == 38
    cable = json.loads((ROOT / "docs/cable-assembly-inventory.json").read_text())
    assert cable["snapshot"] == "current-cable-candidate"
    cable_only = [row["id"] for row in cable["parts"] if "cable" in row["id"]]
    cable_printed = [row["id"] for row in cable["parts"]
                     if row["role"] == "printed" and "cable" in row["id"]]
    assert len(cable_printed) == 8

    feeder = []
    for old in baseline:
        part_id = old["id"]
        source = "cad/electric-feeder-assembly.scad"
        if part_id == "beam-grip":
            source = "cad/electric-feeder-trigger-assembly.scad"
            selector = {"it_part": "beam"}
            action = "replace original fixed beam with integral signal-trigger beam and two cable-tie strain-relief holes"
        elif part_id == "y-cap-left":
            selector = {"ed_part": "optical-left-cap"}
            action = "replace original left Y cap with optical sensor cap"
        elif part_id == "moving-spacer":
            selector = {"ed_part": "optical-moving-spacer"}
            action = "replace original moving spring spacer with optical flag spacer"
        elif part_id == "frame":
            definitions = old["definitions"]
            selector = {"ed_part": "baseline", "ed_legacy_part": "frame",
                        "ed_side": definitions["la_side"],
                        "ed_rear": definitions["la_rear"]}
            action = "retain original cam carriage, guides and both hard-stop shoulders; remove manual finger loop"
        else:
            definitions = old["definitions"]
            selector = {"ed_part": "baseline",
                        "ed_legacy_part": definitions["la_part"],
                        "ed_side": definitions["la_side"],
                        "ed_rear": definitions["la_rear"]}
            action = "retain original non-Bowden geometry"
        feeder.append({"id": f"feeder/{part_id}", "name": old["name"],
                       "role": "printed", "source": source,
                       "definitions": selector, "selection": action})
    feeder.append({"id": "feeder/trigger-lever", "name": "电子信号扳机杠杆",
                   "role": "printed",
                   "source": "cad/electric-feeder-trigger-assembly.scad",
                   "definitions": {"it_part": "lever"},
                   "selection": "independent pull-to-grip lever on fixed-beam M3 pivot"})

    spin = [{"id": f"spin/{name}", "role": "printed",
             "source": "cad/spin-head.scad", "definitions": {"part": name},
             "installed_in_normal_mode": name != "hold-fork"}
            for name in SPIN_PARTS]
    assert len(feeder) == 39 and len(spin) == 10
    selected_ids = {row["id"] for row in feeder + spin}
    assert len(selected_ids) == 49
    assert selected_ids.isdisjoint(cable_only)
    assert feeder[2]["id"] == "feeder/beam-grip"
    assert feeder[2]["source"] == "cad/electric-feeder-trigger-assembly.scad"
    assert next(row for row in feeder if row["id"] == "feeder/frame")["selection"] == \
        "retain original cam carriage, guides and both hard-stop shoulders; remove manual finger loop"

    result = {
        "schema_version": 1,
        "snapshot": "electric-drive-selected-unreleased",
        "basis": "Original 38-instance feeder with trigger beam replacement and one new lever, plus independent 10-instance spin head",
        "feeder_stroke_mm": 20,
        "motor_nominal_stroke_mm": 30,
        "drive_ratio_required": "20/30 = 2/3, positive in both directions",
        "counts": {"feeder_printed_with_optical_replacements_and_trigger_lever": 39,
                   "spin_printed_including_optional_hold_fork": 10,
                   "selected_printed_instances": 49,
                   "normal_installed_printed_instances": 48,
                   "removed_bowden_printed_instances": len(cable_printed)},
        "printed_parts": feeder + spin,
        "external_components": [
            {"id": "motor/BY141-3", "item_id": "988456349136",
             "sku_id": "5952763100025", "status": "selected, not dimensionally modeled",
             "visible_listing": {"voltage_v": 3.7, "nominal_stroke_mm": 30,
                                 "rated_current_a": 0.36, "rated_power_w": 1.33},
             "dimensioned_mount_and_rod_end": False},
            {"id": "sensor/EE-SX675-WR-1M", "status": "optical geometry candidate",
             "source": "cad/feeder-optical-home.scad"},
            {"id": "switch/D2F-01FL30-D3", "status": "catalogue-sized trigger switch; not physically calibrated",
             "source": "cad/electronic-trigger-candidate.scad"},
            {"id": "spring/WR4-15", "status": "catalogue-sized trigger return spring; not physically fitted"},
            {"id": "spacer/CB-306-5E", "status": "catalogue-sized M3 pivot spacer; not physically fitted"},
        ],
        "excluded_previous_cable_ids": cable_only,
        "beam_geometry": "et_beam() replaces sh_beam() with two signal-wire tie holes; independent et_lever() added",
        "frame_geometry": "original feeder_carriage() core, rails and both X=±59 hard-stop shoulders; finger loop removed; not co_frame()",
        "motor_mount_designed": False,
        "positive_two_way_coupling_designed": False,
        "electronic_trigger_selected": True,
        "electronic_trigger_physically_verified": False,
        "control_and_braking_validated": False,
        "assembly_complete": False,
        "manufacturing_release": False,
        "physical_acceptance": False,
        "source_sha256": {name: digest(name) for name in (
            "cad/electric-feeder-assembly.scad",
            "cad/electric-feeder-trigger-assembly.scad",
            "cad/electronic-trigger-candidate.scad",
            "cad/feeder-optical-home.scad",
            "cad/launcher-final-assembly.scad",
            "cad/spin-head.scad",
            "docs/cable-assembly-inventory.json",
            "scripts/build_electric_inventory.py")},
    }
    target = ROOT / "docs/electric-assembly-inventory.json"
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(f"{target}: {len(feeder)} feeder + {len(spin)} spin; "
          f"removed {len(cable_printed)} Bowden printed instances; unreleased")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
