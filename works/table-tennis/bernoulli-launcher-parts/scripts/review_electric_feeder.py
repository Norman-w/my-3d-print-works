#!/usr/bin/env python3
"""Rebuild the electric feeder's optical replacements and sample old-part clearance."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "cad/electric-feeder-assembly.scad"
OUT = ROOT / "output/electric-feeder"
OPENSCAD = Path("/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
INSPECT = Path("/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py")
POSES = (0, .25, .5, .75, 1)
EMPTY_PROBES = ("sensor-other-fixed", "sensor-other-moving",
                "sensor-original-hardware", "flag-other-fixed",
                "flag-other-moving", "flag-hardware")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_tree(path: Path, found: set[Path] | None = None) -> set[Path]:
    found = found if found is not None else set()
    path = path.resolve()
    if path in found:
        return found
    found.add(path)
    for name in re.findall(r"\b(?:use|include)\s*<([^>]+)>", path.read_text()):
        source_tree(path.parent / name, found)
    return found


def export(name: str, definitions: dict[str, str]) -> dict:
    target = OUT / f"{name}.stl"
    command = [str(OPENSCAD), "--hardwarnings", "--backend", "Manifold", "-o", str(target)]
    for key, value in definitions.items():
        command += ["-D", f"{key}={value}"]
    command += [str(SOURCE)]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=120)
    log = result.stdout + result.stderr
    if result.returncode == 1 and "Current top level object is empty" in log \
            and "WARNING:" not in log and "ERROR:" not in log:
        target.unlink(missing_ok=True)
        return {"empty": True, "volume_mm3": 0}
    if result.returncode or "WARNING:" in log or "ERROR:" in log:
        return {"error": log[-1600:]}
    measured = subprocess.run([sys.executable, str(INSPECT), str(target), "--json"],
                              text=True, capture_output=True, check=True)
    mesh = json.loads(measured.stdout)
    volume = mesh["volume"]
    return {"empty": volume <= 1e-5, "volume_mm3": volume,
            "watertight": mesh["watertightByEdgeTopology"],
            "triangle_count": mesh["triangleCount"],
            "bounds": mesh["bounds"], "sha256": sha(target),
            "coplanar_sheet_only": volume <= 1e-5 and mesh["triangleCount"] > 0}


def job(kind: str, t: float, dz: int) -> tuple[str, dict]:
    tag = f"{kind}-t{t:.2f}-dz{dz}"
    row = export(tag, {"ed_part": '"probe"', "ed_probe": json.dumps(kind),
                       "ed_t": str(t), "oh_sensor_dz": str(dz)})
    return tag, row


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT / "docs/electric-assembly-inventory.json").read_text())
    assert manifest["snapshot"] == "electric-drive-selected-unreleased"
    assert not manifest["motor_mount_designed"] and not manifest["positive_two_way_coupling_designed"]
    assert not any("cable" in row["id"] for row in manifest["printed_parts"])
    replacements = {
        name: export(name, {"ed_part": json.dumps(name)})
        for name in ("optical-left-cap", "optical-moving-spacer")
    }
    carriage_and_beam = {
        name: export(name, {"ed_part": '"baseline"',
                            "ed_legacy_part": json.dumps(part)})
        for name, part in (("original-beam", "beam-grip"),
                           ("electric-frame", "frame"))
    }
    checks = [(kind, t, dz) for dz in (0, 2) for t in POSES for kind in EMPTY_PROBES]
    checks += [("beam-blocked", t, dz) for dz in (0, 2) for t in (0, .3)]
    checks += [(kind, t, 0) for kind in
               ("right-stop-shoulder", "left-stop-shoulder", "former-trigger-projection")
               for t in (0, 1)]
    checks.append(("positive-control", 0, 0))
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for tag, row in pool.map(lambda args: job(*args), checks):
            results[tag] = row
    failures = []
    for name, row in {**replacements, **carriage_and_beam}.items():
        if row.get("error") or row.get("empty") or not row.get("watertight"):
            failures.append(f"{name}: selected part is not a closed printable mesh")
    frame = carriage_and_beam["electric-frame"]
    if not frame.get("error") and frame["bounds"]["max"][0] > 59.001:
        failures.append("electric-frame: obsolete finger-loop projection remains")
    for kind, t, dz in checks:
        tag = f"{kind}-t{t:.2f}-dz{dz}"
        row = results[tag]
        should_be_present = kind in ("positive-control", "right-stop-shoulder",
                                     "left-stop-shoulder") \
            or kind == "beam-blocked" and t == 0
        if row.get("error") or row.get("empty") == should_be_present:
            failures.append(f"{tag}: wrong occupancy")
    sources = source_tree(SOURCE) | {ROOT / "docs/electric-assembly-inventory.json", Path(__file__)}
    report = {
        "source_sha256": {str(path.relative_to(ROOT)): sha(path)
                          for path in sorted(sources)},
        "replacement_parts": replacements,
        "beam_and_electric_frame": carriage_and_beam,
        "probe_count": len(checks), "probes": dict(sorted(results.items())),
        "failures": failures, "geometry_review_pass": not failures,
        "scope": "Nominal optical replacements on restored non-Bowden feeder; no motor geometry",
        "motor_mount_reviewed": False, "positive_drive_reviewed": False,
        "manufacturing_release": False, "physical_acceptance": False,
    }
    (OUT / "review.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"electric feeder optical review: {'PASS' if not failures else 'FAIL'}; "
          f"{len(checks)} probes")
    for failure in failures:
        print("  " + failure)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
