#!/usr/bin/env python3
"""
将 M7 无缝合体 STL 正交投影为二维轮廓图，并与 parameters.scad 做尺寸/对称性分析。

坐标系（与 OpenSCAD 一致）:
  X — 拍宽
  Y — 拍长（拍尖 ≈ +78.5 mm，柄底 ≈ -178.5 mm）
  Z — 厚度（分型面 Z=0；前壳 Z≥0，后壳 Z≤0）

输出:
  <out>/<name>/top.png      俯视 XY（贴热床轮廓）
  <out>/<name>/front.png    正视 XZ（沿 +Y 看）
  <out>/<name>/side.png     侧视 YZ（沿 +X 看）
  <out>/<name>/width_profile.png
  report.json / report.md
"""

from __future__ import annotations

import argparse
import json
import re
import importlib.util
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from matplotlib.collections import PolyCollection
# 视图: (水平轴, 垂直轴, 深度轴) — 相机在深度轴正方向看向原点，画家算法远→近
VIEWS: dict[str, tuple[int, int, int, str]] = {
    "top": (0, 1, 2, "Top XY — print STL (bezier profiles)"),
    "front": (0, 2, 1, "Front XZ — print STL"),
    "side": (1, 2, 0, "Side YZ — print STL"),
}

BED_MM = 256
BED_MARGIN_MM = 5


@dataclass
class ParamSpec:
    blade_width: float
    blade_tip_y: float
    handle_join_y: float
    handle_butt_y: float
    handle_neck_w: float
    handle_butt_w: float
    blade_core_t: float
    handle_thickness: float

    @property
    def total_length_y(self) -> float:
        return self.blade_tip_y - self.handle_butt_y


def parse_parameters(scad_path: Path) -> ParamSpec:
    text = scad_path.read_text(encoding="utf-8")
    keys = [
        "blade_width",
        "blade_tip_y",
        "handle_join_y",
        "handle_butt_y",
        "handle_neck_w",
        "handle_butt_w",
        "blade_core_t",
        "handle_thickness",
    ]
    vals: dict[str, float] = {}
    for k in keys:
        m = re.search(rf"^{k}\s*=\s*([-\d.]+)\s*;", text, re.M)
        if not m:
            raise ValueError(f"parameters.scad 缺少 {k}")
        vals[k] = float(m.group(1))
    return ParamSpec(**vals)  # type: ignore[arg-type]


def load_mesh(path: Path) -> trimesh.Trimesh:
    mesh = trimesh.load(path, force="mesh")
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    if not isinstance(mesh, trimesh.Trimesh):
        raise TypeError(f"无法作为三角网格读取: {path}")
    return mesh


def bbox_dict(mesh: trimesh.Trimesh) -> dict[str, float]:
    lo, hi = mesh.bounds
    return {
        "x_min": float(lo[0]),
        "x_max": float(hi[0]),
        "y_min": float(lo[1]),
        "y_max": float(hi[1]),
        "z_min": float(lo[2]),
        "z_max": float(hi[2]),
        "size_x": float(hi[0] - lo[0]),
        "size_y": float(hi[1] - lo[1]),
        "size_z": float(hi[2] - lo[2]),
    }


def visible_face_mask(mesh: trimesh.Trimesh, k_ax: int) -> np.ndarray:
    """朝向相机的面（正交投影轮廓用）。"""
    view = np.zeros(3, dtype=np.float64)
    view[k_ax] = -1.0
    return (mesh.face_normals @ view) < -1e-4


