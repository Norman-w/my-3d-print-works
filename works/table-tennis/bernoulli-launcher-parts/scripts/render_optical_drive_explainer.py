#!/usr/bin/env python3
"""Render clean sensor linkage and a separately labeled 30:20 motor concept.

Run with the workspace Python runtime that includes Pillow. The motor scene is
an explanatory displacement model, not a print part or an approved installation.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import subprocess
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
CAD = ROOT / "cad/optical-drive-explainer.scad"
SENSOR_CAD = ROOT / "cad/feeder-optical-home.scad"
GEOMETRY_REPORT = ROOT / "output/optical-home-candidate/review.json"
OUT = ROOT / "output/optical-home-candidate/drive-explainer"
RAW = OUT / "raw"
OPENSCAD = Path("/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
FONT = Path("/System/Library/Fonts/Hiragino Sans GB.ttc")
STEPS = 60
FPS = 25
VIEWS = {
    "chain": ("sensor-chain", "-80,30,10,65,0,315,330"),
    "motor": ("motor-principle", "0,0,77,68,0,35,500"),
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def chinese(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    return ImageFont.truetype(str(FONT), size) if FONT.exists() else ImageFont.load_default()


def render(job: tuple[str, int]) -> tuple[str, int]:
    view, step = job
    part, camera = VIEWS[view]
    target = RAW / f"{view}-{step:03d}.png"
    cmd = [str(OPENSCAD), "--hardwarnings", "--backend", "Manifold", "--render",
           "--imgsize=900,800", "--projection=o", "--colorscheme=Tomorrow",
           f"--camera={camera}", "-D", f'ex_part="{part}"',
           "-D", f"ex_motor_mm={30 * step / STEPS:.5f}",
           "-o", str(target), str(CAD)]
    done = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=90)
    log = done.stdout + done.stderr
    if done.returncode or "WARNING:" in log or "ERROR:" in log or not target.exists():
        raise RuntimeError(f"Render {view} {step}: {log[-1200:]}")
    with Image.open(target) as im:
        if im.size != (900, 800):
            raise RuntimeError(f"Unexpected frame size: {target}")
    return job


def crop_union(view: str) -> tuple[int, int, int, int]:
    bounds = [900, 800, 0, 0]
    for step in range(STEPS + 1):
        with Image.open(RAW / f"{view}-{step:03d}.png") as im:
            rgb = im.convert("RGB")
            background = Image.new("RGB", rgb.size, rgb.getpixel((0, 0)))
            b = ImageChops.difference(rgb, background).getbbox()
        if not b:
            raise RuntimeError(f"Blank CAD view: {view} {step}")
        bounds = [min(bounds[0], b[0]), min(bounds[1], b[1]),
                  max(bounds[2], b[2]), max(bounds[3], b[3])]
    pad = 30
    return (max(0, bounds[0] - pad), max(0, bounds[1] - pad),
            min(900, bounds[2] + pad), min(800, bounds[3] + pad))


def scene(canvas: Image.Image, view: str, step: int, box: tuple[int, int, int, int],
          crops: dict[str, tuple[int, int, int, int]]) -> None:
    x0, y0, x1, y1 = box
    with Image.open(RAW / f"{view}-{step:03d}.png") as im:
        image = im.convert("RGB").crop(crops[view])
    fit = ImageOps.contain(image, (x1-x0, y1-y0), Image.Resampling.LANCZOS)
    canvas.paste(fit, (x0 + (x1-x0-fit.width)//2, y0 + (y1-y0-fit.height)//2))


def compose(step: int, phase: str, crops: dict[str, tuple[int, int, int, int]]) -> Image.Image:
    u = 30 * step / STEPS
    feeder = min(u, 20)
    compression = max(0, u - 20)
    image = Image.new("RGB", (1600, 900), "#eff2f5")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((20, 18, 1580, 132), radius=21, fill="#172333")
    draw.text((45, 27), "伸缩电机 30 mm → 送料架 20 mm", font=chinese(43), fill="white")
    draw.text((47, 86), "左：真实送料机构剖切   右：单向推、候选拉簧回位的示意轨迹", font=chinese(24), fill="#cbd7e2")
    draw.rounded_rectangle((20, 150, 785, 730), radius=19, fill="white", outline="#c5d1da", width=2)
    draw.rounded_rectangle((815, 150, 1580, 730), radius=19, fill="white", outline="#c5d1da", width=2)
    draw.text((44, 164), "实际 CAD：送料架与光电", font=chinese(31), fill="#172333")
    draw.text((839, 164), "电机示意：外形非商品尺寸", font=chinese(31), fill="#172333")
    scene(image, "chain", step, (42, 211, 759, 701), crops)
    scene(image, "motor", step, (837, 211, 1554, 701), crops)
    draw = ImageDraw.Draw(image)
    signal = "挡光" if feeder < 1.2 else "切换区" if feeder < 2.4 else "透光"
    draw.rounded_rectangle((48, 680, 350, 720), radius=12,
                           fill="#188653" if signal == "挡光" else "#bd710d")
    draw.text((61, 685), f"光电：{signal}", font=chinese(23), fill="white")
    draw.rounded_rectangle((20, 748, 1580, 880), radius=18, fill="#dfe7ee")
    draw.text((45, 759), f"{phase}   电机伸出 {u:04.1f} / 30 mm", font=chinese(31), fill="#172333")
    draw.text((593, 759), f"假设送料架 {feeder:04.1f} / 20 mm", font=chinese(28), fill="#8f4908")
    draw.text((1115, 759), f"接头压缩 {compression:04.1f} mm", font=chinese(27), fill="#8a6900")
    for (x0, width, fraction, color) in ((46, 470, u / 30, "#426a8c"),
                                         (594, 447, feeder / 20, "#df7820"),
                                         (1117, 420, compression / 10, "#d5b332")):
        draw.rounded_rectangle((x0, 825, x0 + width, 851), radius=10, fill="#b7c7d1")
        if fraction > 0:
            draw.rounded_rectangle((x0, 825, x0 + max(17, width * fraction), 851),
                                   radius=10, fill=color)
    return image


def connection_map(crops: dict[str, tuple[int, int, int, int]]) -> Image.Image:
    canvas = Image.new("RGB", (1800, 980), "#f0f3f6")
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle((22, 18, 1778, 112), radius=21, fill="#172333")
    d.text((49, 34), "谁固定在谁上：真实机构与电机待设计接口", font=chinese(40), fill="white")
    d.rounded_rectangle((22, 137, 760, 947), radius=18, fill="white", outline="#c6d0da", width=2)
    scene(canvas, "chain", 0, (43, 160, 738, 900), crops)
    d = ImageDraw.Draw(canvas)
    d.text((784, 148), "已建模的两条连接链", font=chinese(34), fill="#172333")
    rows = [
        (220, "固定侧", "机架 → 蓝色左导向盖 → 两颗 M3 → 黑色槽型光电", "#1b608e"),
        (328, "运动侧", "灰色送料架 → 银色肩销 → 橙色间隔套/遮光片", "#ca6918"),
        (436, "回位", "绿弹簧跨接固定销与活动肩销", "#23844d"),
    ]
    for y, tag, description, color in rows:
        d.rounded_rectangle((782, y, 1764, y+86), radius=16, fill="white", outline=color, width=3)
        d.rounded_rectangle((797, y+13, 922, y+73), radius=12, fill=color)
        d.text((815, y+23), tag, font=chinese(26), fill="white")
        d.text((944, y+27), description, font=chinese(23), fill="#172333")
    d.rounded_rectangle((782, 579, 1764, 904), radius=18, fill="#fff8eb", outline="#c69335", width=3)
    d.text((811, 604), "电机端仍是接口方案", font=chinese(33), fill="#7c4a10")
    d.text((812, 671), "固定外壳 → 需设计电机座 → 主机架", font=chinese(27), fill="#172333")
    d.text((812, 729), "伸缩杆 → 需设计补偿接头 → 灰色送料架", font=chinese(27), fill="#172333")
    d.text((812, 788), "30 mm = 送料 20 mm + 补偿 10 mm", font=chinese(27), fill="#a2640b")
    d.text((811, 851), "仅示意单向推动、候选拉簧回位；电机外形未按实物建模。", font=chinese(21), fill="#685f54")
    return canvas


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reuse-raw", action="store_true",
                        help="Recompose labeled graphics from already verified OpenSCAD frames")
    args = parser.parse_args()
    geometry = json.loads(GEOMETRY_REPORT.read_text())
    if not geometry["geometry_review_pass"] or geometry["source_sha256"] != sha(SENSOR_CAD):
        raise RuntimeError("Sensor CAD changed; repeat the geometry review first")
    RAW.mkdir(parents=True, exist_ok=True)
    jobs = [(view, step) for step in range(STEPS + 1) for view in VIEWS]
    if args.reuse_raw:
        prior_report = json.loads((OUT / "render-report.json").read_text())
        if prior_report["source_sha256"] != {
                str(CAD.relative_to(ROOT)): sha(CAD),
                str(SENSOR_CAD.relative_to(ROOT)): sha(SENSOR_CAD)}:
            raise RuntimeError("CAD changed since cached frames were rendered")
        for view, step in jobs:
            target = RAW / f"{view}-{step:03d}.png"
            with Image.open(target) as frame:
                if frame.size != (900, 800):
                    raise RuntimeError(f"Invalid cached frame: {target}")
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            for count, _ in enumerate(pool.map(render, jobs), 1):
                if count % 24 == 0 or count == len(jobs):
                    print(f"rendered {count}/{len(jobs)} clean CAD views", flush=True)
    crops = {view: crop_union(view) for view in VIEWS}
    timeline = ([(0, "零位")] * 15
                + [(i, "伸出") for i in range(1, STEPS + 1)]
                + [(STEPS, "顶端/补偿")] * 15
                + [(i, "缩回") for i in range(STEPS - 1, -1, -1)]
                + [(0, "零位")] * 15)
    first = compose(*timeline[0], crops).resize((1280, 720), Image.Resampling.LANCZOS)
    palette = first.convert("P", palette=Image.Palette.ADAPTIVE, colors=128)
    frames = []
    for step, phase in timeline:
        rgb = compose(step, phase, crops).resize((1280, 720), Image.Resampling.LANCZOS)
        frames.append(rgb.quantize(palette=palette, dither=Image.Dither.NONE))
    animation = OUT / "clean-linkage-and-motor-principle.gif"
    frames[0].save(animation, save_all=True, append_images=frames[1:],
                   duration=1000 // FPS, loop=0, optimize=True, disposal=2)
    with Image.open(animation) as gif:
        encoded = gif.n_frames
        duration = 0
        for i in range(encoded):
            gif.seek(i)
            duration += gif.info["duration"]
    assert duration == len(timeline) * 1000 // FPS
    mapping = OUT / "what-connects-to-what.png"
    connection_map(crops).save(mapping, optimize=True)
    sheet = Image.new("RGB", (2400, 720), "#f0f3f6")
    for i, (step, phase) in enumerate([(0, "零位"), (40, "送料到顶"), (60, "接头补偿")]):
        cell = compose(step, phase, crops).resize((800, 450), Image.Resampling.LANCZOS)
        sheet.paste(cell, (800*i, 135))
    d = ImageDraw.Draw(sheet)
    d.text((35, 26), "三阶段：电机 0 → 20 → 30 mm；送料架 0 → 20 → 20 mm",
           font=chinese(45), fill="#172333")
    d.text((36, 625), "右侧外形不是商品尺寸；回程依赖候选拉簧、位置曲线并非力学计算，双向牵引仍待设计。",
           font=chinese(28), fill="#6f5125")
    stages = OUT / "0-20-30mm-stages.png"
    sheet.save(stages, optimize=True)
    report = {
        "source_sha256": {str(CAD.relative_to(ROOT)): sha(CAD),
                          str(SENSOR_CAD.relative_to(ROOT)): sha(SENSOR_CAD)},
        "source_views_rendered": len(jobs), "source_views_reused": args.reuse_raw,
        "frame_positions": STEPS + 1,
        "timeline_frames": len(timeline), "gif_encoded_frames": encoded,
        "duration_ms": duration, "fps": FPS,
        "real_cad": "left sensor/frame chain only; no transparent overlapping display layers",
        "motor_scene": "generic 30 mm output, spring-return assumption and 10 mm compliant overtravel principle; no force simulation",
        "motor_mount_designed": False, "motor_coupling_designed": False,
        "motor_return_positive_drive_designed": False,
        "physical_acceptance": False,
        "animation": str(animation.relative_to(ROOT)), "animation_sha256": sha(animation),
        "mount_map": str(mapping.relative_to(ROOT)), "mount_map_sha256": sha(mapping),
        "stage_sheet": str(stages.relative_to(ROOT)), "stage_sheet_sha256": sha(stages),
    }
    (OUT / "render-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
