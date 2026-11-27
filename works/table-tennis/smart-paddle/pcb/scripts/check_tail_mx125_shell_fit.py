#!/usr/bin/env python3
# ===== 分区：导入/依赖 =====
"""把 KiCad 尾插（正反 5P）位反算到 SCAD，检查与拍柄内腔是否干涉。"""

from __future__ import annotations

import argparse
import math
import subprocess
import sys
from pathlib import Path

# ===== 分区：常量/配置 =====

ROOT = Path(__file__).resolve().parents[2]
BOARD = ROOT / "pcb" / "layouts" / "default" / "default.kicad_pcb"
OUT_DIR = ROOT / "pcb" / "output" / "tail_mx125_fit"
SCAD_PREVIEW = ROOT / "enclosure" / "_check_tail_mx125_fit.scad"
REFS = ("TAIL_MX125_F", "TAIL_MX125_B")

# Molex PicoBlade 53261-0571（与 .kicad_mod F.Fab / 资料一致）
FAB_HALF_X = 5.70
FAB_Y0 = -2.4
FAB_Y1 = 2.6
CONN_HEIGHT = 3.50
PCB_THICK = 0.80

# ===== 分区：私有成员 =====


def _kicad_to_scad(x: float, y: float, offset: float) -> tuple[float, float]:
    return x, offset - y


def _read_poses(board_path: Path) -> dict[str, tuple[float, float, float, bool]]:
    """ref → (x, y, rot_deg, on_back)."""
    try:
        import pcbnew
    except ImportError:
        return {
            "TAIL_MX125_F": (0.0, 87.1, 0.0, False),
            "TAIL_MX125_B": (0.0, 87.1, 0.0, True),
        }
    board = pcbnew.LoadBoard(str(board_path))
    out: dict[str, tuple[float, float, float, bool]] = {}
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref not in REFS:
            continue
        on_back = fp.IsFlipped() if hasattr(fp, "IsFlipped") else False
        out[ref] = (
            pcbnew.ToMM(fp.GetPosition().x),
            pcbnew.ToMM(fp.GetPosition().y),
            fp.GetOrientationDegrees(),
            on_back,
        )
    if not out:
        raise SystemExit(f"板上未找到 {REFS}")
    return out


def _shell_metrics_via_openscad(ys: list[float]) -> dict[float, dict[str, float]]:
    enc = ROOT / "enclosure"
    tmp = enc / "_tmp_tail_fit_metrics.scad"
    ys_lit = ",".join(str(y) for y in ys)
    tmp.write_text(
        f"""include <parameters.scad>
include <bezier_profile.scad>
USE_BEZIER_PROFILES = true;
function fl_half_w(t) =
    let(waist_t = 0.32, n = handle_neck_w/2, b = handle_butt_w/2)
    n + (b - n) * (1 - cos(180 * max(0, min(1, (t - waist_t) / max(1e-9, 1 - waist_t))))) / 2;
function envelope_hx(y) =
    y >= shoulder_top_y ? blade_hx(y) :
    y >= handle_join_y ?
        blade_hx(shoulder_top_y) + (handle_neck_w/2 - blade_hx(shoulder_top_y)) *
            ((shoulder_top_y - y) / max(1e-9, shoulder_top_y - handle_join_y)) :
    y >= handle_butt_y ? fl_half_w((y - handle_join_y) / (-handle_length)) : 0;
ys = [{ys_lit}];
for (y = ys)
  echo(str("MET|", y, "|", bezier_half_z_at(y), "|", envelope_hx(y), "|",
           bezier_half_z_at(y) - wall_t - handle_cavity_inset, "|",
           envelope_hx(y) - wall_t - handle_cavity_inset));
cube(0.01);
""",
        encoding="utf-8",
    )
    proc = subprocess.run(
        ["openscad", "-o", "/tmp/tail_fit_metrics.stl", str(tmp.name)],
        cwd=str(enc),
        capture_output=True,
        text=True,
    )
    tmp.unlink(missing_ok=True)
    out: dict[float, dict[str, float]] = {}
    for line in (proc.stderr or "").splitlines():
        if "MET|" not in line:
            continue
        try:
            payload = line.split("MET|", 1)[1].rstrip('"')
            y_s, hz, hx, cav_hz, cav_hx = payload.split("|")
            y = float(y_s)
            out[y] = {
                "hz": float(hz),
                "hx": float(hx) if hx != "undef" else float("nan"),
                "cav_hz": float(cav_hz),
                "cav_hx": float(cav_hx) if cav_hx != "undef" else float("nan"),
            }
        except ValueError:
            continue
    return out


