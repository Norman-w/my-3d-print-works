#!/usr/bin/env python3
"""Offline X1C/PETG orientation screen for the unselected root-web fork base."""

from __future__ import annotations

from hashlib import sha256
import json
import math
from pathlib import Path
import shutil
import subprocess

import screen_service_fork_base_orientation as screen
from slice_electric_rocker_service_fork import BAMBU, CONFIG


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "output/electric-rocker-root-gusset-screen"
REVIEW = SOURCE / "review.json"
SECTION = SOURCE / "root-web-section.json"
MESH = SOURCE / "base-root-web-screen.stl"
OUT = SOURCE / "slice-screen"
REPORT = SOURCE / "orientation-screen.json"
ANGLES = (0, 30, 35, 40, 42, 45, 48, 50, 51, 52, 53, 54,
          55, 56, 57, 58, 59, 60, 75, 90)
SHELL_HOLES = (("lower", -10), ("upper", 16))


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def shell_void_cores(point: tuple[float, float, float]) -> tuple[str, ...]:
    x, y, z = point
    found = []
    for label, z_center in SHELL_HOLES:
        radius_squared = (y - 40) ** 2 + (z - z_center) ** 2
        if 6.9 <= x <= 14.1 and radius_squared <= 1.5 ** 2:
            found.append(f"{label}_through_core")
        if 10.8 <= x <= 14.1 and radius_squared <= 2.8 ** 2:
            found.append(f"{label}_counterbore_core")
    return tuple(found)


def support_in_shell_void_cores(gcode: Path, comp: list[float],
                                item: list[float], center: list[float]) -> dict[str, int]:
    hits = {f"{label}_{kind}_core": 0
            for label, _ in SHELL_HOLES for kind in ("through", "counterbore")}
    x = y = None
    z = 0.0
    feature = ""
    for line in gcode.open(errors="replace"):
        if line.startswith("; FEATURE:"):
            feature = line.partition(":")[2].strip()
        if not line.startswith(("G0 ", "G1 ")):
            continue
        fields = {token[0]: token[1:] for token in line.split()[1:]
                  if len(token) > 1 and token[0] in "XYZE"}
        old_x, old_y = x, y
        try:
            if "X" in fields:
                x = float(fields["X"])
            if "Y" in fields:
                y = float(fields["Y"])
            if "Z" in fields:
                z = float(fields["Z"])
            extrusion = float(fields["E"]) if "E" in fields else 0.0
        except ValueError:
            continue
        if (feature not in ("Support", "Support interface") or "E" not in fields
                or extrusion <= 0 or x is None or y is None
                or old_x is None or old_y is None
                or math.hypot(x-old_x, y-old_y) <= 1e-6):
            continue
        found = set()
        steps = max(1, math.ceil(math.hypot(x-old_x, y-old_y) / .15))
        for step in range(steps + 1):
            t = step / steps
            machine = (old_x + (x-old_x)*t, old_y + (y-old_y)*t, z)
            found.update(shell_void_cores(screen.source_point(
                machine, comp, item, center)))
        for name in found:
            hits[name] += 1
    return hits


