#!/usr/bin/env python3
"""Render final FAN76 STL, actual mesh sections and parameterized tooth detail."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import argparse
import json
import math
import os
from pathlib import Path
import subprocess

from export_fan76_direct_v1 import OUT, PARTS, sha, dump

os.environ.setdefault("MPLCONFIGDIR", str(OUT / "verification/matplotlib"))
import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Polygon
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import trimesh

P = json.loads((OUT / "verification/parameters.json").read_text())
BLUE = "#1b658c"
GOLD = "#e38b23"
GREY = "#64748b"


def path(part):
    return OUT / "stl" / f"fan76-direct-v1-{part}-clean.stl"


def read(part):
    return trimesh.load_mesh(path(part), process=True)


def posed(mesh, z, a=None):
    copy = mesh.copy()
    if a is None:
        a = 360 * (z + 4 - 70) / 4
    copy.apply_transform(trimesh.transformations.rotation_matrix(math.radians(a), [0, 0, 1]))
    copy.apply_translation([0, 0, z])
    return copy


def contour(ax, mesh, color, normal=(0, 1, 0), origin=(0, .017, 0), axes=(0, 2), linewidth=.85):
    segments = trimesh.intersections.mesh_plane(mesh, normal, origin)
    coords = segments[:, :, axes]
    ax.add_collection(LineCollection(coords, colors=color, linewidths=linewidth))
    return segments


def axis_style(ax):
    ax.set_aspect("equal")
    ax.grid(alpha=.12)
    ax.set_xlabel("X / radius (mm)")
    ax.set_ylabel("Z (mm)")


def render_stls(selected=None):
    openscad = "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"
    targets = []
    for part in (selected or PARTS):
        height = 222 if part == "body" else 160
        center = height / 2
        wrapper = OUT / "review" / f"mesh-view-{part}.scad"
        wrapper.write_text(f'// FINAL binary STL only, not procedural source geometry.\nimport("../stl/{path(part).name}");\n')
        cameras = {"front": f"0,-450,{center},0,0,{center}",
                   "top": f"0,0,500,0,0,{center}",
                   "iso": f"260,-380,{center+240},0,0,{center}"}
        for view, camera in cameras.items():
            targets.append((part, view, wrapper, camera))

    def render(item):
        part, view, wrapper, camera = item
        target = OUT / "render" / f"{part}-{view}.png"
        command = [openscad, "--backend", "Manifold", "--hardwarnings", "--render", "--projection", "o",
                   "--viewall", "--autocenter", "--imgsize", "600,760", "--colorscheme", "Tomorrow",
                   "--camera", camera, "-o", str(target), str(wrapper)]
        completed = subprocess.run(command, capture_output=True, text=True)
        (OUT / "verification/logs" / f"render-{part}-{view}.log").write_text(completed.stdout + completed.stderr)
        if completed.returncode:
            raise RuntimeError(completed.stderr)
        return {"part_id": part, "view": view, "mesh_sha256": sha(path(part)),
                "image": str(target.relative_to(OUT)), "sha256": sha(target), "command": command}

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(render, targets))
    previous = OUT / "verification/render-provenance.json"
    if selected and previous.exists():
        results += [r for r in json.loads(previous.read_text())["mesh_renders"] if r["part_id"] not in selected]
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
    small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
    sheet = Image.new("RGB", (1500, 1990), "white")
    draw = ImageDraw.Draw(sheet)
    draw.text((22, 15), "FAN76 DIRECT v1 | FINAL STL | FRONT / TOP / ISOMETRIC", fill="#122c43", font=font)
    draw.text((22, 46), "Upright +Z. Individual panels fitted independently; read labeled dimensions. No supports embedded.", fill="#475569", font=small)
    for i, part in enumerate(PARTS):
        for j, view in enumerate(["front", "top", "iso"]):
            picture = Image.open(OUT / "render" / f"{part}-{view}.png").convert("RGB")
            picture.thumbnail((480, 332))
            x, y = j * 500, 85 + i * 380
            sheet.paste(picture, (x + (500 - picture.width) // 2, y + 30))
            size = "86 x 86 x 222 mm" if part == "body" else "41.8 x 41.8 x 160 mm"
            draw.text((x + 15, y), f"{part} | {view} | {size}", fill="#122c43", font=small)
    target = OUT / "render/final-stl-three-views.png"
    sheet.save(target)
    return results


def assembly_sections():
    body = read("body")
    fig, axes = plt.subplots(1, 2, figsize=(12, 15), layout="constrained")
    for ax, offset, title in zip(axes, [70, 150], ["DEEPEST working position", "MOST EXTENDED working position"]):
        contour(ax, body, BLUE, linewidth=1.1)
        contour(ax, posed(read("core15"), offset), GOLD, linewidth=1.1)
        ax.axhline(222, color=GREY, linestyle="--", linewidth=.8)
        ax.axhline(197, color=GREY, linestyle=":", linewidth=.8)
        ax.axhspan(70, 182, xmin=.95, xmax=1, facecolor=BLUE, alpha=.15)
        ax.annotate("outlet Z222", (28, 222), (27, 229), fontsize=8, color=BLUE)
        ax.annotate("25 mm spigot / Y mouth reference Z197", (25, 197), (-53, 188), fontsize=8, color=GREY)
        tip = offset + 160
        ax.annotate(f"tip Z{tip} | protrusion {tip-222} mm", (0, tip), (-49, tip + 10), fontsize=10, color=GOLD,
                    arrowprops={"arrowstyle": "-", "color": GOLD})
        turn_label_z = offset + 37 if offset == 70 else offset - 28
        ax.annotate("4 complete load-bearing turns", (21, offset + 16), (-49, turn_label_z), fontsize=9, color=GOLD,
                    arrowprops={"arrowstyle": "-", "color": GOLD})
        ax.text(-51, 10, "Fan mouth -> +Z\n76.6 mm socket\nrectangular external lugs", fontsize=9, color=BLUE)
        ax.set_title(f"{title}\ncore inlet Z{offset}; ID15 worst narrowing example", fontsize=12)
        ax.set_xlim(-57, 60); ax.set_ylim(-5, 332); axis_style(ax)
    fig.suptitle("80 mm travel = 20 turns at 4 mm pitch | actual final STL sections\n"
                 "Blue: body, orange: core. Y body/branch/ball envelope UNKNOWN, deliberately not invented.", fontsize=14)
    fig.savefig(OUT / "render/assembly-minmax-section.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(2, 4, figsize=(14, 15), layout="constrained")
    for column, id in enumerate([15, 20, 25, 30]):
        for row, z in enumerate([70, 150]):
            ax = axes[row, column]
            contour(ax, body, BLUE)
            contour(ax, posed(read(f"core{id}"), z), GOLD)
            ax.axhline(222, color=GREY, linestyle="--", linewidth=.7)
            ax.set_xlim(-45, 45); ax.set_ylim(0, 317)
            ax.set_aspect("equal"); ax.grid(alpha=.1)
            ax.set_title(f"ID{id}: core Z{z}, tip Z{z+160}", fontsize=10)
            if column == 0: ax.set_ylabel("Z (mm)")
            ax.set_xlabel("X (mm)")
    fig.suptitle("Every final core at BOTH working limits | same outlet Z datum\n"
                 "No external tube/sleeve. Threads are below the long guide; nozzle extends into unmeasured Y space.", fontsize=13)
    fig.savefig(OUT / "render/all-four-minmax-sections.png", dpi=160)
    plt.close(fig)


def thread_sections():
    fig, axes = plt.subplots(1, 3, figsize=(16, 6), layout="constrained")
    male = np.array(P["male_profile"]); female = np.array(P["female_profile"])
    ax = axes[0]
    ax.add_patch(Polygon(female, facecolor=BLUE, alpha=.2, edgecolor=BLUE, label="female CUT envelope"))
    ax.add_patch(Polygon(male, facecolor=GOLD, alpha=.75, edgecolor=GOLD, label="male tooth"))
    ax.axvline(20, color=GREY, linestyle="--", linewidth=.8, label="male core skin R20")
    ax.axvline(20.3, color=BLUE, linestyle=":", linewidth=.8, label="female minor R20.3")
    ax.set_xlim(19.6, 21.4); ax.set_ylim(-2, 2)
    ax.set_title("Actual r-z profile parameters\n0.9 mm height / 0.8 mm flat crest")
    ax.set_aspect("equal"); ax.set_xlabel("Radius (mm)"); ax.set_ylabel("Axial profile offset (mm)")
    ax.grid(alpha=.15); ax.legend(loc="lower left", fontsize=7)
    body = read("body"); core = posed(read("core15"), 70)
    for ax, low, high, label in zip(axes[1:], [77, 179], [91, 185.5],
                                   ["Paired FINAL STL at deepest position", "Outlet lead-in into continuous groove"]):
        contour(ax, body, BLUE, linewidth=1.25)
        if low == 77: contour(ax, core, GOLD, linewidth=1.25)
        ax.set_xlim(19.4, 22.5); ax.set_ylim(low, high); axis_style(ax); ax.set_title(label, fontsize=10)
        ax.axvline(20.9, color=GOLD, linestyle="--", linewidth=.6)
    axes[2].text(19.45, 184.5, "ID44 guide", fontsize=9)
    axes[2].text(19.45, 179.4, "minor40.6\nmajor42.3", fontsize=8)
    fig.suptitle("50 deg exposed flank; 0.20 mm embedded root independent of flank\n"
                 "Final mesh minimum: male 49.95 deg / mother remaining tooth 49.98 deg; slice acceptance pending.", fontsize=13)
    fig.savefig(OUT / "render/thread-profile-and-mesh-section.png", dpi=180)
    plt.close(fig)


def bayonet_sections():
    body = read("body")
    fan = trimesh.load_mesh(OUT / "review/review-fan-envelope.stl", process=True)
    fig, axes = plt.subplots(1, 3, figsize=(16, 6), layout="constrained")
    contour(axes[0], body, BLUE, normal=(1, 0, 0), origin=(.017, 0, 0), axes=(1, 2))
    contour(axes[0], fan, GOLD, normal=(1, 0, 0), origin=(.017, 0, 0), axes=(1, 2))
    axes[0].set_xlim(33, 44); axes[0].set_ylim(-1, 32); axes[0].set_aspect("equal")
    axes[0].set_title("External lug at straight-in position\nY-Z plane near X=0")
    axes[0].set_xlabel("Y (mm)"); axes[0].set_ylabel("Z (mm)")
    for ax, a in zip(axes[1:], [0, 18]):
        contour(ax, body, BLUE, normal=(0, 0, 1), origin=(0, 0, 17), axes=(0, 1))
        contour(ax, posed(fan, 0, a), GOLD, normal=(0, 0, 1), origin=(0, 0, 17), axes=(0, 1))
        ax.set_xlim(-44, 44); ax.set_ylim(-44, 44); ax.set_aspect("equal")
        ax.set_title(f"FINAL body / measured fan envelope\nZ17 section, rotation {a} deg")
        ax.set_xlabel("X (mm)"); ax.set_ylabel("Y (mm)")
    for ax in axes: ax.grid(alpha=.12)
    fig.suptitle("FAN76 rectangular external lugs | straight +Z, then +18 deg rotation\n"
                 "1.9 mm outer web; 12.5 mm floor; 8.5 mm roof-to-collar height. Strength and support removal untested.", fontsize=13)
    fig.savefig(OUT / "render/fan76-bayonet-sections.png", dpi=180)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parts", nargs="+", choices=PARTS)
    args = parser.parse_args()
    rows = render_stls(args.parts)
    assembly_sections(); thread_sections(); bayonet_sections()
    generated = [{"file": str(p.relative_to(OUT)), "sha256": sha(p)} for p in sorted((OUT / "render").glob("*.png"))]
    dump(OUT / "verification/render-provenance.json", {"mesh_renders": rows, "images": generated,
         "section_basis": "Contours intersect FINAL STL with a plane 0.017mm off exact symmetry, avoiding coincident mesh edges.",
         "parameter_plot": "Only left panel of thread figure uses echoed profile points; adjacent panels are actual STL sections.",
         "mesh_sha256": {part: sha(path(part)) for part in PARTS}, "visually_reviewed": False})
    print("Rendered 15 individual final-STL views, contact sheet and four section figures.", flush=True)


if __name__ == "__main__":
    main()
