#!/usr/bin/env python3
"""Render the unreleased electronic trigger from the reviewed CAD snapshot."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import struct
import subprocess


ROOT = Path(__file__).resolve().parents[1]
CAD = ROOT / "cad/electronic-trigger-candidate.scad"
INTEGRATED_CAD = ROOT / "cad/electric-feeder-trigger-assembly.scad"
INTEGRATION_REVIEW = ROOT / "output/electric-trigger-integration/review.json"
OUT = ROOT / "output/electronic-trigger-candidate"
OPENSCAD = Path("/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
VIEWS = {
    "overall-pulled.png": (INTEGRATED_CAD, "it_part", "it_angle", "assembly", -8,
                           "0,0,-60,65,0,150,1000", (1600, 1200)),
    "mechanism-rest.png": (CAD, "et_part", "et_angle", "mechanism", 0,
                           "54,-52,-16,90,0,180,160", (1200, 900)),
    "mechanism-pulled.png": (CAD, "et_part", "et_angle", "mechanism", -8,
                             "54,-52,-16,90,0,180,160", (1200, 900)),
}


def sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def png_size(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"Not a PNG: {path}")
    return struct.unpack(">II", header[16:24])


def main() -> int:
    review_path = OUT / "review.json"
    review = json.loads(review_path.read_text())
    integration = json.loads(INTEGRATION_REVIEW.read_text())
    if review["status"] != "TRIGGER_CANDIDATE_GEOMETRY_PASS_UNRELEASED":
        raise RuntimeError("Geometry review has not passed")
    if integration["status"] != "SELECTED_TRIGGER_GEOMETRY_PASS_UNRELEASED" \
            or integration["trigger_geometry_review_sha256"] != sha(review_path):
        raise RuntimeError("Selected assembly review differs from trigger geometry")
    for name, expected in review["source_sha256"].items():
        if sha(ROOT / name) != expected:
            raise RuntimeError(f"Source changed after geometry review: {name}")
    for name, expected in integration["source_sha256"].items():
        if sha(ROOT / name) != expected:
            raise RuntimeError(f"Source changed after integration review: {name}")
    images = {}
    for name, (source, part_key, angle_key, part, angle, camera, size) in VIEWS.items():
        target = OUT / name
        target.unlink(missing_ok=True)
        command = [str(OPENSCAD), "--hardwarnings", "--backend", "Manifold",
                   "--render", f"--imgsize={size[0]},{size[1]}",
                   f"--camera={camera}", "-D", f'{part_key}="{part}"',
                   "-D", f"{angle_key}={angle}", "-o", str(target), str(source)]
        result = subprocess.run(command, cwd=ROOT, text=True,
                                capture_output=True, timeout=120)
        log = result.stdout + result.stderr
        if result.returncode or "WARNING:" in log or "ERROR:" in log:
            raise RuntimeError(f"{name}: OpenSCAD render failed\n{log[-1500:]}")
        if png_size(target) != size:
            raise RuntimeError(f"{name}: PNG dimensions do not match {size}")
        images[name] = {"sha256": sha(target), "pixels": list(size),
                        "source": str(source.relative_to(ROOT)),
                        "part": part, "angle_deg": angle, "camera": camera}
    for name, expected in review["source_sha256"].items():
        if sha(ROOT / name) != expected:
            raise RuntimeError(f"Source changed during rendering: {name}")
    for name, expected in integration["source_sha256"].items():
        if sha(ROOT / name) != expected:
            raise RuntimeError(f"Integration source changed during rendering: {name}")
    report = {
        "status": "TRIGGER_CANDIDATE_RENDER_MATCHES_GEOMETRY_REVIEW",
        "geometry_review_sha256": sha(review_path),
        "integration_review_sha256": sha(INTEGRATION_REVIEW),
        "images": images,
        "manufacturing_release": False, "physical_acceptance": False,
    }
    (OUT / "render-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"electronic trigger render: {len(images)} current CAD views")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
