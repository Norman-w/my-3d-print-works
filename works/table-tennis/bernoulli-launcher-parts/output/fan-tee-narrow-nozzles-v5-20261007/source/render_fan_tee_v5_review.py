#!/usr/bin/env python3
"""Opaque orthographic renders and measured plane sections of final v5 STL."""
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
import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT/"output/fan-tee-narrow-nozzles-v5-20261007"
IDS = ["mother", "nozzle15", "nozzle20", "nozzle25", "nozzle30"]
BLUE, GOLD = "#2468ad", "#e99d35"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def loops(segments):
    graph, points, edges = defaultdict(list), {}, set()
    for a, b in segments:
        ka, kb = tuple(np.round(a, 5)), tuple(np.round(b, 5))
        if ka==kb:
            continue
        graph[ka].append(kb); graph[kb].append(ka)
        points[ka] = a; points[kb] = b
        edges.add(tuple(sorted((ka, kb))))
    result = []
    while edges:
        start, current = next(iter(edges)); route = [start]
        edges.remove(tuple(sorted((start, current))))
        while current!=start:
            route.append(current)
            choices = [n for n in graph[current] if tuple(sorted((current, n))) in edges]
            assert choices, "Open contour in final STL section"
            following = choices[0]
            edges.remove(tuple(sorted((current, following))))
            current = following
        result.append(np.array([points[n] for n in route]))
    return result


def section(ax, mesh, color, label):
    seg = trimesh.intersections.mesh_plane(mesh, [0, 1, 0], [0, 0, 0])[:, :, [0, 2]]
    for polygon in loops(seg):
        ax.fill(polygon[:, 0], polygon[:, 1], facecolor=color, edgecolor="none")
    ax.add_collection(LineCollection(seg, colors=color, linewidths=.7, label=label))


