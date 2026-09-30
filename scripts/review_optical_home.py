#!/usr/bin/env python3
"""Rebuild and review the EE-SX675-WR feeder-home candidate from source."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "cad/feeder-optical-home.scad"
OUTPUT = ROOT / "output/optical-home-candidate"
OPENSCAD = Path("/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
INSPECT = Path("/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py")
DEPENDENCIES = (
    "cad/cable-trigger-system.scad",
    "cad/launcher-final-assembly.scad",
    "cad/feeder-frame-y-guide.scad",
    "cad/feeder-return-spring.scad",
    "cad/feeder-pin-seat-revision.scad",
    "cad/cable-output-interface.scad",
    "cad/cable-trigger-input.scad",
)


def export(name: str, definitions: dict[str, str]) -> dict:
    output = OUTPUT / f"{name}.stl"
    command = [str(OPENSCAD), "--backend", "Manifold", "-o", str(output)]
    for key, value in definitions.items():
        command += ["-D", f"{key}={value}"]
    command += [str(SOURCE)]
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    empty = result.returncode == 1 and "Current top level object is empty" in result.stderr
    warnings = [line for line in result.stderr.splitlines() if "WARNING:" in line or "ERROR:" in line]
    if empty:
        output.unlink(missing_ok=True)
        return {"name": name, "empty": True, "warnings": warnings}
    if result.returncode != 0 or warnings:
        return {"name": name, "error": result.stderr[-1500:], "warnings": warnings}
    inspected = subprocess.run(
        ["python3", str(INSPECT), str(output), "--json"],
        text=True,
        capture_output=True,
        check=True,
    )
    mesh = json.loads(inspected.stdout)
    return {
        "name": name,
        "empty": False,
        "triangle_count": mesh["triangleCount"],
        "volume_mm3": mesh["volume"],
        "watertight": mesh["watertightByEdgeTopology"],
        "bounds_mm": mesh["bounds"],
        "warnings": warnings,
    }


def probe(name: str, probe_name: str, t: float = 0, dz: int = 0) -> tuple[str, dict]:
    row = export(
        name,
        {
            "oh_part": '"probe"',
            "oh_probe": json.dumps(probe_name),
            "oh_t": str(t),
            "oh_sensor_dz": str(dz),
        },
    )
    return name, row


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    jobs = [
        ("left-y-cap", {"oh_part": '"left-cap"'}),
        ("moving-spring-spacer-flag", {"oh_part": '"moving-spacer"'}),
    ]
    parts = {name: export(name, defs) for name, defs in jobs}
    checks: list[tuple[str, str, float, int, bool]] = []
    for item in ("cap-other-fixed", "cap-fixed-hardware", "cap-service-tools"):
        checks.append((item, item, 0, 0, True))
    for dz in (0, 2):
        for t in (0, .25, .5, .75, 1):
            tag = f"d{dz}-t{str(t).replace('.', 'p')}"
            for kind in (
                "sensor-existing",
                "sensor-fasteners-existing",
                "sensor-head-body",
                "flag-sensor",
                "flag-sensor-screws",
                "flag-new-cap",
                "flag-extension-existing",
                "flag-extension-hardware",
            ):
                checks.append((f"{kind}-{tag}", kind, t, dz, True))
        checks.append((f"beam-blocked-d{dz}-home", "beam-blocked", 0, dz, False))
        checks.append((f"beam-blocked-d{dz}-departed", "beam-blocked", .3, dz, True))
    checks.append(("positive-control", "positive-control", 0, 0, False))

    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(probe, name, kind, t, dz): (name, expected_empty)
                   for name, kind, t, dz, expected_empty in checks}
        for future in concurrent.futures.as_completed(futures):
            name, _ = futures[future]
            _, row = future.result()
            results[name] = row
    failures = []
    for name, part in parts.items():
        if part.get("error") or not part.get("watertight") or part.get("volume_mm3", 0) <= 0:
            failures.append(f"{name}: non-manifold/empty/failed export")
    for name, _, _, _, expected_empty in checks:
        row = results[name]
        present = not row.get("empty", False) and row.get("volume_mm3", 0) > 1e-5
        if row.get("error") or present == expected_empty:
            failures.append(f"{name}: expected {'empty' if expected_empty else 'solid'}")
    report = {
        "sensor": "Omron EE-SX675-WR 1M",
        "source": str(SOURCE.relative_to(ROOT)),
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "dependency_sha256": {
            rel: hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
            for rel in DEPENDENCIES
        },
        "scope": "nominal CAD solids; physical fit, IR opacity, motor phase and braking unverified",
        "printed_parts": parts,
        "probe_count": len(checks),
        "probes": dict(sorted(results.items())),
        "failures": failures,
        "geometry_review_pass": not failures,
    }
    path = OUTPUT / "review.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"{path}: {'PASS' if not failures else 'FAIL'}; {len(checks)} probes")
    for failure in failures:
        print(f"  {failure}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
