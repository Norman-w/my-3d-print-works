#!/usr/bin/env python3
"""Render an exact-CAD optical-home motion GIF and stage sheet.

Use the workspace Python runtime (with Pillow). This is a kinematic visual
review of the adopted 20 mm feeder stroke, not a motor-speed simulation.
"""

from __future__ import annotations

import concurrent.futures
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "cad/feeder-optical-home.scad"
GEOMETRY_REPORT = ROOT / "output/optical-home-candidate/review.json"
OUT = ROOT / "output/optical-home-candidate/motion"
RAW = OUT / "raw"
OPENSCAD = Path("/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
FONT = Path("/System/Library/Fonts/Hiragino Sans GB.ttc")
STEPS = 50
FPS = 25
CANVAS = (1800, 1000)
VIEWS = {
    "context": {"size": (1000, 800), "camera": "-80,30,0,65,0,315,300"},
    "detail": {"size": (900, 800), "camera": "-82,29,10,65,0,315,220"},
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    return ImageFont.truetype(str(FONT), size) if FONT.exists() else ImageFont.load_default()


def render(job: tuple[str, int]) -> tuple[str, int, Path]:
    view, step = job
    spec = VIEWS[view]
    target = RAW / f"{view}-{step:03d}.png"
    command = [
        str(OPENSCAD), "--hardwarnings", "--backend", "Manifold", "--render",
        f"--imgsize={spec['size'][0]},{spec['size'][1]}", "--projection=o",
        "--colorscheme=Tomorrow", f"--camera={spec['camera']}",
        "-D", f'oh_part={json.dumps("context" if view == "context" else "local-assembly")}',
        "-D", f"oh_t={step / STEPS:.6f}", "-o", str(target), str(SOURCE),
    ]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=90)
    log = result.stdout + result.stderr
    if result.returncode or "WARNING:" in log or "ERROR:" in log or not target.is_file():
        raise RuntimeError(f"{view} {step}/{STEPS}: {log[-1500:]}")
    with Image.open(target) as im:
        if im.size != spec["size"]:
            raise RuntimeError(f"Unexpected render size: {target}: {im.size}")
    return view, step, target


def content_bounds(view: str) -> tuple[int, int, int, int]:
    width, height = VIEWS[view]["size"]
    union = [width, height, 0, 0]
    for step in range(STEPS + 1):
        with Image.open(RAW / f"{view}-{step:03d}.png") as im:
            rgb = im.convert("RGB")
            background = Image.new("RGB", rgb.size, rgb.getpixel((0, 0)))
            bounds = ImageChops.difference(rgb, background).getbbox()
        if not bounds:
            raise RuntimeError(f"Blank frame: {view} {step}")
        union = [min(union[0], bounds[0]), min(union[1], bounds[1]),
                 max(union[2], bounds[2]), max(union[3], bounds[3])]
    padding = 38
    return (max(0, union[0] - padding), max(0, union[1] - padding),
            min(width, union[2] + padding), min(height, union[3] + padding))


def paste_view(canvas: Image.Image, view: str, step: int, box: tuple[int, int, int, int],
               crop: tuple[int, int, int, int]) -> None:
    x0, y0, x1, y1 = box
    with Image.open(RAW / f"{view}-{step:03d}.png") as im:
        photo = im.convert("RGB").crop(crop)
    fitted = ImageOps.contain(photo, (x1 - x0, y1 - y0), Image.Resampling.LANCZOS)
    canvas.paste(fitted, (x0 + (x1 - x0 - fitted.width) // 2,
                          y0 + (y1 - y0 - fitted.height) // 2))


def status(step: int) -> tuple[str, str]:
    # The CAD flag edge crosses the nominal beam at z=13 after 2 mm travel.
    # The 1.2-2.4 mm band is shown as transitional, not an exact electrical edge.
    travel = 20 * step / STEPS
    if travel <= 1.2:
        return "遮光 · 归位接近", "#16824e"
    if travel >= 2.4:
        return "透光 · 已离槽", "#b76a05"
    return "光路切换区", "#7662ae"


def compose(step: int, phase: str, crops: dict[str, tuple[int, int, int, int]]) -> Image.Image:
    canvas = Image.new("RGB", CANVAS, "#f1f3f6")
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((25, 22, 1775, 145), radius=24, fill="#172333")
    draw.text((55, 38), "槽型光电归位 · 送料架 20 mm 行程", font=font(46), fill="white")
    draw.text((57, 102), "按当前 CAD 逐帧渲染；橙色件上下移动，黑色传感器固定", font=font(25), fill="#cdd9e5")
    for panel in ((25, 165, 885, 865), (915, 165, 1775, 865)):
        draw.rounded_rectangle(panel, radius=20, fill="white", outline="#c9d3dc", width=2)
    draw.text((55, 184), "机架位置", font=font(34), fill="#172333")
    draw.text((945, 184), "光槽近景", font=font(34), fill="#172333")
    paste_view(canvas, "context", step, (54, 238, 856, 836), crops["context"])
    paste_view(canvas, "detail", step, (944, 238, 1746, 836), crops["detail"])
    draw = ImageDraw.Draw(canvas)
    signal, signal_color = status(step)
    draw.rounded_rectangle((1208, 176, 1743, 228), radius=19, fill=signal_color)
    draw.text((1230, 181), signal, font=font(30), fill="white")
    direction = "↑" if phase == "上行" else "↓" if phase == "回程" else "●"
    draw.text((1653, 450), direction, font=font(94), fill="#db6b25")
    draw.rounded_rectangle((25, 887, 1775, 977), radius=22, fill="#e5ebf0")
    draw.text((58, 903), f"{phase}   位移 {20 * step / STEPS:04.1f} / 20.0 mm",
              font=font(35), fill="#172333")
    draw.text((855, 912), "蓝=固定盖   黑=传感器   橙=活动遮光片   绿=弹簧",
              font=font(24), fill="#40536a")
    return canvas


def render_overview() -> Path:
    raw = RAW / "system-overview.png"
    output = OUT / "system-location.png"
    command = [
        str(OPENSCAD), "--hardwarnings", "--backend", "Manifold", "--render",
        "--imgsize=1400,1000", "--projection=o", "--colorscheme=Tomorrow",
        "--autocenter", "--viewall", "--camera=0,0,0,65,0,315,800",
        "-D", 'oh_part="system"', "-D", "oh_t=0", "-o", str(raw), str(SOURCE),
    ]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=90)
    log = result.stdout + result.stderr
    if result.returncode or "WARNING:" in log or "ERROR:" in log or not raw.exists():
        raise RuntimeError(f"System overview failed: {log[-1500:]}")
    with Image.open(raw) as im:
        canvas = im.convert("RGB")
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((25, 20, 635, 116), radius=20, fill="#172333")
    draw.text((48, 30), "槽型光电在整机左侧", font=font(40), fill="white")
    draw.text((49, 78), "黑=传感器  蓝=安装盖  橙=活动送料件", font=font(21), fill="#cdd9e5")
    draw.ellipse((365, 388, 492, 573), outline="#e05426", width=7)
    draw.line((477, 397, 620, 248), fill="#e05426", width=6)
    draw.polygon(((477, 397), (488, 370), (503, 386)), fill="#e05426")
    draw.rounded_rectangle((594, 200, 1045, 255), radius=15, fill="#e05426")
    draw.text((612, 207), "固定传感器与活动遮光片", font=font(27), fill="white")
    canvas.save(output, optimize=True)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reuse-raw", action="store_true", help="Reuse complete source-matched CAD frames")
    args = parser.parse_args()
    geometry = json.loads(GEOMETRY_REPORT.read_text())
    if not geometry["geometry_review_pass"] or geometry["source_sha256"] != digest(SOURCE):
        raise RuntimeError("Optical-home CAD changed; rerun geometry review before animation")
    for relative, expected in geometry["dependency_sha256"].items():
        if digest(ROOT / relative) != expected:
            raise RuntimeError(f"Geometry dependency changed: {relative}")
    RAW.mkdir(parents=True, exist_ok=True)
    jobs = [(view, step) for step in range(STEPS + 1) for view in VIEWS]
    previous_path = OUT / "render-report.json"
    previous = json.loads(previous_path.read_text()) if previous_path.exists() else {}
    reuse = (args.reuse_raw and previous.get("source_sha256") == digest(SOURCE)
             and all((RAW / f"{view}-{step:03d}.png").exists() for view, step in jobs))
    if args.reuse_raw and not reuse:
        raise RuntimeError("Raw frames are incomplete or source identity changed")
    if not reuse:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            for count, _ in enumerate(pool.map(render, jobs), 1):
                if count % 20 == 0 or count == len(jobs):
                    print(f"rendered {count}/{len(jobs)} CAD views", flush=True)
    crops = {view: content_bounds(view) for view in VIEWS}
    cycle = ([(0, "待机")] * 15
             + [(i, "上行") for i in range(1, STEPS + 1)]
             + [(STEPS, "顶端")] * 10
             + [(i, "回程") for i in range(STEPS - 1, -1, -1)]
             + [(0, "待机")] * 15)
    gif_size = (1280, 711)
    first_rgb = compose(*cycle[0], crops).resize(gif_size, Image.Resampling.LANCZOS)
    palette = first_rgb.convert("P", palette=Image.Palette.ADAPTIVE, colors=128)
    gif_frames = []
    for step, phase in cycle:
        rgb = compose(step, phase, crops).resize(gif_size, Image.Resampling.LANCZOS)
        gif_frames.append(rgb.quantize(palette=palette, dither=Image.Dither.NONE))
    gif_path = OUT / "optical-home-motion.gif"
    gif_frames[0].save(gif_path, save_all=True, append_images=gif_frames[1:],
                       duration=1000 // FPS, loop=0, optimize=True, disposal=2)
    with Image.open(gif_path) as gif:
        encoded_frames = gif.n_frames
        encoded_duration_ms = 0
        for index in range(encoded_frames):
            gif.seek(index)
            encoded_duration_ms += gif.info["duration"]
    if encoded_duration_ms != len(cycle) * (1000 // FPS):
        raise RuntimeError("Encoded animation duration differs from the source timeline")
    stages = [(0, "待机"), (10, "上行"), (STEPS, "顶端"), (2, "回程")]
    sheet = Image.new("RGB", (2400, 1334), "#edf1f4")
    for index, (step, phase) in enumerate(stages):
        thumbnail = compose(step, phase, crops).resize((1200, 667), Image.Resampling.LANCZOS)
        sheet.paste(thumbnail, ((index % 2) * 1200, (index // 2) * 667))
    sheet_path = OUT / "four-stages.png"
    sheet.save(sheet_path, optimize=True)
    overview_path = render_overview()
    report = {
        "source": str(SOURCE.relative_to(ROOT)),
        "source_sha256": digest(SOURCE),
        "scope": "Exact current feeder CAD kinematics; Omron sensor outline is a dimensioned proxy; no motor dynamics",
        "frame_positions": STEPS + 1,
        "source_views_rendered": len(jobs),
        "fps": FPS,
        "animation_frames": len(cycle),
        "encoded_gif_frames": encoded_frames,
        "duration_s": len(cycle) / FPS,
        "crops": crops,
        "gif": str(gif_path.relative_to(ROOT)),
        "gif_sha256": digest(gif_path),
        "stage_sheet": str(sheet_path.relative_to(ROOT)),
        "stage_sheet_sha256": digest(sheet_path),
        "system_location": str(overview_path.relative_to(ROOT)),
        "system_location_sha256": digest(overview_path),
        "physical_acceptance": False,
    }
    (OUT / "render-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