def _write_preview_scad(
    *,
    sx0: float,
    sx1: float,
    sy0: float,
    sy1: float,
    z_f0: float,
    z_f1: float,
    z_b0: float,
    z_b1: float,
) -> None:
    cx = (sx0 + sx1) / 2
    cy = (sy0 + sy1) / 2
    dx = sx1 - sx0
    dy = sy1 - sy0
    SCAD_PREVIEW.write_text(
        f"""// AUTO: MX1.25 正反 5P vs 拍柄 — check_tail_mx125_shell_fit.py
include <parameters.scad>
include <bezier_profile.scad>
USE_BEZIER_PROFILES = true;

module conn_bbox(z0, z1, c) {{
    color(c, 0.85)
        translate([{cx:.3f}, {cy:.3f}, (z0 + z1) / 2])
            cube([{dx:.3f}, {dy:.3f}, z1 - z0], center = true);
}}

conn_bbox({z_f0:.3f}, {z_f1:.3f}, "red");
conn_bbox({z_b0:.3f}, {z_b1:.3f}, "orange");
""",
        encoding="utf-8",
    )


# ===== 分区：公开 API =====


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--board", type=Path, default=BOARD)
    args = parser.parse_args()

    sys.path.insert(0, str(ROOT / "pcb"))
    from tools.mech_geometry import SCAD_TO_KICAD_Y_OFFSET  # noqa: E402

    poses = _read_poses(args.board.resolve())
    # 用正面位姿估算 Fab（正反同原点）
    ox, oy, rot, _ = poses.get("TAIL_MX125_F") or next(iter(poses.values()))
    if abs(rot) > 1e-3 and abs(abs(rot) - 180) > 1e-3:
        print(f"警告: rot={rot}°，按 Fab 轴对齐估算")

    kx0, kx1 = ox - FAB_HALF_X, ox + FAB_HALF_X
    ky0, ky1 = oy + FAB_Y0, oy + FAB_Y1
    corners = [
        _kicad_to_scad(kx0, ky0, SCAD_TO_KICAD_Y_OFFSET),
        _kicad_to_scad(kx0, ky1, SCAD_TO_KICAD_Y_OFFSET),
        _kicad_to_scad(kx1, ky0, SCAD_TO_KICAD_Y_OFFSET),
        _kicad_to_scad(kx1, ky1, SCAD_TO_KICAD_Y_OFFSET),
    ]
    xs = [c[0] for c in corners]
    ys = [c[1] for c in corners]
    sx0, sx1 = min(xs), max(xs)
    sy0, sy1 = min(ys), max(ys)

    pcb_half = PCB_THICK / 2
    z_f0, z_f1 = pcb_half, pcb_half + CONN_HEIGHT
    z_b0, z_b1 = -(pcb_half + CONN_HEIGHT), -pcb_half

    sample_ys = sorted({round(sy0, 3), round((sy0 + sy1) / 2, 3), round(sy1, 3)})
    metrics = _shell_metrics_via_openscad(sample_ys)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = OUT_DIR / "fit_report.txt"
    lines: list[str] = []
    for ref, (x, y, r, back) in sorted(poses.items()):
        lines.append(f"{ref} KiCad=({x:.3f},{y:.3f}) rot={r:.1f} back={back}")
    lines.append(
        f"Fab SCAD X[{sx0:.3f},{sx1:.3f}] Y[{sy0:.3f},{sy1:.3f}] "
        f"Z_F[{z_f0:.3f},{z_f1:.3f}] Z_B[{z_b0:.3f},{z_b1:.3f}]"
    )
    slot_clr = 9.00 - FAB_HALF_X
    lines.append(
        f"相对 PCB 槽侧壁间隙 ≈ {slot_clr:.3f} mm/侧（Fab 半宽 {FAB_HALF_X}）"
    )

    worst_x = math.inf
    worst_z = math.inf
    need_z = max(abs(z_f1), abs(z_b0))
    for y in sample_ys:
        m = None
        for k, v in metrics.items():
            if abs(k - y) < 0.05:
                m = v
                break
        if not m or math.isnan(m["cav_hx"]):
            lines.append(f"Y={y:.3f}: 无法取得 shell 内腔尺寸")
            continue
        gap_x = m["cav_hx"] - FAB_HALF_X
        gap_z = m["cav_hz"] - need_z
        worst_x = min(worst_x, gap_x)
        worst_z = min(worst_z, gap_z)
        lines.append(
            f"Y={y:.3f}: cav_hx={m['cav_hx']:.3f} cav_hz={m['cav_hz']:.3f} | "
            f"间隙X={gap_x:+.3f} 间隙Z={gap_z:+.3f}"
        )

    lines.append("")
    if worst_x < 0 or worst_z < 0:
        lines.append(
            f"结论: 仍有干涉风险（X={worst_x:+.3f} Z={worst_z:+.3f}）"
        )
        rc = 2
    else:
        lines.append(
            f"结论: 相对拍柄内腔 OK（X≥{worst_x:+.3f} Z≥{worst_z:+.3f}）"
        )
        rc = 0

    text = "\n".join(lines) + "\n"
    report.write_text(text, encoding="utf-8")
    _write_preview_scad(
        sx0=sx0, sx1=sx1, sy0=sy0, sy1=sy1,
        z_f0=z_f0, z_f1=z_f1, z_b0=z_b0, z_b1=z_b1,
    )
    print(text)
    print(f"报告 → {report}")
    print(f"预览 → {SCAD_PREVIEW}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
