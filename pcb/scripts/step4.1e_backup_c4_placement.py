#!/usr/bin/env python3
"""Backup or verify every C4 footprint transform by atopile address.

The checked-in full-board snapshot is intentionally created only after the
manual KiCad placement is accepted.  It supersedes the older region-specific
snapshots when Step 4 restores a freshly generated board.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pcb.tools.kicad_update_utils import load_board  # noqa: E402
from pcb.scripts.migrate_c3_to_c4_unrouted import (  # noqa: E402
    EXPECTED_C4_COMPONENTS,
)

DEFAULT_BOARD = ROOT / "pcb" / "layouts" / "default" / "default.kicad_pcb"
DEFAULT_SNAPSHOT = (
    ROOT / "pcb" / "layouts" / "default" / "c4_placement_snapshot.json"
)
EXPECTED_COMPONENTS = EXPECTED_C4_COMPONENTS


def _address(fp) -> str:
    if not fp.HasFieldByName("atopile_address"):
        return ""
    return fp.GetFieldByName("atopile_address").GetText()


def _placement(fp, pcbnew) -> dict[str, object]:
    pos = fp.GetPosition()
    return {
        "addr": _address(fp),
        "ref": fp.GetReference(),
        "x": round(pcbnew.ToMM(pos.x), 6),
        "y": round(pcbnew.ToMM(pos.y), 6),
        "rot": round(fp.GetOrientationDegrees(), 4),
        "flip": bool(fp.IsFlipped()) if hasattr(fp, "IsFlipped") else False,
    }


def _collect(board, pcbnew) -> list[dict[str, object]]:
    footprints = list(board.GetFootprints())
    placements = [_placement(fp, pcbnew) for fp in footprints]
    missing = [entry["ref"] for entry in placements if not entry["addr"]]
    if missing:
        raise RuntimeError(f"footprints missing atopile_address: {missing}")
    addresses = [str(entry["addr"]) for entry in placements]
    duplicates = sorted({addr for addr in addresses if addresses.count(addr) > 1})
    if duplicates:
        raise RuntimeError(f"duplicate atopile_address values: {duplicates}")
    if len(placements) != EXPECTED_COMPONENTS:
        raise RuntimeError(
            f"expected {EXPECTED_COMPONENTS} C4 footprints, found {len(placements)}"
        )
    placements.sort(key=lambda entry: str(entry["addr"]))
    return placements


def _read_snapshot(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise RuntimeError(f"unsupported C4 placement snapshot: {path}")
    placements = data.get("placements")
    if not isinstance(placements, list):
        raise RuntimeError(f"snapshot has no placements list: {path}")
    return data


def _compare(
    actual: list[dict[str, object]], expected: list[dict[str, object]]
) -> list[str]:
    actual_by_addr = {str(entry["addr"]): entry for entry in actual}
    expected_by_addr = {str(entry["addr"]): entry for entry in expected}
    errors: list[str] = []
    if set(actual_by_addr) != set(expected_by_addr):
        errors.append(
            "address set differs: "
            f"board-only={sorted(set(actual_by_addr) - set(expected_by_addr))}, "
            f"snapshot-only={sorted(set(expected_by_addr) - set(actual_by_addr))}"
        )
        return errors
    for addr in sorted(actual_by_addr):
        board_entry = actual_by_addr[addr]
        snapshot_entry = expected_by_addr[addr]
        for key in ("x", "y", "rot", "flip"):
            if board_entry.get(key) != snapshot_entry.get(key):
                errors.append(
                    f"{addr}.{key}: board={board_entry.get(key)!r}, "
                    f"snapshot={snapshot_entry.get(key)!r}"
                )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description=f"Backup all {EXPECTED_COMPONENTS} C4 placements"
    )
    parser.add_argument("--board", type=Path, default=DEFAULT_BOARD)
    parser.add_argument("--output", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument(
        "--replace",
        action="store_true",
        help="deliberately replace an existing accepted placement snapshot",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="compare the board with the existing snapshot without writing",
    )
    args = parser.parse_args()

    import pcbnew

    board_path = args.board.resolve()
    output = args.output.resolve()
    board = load_board(pcbnew, board_path)
    title = board.GetTitleBlock()
    if title.GetTitle() != "SmartPaddle Rigid PCB" or title.GetRevision() != "C4":
        print(
            "ERROR: refusing non-C4 board: "
            f"title={title.GetTitle()!r} revision={title.GetRevision()!r}",
            file=sys.stderr,
        )
        return 1

    try:
        placements = _collect(board, pcbnew)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.check_only:
        if not output.is_file():
            print(f"ERROR: placement snapshot does not exist: {output}", file=sys.stderr)
            return 1
        try:
            snapshot = _read_snapshot(output)
            expected = snapshot["placements"]
            errors = _compare(placements, expected)  # type: ignore[arg-type]
        except (KeyError, RuntimeError, ValueError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        if errors:
            print("C4 placement snapshot differs from board:", file=sys.stderr)
            for error in errors[:20]:
                print(f"  x {error}", file=sys.stderr)
            if len(errors) > 20:
                print(f"  ... and {len(errors) - 20} more", file=sys.stderr)
            return 1
        print(f"C4 placement snapshot OK: {len(placements)} transforms match {output}")
        return 0

    if output.exists() and not args.replace:
        print(
            f"ERROR: refusing to overwrite accepted snapshot: {output}; use --replace",
            file=sys.stderr,
        )
        return 2

    try:
        source_board = str(board_path.relative_to(ROOT))
    except ValueError:
        source_board = str(board_path)
    payload = {
        "schema_version": 1,
        "source_board": source_board,
        "source_board_sha256": hashlib.sha256(board_path.read_bytes()).hexdigest(),
        "component_count": len(placements),
        "placements": placements,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(output)
    print(f"C4 placement snapshot written: {len(placements)} transforms -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
