#!/usr/bin/env python3
# ===== 分区：导入/依赖 =====
from __future__ import annotations

import json
import logging
import subprocess
import sys
from pathlib import Path


# ===== 分区：常量/配置 =====
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from parts.standard_parts import PartsCatalog
from simulation.part_models import simulate_catalog

LOGGER = logging.getLogger("simulate_by_parts")
OUT_DIR = ROOT / "output" / "simulation"
WEB_REPORT = ROOT / "web" / "parts-report.json"
FREECAD_SCRIPT = ROOT / "cad" / "build_parts_freecad.py"


# ===== 分区：业务逻辑 =====
def _run_freecad() -> dict:
    command = ["bash", str(ROOT / "scripts" / "freecad.sh"), str(FREECAD_SCRIPT)]
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        LOGGER.error("启动 FreeCAD 失败: %s", exc)
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if completed.returncode != 0:
        LOGGER.error("FreeCAD 按零件建模失败: %s", completed.stderr.strip() or completed.stdout.strip())
        return {
            "ok": False,
            "error": completed.stderr.strip() or completed.stdout.strip() or f"exit {completed.returncode}",
        }
    report_path = OUT_DIR / "freecad-parts.json"
    assembly = OUT_DIR / "drive_module.step"
    if not report_path.is_file() or not assembly.is_file():
        LOGGER.error("FreeCAD 未写出 STEP 装配。stdout=%s stderr=%s", completed.stdout.strip(), completed.stderr.strip())
        return {
            "ok": False,
            "error": completed.stderr.strip() or completed.stdout.strip() or "missing STEP output",
        }
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    payload["ok"] = True
    return payload


# ===== 分区：公开 API =====
def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    catalog = PartsCatalog.from_json_path()
    report = simulate_catalog(catalog)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report["cad"]["freecad"] = _run_freecad()
    text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    (OUT_DIR / "parts-report.json").write_text(text, encoding="utf-8")
    WEB_REPORT.write_text(text, encoding="utf-8")
    print(text)
    cad_ok = bool(report.get("cad", {}).get("freecad", {}).get("ok"))
    return 0 if report["ok"] and cad_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