def render_silhouette(
    mesh: trimesh.Trimesh,
    i_ax: int,
    j_ax: int,
    k_ax: int,
    out_path: Path,
    title: str,
    dpi: int = 160,
) -> None:
    """
    正交投影：背面剔除 + 按深度排序填充（空壳 STL 侧视必需）。
    """
    verts = mesh.vertices
    faces = mesh.faces
    vis = visible_face_mask(mesh, k_ax)
    tris: list[tuple[float, np.ndarray]] = []
    for fi, f in enumerate(faces):
        if not vis[fi]:
            continue
        tri_ij = verts[f][:, [i_ax, j_ax]]
        depth = float(verts[f][:, k_ax].mean())
        tris.append((depth, tri_ij))
    tris.sort(key=lambda t: t[0], reverse=True)
    polys = [t[1] for t in tris]

    fig, ax = plt.subplots(figsize=(6, 8), dpi=dpi)
    ax.set_aspect("equal", adjustable="box")
    ax.set_title(title, fontsize=9)
    ax.add_collection(
        PolyCollection(
            polys,
            facecolor="#c9a227",
            edgecolor="none",
            linewidths=0,
            antialiased=True,
        )
    )
    ax.autoscale()
    ax.grid(True, alpha=0.25, linewidth=0.5)
    ax.set_xlabel(["X", "Y", "Z"][i_ax] + " (mm)")
    ax.set_ylabel(["X", "Y", "Z"][j_ax] + " (mm)")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, facecolor="#f5f0e6")
    plt.close(fig)


