#!/usr/bin/env python3
"""Extract auditable placement facts from a KiCad PCB without deciding layout."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Sequence


def unquote(token: str) -> str:
    if not token.startswith('"'):
        return token
    return token[1:-1].replace(r"\"", '"').replace(r"\\", "\\")


def parse_sexpr(text: str) -> list[Any]:
    token_re = re.compile(r'"(?:\\.|[^"\\])*"|\(|\)|[^\s()]+')
    roots: list[Any] = []
    stack: list[list[Any]] = []
    for match in token_re.finditer(text):
        token = match.group(0)
        if token == "(":
            node: list[Any] = []
            (stack[-1] if stack else roots).append(node)
            stack.append(node)
        elif token == ")":
            if not stack:
                raise ValueError("unexpected closing parenthesis")
            stack.pop()
        elif stack:
            stack[-1].append(unquote(token))
        else:
            raise ValueError("atom outside S-expression")
    if stack:
        raise ValueError("unclosed S-expression")
    if len(roots) != 1 or not roots[0] or roots[0][0] != "kicad_pcb":
        raise ValueError("input is not a KiCad PCB")
    return roots[0]


def children(node: Sequence[Any], name: str) -> list[list[Any]]:
    return [item for item in node[1:] if isinstance(item, list) and item and item[0] == name]


def child(node: Sequence[Any], name: str) -> list[Any] | None:
    return next(iter(children(node, name)), None)


def number(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(result):
        raise ValueError(f"non-finite number: {value}")
    return result


def property_value(node: Sequence[Any], name: str) -> str:
    for prop in children(node, "property"):
        if len(prop) >= 3 and prop[1] == name:
            return str(prop[2])
    return ""


def transform(fx: float, fy: float, angle_deg: float, lx: float, ly: float) -> tuple[float, float]:
    angle = math.radians(angle_deg)
    return (
        fx + lx * math.cos(angle) - ly * math.sin(angle),
        fy + lx * math.sin(angle) + ly * math.cos(angle),
    )


def extract_footprints(board: Sequence[Any]) -> list[dict[str, Any]]:
    footprints: list[dict[str, Any]] = []
    for fp in children(board, "footprint"):
        at = child(fp, "at") or ["at", 0, 0, 0]
        layer = child(fp, "layer") or ["layer", "F.Cu"]
        fx, fy = number(at[1]), number(at[2])
        rotation = number(at[3] if len(at) > 3 else 0) % 360
        ref = property_value(fp, "Reference")
        if not ref:
            continue
        pads: list[dict[str, Any]] = []
        for pad_node in children(fp, "pad"):
            if len(pad_node) < 2:
                continue
            pad_at = child(pad_node, "at") or ["at", 0, 0]
            px, py = transform(fx, fy, rotation, number(pad_at[1]), number(pad_at[2]))
            net_node = child(pad_node, "net")
            pads.append({
                "number": str(pad_node[1]),
                "x_mm": round(px, 6),
                "y_mm": round(py, 6),
                "net": str(net_node[2]) if net_node and len(net_node) > 2 else "",
            })
        descr = child(fp, "descr")
        footprints.append({
            "reference": ref,
            "value": property_value(fp, "Value"),
            "footprint": str(fp[1]) if len(fp) > 1 else "",
            "side": "bottom" if str(layer[1]).startswith("B.") else "top",
            "x_mm": round(fx, 6),
            "y_mm": round(fy, 6),
            "rotation_deg": round(rotation, 6),
            "description": str(descr[1]) if descr and len(descr) > 1 else "",
            "pads": pads,
        })
    refs = [item["reference"] for item in footprints]
    if not footprints:
        raise ValueError("no footprints found")
    if len(refs) != len(set(refs)):
        duplicates = sorted(ref for ref in set(refs) if refs.count(ref) > 1)
        raise ValueError(f"duplicate references: {duplicates}")
    return sorted(footprints, key=lambda item: item["reference"])


def xy(node: Sequence[Any], name: str) -> list[float] | None:
    point = child(node, name)
    if not point or len(point) < 3:
        return None
    return [number(point[1]), number(point[2])]


def extract_edge_cuts(board: Sequence[Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for node in board[1:]:
        if not isinstance(node, list) or not node:
            continue
        layer = child(node, "layer")
        if not layer or len(layer) < 2 or layer[1] != "Edge.Cuts":
            continue
        kind = str(node[0])
        if kind == "gr_line":
            result.append({"type": "line", "start": xy(node, "start"), "end": xy(node, "end")})
        elif kind == "gr_arc":
            result.append({"type": "arc", "start": xy(node, "start"), "mid": xy(node, "mid"), "end": xy(node, "end")})
        elif kind == "gr_rect":
            result.append({"type": "rect", "start": xy(node, "start"), "end": xy(node, "end")})
        elif kind in {"gr_poly", "gr_curve"}:
            points_node = child(node, "pts")
            points: list[list[float]] = []
            if points_node:
                points = [[number(item[1]), number(item[2])] for item in points_node[1:] if isinstance(item, list) and item and item[0] == "xy"]
            result.append({"type": kind.removeprefix("gr_"), "points": points})
    if not result:
        raise ValueError("no Edge.Cuts geometry found")
    return result


def title_block(board: Sequence[Any]) -> dict[str, str]:
    block = child(board, "title_block")
    if not block:
        return {"title": "", "revision": ""}
    title = child(block, "title")
    revision = child(block, "rev")
    return {
        "title": str(title[1]) if title and len(title) > 1 else "",
        "revision": str(revision[1]) if revision and len(revision) > 1 else "",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pcb", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    source = args.pcb.resolve()
    raw = source.read_bytes()
    board = parse_sexpr(raw.decode("utf-8"))
    footprints = extract_footprints(board)
    payload = {
        "schema_version": 1,
        "source_path": str(source),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "title_block": title_block(board),
        "counts": {
            "footprints": len(footprints),
            "top": sum(item["side"] == "top" for item in footprints),
            "bottom": sum(item["side"] == "bottom" for item in footprints),
        },
        "footprints": footprints,
        "edge_cuts": extract_edge_cuts(board),
    }
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
        print(args.out)
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
