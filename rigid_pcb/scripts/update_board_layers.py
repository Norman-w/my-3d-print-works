#!/usr/bin/env python3
"""Run the incremental KiCad update scripts in a safe order."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent


def run(script: str, board: Path | None, extra: list[str] | None = None) -> None:
    cmd = [sys.executable, str(HERE / script)]
    if board is not None:
        cmd.extend(["--board", str(board)])
    if extra:
        cmd.extend(extra)
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--board", type=Path)
    parser.add_argument(
        "--force-placement",
        action="store_true",
        help="re-apply scaffold placement to already moved atopile footprints",
    )
    args = parser.parse_args()

    run("update_reference_lines.py", args.board)
    run("update_cutouts.py", args.board)
    run("normalize_kicad_for_atopile.py", args.board)
    run("place_atopile_scaffold.py", args.board, ["--force"] if args.force_placement else None)


if __name__ == "__main__":
    main()
