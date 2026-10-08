#!/usr/bin/env python3
"""Publish both current fan assemblies at the existing /fan-nozzle/ endpoint.

Never regenerate print parts, slice, connect to a printer, or start another port.
Use exact clean STLs. A CAD-review release must pass its independent geometry
audit; offline comparison slicing is labelled separately from print readiness.
An existing print release must additionally pass its native package audit.
Never inherit a prior release's print readiness.
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
from prepare_fan_tee_v5_print import binary_mesh

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web/fan-nozzle"
STAGING = ROOT / "output/fan-nozzle-preview"
DEPLOY = ROOT / "output/revision-review/fan-nozzle"
VARIANTS = {
    "fan76-direct": ("fan76-smooth-v5-20261008", "fan76-smooth-v5.scad", "fan76_smooth_contract", "Ø76 · 薄壁缓收缩 v5", 20),
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


def check_snapshot(folder, scad, echo_name, openscad, stage, *, cad_review=False):
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
    if cad_review:
        geometry = read(folder / "verification/summary.json")
        if geometry["status"] != "PASS_DIGITAL_GEOMETRY_NOT_SLICED" or geometry["sliced"]:
            raise ValueError("CAD review requires a passing geometry audit, never an inherited slice audit")
        if geometry["source_sha256"] != exported["source_sha256"]:
            raise ValueError("Geometry audit source mismatch")
        if geometry["file_sha256"] != {r["part_id"]: r["sha256"] for r in exported["files"]}:
            raise ValueError("Geometry audit STL mismatch")
        for row in exported["files"]:
            if row.get("copied_from") and sha(ROOT / row["copied_from"]) != row["sha256"]:
                raise ValueError("Reused Ø41 nozzle is not byte-identical")
        return params, exported
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


def check_offline_estimates(folder, exported):
    """Evidence for estimates only; never authorize dispatch from an analysis package."""
    report = read(folder / "verification/slice-comparison.json")
    if report["status"] != "OFFLINE_COMPARISON_ONLY_NOT_FOR_PRINT" or report["printer_contacted"]:
        raise ValueError("Offline estimate has incorrect evidence boundary")
    cases = {row["case"]: row for row in report["cases"]}
    if set(cases) != {"v4-w4", "v5-w4"}:
        raise ValueError("Missing current or baseline estimate")
    current_hash = next(row["sha256"] for row in exported["files"] if row["part_id"] == "body")
    for key, row in cases.items():
        if sha(ROOT / row["input_stl"]) != row["input_sha256"]:
            raise ValueError("Offline estimate input mesh changed")
        if key.startswith("v5-") and row["input_sha256"] != current_hash:
            raise ValueError("Offline estimate belongs to a different shell")
        if (row["dispatch_authorized"] or row["printer_contacted"] or not row["preset_verified"]
                or not row["startup_unchanged"] or not row["end_code_unchanged"]
                or row["height_margin_mm"] < 2 or row["seconds_estimate"] <= 0 or row["grams_estimate"] <= 0):
            raise ValueError("Invalid offline estimate provenance")
    chosen = cases["v5-w4"]
    if chosen["wall_loops"] != 4:
        raise ValueError("Thin-shell recommendation retains four walls")
    return {"wallLoops": 4, "seconds": chosen["seconds_estimate"], "grams": chosen["grams_estimate"],
            "scope": "single body / offline comparison only", "dispatchAuthorized": False,
            "supportContactReviewed": chosen["support_contact_reviewed"],
            "reportSha256": sha(folder / "verification/slice-comparison.json")}


def build_variant(variant_id, stage, openscad, reference_y, reference41, tee_contract):
    directory, scad, echo_name, label, expected_travel = VARIANTS[variant_id]
    folder = ROOT / "output" / directory
    big = variant_id == "fan76-direct"
    p, exported = check_snapshot(folder, scad, echo_name, openscad, stage, cad_review=big)
    travel = p["travel" if big else "work_travel"]
    seated = p["core_min_z" if big else "core_seated_z"]
    length = p["core_height" if big else "core_l"]
    body_end = p["body_height" if big else "tee_z1"]
    assert travel == expected_travel and p["pitch"] == 4
    assert p["outlet_ids"] == [15, 20, 25, 30]
    prefix = Path(scad).stem if big else "fan-tee-v5"
    estimate = check_offline_estimates(folder, exported) if big else None
    if big:
        minutes = round(estimate["seconds"]/60)
        estimate_text = f"{minutes//60}小时{minutes%60}分/{estimate['grams']:.0f}克"
    body_id = "body" if big else "mother"
    parts = [part(stage, scad, folder / f"stl/{prefix}-{body_id}-clean.stl", "body",
                  f"{label} 主体 · Ø50 直插段 · P4 母丝", opacity=0.38)]
    for diameter in p["outlet_ids"]:
        selector = f"nozzle{diameter}"
        core_source = "fan-tee-narrow-v5.scad" if big else scad
        parts.append(part(stage, core_source, folder / f"stl/fan-tee-v5-{selector}-clean.stl",
                          f"core{diameter}", f"气嘴 Ø{diameter} mm · {length} mm 长",
                          parent="core-screw", color="#31ce72", visible=diameter == 20,
                          group="optional", selector=f'part="{selector}"', explosion=[0, 0, 36]))
    parts[0]["source"]["selector"] = f'part="{body_id}"'
    for core in parts[1:]:
        core["exclusiveGroup"] = "nozzle"
    parts.append(part(stage, "y-tee-preview-reference.scad", reference_y, "tee",
                      "Y 三通 · 三端加厚承口 · 上方进球口向风机侧后倾（外形参考）", z=body_end,
                      role="purchased", group="reference", color="#a2cddd", opacity=0.43,
                      selector='part="reference"', explosion=[0, 0, 24]))
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
         "kind": "fixed", "localTransform": transform(rotation=[math.radians(a) for a in tee_contract["display_rotation_deg"]])},
        {"id": "core-screw", "label": "气嘴螺旋调节（轴向移动 + 同步旋转）", "parentFrameId": "assembly",
         "kind": "prismatic", "axis": [0, 0, 1], "range": [0, travel], "defaultValue": 0,
         "localTransform": transform(seated)},
    ]
    release = {"id": f"{prefix}-{'20261008' if big else '20261007'}", "label": label, "package": f"output/{directory}",
               "sources": exported["source_sha256"], "pitchMm": p["pitch"], "travelMm": travel,
               "outletIdsMm": p["outlet_ids"], "bodyLengthMm": p["body_height"] if big else p["tee_z1"]-p["fan_back_z"],
               "coreLengthMm": length, "nativeAudit": "OFFLINE_ESTIMATE_ONLY" if big else "DIGITAL_FIVE_PART_SLICE_PASS",
               "validationLabel": "几何检查通过 · 离线试切估算 · 未放行打印" if big else "原始已核验切片 STL",
               **({"offlineEstimate": estimate} if big else {}),
               "physicalFitVerified": False}
    return {
        "schemaVersion": 1, "variantId": variant_id, "title": f"{label} · Y口直插 · {travel} mm 行程",
        "release": release, "ui": {"persistPanelState": True, "showSearch": True, "showGroups": True,
                                     **({"motionStateVersion": release["id"]} if big else {})},
        "teeReference": tee_contract,
        "instructions": [
            "拖动旋转，滚轮缩放；Tab 保留视角、爆炸比例、透明度及面板布局，各方案记住自己的气嘴和行程。",
            f"直接加载本次原始 STL：{label}，15 / 20 / 25 / 30 mm 四种出口。蓝色主体直插三通，不再使用中间透明管或外套夹紧件。",
            (f"Ø76 新壳长{p['body_height']} mm、收缩段{p['blend_length']} mm、内丝{p['female_length']} mm、名义风机套口ID76。薄壁区径向名义{p['thin_wall_radial_nominal']:.1f} mm、母沟底2.4 mm、三通插接段3 mm，卡槽结构保留。四个{length} mm气嘴与Ø41 v5文件完全相同。4圈墙离线试切约{estimate_text}，仅为单主体估算，未放行打印。导流件型式待确认，当前仅为光滑基础壳。"
             if big else "Ø41 v5 主体及气嘴保持原已切片文件不变。"),
            (f"本版首次打开默认缩回0 mm；嘴端超出主体插入端{p['protrusion_min']} mm，全行程为{p['protrusion_min']}..{p['protrusion_max']} mm。按参考承口深度{p['spigot_length']} mm计算，默认从Y管口量至嘴端为{p['spigot_length']+p['protrusion_min']} mm。几何改版不继承旧壳行程，之后Tab切换仍记忆各自位置。"
             if big else "原Ø41方案的气嘴和行程记忆保持不变。"),
            f"P{p['pitch']} 螺距不变，每圈轴向移动4 mm，本版机构行程 {travel} mm（{travel/p['pitch']:g} 圈）；只转动/移动绿色气嘴，主体与三通保持固定。",
            "气嘴从 Y 侧旋入；默认主体半透明以展示内芯。隐藏主体可看真实梯形螺纹；没有示意螺旋片或额外锁紧件。",
            "灰蓝色 Y 按商品首图重建三端加厚承口；上方进球支口向风机侧后倾，球进入交汇处后与出风同向。风机接直通主管，另一端出球。",
            "Y 承口 Ø50.2 按用户实测；总长 128 / 外径 56.38 按商家规格图（未实测）。止挡深度、交汇位置及通球安全范围仍待实物确认；机构全行程不等于安全通球行程。",
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
        for name in ["y-tee-preview-reference.scad", "fan41-preview-reference.scad"]:
            shutil.copy2(ROOT / "cad" / name, stage / "source" / name)
        y_mesh, fan41 = stage / "y-reference.stl", stage / "fan41-reference.stl"
        tee_source = ROOT / "cad/y-tee-preview-reference.scad"
        run_scad(args.openscad, tee_source, y_mesh, ['part="reference"'])
        binary_mesh(y_mesh)  # Reject collapsed faces / open or non-manifold seams BEFORE publishing.
        tee_echo = stage / "y-reference.echo"
        run_scad(args.openscad, tee_source, tee_echo, ['part="contract"'])
        match = re.search(r"ECHO: y_reference_contract = (\[.*\])", tee_echo.read_text())
        if not match:
            raise ValueError("Missing Y reference port contract")
        tee_contract = dict(json.loads(match.group(1)))
        tee_contract["source_sha256"] = sha(tee_source)
        tee_echo.unlink()
        run_scad(args.openscad, ROOT / "cad/fan41-preview-reference.scad", fan41)
        manifests = {key: build_variant(key, stage, args.openscad, y_mesh, fan41, tee_contract) for key in VARIANTS}
        y_mesh.unlink()
        fan41.unlink()
        manifests["fan76-direct"]["variantCatalog"] = {
            "defaultId": "fan76-direct", "variants": [
                {"id": "fan76-direct", "label": "Ø76 · 薄壁缓收缩 / 20 mm", "manifest": "./manifest.json"},
                {"id": "fan41-direct", "label": "Ø41 · Y口直插 / 40 mm", "manifest": "./manifest-fan41-direct.json"}]}
        for key, name in [("fan76-direct", "manifest.json"), ("fan41-direct", "manifest-fan41-direct.json")]:
            dump(stage / name, manifests[key])
        atomic_publish(stage, STAGING)
        atomic_publish(stage, DEPLOY)
        for key, manifest in manifests.items():
            print(f"{key}: {manifest['release']['id']}; P4 / {manifest['release']['travelMm']} mm; {manifest['release']['nativeAudit']}")
    print("Published /fan-nozzle/ on the EXISTING port 8877; printer untouched.")


if __name__ == "__main__":
    main()
