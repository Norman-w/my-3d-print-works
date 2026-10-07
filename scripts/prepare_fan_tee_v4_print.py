#!/usr/bin/env python3
"""Prepare an isolated, one-connector X1C slice using a native preset snapshot.

Seeding is explicit and one-time. Subsequent slices use the new package's own
config files, not any retired output. This script never contacts a printer.
CLI output is a preflight only: native GUI import can restore system defaults,
and the CLI slice can omit printer_model_id. Use the audited native project
for dispatch, not this script's intermediate packages.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/fan-tee-direct-print-v4-20261007/print"
BAMBU = Path("/Applications/BambuStudio.app/Contents/MacOS/BambuStudio")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def seed(package: Path, config_dir: Path) -> None:
    if (OUT / "config/native-baseline.json").exists():
        raise SystemExit("Preset snapshot already exists; refusing to replace it")
    with ZipFile(package) as archive:
        native = json.loads(archive.read("Metadata/project_settings.config"))
    assert native["printer_settings_id"] == "Bambu Lab X1 Carbon 0.4 nozzle"
    assert native["filament_type"] == ["PETG"]
    sources = {}
    for category in ("machine", "process", "filament"):
        source = config_dir / (category + ".json")
        values = json.loads(source.read_text())
        # Retain the category identity; use native project values for options.
        for key in values:
            if key in native and key not in {"name", "type", "from", "setting_id", "inherits"}:
                values[key] = native[key]
        if category == "machine":
            values["printer_settings_id"] = native["printer_settings_id"]
            values["curr_bed_type"] = native["curr_bed_type"]
            assert values["machine_start_gcode"] == native["machine_start_gcode"]
            assert values["machine_end_gcode"] == native["machine_end_gcode"]
        elif category == "process":
            values.update(
                print_settings_id=native["print_settings_id"],
                enable_support="1", support_type="tree(auto)",
                support_threshold_angle="45", support_on_build_plate_only="1",
                support_remove_small_overhang="0", support_top_z_distance="0.2",
                support_object_xy_distance="0.25", wall_loops="4",
                layer_height="0.2", enable_arc_fitting="0",
                brim_type="outer_only", brim_width="6", brim_object_gap="0.1",
                enable_prime_tower="0",
            )
        else:
            values["filament_settings_id"] = native["filament_settings_id"]
            assert values["filament_start_gcode"] == native["filament_start_gcode"]
        target = OUT / "config" / (category + ".json")
        write_json(target, values)
        sources[category] = {"seed_sha256": digest(source), "snapshot_sha256": digest(target)}
    write_json(OUT / "config/native-baseline.json", {
        "origin_package": str(package), "origin_package_sha256": digest(package),
        "origin_is_historical_provenance_only": True,
        "native_start_gcode_sha256": hashlib.sha256(native["machine_start_gcode"].encode()).hexdigest(),
        "native_end_gcode_sha256": hashlib.sha256(native["machine_end_gcode"].encode()).hexdigest(),
        "preset_snapshot": sources,
        "printer": native["printer_settings_id"],
        "material": native["filament_type"], "plate": native["curr_bed_type"],
        "startup_gcodes_preserved": True,
        "scope": "one clean outer connector only; no nozzle cores or embedded support geometry",
        "printer_contacted": False,
    })


def slice_model(stl: Path) -> None:
    if not stl.is_file():
        raise SystemExit(f"STL missing: {stl}")
    config = OUT / "config"
    for name in ("machine", "process", "filament"):
        if not (config / (name + ".json")).is_file():
            raise SystemExit("Seed the native preset snapshot before slicing")
    target = OUT / "slice"
    target.mkdir(parents=True, exist_ok=True)
    (OUT / "bambu-cli-data").mkdir(exist_ok=True)
    command = [str(BAMBU), "--datadir", str(OUT / "bambu-cli-data"),
               "--load-settings", str(config / "machine.json") + ";" + str(config / "process.json"),
               "--load-filaments", str(config / "filament.json"),
               "--orient", "0", "--arrange", "1", "--ensure-on-bed",
               "--slice", "0", "--export-3mf", "fan-tee-v4-connector-x1c.gcode.3mf",
               "--outputdir", str(target), str(stl)]
    record = {"command": command, "input_stl": str(stl), "input_sha256": digest(stl),
              "config_sha256": {p.name: digest(p) for p in config.glob("*.json")},
              "slicer_binary_sha256": digest(BAMBU), "printer_contacted": False}
    write_json(OUT / "slice-command.json", record)
    with (OUT / "slicer.log").open("w") as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=False)
    record["exit_code"] = result.returncode
    package = target / "fan-tee-v4-connector-x1c.gcode.3mf"
    if result.returncode == 0 and package.exists():
        record["sliced_package"] = str(package)
        record["sliced_package_sha256"] = digest(package)
        project = target / "fan-tee-v4-connector-project.3mf"
        shutil.copy2(package, project)
        record["editable_project"] = str(project)
        record["editable_project_sha256"] = digest(project)
    write_json(OUT / "slice-result.json", record)
    print(json.dumps(record, ensure_ascii=False, indent=2))
    if result.returncode:
        raise SystemExit(result.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-package", type=Path)
    parser.add_argument("--seed-config-dir", type=Path)
    parser.add_argument("--slice-stl", type=Path)
    args = parser.parse_args()
    if bool(args.seed_package) != bool(args.seed_config_dir):
        parser.error("Both seed paths are required together")
    if args.seed_package:
        seed(args.seed_package.resolve(), args.seed_config_dir.resolve())
        print("Native X1C/PETG preset snapshot saved; printer untouched")
    if args.slice_stl:
        slice_model(args.slice_stl.resolve())
    if not args.seed_package and not args.slice_stl:
        parser.error("Choose explicit seeding or slicing")


if __name__ == "__main__":
    main()
