#!/usr/bin/env python3
"""Render opaque final STL and exact mesh sections; no CAD/slicer mutation."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import subprocess

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.collections import LineCollection
from matplotlib.patches import Rectangle
import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT/"output/fan-tee-direct-print-v4-20261007"
BLUE = "#2267ac"
ORANGE = "#eaa044"


def setup_font() -> None:
    for path in ["/System/Library/Fonts/PingFang.ttc",
                 "/System/Library/Fonts/STHeiti Medium.ttc",
                 "/Library/Fonts/Arial Unicode.ttf"]:
        if Path(path).exists():
            font_manager.fontManager.addfont(path)
            plt.rcParams["font.family"] = font_manager.FontProperties(fname=path).get_name()
            break
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.size"] = 10


def loops_from_segments(segments: np.ndarray) -> list[np.ndarray]:
    """Join section segments solely for presentation; validation uses meshes."""
    graph = defaultdict(list)
    points = {}
    edges = set()
    for a, b in segments:
        ka, kb = tuple(np.round(a, 5)), tuple(np.round(b, 5))
        if ka == kb:
            continue
        graph[ka].append(kb); graph[kb].append(ka)
        points[ka] = a; points[kb] = b
        edges.add(tuple(sorted((ka, kb))))
    loops = []
    while edges:
        start, next_point = next(iter(edges))
        route = [start]; previous, current = start, next_point
        edges.remove(tuple(sorted((previous, current))))
        while current != start:
            route.append(current)
            choices = [q for q in graph[current] if tuple(sorted((current, q))) in edges]
            if not choices:
                raise ValueError("Unexpected open section contour")
            following = choices[0]
            edges.remove(tuple(sorted((current, following))))
            previous, current = current, following
        loops.append(np.asarray([points[q] for q in route]))
    return loops


def axial_section(ax, mesh, color, label):
    lines = trimesh.intersections.mesh_plane(mesh, [0, 1, 0], [0, 0, 0])[:, :, [0, 2]]
    for loop in loops_from_segments(lines):
        ax.fill(loop[:, 0], loop[:, 1], facecolor=color, edgecolor="none", alpha=.85)
    ax.add_collection(LineCollection(lines, colors=color, linewidths=.8, label=label))


def style_section(ax, xlim, ylim, title):
    ax.set(xlim=xlim, ylim=ylim, xlabel="X / mm", ylabel="模型 Z / mm", title=title)
    ax.set_aspect("equal")
    ax.grid(alpha=.18, linewidth=.5)
    ax.set_axisbelow(True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--openscad", default="/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
    args = ap.parse_args()
    out = args.out.resolve(); (out/"render").mkdir(exist_ok=True)
    setup_font()
    connector = out/"stl/fan-tee-v4-connector-clean.stl"
    mesh = trimesh.load_mesh(connector)
    core = trimesh.load_mesh(out/"verification/reference/printed-core36.stl")
    core.apply_transform(trimesh.transformations.rotation_matrix(np.radians(129.6), [0, 0, 1]))
    core.apply_translation([0, 0, 34])
    p = json.loads((out/"verification/parameters.json").read_text())
    figs = []

    # Native depth-buffered rendering avoids painter-sort artefacts where
    # long exterior triangles and inner bore triangles overlap in projection.
    fig = plt.figure(figsize=(14, 7.8), facecolor="white")
    native_views = []
    for i, name, title, camera in [
        (1, "front", "正视：从 −Y 看", "0,-200,30.75,0,0,30.75"),
        (2, "top", "俯视：从 +Z 看", "0,0,30.75,0,0,0,200"),
        (3, "iso", "等轴视图", "140,-140,170.75,0,0,30.75")]:
        png = out/f"render/stl-{name}.png"
        command = [args.openscad, "--backend", "Manifold", "--render", "--colorscheme", "Tomorrow",
                   "--projection", "o", "--imgsize", "1000,1100", "--camera", camera,
                   "--viewall", "-o", str(png), str(out/"review/mesh-render.scad")]
        result = subprocess.run(command, capture_output=True, text=True)
        (out/f"logs/render-{name}.log").write_text(result.stdout+result.stderr)
        if result.returncode:
            raise RuntimeError(result.stderr)
        native_views.append({"file": str(png.relative_to(out)), "command": command,
                             "sha256": hashlib.sha256(png.read_bytes()).hexdigest()})
        ax = fig.add_subplot(1, 3, i)
        ax.imshow(plt.imread(png)); ax.set_axis_off()
        ax.set_title(title, pad=8, fontsize=14)
    fig.suptitle("v4 外部连接件｜直接显示最终 STL，不含支撑、不含风嘴芯", fontsize=17)
    fig.text(.5, .06, "外包络 50 × 50 × 98.5 mm  ·  风机端在下 / 气流向上  ·  三通段 Ø50 / 内孔 Ø44 / 长25 mm", ha="center", fontsize=12)
    fig.subplots_adjust(left=.01, right=.99, bottom=.09, top=.89, wspace=.01)
    figs.append(("mesh-views.png", fig))

    fig, axs = plt.subplots(1, 3, figsize=(16, 10), gridspec_kw={"width_ratios": [1.15, 1, 1]})
    for ax in axs:
        axial_section(ax, mesh, BLUE, "v4 母件：本次唯一打印件")
        axial_section(ax, core, ORANGE, "旧 core36：仅配合验证，不重打")
    style_section(axs[0], (-28, 28), (-21, 86), "轴向实体剖面：Y = 0")
    style_section(axs[1], (18.5, 25.6), (37.5, 52.5), "螺纹局部：旧公牙保留")
    style_section(axs[2], (16.5, 26), (-14, 5.5), "卡扣局部：只改位置和径向厚度")
    axs[0].annotate("旧风嘴芯从上方旋入", xy=(0, 69), xytext=(0, 84), ha="center",
                    arrowprops={"arrowstyle": "->", "color": "#555"})
    axs[0].annotate("风机从下方装入", xy=(0, -3), xytext=(0, -19), ha="center",
                    arrowprops={"arrowstyle": "->", "color": "#555"})
    axs[0].legend(loc="upper left", bbox_to_anchor=(0, -.08), fontsize=9)
    axs[1].annotate("母沟上侧让位\n下悬牙侧约50°", xy=(20.75, 43.24), xytext=(22.0, 41.3),
                    fontsize=10, arrowprops={"arrowstyle": "->", "color": "#555"})
    axs[1].annotate("小径处保留\n约0.787 mm牙厚", xy=(20.30, 48.16), xytext=(21.9, 49.0),
                    fontsize=10, arrowprops={"arrowstyle": "->", "color": "#555"})
    # Old lug Y=0 section is a rectangle. It is an explicitly labelled
    # parametric comparison, not substituted for the new STL contour.
    axs[2].add_patch(Rectangle((18.7, -10), 3.6, 6, fill=False, edgecolor="#d25824",
                              linestyle="--", linewidth=1.6, label="旧卡扣轮廓（基线参数）"))
    axs[2].annotate("向内多伸出1 mm", xy=(17.7, -6.0), xytext=(18, 1.5),
                    fontsize=10, arrowprops={"arrowstyle": "->", "color": "#555"})
    axs[2].annotate("圆片 Ø6 不变\n中心 Z=-7.5\n向风机移0.5 mm", xy=(20, -7.5), xytext=(21.9, -12.3),
                    fontsize=10, arrowprops={"arrowstyle": "->", "color": "#555"})
    axs[2].legend(loc="lower left", bbox_to_anchor=(0, -.12), fontsize=8)
    fig.suptitle("最终 STL 切面：蓝色为实体材料，白色为气道／沟槽，橙色为已打印芯的数字参考", fontsize=15)
    fig.text(.5, .025, "母牙让位不改公牙：导程4 mm、母小径40.6、母沟大径42.3；实体装配和承力仍需首件确认。", ha="center", fontsize=11)
    fig.subplots_adjust(left=.05, right=.98, bottom=.14, top=.91, wspace=.25)
    figs.append(("mesh-axial-sections.png", fig))

    fig, ax = plt.subplots(figsize=(10, 9))
    seg = trimesh.intersections.mesh_plane(mesh, [0, 0, 1], [0, 0, p["lug_z"]])[:, :, :2]
    loops = loops_from_segments(seg)
    area = lambda a: abs(np.dot(a[:, 0], np.roll(a[:, 1], 1))-np.dot(a[:, 1], np.roll(a[:, 0], 1)))
    for index, loop in enumerate(sorted(loops, key=area, reverse=True)):
        ax.fill(loop[:, 0], loop[:, 1], facecolor=BLUE if index==0 else "white", edgecolor=BLUE, lw=.7)
    theta = np.linspace(0, 2*np.pi, 361)
    ax.plot(20.5*np.cos(theta), 20.5*np.sin(theta), linestyle="--", color="#cf7337", linewidth=1.3,
            label="风机已知外圆 Ø41（不代表内壁或L槽形状）")
    ax.annotate("两侧卡扣实体端面\n向内突出3.4 mm", xy=(17.7, 0), xytext=(1, -6),
                arrowprops={"arrowstyle": "->"}, fontsize=12)
    ax.annotate("根部嵌入1.2 mm\n每侧融合体积约35.47 mm³", xy=(-22.0, 0), xytext=(-15, 11),
                arrowprops={"arrowstyle": "->"}, fontsize=12)
    ax.set(xlim=(-28, 28), ylim=(-28, 28), xlabel="X / mm", ylabel="Y / mm")
    ax.set_aspect("equal"); ax.grid(alpha=.15); ax.set_axisbelow(True)
    ax.legend(loc="lower center", bbox_to_anchor=(.5, -.13), fontsize=10)
    ax.set_title("卡扣横剖面：Z=-7.5 mm｜最终 STL 实体轮廓", fontsize=15)
    fig.text(.5, .03, "注意：风机槽底深度和内壁尚未实测；径向承锁约2.8 mm，必须确认不会顶到底。", ha="center", fontsize=11)
    fig.subplots_adjust(bottom=.17, top=.92)
    figs.append(("mesh-lug-cross-section.png", fig))

    records = []
    for filename, fig in figs:
        destination = out/"render"/filename
        fig.savefig(destination, dpi=160, facecolor="white")
        plt.close(fig)
        records.append({"file": f"render/{filename}", "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()})
    (out/"verification/render-provenance.json").write_text(json.dumps({
        "source_stl": str(connector.relative_to(out)),
        "source_stl_sha256": hashlib.sha256(connector.read_bytes()).hexdigest(),
        "reference_core": "verification/reference/printed-core36.stl",
        "method": "Native OpenSCAD depth-buffered opaque import of the final STL; orthographic views; exact plane/triangle sections",
        "native_views": native_views,
        "new_model_images": records,
        "visual_review_performed_by_script": False,
    }, ensure_ascii=False, indent=2)+"\n")
    print("Rendered", [name for name, _ in figs])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
