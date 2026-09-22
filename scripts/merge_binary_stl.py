#!/usr/bin/env python3
"""Merge closed binary STL shells without performing a geometric CSG union.

The center mechanism plate is one published part made from three disjoint
row shells.  OpenSCAD's top-level Manifold merge can introduce a tiny
non-manifold seam between those rows even though every row is independently
closed.  This helper preserves the individual triangle shells in one binary
STL container; it does not duplicate, transform, or alter their geometry.
"""

from __future__ import annotations

import argparse
import struct
from pathlib import Path


def read_binary_stl(path: Path) -> tuple[int, bytes]:
    data = path.read_bytes()
    if len(data) < 84:
        raise ValueError(f"binary STL too short: {path}")
    triangle_count = struct.unpack_from("<I", data, 80)[0]
    expected_size = 84 + triangle_count * 50
    if len(data) != expected_size:
        raise ValueError(
            f"binary STL size mismatch: {path} "
            f"bytes={len(data)} expected={expected_size}"
        )
    if triangle_count == 0:
        raise ValueError(f"binary STL has no triangles: {path}")
    return triangle_count, data[84:]


def merge_binary_stls(output: Path, inputs: list[Path]) -> None:
    if not inputs:
        raise ValueError("at least one input STL is required")
    counts: list[int] = []
    payloads: list[bytes] = []
    for path in inputs:
        count, payload = read_binary_stl(path)
        counts.append(count)
        payloads.append(payload)
    total = sum(counts)
    header = (
        b"SmartPartsDrawer single published part; independent closed row shells"
    ).ljust(80, b" ")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(header + struct.pack("<I", total) + b"".join(payloads))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("inputs", nargs="+", type=Path)
    args = parser.parse_args()
    merge_binary_stls(args.output, args.inputs)
    print(
        f"merged {len(args.inputs)} closed STL shells -> {args.output} "
        f"({args.output.stat().st_size} bytes)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
