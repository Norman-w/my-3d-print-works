#!/usr/bin/env python3
"""Create an X1C-ready single core print and its identity-transform 3MF.

The source core meshes use assembly coordinates.  Bambu Studio validates an
object's raw mesh bounds before applying a build-item transform, so the print
artifact stores the already-oriented mesh in bed coordinates and uses an
identity 3MF transform.
"""

from __future__ import annotations

import argparse
import struct
from pathlib import Path

from scripts.build_3mf_package import model_xml, package_3mf
from scripts.build_print_plates import (
    TRIANGLE,
    bounds_of,
    flat_core,
    load_binary_stl,
    transform_triangles,
)


def write_binary_stl(path: Path, triangles: tuple[tuple[float, ...], ...], label: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = f"SmartPaddle {label}; X1C single core; rigid transform".encode("ascii", "replace")[:80]
    with path.open("wb") as handle:
        handle.write(header.ljust(80, b"\0"))
        handle.write(struct.pack("<I", len(triangles)))
        for values in triangles:
            quantized = [struct.unpack("<f", struct.pack("<f", value))[0] for value in values[:12]]
            handle.write(TRIANGLE.pack(*quantized, 0))


def build(source: Path, output_stl: Path, output_3mf: Path, *, flip_face_up: bool, label: str) -> None:
    source_mesh = load_binary_stl(source)
    oriented = flat_core(source_mesh, flip_face_up=flip_face_up)
    minimum, _ = oriented.bounds
    margin = 5.0
    shifted = transform_triangles(
        oriented.triangles,
        ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        (margin - minimum[0], margin - minimum[1], -minimum[2]),
    )
    final_bounds = bounds_of(shifted)
    if any(value < -1e-4 or value > 256.0 + 1e-4 for bound in final_bounds for value in bound):
        raise ValueError(f"{label} 超出 X1C 256mm 构建体积: {final_bounds}")
    write_binary_stl(output_stl, shifted, label)
    selected = {
        "label": label,
        "assemblyGeometryUnchanged": True,
        "parts": [{
            "source": output_stl.name,
            "rotationMatrix": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
            "translationAfterRotation": [0.0, 0.0, 0.0],
        }],
    }
    package_3mf(output_3mf, model_xml(selected, output_stl.parent))
    print(f"✓ {output_stl} bounds={final_bounds} triangles={len(shifted)}")
    print(f"✓ {output_3mf} identity-transform 3MF")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-stl", type=Path, required=True)
    parser.add_argument("--output-3mf", type=Path, required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--flip-face-up", action="store_true")
    args = parser.parse_args()
    build(
        args.source,
        args.output_stl,
        args.output_3mf,
        flip_face_up=args.flip_face_up,
        label=args.label,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