def style(ax, xlim, ylim, title):
    ax.set(xlim=xlim, ylim=ylim, title=title, xlabel="X / mm", ylabel="模型 Z / mm")
    ax.set_aspect("equal"); ax.grid(alpha=.18); ax.set_axisbelow(True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--openscad", default="/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
    a = ap.parse_args(); out = a.out.resolve()
    for font in map(Path, ["/System/Library/Fonts/PingFang.ttc",
                           "/System/Library/Fonts/STHeiti Medium.ttc",
                           "/System/Library/Fonts/Supplemental/Songti.ttc"]):
        if font.exists():
            font_manager.fontManager.addfont(font)
            plt.rcParams["font.family"] = font_manager.FontProperties(fname=font).get_name()
            break
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.size"] = 10
    paths = {n: out/f"stl/fan-tee-v5-{n}-clean.stl" for n in IDS}
    meshes = {n: trimesh.load_mesh(p) for n, p in paths.items()}
    renders = []
    def render(name, body, camera, size="720,1000"):
        wrapper = out/f"review/render-{name}.scad"
        wrapper.write_text("// Review only: direct final binary STL import; no reconstructed CAD.\n"+body+"\n")
        target = out/f"render/{name}.png"
        cmd = [a.openscad, "--backend", "Manifold", "--render", "--colorscheme", "Tomorrow",
               "--projection", "o", "--imgsize", size, "--camera", camera, "--viewall",
               "-o", str(target), str(wrapper)]
        run = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        (out/f"verification/logs/render-{name}.log").write_text(run.stdout+run.stderr)
        if run.returncode:
            raise RuntimeError(run.stderr)
        renders.append({"file": f"render/{name}.png", "sha256": sha(target), "command": cmd})
        print("render", name, flush=True)
        return target
    for name in IDS:
        centre = float(np.mean(meshes[name].bounds[:, 2]))
        body = f'color([0.14,0.40,0.68]) import("../stl/fan-tee-v5-{name}-clean.stl");'
        for view, camera in [
            ("front", f"0,-220,{centre},0,0,{centre}"),
            ("top", f"0,0,{centre},0,0,0,220"),
            ("iso", f"140,-140,{centre+140},0,0,{centre}")]:
            render(f"{name}-{view}", body, camera)
    for offset in [0, 40]:
        # Exact half-space clipping of imported STL, never a parametric proxy.
        body = ('color([0.14,0.40,0.68]) intersection(){import("../stl/fan-tee-v5-mother-clean.stl");'
                'translate([-30,0,-19]) cube([60,30,220]);}\n'
                f'color([0.91,0.61,0.20]) intersection(){{translate([0,0,{34+offset}]) '
                f'rotate([0,0,{90*offset}]) import("../stl/fan-tee-v5-nozzle15-clean.stl");'
                'translate([-30,0,-19]) cube([60,30,230]);}')
        render(f"assembly-section-{offset}mm", body, "140,-140,220,0,0,80", "900,1300")
    figures = []
    fig, axes = plt.subplots(1, 5, figsize=(16, 9.5))
    for ax, name in zip(axes, IDS):
        ax.imshow(plt.imread(out/f"render/{name}-iso.png")); ax.axis("off")
        ax.set_title("母件 Ø50\n高146.5mm" if name=="mother" else f"出口内径 Ø{name[6:]}\n统一总长106mm", fontsize=13)
    fig.suptitle("Ø41风机 · v5 五个实际STL｜均为干净单实体，未嵌入支撑", fontsize=17)
    fig.text(.5, .05, "每件单独取景，图中不是同一比例尺。螺距P4不变，正常有效行程40mm；喷口伸出12～52mm。", ha="center", fontsize=12)
    fig.subplots_adjust(left=.01, right=.99, bottom=.1, top=.89, wspace=.02)
    figures.append(("five-parts-iso.png", fig))
    fig, axes = plt.subplots(1, 3, figsize=(13, 8))
    for ax, view, title in zip(axes, ["front", "top", "iso"], ["正视 −Y", "俯视 +Z", "等轴"]):
        ax.imshow(plt.imread(out/f"render/mother-{view}.png")); ax.axis("off"); ax.set_title(title)
    fig.suptitle("母件最终STL｜风机端在下，三通直插端在上", fontsize=16)
    fig.text(.5, .05, "Ø50 / 高146.5mm · 三通配合段Ø50/Ø44×25mm · 卡扣与v4相同", ha="center", fontsize=12)
    fig.subplots_adjust(bottom=.1, top=.89)
    figures.append(("mother-views.png", fig))
    fig, axes = plt.subplots(1, 4, figsize=(16, 10), gridspec_kw={"width_ratios": [1.5, .8, 1.5, .8]})
    for i, offset in enumerate([0, 40]):
        core = meshes["nozzle15"].copy()
        core.apply_translation([0, 0, 34+offset])
        for ax in axes[i*2:i*2+2]:
            section(ax, meshes["mother"], BLUE, "母件实体")
            section(ax, core, GOLD, "Ø15气嘴实体")
        style(axes[i*2], (-27, 27), (-22, 185), "最深正常旋入" if offset==0 else "最大正常伸出")
        style(axes[i*2+1], (19.6, 22.0), (43+offset, 55+offset), "真实STL螺纹局部")
        axes[i*2].axhline(128, color="#555", lw=.8, linestyle="--")
        axes[i*2].annotate(f"喷口伸出{12+offset}mm", xy=(9.5, 140+offset), xytext=(-24, 161+offset*.2),
                           arrowprops={"arrowstyle": "->"}, fontsize=10)
    axes[0].legend(loc="lower left", bbox_to_anchor=(0, -.13), fontsize=9)
    fig.suptitle("实际STL轴向剖面｜P4×10圈＝40mm行程，残圈不计入有效啮合", fontsize=16)
    fig.text(.5, .025, "蓝色母件／橙色公芯／白色沟槽和气道。全行程至少3完整啮合圈；52mm伸出须现场核对Y交汇与球路。", ha="center", fontsize=11)
    fig.subplots_adjust(left=.04, right=.99, bottom=.13, top=.9, wspace=.3)
    figures.append(("thread-and-travel-sections.png", fig))
    fig, axes = plt.subplots(1, 4, figsize=(14, 10), sharex=True, sharey=True)
    for ax, name in zip(axes, IDS[1:]):
        section(ax, meshes[name], GOLD, name)
        style(ax, (-23, 23), (-2, 110), f"出气内径 Ø{name[6:]}mm")
        for z in [46, 90]:
            ax.axhline(z, color="#555", lw=.6, ls="--")
    fig.suptitle("四个气嘴同尺度实际STL剖面｜粗直46＋渐缩44＋出口直段16＝106mm", fontsize=16)
    fig.text(.5, .035, "入口内径36mm；径向壁厚2mm；公牙芯体Ø40、牙大径Ø41.8。出口参考面相同，便于A/B比较。", ha="center", fontsize=11)
    fig.subplots_adjust(bottom=.12, top=.9, wspace=.14)
    figures.append(("nozzle-sections.png", fig))
    fig, axes = plt.subplots(1, 2, figsize=(12, 10))
    for ax, offset in zip(axes, [0, 40]):
        ax.imshow(plt.imread(out/f"render/assembly-section-{offset}mm.png")); ax.axis("off")
        ax.set_title(f"调节量{offset}mm｜喷口伸出{12+offset}mm", fontsize=14)
    fig.suptitle("最终STL装配半剖等轴｜完全不透明，保留实际沟槽和壁厚", fontsize=16)
    fig.text(.5, .025, "风机、Y三通和球路未在此虚构；出气端现场干涉仍需实测。", ha="center", fontsize=12)
    fig.subplots_adjust(left=.01, right=.99, bottom=.06, top=.9)
    figures.append(("assembly-two-states.png", fig))
    records = []
    for name, fig in figures:
        path = out/"render"/name
        fig.savefig(path, dpi=155, facecolor="white")
        plt.close(fig)
        records.append({"file": f"render/{name}", "sha256": sha(path)})
    (out/"verification/render-provenance.json").write_text(json.dumps({
        "method": "Native depth-buffered orthographic import of final STL; section polygons from triangle-plane intersection",
        "input_stl_sha256": {n: sha(p) for n, p in paths.items()},
        "native_views": renders, "review_figures": records,
        "script_does_not_claim_human_visual_review": True,
    }, ensure_ascii=False, indent=2)+"\n")
    print("Review complete", flush=True)


if __name__ == "__main__":
    main()
