#!/usr/bin/env python3
"""Offline time/material comparison only; isolated CLI data, never printer IO.

All cases use the same frozen native X1C/PETG options. Only the STL and the
explicit wall-loop count vary. Analysis G-code is NOT a dispatch package.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from zipfile import ZipFile

from build_fan76_smooth_v2 import ROOT, dump, sha
from fan76_smooth_release import smooth_release

OUT = smooth_release(4).out
TEMPLATE = ROOT / "output/fan76-direct-longtravel-v1-20261007/print/slice/fan76-direct-v1-native-project.3mf"
CATEGORY = ROOT / "output/fan-tee-direct-print-v4-20261007/print/config"
BAMBU = Path("/Applications/BambuStudio.app/Contents/MacOS/BambuStudio")
CASES = {"v3-w4": (3, 4), "v4-w4": (4, 4), "v4-w3": (4, 3)}


def compare_case(name, *, output=OUT, cases=CASES):
    revision, walls = cases[name]
    release = smooth_release(revision)
    stl = release.out / f"stl/{release.stem}-body-clean.stl"
    exported = json.loads((release.out / "verification/export.json").read_text())
    assert sha(stl) == next(row["sha256"] for row in exported["files"] if row["part_id"] == "body")
    folder = output / "analysis-slices" / name
    folder.mkdir(parents=True, exist_ok=True)
    with ZipFile(TEMPLATE) as archive:
        native = json.loads(archive.read("Metadata/project_settings.config"))
    assert native["printer_settings_id"] == "Bambu Lab X1 Carbon 0.4 nozzle"
    assert native["filament_type"] == ["PETG"] and native["wall_loops"] == "4"
    model_height = exported["mechanical_contract"]["body_height"]
    assert float(native["printable_height"])-model_height >= 2
    identities = {"name", "type", "from", "setting_id", "inherits", "instantiation"}
    configs = {}
    for category in ["machine", "process", "filament"]:
        source = CATEGORY / f"{category}.json"
        values = json.loads(source.read_text())
        for key in values:
            if key in native and key not in identities:
                values[key] = native[key]
        if category == "process":
            values["wall_loops"] = str(walls)
        if category == "machine":
            assert values["machine_start_gcode"] == native["machine_start_gcode"]
            assert values["machine_end_gcode"] == native["machine_end_gcode"]
        dump(folder / f"{category}.json", values)
        configs[category] = {"schema_sha256": sha(source), "effective_sha256": sha(folder / f"{category}.json")}
    package = folder / "analysis-only-not-for-print.3mf"
    with tempfile.TemporaryDirectory(prefix=f"fan76-{name}-cli-") as appdata:
        command = [str(BAMBU), "--datadir", appdata, "--debug", "2",
                   "--load-settings", f"{folder/'machine.json'};{folder/'process.json'}",
                   "--load-filaments", str(folder / "filament.json"),
                   "--orient", "0", "--arrange", "1", "--ensure-on-bed", "--slice", "0",
                   "--export-3mf", package.name, "--outputdir", str(folder), str(stl)]
        with (folder / "cli.log").open("w") as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f"{name}: CLI failed {result.returncode}; inspect {folder/'cli.log'}")
    report = json.loads((folder / "result.json").read_text())
    assert report["return_code"] == 0 and len(report["sliced_plates"]) == 1
    plate = report["sliced_plates"][0]
    with ZipFile(package) as archive:
        effective = json.loads(archive.read("Metadata/project_settings.config"))
    for key, expected in {"wall_loops": str(walls), "layer_height": "0.2", "filament_type": ["PETG"],
                          "nozzle_diameter": ["0.4"], "support_type": "tree(auto)",
                          "printable_height": native["printable_height"],
                          "sparse_infill_density": native["sparse_infill_density"]}.items():
        assert effective[key] == expected, (name, key, effective[key], expected)
    assert effective["machine_start_gcode"] == native["machine_start_gcode"]
    assert effective["machine_end_gcode"] == native["machine_end_gcode"]
    row = {"case": name, "revision": revision, "wall_loops": walls,
           "input_stl": str(stl.relative_to(ROOT)), "input_sha256": sha(stl),
           "seconds_estimate": plate["total_predication"],
           "grams_estimate": sum(float(f["total_used_g"]) for f in plate["filaments"]),
           "warning": plate.get("warning_message"), "command": command,
           "slicer_binary_sha256": sha(BAMBU), "native_template_sha256": sha(TEMPLATE),
           "configs": configs, "package_sha256": sha(package), "dispatch_authorized": False,
           "preset_verified": True, "support_contact_reviewed": False,
           "startup_unchanged": effective["machine_start_gcode"] == native["machine_start_gcode"],
           "end_code_unchanged": effective["machine_end_gcode"] == native["machine_end_gcode"],
           "printable_height_mm": float(effective["printable_height"]),
           "model_height_mm": model_height,
           "height_margin_mm": float(effective["printable_height"])-model_height,
           "printer_contacted": False}
    dump(output / f"verification/slice-estimate-{name}.json", row)
    print(f"{name}: {row['seconds_estimate']} seconds / {row['grams_estimate']:.2f} g (estimate only)", flush=True)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", type=int, choices=[4, 5], default=4)
    parser.add_argument("--case", action="append")
    args = parser.parse_args()
    output = smooth_release(args.revision).out
    cases = CASES if args.revision == 4 else {"v4-w4": (4, 4), "v5-w4": (5, 4)}
    if args.case and not set(args.case) <= set(cases):
        parser.error(f"Valid cases for revision {args.revision}: {list(cases)}")
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(partial(compare_case, output=output, cases=cases), args.case or cases))
    files = [output / f"verification/slice-estimate-{name}.json" for name in cases]
    if all(path.is_file() for path in files):
        rows = [json.loads(path.read_text()) for path in files]
        baseline = rows[0]
        for row in rows:
            assert sha(ROOT / row["input_stl"]) == row["input_sha256"]
            assert row["native_template_sha256"] == sha(TEMPLATE)
            assert row["slicer_binary_sha256"] == sha(BAMBU)
            suffix = baseline["case"].replace("-", "_")
            row[f"time_reduction_percent_vs_{suffix}"] = 100*(1-row["seconds_estimate"]/baseline["seconds_estimate"])
            row[f"material_reduction_percent_vs_{suffix}"] = 100*(1-row["grams_estimate"]/baseline["grams_estimate"])
        dump(output / "verification/slice-comparison.json", {
            "status": "OFFLINE_COMPARISON_ONLY_NOT_FOR_PRINT", "cases": rows,
            "baseline_case": baseline["case"], "selected_case": f"v{args.revision}-w4",
            "limitations": ["Same native preset snapshot, 0.2mm layer, PETG, tree-auto, 25% infill; one shell per plate.",
                            "Slicer estimates, not elapsed printer time. Model solid volume is not sliced material.",
                            "No native GUI release audit, support-contact acceptance, fit/strength/airflow test or dispatch."],
            "printer_contacted": False})


if __name__ == "__main__":
    main()