def _load_bezier_sampling():
    path = Path(__file__).resolve().parents[1] / "scripts/bezier_to_openscad.py"
    spec = importlib.util.spec_from_file_location("bezier_to_openscad", path)
    if spec is None or spec.loader is None:
        raise ImportError("bezier_to_openscad.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def width_profile_mesh_debug(mesh: trimesh.Trimesh, n_bins: int = 120) -> dict[str, Any]:
    """STL 全部顶点按 Y 分箱 — 含内腔/螺柱，不能当拍形轮廓。"""
    x, y = mesh.vertices[:, 0], mesh.vertices[:, 1]
    y0, y1 = float(y.min()), float(y.max())
    edges = np.linspace(y0, y1, n_bins + 1)
    centers: list[float] = []
    half_w_pos: list[float] = []
    half_w_neg: list[float] = []
    for a, b in zip(edges[:-1], edges[1:]):
        mask = (y >= a) & (y < b)
        if not np.any(mask):
            continue
        xs = x[mask]
        centers.append((a + b) / 2)
        half_w_pos.append(float(xs[xs >= 0].max()) if np.any(xs >= 0) else 0.0)
        half_w_neg.append(float(-xs[xs < 0].min()) if np.any(xs < 0) else 0.0)
    centers_a = np.array(centers)
    hp = np.array(half_w_pos)
    hn = np.array(half_w_neg)
    asym = np.abs(hp - hn)
    return {
        "y_centers": centers_a.tolist(),
        "half_width_pos_x": hp.tolist(),
        "half_width_neg_x": hn.tolist(),
        "max_asymmetry_mm": float(asym.max()) if len(asym) else 0.0,
        "mean_asymmetry_mm": float(asym.mean()) if len(asym) else 0.0,
    }


def thickness_along_y(mesh: trimesh.Trimesh, n_bins: int = 120) -> dict[str, float]:
    """侧视：每个 Y  bin 的 Z 跨度。"""
    y, z = mesh.vertices[:, 1], mesh.vertices[:, 2]
    y0, y1 = float(y.min()), float(y.max())
    edges = np.linspace(y0, y1, n_bins + 1)
    out: dict[str, float] = {}
    for a, b in zip(edges[:-1], edges[1:]):
        mask = (y >= a) & (y < b)
        if not np.any(mask):
            continue
        zm = z[mask]
        out[f"{(a+b)/2:.1f}"] = float(zm.max() - zm.min())
    return out


def half_shell_thickness_z(mesh: trimesh.Trimesh, which: str = "auto") -> float:
    """半壳在各自一侧的最大 Z 跨度（忽略跨分型面的细小几何）。"""
    z = mesh.vertices[:, 2]
    if which == "front" or (which == "auto" and float(z.max()) > abs(float(z.min()))):
        zs = z[z >= -0.05]
        return float(zs.max() - zs.min()) if len(zs) else float(z.max() - z.min())
    if which == "back" or which == "auto":
        zs = z[z <= 0.05]
        return float(zs.max() - zs.min()) if len(zs) else float(z.max() - z.min())
    return float(z.max() - z.min())


def max_width_in_y_band(mesh: trimesh.Trimesh, y_min: float, y_max: float) -> dict[str, Any]:
    y, x = mesh.vertices[:, 1], mesh.vertices[:, 0]
    m = (y >= y_min) & (y <= y_max)
    if not np.any(m):
        return {"found": False, "y_band": [y_min, y_max]}
    xs = x[m]
    return {
        "found": True,
        "y_band": [y_min, y_max],
        "full_width_x": float(xs.max() - xs.min()),
        "half_width_x": float(max(xs.max(), -xs.min())),
    }


def sample_at_y(mesh: trimesh.Trimesh, y_target: float, tol: float = 2.0) -> dict[str, float]:
    y, x, z = mesh.vertices[:, 1], mesh.vertices[:, 0], mesh.vertices[:, 2]
    m = np.abs(y - y_target) < tol
    if not np.any(m):
        return {"y": y_target, "found": False}
    xs, zs = x[m], z[m]
    return {
        "y": y_target,
        "found": True,
        "half_width_x": float(max(xs.max(), -xs.min())),
        "full_width_x": float(xs.max() - xs.min()),
        "thickness_z": float(zs.max() - zs.min()),
    }


def run_checks(
    mesh: trimesh.Trimesh,
    bbox: dict[str, float],
    prof: dict[str, Any],
    spec: ParamSpec,
    shell_kind: str = "auto",
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    tol_len, tol_w, tol_t = 6.0, 2.5, 2.5

    def add(name: str, expected: float, actual: float, tol: float) -> None:
        delta = actual - expected
        checks.append(
            {
                "name": name,
                "expected": expected,
                "actual": round(actual, 2),
                "delta": round(delta, 2),
                "tolerance": tol,
                "ok": abs(delta) <= tol,
            }
        )

    add("总长度 Y", spec.total_length_y, bbox["size_y"], tol_len)
    add("包络宽度 X", spec.blade_width, bbox["size_x"], tol_w)

    half_t = half_shell_thickness_z(mesh, shell_kind)
    add("半壳厚度 Z", spec.handle_thickness / 2, half_t, tol_t)

    hp = np.array(prof["half_width_pos_x"])
    hn = np.array(prof["half_width_neg_x"])
    max_full_w = float((hp + hn).max()) if len(hp) else bbox["size_x"]
    add("俯视最大全宽 X", spec.blade_width, max_full_w, tol_w)

    # 柄颈：略低于 join，避免采到拍面肩部宽轮廓
    neck = sample_at_y(mesh, spec.handle_join_y - 8.0, tol=3.0)
    # 柄尾：在柄底向上 10–25 mm 取 FL 最宽处（避免端盖收窄）
    y_lo = float(mesh.vertices[:, 1].min())
    butt = max_width_in_y_band(mesh, y_lo + 8.0, y_lo + 28.0)
    if neck.get("found"):
        add("柄颈区全宽 X", spec.handle_neck_w, neck["full_width_x"], tol_w)
    if butt.get("found"):
        add("柄尾 FL 区全宽 X", spec.handle_butt_w, butt["full_width_x"], tol_w + 2)

    checks.append(
        {
            "name": "俯视左右对称 (最大半宽差)",
            "expected": 0,
            "actual": round(prof["max_asymmetry_mm"], 2),
            "tolerance": 1.5,
            "ok": prof["max_asymmetry_mm"] <= 1.5,
        }
    )

    longest = max(bbox["size_x"], bbox["size_y"])
    bed_ok = longest <= BED_MM
    checks.append(
        {
            "name": f"热床最长边 ≤ {BED_MM} mm（可旋转摆放）",
            "expected": BED_MM,
            "actual": round(longest, 2),
            "tolerance": 0,
            "ok": bed_ok,
        }
    )
    return checks


def plot_width_profile(
    design_prof: dict[str, Any],
    spec: ParamSpec,
    out_path: Path,
    mesh_debug: dict[str, Any] | None = None,
) -> None:
    y = np.array(design_prof["y_centers"])
    hw = np.array(design_prof["half_width_pos_x"])
    fig, ax = plt.subplots(figsize=(7, 4), dpi=140)
    ax.fill_between(y, -hw, hw, color="#e2bf6e", alpha=0.35, label="design silhouette")
    ax.plot(y, hw, color="#b45309", lw=1.8, label="+X design")
    ax.plot(y, -hw, color="#1d4ed8", lw=1.8, label="-X design")
    if mesh_debug:
        ym = np.array(mesh_debug["y_centers"])
        hm = np.array(mesh_debug["half_width_pos_x"])
        ax.plot(ym, hm, color="#999", lw=0.8, ls=":", label="STL verts (wrong)")
    ax.axvline(spec.blade_tip_y, color="#888", ls="--", lw=0.8, label="tip Y")
    ax.axvline(spec.handle_join_y, color="#888", ls=":", lw=0.8, label="join Y")
    ax.axvline(spec.handle_butt_y, color="#888", ls="-.", lw=0.8, label="butt Y")
    ax.set_xlabel("Y (mm)")
    ax.set_ylabel("Half-width |X| (mm)")
    ax.set_title("Paddle silhouette half-width (Bezier design)")
    ax.legend(fontsize=7, loc="upper right")
    ax.grid(alpha=0.3)
    ax.set_ylim(bottom=-85, top=85)
    fig.tight_layout()
    fig.savefig(out_path, facecolor="#f5f0e6")
    plt.close(fig)


def analyze_one(
    mesh: trimesh.Trimesh,
    name: str,
    out_root: Path,
    spec: ParamSpec,
    shell_kind: str = "auto",
) -> dict[str, Any]:
    out_dir = out_root / name
    out_dir.mkdir(parents=True, exist_ok=True)

    bbox = bbox_dict(mesh)
    prof = width_profile_mesh_debug(mesh)

    for view_key, (i_ax, j_ax, k_ax, desc) in VIEWS.items():
        render_silhouette(
            mesh,
            i_ax,
            j_ax,
            k_ax,
            out_dir / f"{view_key}.png",
            f"{name} — {desc}",
        )

    plot_width_profile(prof, spec, out_dir / "width_profile.png")

    checks = run_checks(mesh, bbox, prof, spec, shell_kind=shell_kind)
    thickness = thickness_along_y(mesh)

    report: dict[str, Any] = {
        "name": name,
        "bbox_mm": bbox,
        "width_profile_summary": {
            "max_asymmetry_mm": prof["max_asymmetry_mm"],
            "mean_asymmetry_mm": prof["mean_asymmetry_mm"],
        },
        "samples": {
            "tip_y": sample_at_y(mesh, spec.blade_tip_y),
            "join_y": sample_at_y(mesh, spec.handle_join_y),
            "butt_y": sample_at_y(mesh, spec.handle_butt_y),
        },
        "thickness_along_y_mm": thickness,
        "checks": checks,
        "all_checks_ok": all(c.get("ok", False) for c in checks),
    }

    (out_dir / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return report


def write_markdown(
    reports: list[dict[str, Any]],
    spec: ParamSpec,
    out_root: Path,
    paths: list[Path],
) -> None:
    lines = [
        "# STL 二维投影分析报告",
        "",
        "由 `scripts/analyze_stl_views.py` 自动生成。",
        "",
        "## 坐标系",
        "",
        "| 轴 | 含义 |",
        "|----|------|",
        "| X | 拍宽 |",
        "| Y | 拍长（+ 为拍尖方向） |",
        "| Z | 厚度（分型面 Z=0） |",
        "",
        f"## 设计参数 (`parameters.scad`)",
        "",
        f"- 标称总长: **{spec.total_length_y:.1f} mm**",
        f"- 标称拍宽: **{spec.blade_width:.1f} mm**",
        f"- 柄颈 / 柄尾宽: **{spec.handle_neck_w} / {spec.handle_butt_w} mm**",
        "",
    ]
    for r in reports:
        lines.append(f"## {r['name']}")
        lines.append("")
        b = r["bbox_mm"]
        lines.append(
            f"包络: X={b['size_x']:.1f} Y={b['size_y']:.1f} Z={b['size_z']:.1f} mm"
        )
        lines.append("")
        lines.append("| 检查项 | 期望 | 实测 | Δ | 通过 |")
        lines.append("|--------|------|------|---|------|")
        for c in r["checks"]:
            ok = "✓" if c.get("ok") else "✗"
            exp = c.get("expected", "—")
            act = c.get("actual", "—")
            delta = c.get("delta", "—")
            lines.append(f"| {c['name']} | {exp} | {act} | {delta} | {ok} |")
        lines.append("")
        lines.append(f"**全部通过:** {'是' if r['all_checks_ok'] else '否 — 见上表 ✗'}")
        lines.append("")
        sub = out_root / r["name"]
        lines.append("视图文件:")
        for v in ("top", "front", "side", "width_profile"):
            lines.append(f"- `{sub / (v + '.png')}`")
        lines.append("")

    if len(reports) >= 2:
        lines.append("## 输入 STL")
        for p in paths:
            lines.append(f"- `{p}`")
        lines.append("")

    (out_root / "SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="STL → 正交二维视图 + 尺寸分析")
    parser.add_argument(
        "--front",
        type=Path,
        default=root / "enclosure/stl/paddle_m7_monolithic_front.stl",
    )
    parser.add_argument(
        "--back",
        type=Path,
        default=root / "enclosure/stl/paddle_m7_monolithic_back.stl",
    )
    parser.add_argument(
        "--params",
        type=Path,
        default=root / "enclosure/parameters.scad",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=root / "enclosure/analysis",
    )
    parser.add_argument("--no-back", action="store_true", help="只分析前壳")
    args = parser.parse_args()

    if not args.front.is_file():
        print(f"缺少 STL: {args.front}\n请先运行 ./scripts/export-stl.sh", file=sys.stderr)
        return 1

    spec = parse_parameters(args.params)
    args.out.mkdir(parents=True, exist_ok=True)

    paths: list[Path] = [args.front]
    reports: list[dict[str, Any]] = []

    print(f"参数: 总长 {spec.total_length_y} mm, 拍宽 {spec.blade_width} mm")
    print(f"输出: {args.out}\n")

    front_mesh = load_mesh(args.front)
    reports.append(
        analyze_one(front_mesh, "paddle_m7_monolithic_front", args.out, spec, shell_kind="front")
    )
    print(f"✓ M7 正面合体件 → {args.out / 'paddle_m7_monolithic_front'}")

    if not args.no_back and args.back.is_file():
        paths.append(args.back)
        back_mesh = load_mesh(args.back)
        reports.append(
            analyze_one(back_mesh, "paddle_m7_monolithic_back", args.out, spec, shell_kind="back")
        )
        print(f"✓ M7 背面合体件 → {args.out / 'paddle_m7_monolithic_back'}")

        asm = trimesh.util.concatenate([front_mesh, back_mesh])
        reports.append(
            analyze_one(asm, "assembly_envelope", args.out, spec, shell_kind="auto")
        )
        print(f"✓ 合拢包络 → {args.out / 'assembly_envelope'}")
    elif not args.no_back:
        print(f"跳过: 未找到后壳 {args.back}", file=sys.stderr)

    write_markdown(reports, spec, args.out, paths)

    all_ok = all(r["all_checks_ok"] for r in reports)
    print(f"\n汇总: {args.out / 'SUMMARY.md'}")
    print(f"检查: {'全部通过' if all_ok else '存在未通过项 — 打开 SUMMARY.md'}")
    return 0 if all_ok else 2


if __name__ == "__main__":
    sys.exit(main())
