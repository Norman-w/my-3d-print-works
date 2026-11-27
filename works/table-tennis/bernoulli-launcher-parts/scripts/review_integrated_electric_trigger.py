#!/usr/bin/env python3
"""Verify that the selected trigger parts replace the old beam in one scene."""

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
CAD = ROOT / "cad/electric-feeder-trigger-assembly.scad"
TRIGGER_REVIEW = ROOT / "output/electronic-trigger-candidate/review.json"
INVENTORY = ROOT / "docs/electric-assembly-inventory.json"
OUT = ROOT / "output/electric-trigger-integration"
OPENSCAD = Path("/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
INSPECT = Path("/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py")


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


def module_body(source: str, name: str) -> str | None:
    match = re.search(rf"\bmodule\s+{re.escape(name)}\([^)]*\)\s*\{{", source)
    if not match:
        return None
    start = match.end()
    depth = 1
    for index in range(start, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index]
    return None


def export(name: str, part: str, probe: str = "", angle: float = 0,
           feed: float = 0) -> dict:
    target = OUT / f"{name}.stl"
    target.unlink(missing_ok=True)
    cmd = [str(OPENSCAD), "--hardwarnings", "--backend", "Manifold",
           "-o", str(target), "-D", f'it_part="{part}"',
           "-D", f"it_angle={angle}", "-D", f"it_feed_t={feed}"]
    if probe:
        cmd += ["-D", f'it_probe="{probe}"']
    cmd.append(str(CAD))
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True,
                            timeout=120)
    log = result.stdout + result.stderr
    if result.returncode == 1 and "Current top level object is empty" in log \
            and "WARNING:" not in log and "ERROR:" not in log:
        return {"empty": True, "volume_mm3": 0}
    if result.returncode or "WARNING:" in log or "ERROR:" in log:
        return {"error": log[-1500:]}
    inspected = subprocess.run([sys.executable, str(INSPECT), str(target),
                                "--json"], capture_output=True, text=True,
                               timeout=60, check=True)
    mesh = json.loads(inspected.stdout)
    return {"empty": mesh["volume"] <= 1e-5,
            "volume_mm3": mesh["volume"],
            "watertight": mesh["watertightByEdgeTopology"],
            "bounds_mm": mesh["bounds"], "sha256": sha(target),
            "file": str(target.relative_to(ROOT))}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    review = json.loads(TRIGGER_REVIEW.read_text())
    inventory = json.loads(INVENTORY.read_text())
    if review["status"] != "TRIGGER_CANDIDATE_GEOMETRY_PASS_UNRELEASED":
        raise RuntimeError("Trigger part geometry review has not passed")
    for name, expected in review["source_sha256"].items():
        if sha(ROOT / name) != expected:
            raise RuntimeError(f"Trigger source changed since review: {name}")
    before = {str(p.relative_to(ROOT)): sha(p)
              for p in sorted(source_tree(CAD) | {Path(__file__).resolve(), INVENTORY})}
    parts = {name: export(name, name) for name in ("beam", "lever")}
    probes = [("trigger-drive-corridor", angle, 0, False)
              for angle in (0, -8)]
    probes += [("lever-other-fixed", angle, 0, False)
               for angle in (0, -4, -8)]
    probes += [("lever-other-moving", angle, feed, False)
               for feed in (0, .5, 1) for angle in (0, -4, -8)]
    probes += [("mount-other-fixed", 0, 0, False),
               ("beam-self-positive-control", 0, 0, True)]

    def run_probe(row: tuple[str, float, float, bool]):
        kind, angle, feed, occupied = row
        tag = f"{kind}-a{angle:+.1f}-t{feed:.1f}"
        return tag, export("probe-" + tag, "probe", kind, angle, feed), occupied

    with ThreadPoolExecutor(max_workers=4) as pool:
        checked = list(pool.map(run_probe, probes))
    failures = []
    selected = {part["id"]: part for part in inventory["printed_parts"]}
    wrapper = CAD.read_text()
    fixed = module_body(wrapper, "it_fixed_printed")
    assembly = module_body(wrapper, "it_assembly")
    base = (ROOT / "cad/electric-feeder-assembly.scad").read_text()
    beam_free = module_body(base, "ed_fixed_without_beam")
    selected_replacement_only = (
        inventory.get("electronic_trigger_selected") is True
        and selected.get("feeder/beam-grip", {}).get("source") == str(CAD.relative_to(ROOT))
        and selected.get("feeder/beam-grip", {}).get("definitions") == {"it_part": "beam"}
        and selected.get("feeder/trigger-lever", {}).get("definitions") == {"it_part": "lever"}
        and fixed is not None and assembly is not None and beam_free is not None
        and "ed_fixed_without_beam();" in fixed
        and "et_beam();" in fixed
        and "ed_fixed_without_beam();" in assembly
        and assembly.count("et_beam();") == 1
        and "sh_beam();" not in fixed + assembly + beam_free
        and "ed_assembly();" not in assembly
    )
    if not selected_replacement_only:
        failures.append("selected assembly may co-install the original beam")
    for name, row in parts.items():
        expected = review["parts"][name]["sha256"]
        if row.get("error") or row.get("empty") or not row.get("watertight"):
            failures.append(f"{name}: not a closed selected mesh")
        elif row["sha256"] != expected:
            failures.append(f"{name}: selected mesh differs from reviewed trigger mesh")
    for tag, row, occupied in checked:
        if row.get("error") or row.get("empty") == occupied:
            failures.append(f"{tag}: wrong occupancy")
    image = OUT / "current-assembly.png"
    image.unlink(missing_ok=True)
    camera = "0,0,-60,65,0,150,1000"
    image_size = (1600, 1200)
    command = [str(OPENSCAD), "--hardwarnings", "--backend", "Manifold",
               "--render", f"--imgsize={image_size[0]},{image_size[1]}",
               f"--camera={camera}", "-D", 'it_part="assembly"',
               "-D", "it_angle=0", "-o", str(image), str(CAD)]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                            timeout=120)
    log = result.stdout + result.stderr
    if result.returncode or "WARNING:" in log or "ERROR:" in log:
        failures.append(f"integrated assembly render failed: {log[-700:]}")
    elif image.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n" \
            or struct.unpack(">II", image.read_bytes()[16:24]) != image_size:
        failures.append("integrated assembly image dimensions are wrong")
    after = {str(p.relative_to(ROOT)): sha(p)
             for p in sorted(source_tree(CAD) | {Path(__file__).resolve(), INVENTORY})}
    if before != after:
        failures.append("source tree changed during review")
    report = {
        "status": "SELECTED_TRIGGER_GEOMETRY_PASS_UNRELEASED" if not failures else "FAIL",
        "source_sha256": before,
        "trigger_geometry_review_sha256": sha(TRIGGER_REVIEW),
        "printed_parts": parts,
        "assembly_image": {"file": str(image.relative_to(ROOT)),
                           "sha256": sha(image) if image.exists() else None,
                           "pixels": list(image_size), "camera": camera,
                           "trigger_angle_deg": 0},
        "probe_count": len(checked), "probes": {name: row for name, row, _ in checked},
        "old_beam_replaced_not_coinstalled": bool(selected_replacement_only),
        "mechanical_load_path": "finger to lever to M3 pivot and printed stops to integral fixed beam",
        "motor_mount_reviewed": False,
        "switch_spring_and_pivot_physically_verified": False,
        "manufacturing_release": False,
        "failures": failures,
    }
    (OUT / "review.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"integrated electronic trigger: {'PASS' if not failures else 'FAIL'}; "
          f"{len(checked)} probes")
    for failure in failures:
        print("  " + failure)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
