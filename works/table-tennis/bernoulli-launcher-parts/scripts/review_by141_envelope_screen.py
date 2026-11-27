#!/usr/bin/env python3
"""Screen seller-gallery cylinder against selected electric assembly poses.

This deliberately cannot approve a motor mount or transmission: the diameter,
overall length and stroke are from shared seller images, not measured SKU CAD.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import re
import struct
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
CAD = ROOT / "cad/by141-envelope-screen.scad"
OUT = ROOT / "output/by141-envelope-screen"
DRIVE = ROOT / "output/electric-drive-feasibility/report.json"
INTEGRATION = ROOT / "output/electric-trigger-integration/review.json"
OPENSCAD = Path("/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
INSPECT = Path("/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py")
CENTERS = ((100, 63), (100, 70), (85, 70), (85, 63))
DIAMETERS = (22, 29)
POSITIONS = (0, .25, .5, .75, 1)
TARGETS = ("fixed", "moving", "hardware")


def sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def source_tree(path: Path, found: set[Path] | None = None) -> set[Path]:
    found = found if found is not None else set()
    path = path.resolve()
    if path in found:
        return found
    found.add(path)
    for name in re.findall(r"\b(?:use|include)\s*<([^>]+)>", path.read_text()):
        source_tree(path.parent / name, found)
    return found


def export_probe(row: tuple[int, int, int, str, float]) -> tuple[str, dict]:
    diameter, x, y, target, position = row
    tag = f"d{diameter}-x{x}-y{y}-{target}-t{position:.2f}"
    destination = OUT / f"{tag}.stl"
    destination.unlink(missing_ok=True)
    command = [str(OPENSCAD), "--hardwarnings", "--backend", "Manifold",
               "-D", f"me_d={diameter}", "-D", f"me_x={x}", "-D", f"me_y={y}",
               "-D", f'me_target="{target}"', "-D", f"me_t={position}",
               "-o", str(destination), str(CAD)]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=120)
    log = result.stdout + result.stderr
    if (result.returncode == 1 and "Current top level object is empty" in log
            and "WARNING:" not in log and "ERROR:" not in log):
        return tag, {"occupied": False, "volume_mm3": 0}
    if result.returncode or "WARNING:" in log or "ERROR:" in log:
        return tag, {"error": log[-1400:]}
    inspected = subprocess.run([sys.executable, str(INSPECT), str(destination),
                                "--json", "--require-watertight"], cwd=ROOT,
                               text=True, capture_output=True, timeout=60)
    if inspected.returncode:
        return tag, {"error": inspected.stdout[-1000:] + inspected.stderr[-1000:]}
    mesh = json.loads(inspected.stdout)
    volume = mesh["volume"]
    if volume <= 1e-9:
        return tag, {"occupied": False, "volume_mm3": volume,
                     "sheet_only": min(mesh["bounds"]["size"]) < 1e-9}
    return tag, {"occupied": True, "volume_mm3": volume,
                 "bounds": mesh["bounds"], "stl_sha256": sha(destination)}


def main() -> int:
    drive = json.loads(DRIVE.read_text())
    gallery = drive["archived_seller_gallery_unverified"]
    if (gallery["seller_listing_item_id"] != "988456349136"
            or gallery["selected_sku_id"] != "5952763100025"
            or gallery["image_02_claims"]["outside_diameter_mm"] != 20.5
            or gallery["image_02_claims"]["overall_length_mm"] != 99
            or gallery["image_02_claims"]["stroke_mm"] != 30
            or gallery["main_05_claims"]["white_end_outside_diameter_mm"] != 22
            or gallery["main_05_claims"]["yellow_protective_sleeve_outside_diameter_mm"] != 29
            or gallery["main_05_claims"]["yellow_protective_sleeve_length_mm"] != 68
            or gallery["main_05_claims"]["protective_sleeve_in_selected_sku_confirmed"]
            or gallery["exact_selected_sku_identity_proven_by_images"]):
        raise RuntimeError("Shared seller-image dimensions changed; rescope screen")
    for row in gallery["source_images"].values():
        if sha(ROOT / row["path"]) != row["sha256"]:
            raise RuntimeError("Archived seller image changed")
    integration = json.loads(INTEGRATION.read_text())
    if integration["status"] != "SELECTED_TRIGGER_GEOMETRY_PASS_UNRELEASED":
        raise RuntimeError("Selected integrated trigger review missing")
    for name, expected in integration["source_sha256"].items():
        if sha(ROOT / name) != expected:
            raise RuntimeError(f"Selected trigger source changed: {name}")
    OUT.mkdir(parents=True, exist_ok=True)
    sources = source_tree(CAD) | {Path(__file__).resolve()}
    before = {str(path.relative_to(ROOT)): sha(path) for path in sorted(sources)}
    rows = [(diameter, x, y, target, t) for diameter in DIAMETERS for x, y in CENTERS
            for target in TARGETS for t in POSITIONS]
    control = (22, 63, 27, "fixed", 0)
    with ThreadPoolExecutor(max_workers=4) as pool:
        probes = dict(pool.map(export_probe, rows + [control]))
    image = OUT / "context.png"
    image.unlink(missing_ok=True)
    image_size = (1400, 1000)
    command = [str(OPENSCAD), "--hardwarnings", "--backend", "Manifold",
               "--render", f"--imgsize={image_size[0]},{image_size[1]}",
               "--camera=0,0,-60,65,0,150,1000", "-D", 'me_part="context"',
               "-D", "me_x=85", "-D", "me_y=63", "-D", "me_d=29",
               "-o", str(image), str(CAD)]
    rendered = subprocess.run(command, cwd=ROOT, text=True, capture_output=True,
                              timeout=120)
    after = {str(path.relative_to(ROOT)): sha(path) for path in sorted(sources)}
    failures = [name for name, row in probes.items() if "error" in row]
    control_tag = "d22-x63-y27-fixed-t0.00"
    if not probes[control_tag].get("occupied"):
        failures.append("intersection positive control is empty")
    image_bytes = image.read_bytes() if image.exists() else b""
    if (rendered.returncode or "WARNING:" in rendered.stderr
            or "ERROR:" in rendered.stderr or image_bytes[:8] != b"\x89PNG\r\n\x1a\n"
            or len(image_bytes) < 24
            or struct.unpack(">II", image_bytes[16:24]) != image_size):
        failures.append("assembly context render failed")
    if before != after:
        failures.append("source changed during screen")
    candidates = {}
    for diameter in DIAMETERS:
        for x, y in CENTERS:
            prefix = f"d{diameter}-x{x}-y{y}-"
            collisions = [name for name, row in probes.items()
                          if name.startswith(prefix) and row.get("occupied")]
            candidates[f"d{diameter}-x{x}-y{y}"] = {
                "full_length_diameter_mm": diameter,
                "axis_xy_mm": [x, y],
                "sampled_collision_free": not collisions,
                "colliding_probes": collisions,
            }
    report = {
        "status": "SCHEMATIC_SELLER_ENVELOPE_SCREEN_ONLY" if not failures else "FAIL",
        "selected_item_id": gallery["seller_listing_item_id"],
        "selected_sku_id": gallery["selected_sku_id"],
        "seller_picture_scope": gallery["scope"],
        "source_sha256": before,
        "drive_report_sha256": sha(DRIVE),
        "integrated_trigger_review_sha256": sha(INTEGRATION),
        "seller_image_sha256": {name: row["sha256"]
                                for name, row in gallery["source_images"].items()},
        "screen_envelopes_mm": {
            "bare_seller_main_picture": {"full_length_diameter": 22,
                                         "interpretation": "Ø22 full 129 mm length bounds depicted bare Ø21 metal motor and Ø22 white tip"},
            "optional_cover_overbound": {"full_length_diameter": 29,
                                         "seller_cover_length": 68,
                                         "interpretation": "Ø29 conservatively covers full 129 mm, more than the pictured 68 mm sleeve; its inclusion in the selected SKU is unknown"},
            "retracted_length": 99, "output_sweep": 30,
            "axis": "+Z", "rear_z": -91, "retracted_tip_z": 8,
            "extended_tip_z": 38,
            "interpretation": "Both cylinders are bounding tools, not actual casing shape, mounting base or moving connector",
        },
        "pose_samples": list(POSITIONS),
        "trigger_angle_deg": 0,
        "probes": probes, "positive_control": control_tag,
        "candidates": candidates,
        "probe_count": len(rows) + 1,
        "context_image": {"file": str(image.relative_to(ROOT)),
                          "sha256": sha(image) if image.exists() else None,
                          "pixels": list(image_size), "axis_xy_mm": [85, 63],
                          "full_length_diameter_mm": 29},
        "real_motor_mounted": False,
        "motor_mount_designed": False,
        "rocker_and_joints_designed": False,
        "continuous_sweep_proven": False,
        "clearance_allowance_verified": False,
        "manufacturing_release": False,
        "physical_acceptance": False,
        "failures": failures,
    }
    (OUT / "review.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"BY141 shared-image envelope screen: {len(rows)+1} probes, {len(failures)} errors")
    for name, row in candidates.items():
        print(f"  {name}: {'clear at samples' if row['sampled_collision_free'] else 'collides'}"
              f" ({len(row['colliding_probes'])} probes)")
    for failure in failures:
        print("  ERROR " + failure)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
