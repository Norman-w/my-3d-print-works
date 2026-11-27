#!/usr/bin/env python3
"""Real exported STL views/sections; no illustrative replacement for CAD geometry."""
from concurrent.futures import ThreadPoolExecutor
import argparse
import json
import os
import subprocess

from build_fan76_smooth_v2 import ROOT, sha, dump
from fan76_smooth_release import smooth_release

os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "output/preview-service/matplotlib"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import numpy as np
import trimesh


def contour(ax, mesh, color, lw=1):
    seg = trimesh.intersections.mesh_plane(mesh, [0, 1, 0], [0, .017, 0])
    ax.add_collection(LineCollection(seg[:, :, [0, 2]], colors=color, linewidths=lw))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", type=int, choices=[2, 3, 4, 5], default=2)
    release = smooth_release(parser.parse_args().revision)
    OUT = release.out
    p = json.loads((OUT / "verification/parameters.json").read_text())
    body_path = OUT / f"stl/{release.stem}-body-clean.stl"
    body = trimesh.load_mesh(body_path)
    core_path = OUT / "stl/fan-tee-v5-nozzle15-clean.stl"
    core = trimesh.load_mesh(core_path)
    old_path = ROOT / "output" / release.previous_package / "stl" / f"{release.previous_stem}-body-clean.stl"
    old = trimesh.load_mesh(old_path)
    old_p = json.loads((old_path.parent.parent / "verification/parameters.json").read_text())
    preview = ROOT / "output/fan-nozzle-preview"
    manifest = json.loads((preview / "manifest.json").read_text())
    tee_part = next(row for row in manifest["parts"] if row["id"] == "tee")
    tee_path = preview / tee_part["file"]
    assert sha(tee_path) == tee_part["sha256"]
    tee = trimesh.load_mesh(tee_path)
    tee.apply_translation([0, 0, p["body_height"]])
    font_path = "/System/Library/Fonts/STHeiti Medium.ttc"
    from matplotlib.font_manager import FontProperties
    cn = FontProperties(fname=font_path)
    plt.rcParams.update({"axes.unicode_minus": False})
    ymax = p["body_height"] + 123
    fig, axes = plt.subplots(1, 3, figsize=(14, 11), layout="constrained")
    ax = axes[0]
    contour(ax, old, "#94a3b8", 1)
    contour(ax, body, "#0b73ba", 1.4)
    ax.set_title("新旧外壳实际 STL 剖面对比", fontproperties=cn)
    ax.text(-51, ymax-40, f"灰：上版 {old_p['body_height']} mm\n蓝：本版 {p['body_height']} mm\n风机端面对齐，同一比例", fontproperties=cn, color="#334155")
    ax.annotate(f"收缩段 {p['blend_length']} mm\n内外壁连续渐变", xy=(32, p['blend_z0']+p['blend_length']/2), xytext=(-51, 25),
                arrowprops={"arrowstyle": "->", "color": "#0b73ba"}, fontproperties=cn, color="#0b73ba")
    if release.revision >= 4:
        ax.text(-51, ymax-63, f"本版薄壁区：{p['thin_wall_radial_nominal']:.1f} mm\n母沟底：{(p['thread_shell_od']-p['female_major'])/2:.1f} mm；插接段：3 mm",
                fontproperties=cn, color="#0b73ba")
    for ax, z, title in zip(axes[1:], [p["core_min_z"], p["core_max_z"]], ["默认：完全缩回", f"伸出 {p['travel']} mm位置"]):
        current = core.copy()
        angle = 2*np.pi*(z+p["male_z0"]-p["female_z0"])/p["pitch"]
        current.apply_transform(trimesh.transformations.rotation_matrix(angle, [0, 0, 1]))
        current.apply_translation([0, 0, z])
        contour(ax, body, "#0b73ba", 1.2)
        contour(ax, current, "#ca7205", 1.3)
        contour(ax, tee, "#a2a0b8", .9)
        ax.axhline(p["body_height"], color="#64748b", linestyle="--", lw=.8)
        ax.axhline(p["spigot_z0"], color="#64748b", linestyle=":", lw=.8)
        protrusion = z+p['core_height']-p['body_height']
        ax.annotate(f"嘴端超出主体 {protrusion:g} mm", xy=(0,z+p['core_height']), xytext=(-52,p['body_height']+45),
                    arrowprops={"arrowstyle":"->", "color":"#ca7205"}, fontproperties=cn, color="#ca7205")
        ax.text(-51, 60, f"原Ø41气嘴，{p['core_height']} mm\n内丝{p['female_length']} mm / P4\n灰紫：Y参考件（非实测）", fontproperties=cn, color="#0b73ba")
        ax.text(32,p['spigot_z0']-12,"Y管口", fontproperties=cn, color="#7a7890")
        ax.set_title(title, fontproperties=cn)
    for ax in axes:
        ax.set_aspect("equal"); ax.set_xlim(-55, 95); ax.set_ylim(-5, ymax)
        ax.set_xlabel("X / mm"); ax.set_ylabel("Z / mm"); ax.grid(alpha=.13)
    fig.suptitle(f"Ø76 平滑收缩 v{release.revision}｜最终STL真实剖面｜蓝色主体、橙色兼容气嘴", fontproperties=cn, fontsize=17)
    fig.savefig(OUT / "render/comparison-and-travel.png", dpi=160)
    plt.close(fig)

    wrapper = OUT / "review/final-mesh-view.scad"
    wrapper.write_text(f'// Render the final STL only.\nimport("../stl/{body_path.name}");\n')
    section = OUT / "review/final-assembly-section.scad"
    section.write_text(
        '// Imported final meshes, exact phase, no procedural preview substitutes.\n'
        f'color([0.12,0.43,0.68]) intersection(){{import("../stl/{body_path.name}");'
        'translate([-100,0,-1]) cube([200,100,400]);}\n'
        f'color([0.87,0.48,0.08]) translate([0,0,{p["core_min_z"]}]) '
        'intersection(){import("../stl/fan-tee-v5-nozzle15-clean.stl");'
        'translate([-100,0,-1]) cube([200,100,400]);}\n')
    mid = p['body_height']/2
    targets = [("front", wrapper, f"0,-480,{mid},0,0,{mid}"),
               ("top", wrapper, f"0,0,550,0,0,{mid}"),
               ("iso", wrapper, f"240,-420,300,0,0,{mid}"),
               ("assembly-section-iso", section, f"170,-440,300,0,0,{mid}")]
    def render(row):
        view, source, camera = row
        output = OUT / f"render/{view}.png"
        command = ["/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD", "--backend", "Manifold",
                   "--hardwarnings", "--render", "--projection", "o", "--viewall", "--autocenter",
                   "--imgsize", "850,1000", "--colorscheme", "Tomorrow", "--camera", camera,
                   "-o", str(output), str(source)]
        run = subprocess.run(command, capture_output=True, text=True)
        (OUT / f"verification/logs/render-{view}.log").write_text(run.stdout+run.stderr)
        if run.returncode:
            raise RuntimeError(run.stderr)
        print("Rendered", view, flush=True)
        return {"view": view, "source_wrapper": str(source.relative_to(OUT)), "image": str(output.relative_to(OUT)), "sha256": sha(output)}
    with ThreadPoolExecutor(max_workers=2) as pool:
        images = list(pool.map(render, targets))
    dump(OUT / "verification/render.json", {"body_sha256": sha(body_path), "core15_sha256": sha(core_path),
        "previous_body_sha256": sha(old_path), "tee_reference_sha256": sha(tee_path),
        "images": images, "sections": "Real STL plane intersections, not illustrative outlines"})


if __name__ == "__main__":
    main()
