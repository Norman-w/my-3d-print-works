#!/usr/bin/env python3
"""Export JLCPCB SMT BOM + CPL for the current main board, excluding hand-assembly parts.

Default exclusions (not placed by SMT):
  - ESP32-S3 / IM948 embedded modules
  - Tail MX1.25 connectors
  - PZT wire pads (SIG/GND)
  - KiCad DNP footprints (JP_ADC_*)
  - Through-hole tactiles (SW_*)

Everything else that is SMD and has a Value enters BOM/CPL.
Missing LCSC numbers still appear in BOM with an empty LCSC column and are
listed in reports/smt_needs_lcsc.csv for manual selection at order time.
"""

from __future__ import annotations

# ===== 分区：导入/依赖 =====
import argparse
import csv
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import yaml

# ===== 分区：常量/配置 =====
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BOARD = ROOT / "pcb" / "layouts" / "default" / "default.kicad_pcb"
DEFAULT_MAP = ROOT / "pcb" / "jlcpcb" / "smt_parts_map.yaml"
KICAD_PYTHON = (
    "/Applications/KiCad/KiCad.app/Contents/Frameworks/"
    "Python.framework/Versions/Current/bin/python3"
)

HAND_ADDR_EXACT = frozenset(
    {
        "mcu",
        "imu",
        "tail.conn_f",
        "tail.conn_b",
        "debug_sw.sw_boot",
        "debug_sw.sw_en",
        "debug_sw.sw_pwr",
    }
)
HAND_ADDR_SUFFIXES = (
    ".pzt_signal_pad",
    ".pzt_gnd_pad",
)


# ===== 分区：模型/类型 =====
@dataclass(frozen=True)
class FootprintRow:
    ref: str
    value: str
    addr: str
    footprint: str
    x_mm: float
    y_mm: float
    rot_deg: float
    flip: bool
    dnp: bool
    smd: bool
    tht: bool
    exclude_bom: bool


# ===== 分区：私有成员 =====
def _addr_of(fp) -> str:
    if fp.HasFieldByName("atopile_address"):
        return fp.GetFieldByName("atopile_address").GetText() or ""
    return ""


def _load_footprints(board_path: Path) -> list[FootprintRow]:
    """Load footprints via KiCad Python (must match board used for Gerbers)."""
    import pcbnew  # type: ignore

    board = pcbnew.LoadBoard(str(board_path))
    # KiCad: FP_THROUGH_HOLE=1<<0, FP_SMD=1<<1, FP_EXCLUDE_FROM_BOM=1<<3
    fp_smd = int(pcbnew.FP_SMD)
    fp_tht = int(pcbnew.FP_THROUGH_HOLE)
    fp_ex_bom = int(pcbnew.FP_EXCLUDE_FROM_BOM)
    rows: list[FootprintRow] = []
    for fp in board.GetFootprints():
        attrs = int(fp.GetAttributes())
        rows.append(
            FootprintRow(
                ref=fp.GetReference(),
                value=fp.GetValue(),
                addr=_addr_of(fp),
                footprint=fp.GetFPIDAsString(),
                x_mm=round(pcbnew.ToMM(fp.GetPosition().x), 4),
                y_mm=round(pcbnew.ToMM(fp.GetPosition().y), 4),
                rot_deg=round(fp.GetOrientationDegrees() % 360.0, 3),
                flip=bool(fp.IsFlipped()),
                dnp=bool(fp.IsDNP()),
                smd=bool(attrs & fp_smd),
                tht=bool(attrs & fp_tht),
                exclude_bom=bool(attrs & fp_ex_bom),
            )
        )
    return sorted(rows, key=lambda row: row.ref)


def _hand_reason(row: FootprintRow, part_map: dict) -> str | None:
    if row.dnp:
        return "dnp"
    if row.exclude_bom:
        return "exclude_from_bom"
    if row.addr in HAND_ADDR_EXACT:
        return f"hand_addr:{row.addr}"
    if any(row.addr.endswith(suffix) for suffix in HAND_ADDR_SUFFIXES):
        return "pzt_wire_pad"
    mapped = part_map.get(row.value) or {}
    if mapped.get("smt") is False:
        return str(mapped.get("reason") or "map_smt_false")
    if row.tht and not row.smd:
        return "through_hole"
    if not row.smd:
        return "not_smd"
    return None


def _resolve_part(value: str, footprint: str, part_map: dict) -> dict:
    entry = dict(part_map.get(value) or {})
    contains = entry.get("footprint_contains")
    if contains and contains not in footprint:
        return {}
    return entry


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _group_bom(smt_rows: list[tuple[FootprintRow, dict]]) -> list[dict]:
    groups: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    meta: dict[tuple[str, str, str], dict] = {}
    for row, part in smt_rows:
        package = part.get("package") or row.footprint.split(":")[-1]
        comment = part.get("comment") or row.value
        lcsc = part.get("lcsc") or ""
        key = (comment, package, lcsc)
        groups[key].append(row.ref)
        meta[key] = part
    bom: list[dict] = []
    for (comment, package, lcsc), refs in sorted(
        groups.items(), key=lambda item: (item[0][0], ",".join(item[1]))
    ):
        bom.append(
            {
                "Comment": comment,
                "Designator": ",".join(refs),
                "Footprint": package,
                "LCSC Part #": lcsc,
                "Quantity": str(len(refs)),
            }
        )
    return bom


