#!/usr/bin/env python3
"""Publish both current fan assemblies at the existing /fan-nozzle/ endpoint.

Never regenerate print parts, slice, connect to a printer, or start another port.
Use the exact audited clean STLs. Evaluate motion parameters from their SCAD
snapshots and reject changed sources, meshes or native print packages.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web/fan-nozzle"
STAGING = ROOT / "output/fan-nozzle-preview"
DEPLOY = ROOT / "output/revision-review/fan-nozzle"
VARIANTS = {
    "fan76-direct": ("fan76-direct-longtravel-v1-20261007", "fan76-direct-v1.scad", "fan76_contract", "Ø76 · v1", 80),
    "fan41-direct": ("fan-tee-narrow-nozzles-v5-20261007", "fan-tee-narrow-v5.scad", "v5_parameters", "Ø41 · v5", 40),
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def transform(z=0, rotation=None):
    return {"position": [0, 0, z], "rotation": rotation or [0, 0, 0]}


def run_scad(openscad, source, target, defines=()):
    command = [openscad, "--backend", "Manifold", "--hardwarnings", "-o", str(target)]
    if target.suffix == ".stl":
        command += ["--export-format", "binstl"]
    for define in defines:
        command += ["-D", define]
    subprocess.run(command + [str(source)], check=True, capture_output=True, text=True)


def copy_mesh(source, stage):
    digest = sha(source)
    target = Path("models") / f"{source.stem}-{digest[:12]}.stl"
    (stage / target).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, stage / target)
    return {"file": target.as_posix(), "sha256": digest}


def part(stage, source, model, part_id, name, *, parent="assembly", z=0,
         role="printed", group="printed", color="#3976dd", opacity=1,
         visible=True, selector="part=\"body\"", explosion=None):
    return {"id": part_id, "name": name, **copy_mesh(model, stage),
            "source": {"kind": "scad", "file": f"source/{source}", "selector": selector},
            "geometrySpace": "local", "role": role, "groupId": group,
            "renderMode": "solid", "color": color, "opacity": opacity,
            "renderOrder": 10 if role == "printed" else 30,
            "instances": [{"id": part_id, "name": name, "parentFrameId": parent,
                           "localTransform": transform(z), "visible": visible,
                           "explosion": explosion or [0, 0, 0]}]}


def check_snapshot(folder, scad, echo_name, openscad, stage):
    exported = read(folder / "verification/export.json")
    for name, expected in exported["source_sha256"].items():
        for source in (ROOT / "cad" / name, folder / "source" / name):
            if sha(source) != expected:
                raise ValueError(f"Source differs from exported geometry: {source}")
        shutil.copy2(folder / "source" / name, stage / "source" / name)
    echo = stage / f"{scad}.echo"
    run_scad(openscad, folder / "source" / scad, echo, ['part="contract"'])
    match = re.search(r"ECHO: " + re.escape(echo_name) + r" = (\[.*\])", echo.read_text())
    if not match:
        raise ValueError(f"Missing evaluated contract in {echo}")
    params = dict(json.loads(match.group(1)))
    echo.unlink()  # Only this temporary generator product, never delivery files.
    if params != read(folder / "verification/parameters.json"):
        raise ValueError(f"Evaluated parameters differ from audit: {folder.name}")
    for row in exported["files"]:
        if row.get("print_target") and sha(folder / row["file"]) != row["sha256"]:
            raise ValueError(f"STL changed since export: {row['file']}")
    audit = read(folder / "print/native-slice-audit.json")
    if not all(audit["checks"].values()):
        raise ValueError("Native print audit has failed checks")
    # Audit files retain their original absolute paths; resolve by exact basename.
    for key, hash_key in [("native_project", "project_sha256"), ("package", "package_sha256")]:
        if sha(folder / "print/slice" / Path(audit[key]).name) != audit[hash_key]:
            raise ValueError(f"Native package changed: {key}")
    for row in audit["parts"]:
        if sha(folder / "stl" / Path(row["source"]).name) != row["sha256"]:
            raise ValueError("Preview STL is not the audited print mesh")
    return params, exported


def build_variant(variant_id, stage, openscad, reference_y, reference41):
    directory, scad, echo_name, label, expected_travel = VARIANTS[variant_id]
    folder = ROOT / "output" / directory
    p, exported = check_snapshot(folder, scad, echo_name, openscad, stage)
    big = variant_id == "fan76-direct"
    travel = p["travel" if big else "work_travel"]
    seated = p["core_min_z" if big else "core_seated_z"]
    length = p["core_height" if big else "core_l"]
    body_end = p["body_height" if big else "tee_z1"]
    assert travel == expected_travel and p["pitch"] == 4
    assert p["outlet_ids"] == [15, 20, 25, 30]
    prefix = "fan76-direct-v1" if big else "fan-tee-v5"
    body_id = "body" if big else "mother"
    parts = [part(stage, scad, folder / f"stl/{prefix}-{body_id}-clean.stl", "body",
                  f"{label} 主体 · Ø50 直插段 · P4 母丝", opacity=0.38)]
    for diameter in p["outlet_ids"]:
        selector = f"{'core' if big else 'nozzle'}{diameter}"
        parts.append(part(stage, scad, folder / f"stl/{prefix}-{selector}-clean.stl",
                          f"core{diameter}", f"气嘴 Ø{diameter} mm · {length} mm 长",
                          parent="core-screw", color="#31ce72", visible=diameter == 20,
                          group="optional", selector=f'part="{selector}"', explosion=[0, 0, 36]))
    parts[0]["source"]["selector"] = f'part="{body_id}"'
    for core in parts[1:]:
        core["exclusiveGroup"] = "nozzle"
    parts.append(part(stage, "fan-nozzle-bayonet-adjustable.scad", reference_y, "tee",
                      "Y 三通参考 · 承口实测约 Ø50.2 · 其余外形/止挡为示意", z=body_end,
                      role="purchased", group="reference", color="#edbe32", opacity=0.25,
                      selector='part="y-tee-preview"; fn_y_tee_socket_id=50.2', explosion=[0, 0, 24]))
    fan_model = folder / "review/review-fan-envelope.stl" if big else reference41
    if big:
        expected = next(row["sha256"] for row in exported["files"] if row["part_id"] == "review-fan-envelope")
        if sha(fan_model) != expected:
            raise ValueError("Fan reference differs from exported CAD snapshot")
    parts.append(part(stage, scad if big else "fan41-preview-reference.scad", fan_model, "fan",
                      "Ø76 风机出口及双凸耳参考" if big else "Ø41 出口外表面示意（非真实壁厚/内径/L槽）",
                      role="purchased", group="reference", color="#b3bdcb", opacity=0.38,
                      selector='part="review-fan-envelope"' if big else "display-only outlet skin",
                      explosion=[0, 0, -28]))
    frames = [
        {"id": "world", "label": "世界坐标", "parentFrameId": None, "kind": "fixed", "localTransform": transform()},
        {"id": "assembly", "label": "固定风机 / 主体 / Y三通（主管横向、分支向上）", "parentFrameId": "world",
         "kind": "fixed", "localTransform": transform(rotation=[0, -math.pi / 2, 0])},
        {"id": "core-screw", "label": "气嘴螺旋调节（轴向移动 + 同步旋转）", "parentFrameId": "assembly",
         "kind": "prismatic", "axis": [0, 0, 1], "range": [0, travel], "defaultValue": 0,
         "localTransform": transform(seated)},
    ]
    release = {"id": f"{prefix}-20261007", "label": label, "package": f"output/{directory}",
               "sources": exported["source_sha256"], "pitchMm": p["pitch"], "travelMm": travel,
               "outletIdsMm": p["outlet_ids"], "bodyLengthMm": p["body_height"] if big else p["tee_z1"]-p["fan_back_z"],
               "coreLengthMm": length, "nativeAudit": "DIGITAL_FIVE_PART_SLICE_PASS",
               "physicalFitVerified": False}
    return {
        "schemaVersion": 1, "variantId": variant_id, "title": f"{label} · Y口直插 · {travel} mm 行程",
        "release": release, "ui": {"persistPanelState": True, "showSearch": True, "showGroups": True},
        "instructions": [
            "拖动旋转，滚轮缩放；Tab 保留视角、爆炸比例、透明度及面板布局，各方案记住自己的气嘴和行程。",
            f"直接加载本次原始打印 STL：{label}，15 / 20 / 25 / 30 mm 四种出口。蓝色主体直插三通，不再使用中间透明管或外套夹紧件。",
            f"P{p['pitch']} 螺距不变，通过增加母丝圈数得到 {travel} mm 机构行程（{travel/p['pitch']:g} 圈）；只转动/移动绿色气嘴，主体与三通保持固定。",
            "气嘴从 Y 侧旋入；默认主体半透明以展示内芯。隐藏主体可看真实梯形螺纹；没有示意螺旋片或额外锁紧件。",
            "黄色 Y 为参考外形，仅承口 Ø50.2 为实测；止挡深度、分支交汇位置及通球安全范围仍待实物确认。机构全行程不等于三通内全程均可安全通球。",
        ],
        "assembly": {"coordinateSystem": {"units": "mm", "handedness": "right", "up": "z"},
                     "rootFrameId": "world", "frames": frames},
        "groups": [{"id": "printed", "label": "主连接件"}, {"id": "optional", "label": "互换气嘴"},
                   {"id": "reference", "label": "非打印参考"}],
        "parts": parts,
        "motionAdapterModule": "./project-motion.mjs",
        "screwMotion": {"frameId": "core-screw", "pitchMm": p["pitch"], "travelMm": travel,
                        "baseAngleRad": 2*math.pi*(seated+p["male_z0"]-p["female_z0"])/p["pitch"],
                        "tipProtrusionAtZeroMm": seated+length-body_end},
        "nozzleOptions": [{"diameterMm": d, "instanceId": f"core{d}"} for d in p["outlet_ids"]],
        "defaultNozzleId": "core20",
        "stages": [{"id": name, "label": f"{label2} · {value:g} mm / {value/p['pitch']:g} 圈",
                    "values": {"core-screw": value}} for name, label2, value in
                   [("retracted", "缩回", 0), ("middle", "中间", travel/2), ("extended", "伸出", travel)]],
        "playback": {"sequence": ["retracted", "middle", "extended", "middle"], "secondsPerTransition": 8, "loop": True},
        "views": [{"id": "assembly", "label": "等轴总装", "direction": [0.65, -1, 0.65]},
                  {"id": "side", "label": "轴向侧视", "direction": [0, -1, 0.15]},
                  {"id": "fan", "label": "风机卡口", "direction": [1, -0.5, 0.35], "focusInstanceIds": ["fan", "body"]},
                  {"id": "tee", "label": "三通接口", "direction": [0.5, -1, 0.6], "focusInstanceIds": ["tee"]}],
    }


def atomic_publish(stage, destination):
    # Assets first, catalog last. Existing readers never get a manifest whose
    # content-addressed mesh has not arrived yet. Unrelated files are untouched.
    files = [p for p in stage.rglob("*") if p.is_file()]
    files.sort(key=lambda p: (p.name == "manifest.json", p.name.startswith("manifest-"), str(p)))
    for source in files:
        target = destination / source.relative_to(stage)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and sha(target) == sha(source):
            continue
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".publish-", delete=False) as handle:
            temporary = Path(handle.name)
        try:
            shutil.copy2(source, temporary)
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openscad", default="/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="fan-preview-") as temporary:
        stage = Path(temporary)
        shutil.copytree(WEB, stage, dirs_exist_ok=True)
        (stage / "source").mkdir(exist_ok=True)
        for name in ["fan-nozzle-bayonet-adjustable.scad", "fan-nozzle-parameters.scad", "thread-profile.scad", "fan41-preview-reference.scad"]:
            shutil.copy2(ROOT / "cad" / name, stage / "source" / name)
        y_mesh, fan41 = stage / "y-reference.stl", stage / "fan41-reference.stl"
        run_scad(args.openscad, ROOT / "cad/fan-nozzle-bayonet-adjustable.scad", y_mesh,
                 ['part="y-tee-preview"', "fn_y_tee_socket_id=50.2"])
        run_scad(args.openscad, ROOT / "cad/fan41-preview-reference.scad", fan41)
        manifests = {key: build_variant(key, stage, args.openscad, y_mesh, fan41) for key in VARIANTS}
        y_mesh.unlink()
        fan41.unlink()
        manifests["fan76-direct"]["variantCatalog"] = {
            "defaultId": "fan76-direct", "variants": [
                {"id": "fan76-direct", "label": "Ø76 · Y口直插 / 80 mm", "manifest": "./manifest.json"},
                {"id": "fan41-direct", "label": "Ø41 · Y口直插 / 40 mm", "manifest": "./manifest-fan41-direct.json"}]}
        for key, name in [("fan76-direct", "manifest.json"), ("fan41-direct", "manifest-fan41-direct.json")]:
            dump(stage / name, manifests[key])
        atomic_publish(stage, STAGING)
        atomic_publish(stage, DEPLOY)
        for key, manifest in manifests.items():
            print(f"{key}: {manifest['release']['id']}; P4 / {manifest['release']['travelMm']} mm; exact audited STL hashes")
    print("Published /fan-nozzle/ on the EXISTING port 8877; printer untouched.")


if __name__ == "__main__":
    main()
