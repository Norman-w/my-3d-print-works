#!/usr/bin/env python3
"""
从 web 贝塞尔 JSON 绘制与 Shape 页一致的 2D 轮廓（非 OpenSCAD STL）。

与浏览器中一致的数据源:
  - localStorage 键 smartpaddle-bezier-*（若提供 --from-browser 则跳过）
  - 默认: web/src/data/userBezierProfiles.json

输出: enclosure/analysis/bezier_design/
    front_silhouette.png   — 拍面+拍柄合拢
    blade_silhouette.png   — 仅拍面（Y ≥ join，与 OpenSCAD 裁剪一致）
    handle_silhouette.png  — 仅拍柄
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

def _xy(p: dict[str, float]) -> tuple[float, float]:
    return p["x"], p["y"]


def cubic_at(p0, p1, p2, p3, t: float) -> tuple[float, float]:
    a, b, c, d = _xy(p0), _xy(p1), _xy(p2), _xy(p3)
    u = 1 - t
    x = u**3 * a[0] + 3 * u**2 * t * b[0] + 3 * u * t**2 * c[0] + t**3 * d[0]
    y = u**3 * a[1] + 3 * u**2 * t * b[1] + 3 * u * t**2 * c[1] + t**3 * d[1]
    return x, y


def sample_profile(profile: dict[str, Any], steps_per_seg: int = 32) -> np.ndarray:
    pts: list[tuple[float, float]] = [(profile["start"]["x"], profile["start"]["y"])]
    p0 = profile["start"]
    for seg in profile["segments"]:
        p1, p2, p3 = seg["cp1"], seg["cp2"], seg["end"]
        for i in range(1, steps_per_seg + 1):
            t = i / steps_per_seg
            pts.append(cubic_at(p0, p1, p2, p3, t))
        p0 = p3
    return np.array(pts)


def mirror_x(pts: np.ndarray) -> np.ndarray:
    m = pts.copy()
    m[:, 0] *= -1
    return m[::-1]


def clip_open_polyline_at_min_y(pts: np.ndarray, y_min: float) -> np.ndarray:
    """Match paddleFromBezier.ts / bezier_to_openscad.py."""
    if len(pts) < 2:
        return pts
    out: list[tuple[float, float]] = []
    if pts[0, 1] >= y_min:
        out.append((float(pts[0, 0]), float(pts[0, 1])))
    for i in range(1, len(pts)):
        ax, ay = float(pts[i - 1, 0]), float(pts[i - 1, 1])
        bx, by = float(pts[i, 0]), float(pts[i, 1])
        if ay >= y_min and by >= y_min:
            out.append((bx, by))
        elif ay >= y_min and by < y_min:
            t = (y_min - ay) / (by - ay)
            out.append((ax + t * (bx - ax), y_min))
        elif ay < y_min and by >= y_min:
            t = (y_min - ay) / (by - ay)
            out.append((ax + t * (bx - ax), y_min))
            out.append((bx, by))
    return np.array(out) if len(out) >= 2 else pts


def right_half_from_profile(profile: dict[str, Any], y_min: float | None = None) -> np.ndarray:
    pts = sample_profile(profile)
    if y_min is not None:
        pts = clip_open_polyline_at_min_y(pts, y_min)
    right = pts.copy()
    right[:, 0] = np.maximum(right[:, 0], 0.0)
    return right


def closed_silhouette(right: np.ndarray) -> np.ndarray:
    left = mirror_x(right)
    return np.vstack([right, left, right[:1]])


def closed_front_silhouette(blade: dict, handle: dict, join_y: float) -> np.ndarray:
    """Full blade outline (含鬓角) + handle; matches OpenSCAD bezier_blade_solid."""
    blade_r = right_half_from_profile(blade)
    handle_r = right_half_from_profile(handle)
    combined = np.vstack([blade_r, handle_r[1:]])
    return closed_silhouette(combined)


def save_silhouette(
    pts: np.ndarray,
    path: Path,
    title: str,
    facecolor: str = "#e2bf6e",
    edgecolor: str = "#8a7030",
    join_y: float | None = None,
) -> None:
    fig, ax = plt.subplots(figsize=(5, 9), dpi=140)
    ax.fill(pts[:, 0], pts[:, 1], facecolor=facecolor, edgecolor=edgecolor, lw=1.2)
    if join_y is not None:
        ax.axhline(join_y, color="#c62828", ls="--", lw=0.9, alpha=0.7, label=f"join Y={join_y:.1f}")
        ax.legend(fontsize=7, loc="upper right")
    ax.set_aspect("equal")
    ax.set_title(title)
    ax.grid(alpha=0.3)
    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Y (mm)")
    fig.tight_layout()
    fig.savefig(path, facecolor="#f5f0e6")
    plt.close(fig)


def plot_path(ax, pts: np.ndarray, color: str, label: str, mirror: bool = False) -> None:
    ax.plot(pts[:, 0], pts[:, 1], color=color, lw=2, label=label)
    if mirror:
        ax.plot(-pts[:, 0], pts[:, 1], color=color, lw=2, alpha=0.85)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--json",
        type=Path,
        default=root / "web/src/data/userBezierProfiles.json",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=root / "enclosure/analysis/bezier_design",
    )
    args = parser.parse_args()

    if not args.json.is_file():
        print(f"缺少 {args.json}", file=sys.stderr)
        return 1

    data = json.loads(args.json.read_text(encoding="utf-8"))
    args.out.mkdir(parents=True, exist_ok=True)

    blade = data["blade-front"]
    handle = data["handle-front"]
    side = data.get("side")
    bottom = data.get("handle-bottom")
    join_y = float(handle["start"]["y"])

    # 合拢 + 分件 silhouette（拍面在 join 处裁剪，与 OpenSCAD BEZIER_JOIN_Y 一致）
    save_silhouette(
        closed_front_silhouette(blade, handle, join_y),
        args.out / "front_silhouette.png",
        "Bezier: front silhouette (blade + handle)",
        join_y=join_y,
    )
    save_silhouette(
        closed_silhouette(right_half_from_profile(blade, y_min=join_y)),
        args.out / "blade_silhouette.png",
        "Bezier: blade only (front, Y ≥ join)",
        facecolor="#e2bf6e",
        edgecolor="#8a7030",
        join_y=join_y,
    )
    save_silhouette(
        closed_silhouette(right_half_from_profile(handle)),
        args.out / "handle_silhouette.png",
        "Bezier: handle only (front)",
        facecolor="#5d4037",
        edgecolor="#3e2723",
    )

    fig, ax = plt.subplots(figsize=(5, 9), dpi=140)
    sil = closed_front_silhouette(blade, handle, join_y)
    ax.fill(sil[:, 0], sil[:, 1], facecolor="#e2bf6e", edgecolor="#8a7030", lw=1.2, alpha=0.35)
    blade_only = closed_silhouette(right_half_from_profile(blade, y_min=join_y))
    handle_only = closed_silhouette(right_half_from_profile(handle))
    ax.fill(blade_only[:, 0], blade_only[:, 1], facecolor="#ff1744", edgecolor="#b71c1c", lw=1.0, alpha=0.45)
    ax.fill(handle_only[:, 0], handle_only[:, 1], facecolor="#00acc1", edgecolor="#006064", lw=1.0, alpha=0.45)
    ax.axhline(join_y, color="#c62828", ls="--", lw=0.9, alpha=0.7)
    ax.set_aspect("equal")
    ax.set_title("Bezier: blade + handle (split preview)")
    ax.grid(alpha=0.3)
    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Y (mm)")
    fig.tight_layout()
    fig.savefig(args.out / "silhouette_split.png", facecolor="#f5f0e6")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(4, 9), dpi=140)
    plot_path(ax, sample_profile(blade), "#ff1744", "blade-front")
    plot_path(ax, sample_profile(handle), "#00e5ff", "handle-front")
    ax.set_aspect("equal")
    ax.set_title("Bezier: right half profiles")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(args.out / "front_profiles.png", facecolor="#f5f0e6")
    plt.close(fig)

    if side:
        pts = sample_profile(side)
        fig, ax = plt.subplots(figsize=(4, 9), dpi=140)
        plot_path(ax, pts, "#1565c0", "side (+X half-thickness)", mirror=True)
        ax.set_aspect("equal")
        ax.set_title("Bezier: side (x=half thickness, y=length)")
        ax.set_xlabel("x (mm)")
        ax.set_ylabel("Y (mm)")
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(args.out / "side_profile.png", facecolor="#f5f0e6")
        plt.close(fig)

    if bottom:
        pts = sample_profile(bottom)
        fig, ax = plt.subplots(figsize=(5, 4), dpi=140)
        plot_path(ax, pts, "#ab47bc", "handle-bottom", mirror=True)
        ax.set_aspect("equal")
        ax.set_title("Bezier: handle-bottom (x=half width, y=half thickness)")
        ax.set_xlabel("x (mm)")
        ax.set_ylabel("y (mm)")
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(args.out / "handle_bottom.png", facecolor="#f5f0e6")
        plt.close(fig)

    print(f"✓ Bezier 2D → {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