# ===== 分区：公开 API =====
def export_smt(
    board: Path,
    output: Path,
    parts_map_path: Path,
    *,
    require_lcsc: bool = False,
) -> dict:
    part_map = yaml.safe_load(parts_map_path.read_text(encoding="utf-8")) or {}
    parts = part_map.get("parts") or {}
    footprints = _load_footprints(board)

    smt_pairs: list[tuple[FootprintRow, dict]] = []
    hand_rows: list[dict] = []
    missing_lcsc: list[dict] = []

    for row in footprints:
        reason = _hand_reason(row, parts)
        if reason:
            hand_rows.append(
                {
                    "Designator": row.ref,
                    "Value": row.value,
                    "Address": row.addr,
                    "Footprint": row.footprint,
                    "Reason": reason,
                    "Layer": "bottom" if row.flip else "top",
                }
            )
            continue
        part = _resolve_part(row.value, row.footprint, parts)
        if require_lcsc and not part.get("lcsc"):
            missing_lcsc.append(
                {
                    "Designator": row.ref,
                    "Value": row.value,
                    "Footprint": row.footprint,
                    "Note": "no LCSC in smt_parts_map.yaml",
                }
            )
            hand_rows.append(
                {
                    "Designator": row.ref,
                    "Value": row.value,
                    "Address": row.addr,
                    "Footprint": row.footprint,
                    "Reason": "missing_lcsc",
                    "Layer": "bottom" if row.flip else "top",
                }
            )
            continue
        if not part.get("lcsc"):
            missing_lcsc.append(
                {
                    "Designator": row.ref,
                    "Value": row.value,
                    "Footprint": row.footprint,
                    "Note": "BOM row kept; pick LCSC at JLCPCB upload",
                }
            )
        smt_pairs.append((row, part))

    if any(row.flip for row, _ in smt_pairs):
        raise RuntimeError(
            "Main-board SMT export expects top-only Economic SMT; found bottom SMD parts"
        )

    bom_rows = _group_bom(smt_pairs)
    cpl_rows = [
        {
            "Designator": row.ref,
            "Mid X": f"{row.x_mm:.4f}",
            "Mid Y": f"{row.y_mm:.4f}",
            "Layer": "top",
            "Rotation": f"{row.rot_deg:.3f}".rstrip("0").rstrip(".")
            if "." in f"{row.rot_deg:.3f}"
            else f"{row.rot_deg:.0f}",
        }
        for row, _ in smt_pairs
    ]

    smt_dir = output / "smt"
    reports = output / "reports"
    smt_dir.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)

    bom_path = smt_dir / "bom.csv"
    cpl_path = smt_dir / "cpl.csv"
    hand_path = smt_dir / "hand_solder.csv"
    missing_path = reports / "smt_needs_lcsc.csv"
    readme_path = smt_dir / "README.txt"

    _write_csv(
        bom_path,
        ["Comment", "Designator", "Footprint", "LCSC Part #", "Quantity"],
        bom_rows,
    )
    _write_csv(
        cpl_path,
        ["Designator", "Mid X", "Mid Y", "Layer", "Rotation"],
        cpl_rows,
    )
    _write_csv(
        hand_path,
        ["Designator", "Value", "Address", "Footprint", "Reason", "Layer"],
        hand_rows,
    )
    _write_csv(
        missing_path,
        ["Designator", "Value", "Footprint", "Note"],
        missing_lcsc,
    )

    readme_path.write_text(
        "\n".join(
            [
                "SmartPaddle — JLCPCB partial SMT package",
                "",
                "Full ordering playbook: pcb/JLCPCB_ORDERING.md",
                "",
                "Upload:",
                f"  BOM -> {bom_path.name}",
                f"  CPL -> {cpl_path.name}",
                "",
                "NOT placed by SMT (see hand_solder.csv):",
                "  embedded modules, tail connectors, PZT wire pads,",
                "  test points, THT switches, DNP jumpers",
                "",
                "After SMT: hand-solder items in hand_solder.csv,",
                "then bring-up per that revision's FAB_READINESS.",
                "",
                f"SMT designators: {len(smt_pairs)}",
                f"Hand-solder / excluded: {len(hand_rows)}",
                f"Missing LCSC rows: {len(missing_lcsc)}",
                f"Parts map: {parts_map_path}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    summary = {
        "schema_version": 1,
        "board": str(board.resolve()),
        "parts_map": str(parts_map_path.resolve()),
        "smt_count": len(smt_pairs),
        "hand_count": len(hand_rows),
        "bom_lines": len(bom_rows),
        "missing_lcsc": len(missing_lcsc),
        "bom": str(bom_path),
        "cpl": str(cpl_path),
        "hand_solder": str(hand_path),
    }
    (reports / "smt_manifest.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--board", type=Path, default=DEFAULT_BOARD)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--parts-map", type=Path, default=DEFAULT_MAP)
    parser.add_argument(
        "--require-lcsc",
        action="store_true",
        help="Exclude SMT candidates that lack an LCSC C-number in the map",
    )
    args = parser.parse_args()
    if sys.executable != KICAD_PYTHON and "KiCad" not in sys.executable:
        # Allow KiCad-bundled python or any env that can import pcbnew.
        try:
            import pcbnew  # noqa: F401
        except ImportError:
            print(
                "Need KiCad Python with pcbnew. Re-run with:\n"
                f"  {KICAD_PYTHON} {Path(__file__).name} ...",
                file=sys.stderr,
            )
            return 2
    summary = export_smt(
        args.board.resolve(),
        args.output.resolve(),
        args.parts_map.resolve(),
        require_lcsc=args.require_lcsc,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