def screen_x55_without_support() -> dict:
    folder = OUT / "base-x-plus-55-no-support"
    folder.mkdir(parents=True, exist_ok=True)
    for name in ("machine", "filament"):
        shutil.copy2(CONFIG / f"{name}.json", folder / f"{name}.json")
    process = json.loads((CONFIG / "process.json").read_text())
    process.update(enable_support="0", layer_height="0.2",
                   initial_layer_print_height="0.2", wall_loops="4",
                   sparse_infill_density="25%", brim_type="outer_only",
                   brim_width="5")
    (folder / "process.json").write_text(json.dumps(process, indent=2) + "\n")
    for name in ("result.json", "slice-review.3mf", "plate_1.gcode"):
        (folder / name).unlink(missing_ok=True)
    run = subprocess.run([
        str(BAMBU), "--datadir", str(folder / "app-data"),
        "--load-settings", f"{folder/'machine.json'};{folder/'process.json'}",
        "--load-filaments", str(folder / "filament.json"),
        "--orient", "0", "--rotate-x", "55", "--arrange", "1",
        "--ensure-on-bed", "--slice", "0", "--export-3mf", "slice-review.3mf",
        "--outputdir", str(folder), str(MESH),
    ], cwd=ROOT, text=True, capture_output=True, timeout=240)
    (folder / "bambu-cli.log").write_text(run.stdout + run.stderr)
    native_path = folder / "result.json"
    native = json.loads(native_path.read_text()) if native_path.is_file() else {}
    plates = native.get("sliced_plates", [])
    warnings = [plate.get("warning_message") for plate in plates
                if plate.get("warning_message")]
    if run.returncode or native.get("return_code") != 0 or len(plates) != 1 \
            or not any("floating regions" in warning for warning in warnings):
        raise RuntimeError("X55 no-support native warning was not reproduced")
    return {
        "status": "NO_SUPPORT_FLOATING_REGIONS_WARNING_UNRELEASED",
        "rotation_x_deg": 55, "support_enabled": False,
        "cli_return_code": run.returncode,
        "native_return_code": native["return_code"],
        "native_warnings": warnings,
        "native_result_file": str(native_path.relative_to(ROOT)),
        "native_result_sha256": digest(native_path),
        "manufacturing_release": False,
    }


def main() -> int:
    review = json.loads(REVIEW.read_text())
    root_section = json.loads(SECTION.read_text())
    if (review["status"] != "ROOT_WEB_NOMINAL_GEOMETRY_ONLY_UNRELEASED"
            or review["base"]["sha256"] != digest(MESH)
            or root_section["status"] != "ROOT_WEB_LOBE_AREA_GAIN_ONLY_UNRELEASED"
            or root_section["source_sha256"][str(REVIEW.relative_to(ROOT))] != digest(REVIEW)):
        raise RuntimeError("Root-web geometry or section is stale")
    if not BAMBU.is_file():
        raise RuntimeError("BambuStudio CLI is unavailable")
    sources = (Path(__file__).resolve(),
               ROOT / "scripts/screen_service_fork_base_orientation.py",
               ROOT / "scripts/slice_electric_rocker_service_fork.py",
               REVIEW, SECTION, MESH,
               CONFIG / "machine.json", CONFIG / "filament.json", CONFIG / "process.json")
    before = {str(path.relative_to(ROOT)): digest(path) for path in sources}
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MESH, OUT / "base.stl")
    screen.OUT = OUT
    geometry = {"parts": {"base": review["base"]}}
    rows = {}
    for angle in ANGLES:
        row = screen.slice_angle(angle, geometry)
        folder = OUT / "orientation-screen" / f"base-x-plus-{angle}-tree"
        archive = folder / "slice-review.3mf"
        gcode = folder / "plate_1.gcode"
        if row["status"] != "OFFLINE_SLICE_ONLY" or not archive.is_file() or not gcode.is_file():
            raise RuntimeError(f"X{angle} root-web slice failed")
        comp, item, center = screen.placement(archive, review["base"]["bounds_mm"])
        row["shell_anchor_support_segments_in_void_cores"] = support_in_shell_void_cores(
            gcode, comp, item, center)
        rows[f"x{angle}"] = row
    no_support_x55 = screen_x55_without_support()
    after = {str(path.relative_to(ROOT)): digest(path) for path in sources}
    if before != after:
        raise RuntimeError("Root-web sources changed during slicing")
    report = {
        "status": "ROOT_WEB_ORIENTATION_SCREEN_ONLY_UNRELEASED",
        "source_sha256": before,
        "machine": "Bambu Lab X1 Carbon; 0.4 mm nozzle; Textured PEI",
        "material_profile": "Generic PETG",
        "process": "0.2 mm layers; 4 walls; 25% infill; 5 mm brim; tree support from bed only",
        "shell_void_scan": "Support segment centerlines sampled every <=0.15 mm in nominal shell M3 through-hole and counterbore cores; extrusion width, print error and support removal unverified",
        "orientations": rows,
        "no_support_x55": no_support_x55,
        "best_orientation_selected": False,
        "manufacturing_release": False,
        "physical_acceptance": False,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    for label, row in rows.items():
        print(label, row["status"], round(row["filament_g"], 3), "g",
              row["gcode_layers"], "layers", "shell-core-support",
              row["shell_anchor_support_segments_in_void_cores"], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
