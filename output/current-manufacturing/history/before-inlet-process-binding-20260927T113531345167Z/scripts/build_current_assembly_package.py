#!/usr/bin/env python3
"""Join source-enumerated installation requirements; never order or print.

The two input audits own their extraction. This join removes replaced host
instances, retains shared nuts once, and keeps kit members and subcomponents
at different accounting levels. Every run writes a new evidence directory.
"""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import csv
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
INPUTS = {
    "base": "output/current-assembly-package/base-hardware/inventory.json",
    "cable": "output/current-assembly-package/cable-hardware/hardware.json",
    "scene": "docs/cable-assembly-inventory.json",
    "manufacturing": "output/current-manufacturing/manifest.json",
    "selections": "docs/current-assembly-selections.json",
}


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def primary_group(part):
    key = part["id"].split("/", 1)[1]
    if part["group"] == "hold":
        return "退出保持附件"
    if part["group"] == "spin":
        return "旋转头台面装配"
    if key in ("positive-half", "negative-half"):
        return "主壳定位与外缝密封"
    if key == "liner" or key.startswith(("capture-", "pipe-clamp-")):
        return "出口内衬与PC固定"
    if key in ("fixed-spacer", "moving-spacer"):
        return "回位弹簧"
    if key == "beam-grip" or key.startswith("inlet-"):
        return "背梁与入口夹预组"
    if key.startswith("cable-input-"):
        return "输入模块台面装配"
    if key == "cable-output-cap":
        return "输出夹线与端盖"
    if key.startswith("cable-route-"):
        return "护套第三弯导向"
    return "挡指凸轮及导向"


def main():
    data = {key: json.loads((ROOT / file).read_text()) for key, file in INPUTS.items()}
    base, cable = data["base"], data["cable"]
    identity = {}

    def bind(file, digest):
        if file in identity:
            assert identity[file] == digest, ("Conflicting source identities", file)
        assert (ROOT / file).is_file() and sha(ROOT / file) == digest, ("Stale source", file)
        identity[file] = digest

    for name, file in INPUTS.items():
        bind(file, sha(ROOT / file))
    bind(str(Path(__file__).resolve().relative_to(ROOT)), sha(Path(__file__)))
    for report in (base, cable):
        assert report.get("source_stable", report.get("sources_stable", False))
        for file, digest in report["source_sha256"].items():
            bind(file, digest)

    removed = set(base["cable_adoption_hand_off"]["remove_in_cable_adoption"])
    retained = set(base["cable_adoption_hand_off"]["retain_in_cable_adoption"])
    original = {row["instance_id"]: row for row in base["instances"]}
    assert len(original) == len(base["instances"])
    assert len(removed) == 8 and len(retained) == 4
    assert not (removed & retained) and removed | retained <= original.keys()
    assert Counter(original[key]["spec_id"] for key in removed) == {
        "M4x20-socket": 4, "M4-washer-9x0.8": 4,
    }
    assert all(original[key]["spec_id"] == "M4-nut" for key in retained)
    assert cable["replacement_delta"]["remove_from_old_BOM"][0]["quantity"] == 4
    assert cable["replacement_delta"]["remove_from_old_BOM"][1]["quantity"] == 4

    # Only these five specifications are merged across independent audits.
    aliases = {
        "m3x16-socket": "M3x16-socket", "m3-nut": "M3-nut", "m4-nut": "M4-nut",
        "m3-flat-washer": "M3-washer-7x0.5", "m4-flat-washer": "M4-washer-9x0.8",
    }
    cable_specs = {row["item_id"]: row for row in cable["items"]}
    for key, canonical in aliases.items():
        b = base["specifications"][canonical]["dimensions_mm"]
        c = cable_specs[key]["nominal"]
        if key.endswith("socket"):
            pairs = [("length_under_head", "underhead_length_mm"), ("head_d", "head_diameter_mm"),
                     ("head_h", "head_height_mm"), ("hex_key", "socket_AF_mm")]
            assert c["thread_nominal"] == "M" + str(b["thread_nominal_d"])
        elif key.endswith("nut"):
            pairs = [("across_flats", "AF_mm"), ("thickness", "height_mm")]
            assert c["thread_nominal"] == "M" + str(b["thread_nominal_d"])
        else:
            pairs = [("ID", "ID_mm"), ("OD", "OD_mm"), ("thickness", "thickness_mm")]
        assert all(b[left] == c[right] for left, right in pairs), ("Mismatched merged spec", key)

    specs, occurrences, children = {}, [], []
    for key, value in base["specifications"].items():
        specs[key] = {
            "spec_id": key, "description": value["description"],
            "nominal_contracts": [{"source": INPUTS["base"], "spec_id": key, "details": value}],
            "accounting": "separate_assembly_item", "purchase_quantity": None,
            "ownership_status": "not_confirmed", "printable": False,
        }
    for row in base["instances"]:
        if row["instance_id"] in removed:
            continue
        modes = ["work", "held"] if row["scope"] == "feeder-base38" else row["installed_modes"]
        occurrences.append({
            "id": "base/" + row["instance_id"], "spec_id": row["spec_id"], "quantity": row["quantity"],
            "installed_modes": modes, "source_report": INPUTS["base"],
            "source_instance_id": row["instance_id"], "source_site": row["site_id"],
            "host_shared_retained": row["instance_id"] in retained,
        })
    for item in cable["items"]:
        key = item["item_id"]
        if item["procurement_category"].startswith("nonadditive_"):
            continue
        canonical = aliases.get(key, "cable/" + key)
        if canonical not in specs:
            specs[canonical] = {
                "spec_id": canonical, "description": item["name_zh"], "nominal_contracts": [],
                "accounting": "kit_member_requirement" if item["procurement_category"] == "kit_eligible_member"
                              else "separate_assembly_item",
                "purchase_quantity": None, "ownership_status": "not_confirmed", "printable": False,
            }
        specs[canonical]["nominal_contracts"].append({"source": INPUTS["cable"], "spec_id": key, "details": item})
    for selection in data["selections"]["selections"]:
        item = cable_specs[selection["cable_item_id"]]
        for dimension in ("thread_nominal", "underhead_length_mm", "head_diameter_mm", "head_height_mm"):
            assert selection["nominal"][dimension] == item["nominal"][dimension]
        assert selection["quantity"] == item["assembly_required_new_quantity"]
        canonical = aliases.get(item["item_id"], "cable/" + item["item_id"])
        specs[canonical]["description"] = selection["description"]
        specs[canonical]["design_selection"] = selection
        specs[canonical]["nominal_contracts"].insert(0, {
            "source": INPUTS["selections"], "spec_id": selection["id"], "details": selection,
        })
    cable_retained = []
    for row in cable["installed_occurrences"]:
        if row["change"] == "retained_from_baseline":
            cable_retained.append(row)
            continue
        if row["parent_occurrence_id"] is not None:
            children.append(row)
            continue
        occurrences.append({
            "id": "cable/" + row["occurrence_id"], "spec_id": aliases.get(row["item_id"], "cable/" + row["item_id"]),
            "quantity": row["quantity"], "installed_modes": ["work", "held"],
            "source_report": INPUTS["cable"], "source_instance_id": row["occurrence_id"],
            "source_site": row["installation_id"], "host_shared_retained": False,
        })
    assert len(cable_retained) == 4 and all(row["item_id"] == "m4-nut" for row in cable_retained)
    assert len({row["id"] for row in occurrences}) == len(occurrences)
    work = Counter()
    held = Counter()
    for row in occurrences:
        assert row["quantity"] == 1 and row["spec_id"] in specs
        if "work" in row["installed_modes"]:
            work[row["spec_id"]] += row["quantity"]
        if "held" in row["installed_modes"]:
            held[row["spec_id"]] += row["quantity"]
    assert work["M4x20-socket"] == held["M4x20-socket"] == 0
    assert held - work == {"M3x16-socket": 1, "M3-washer-7x0.5": 1}
    assert work["cable/m4x60-socket"] == 4
    rows = []
    for key in sorted(specs):
        if not held[key]:
            continue
        row = dict(specs[key])
        row.update(work_quantity=work[key], held_quantity=held[key], held_only_extra=held[key] - work[key],
                   required_inventory_quantity=held[key],
                   installation_ids=[o["id"] for o in occurrences if o["spec_id"] == key])
        rows.append(row)

    manufacturing = {r["instance_id"]: r for r in data["manufacturing"]["items"]}
    printed = [p for p in data["scene"]["parts"] if p["role"] == "printed"]
    assert len(printed) == 56 and {p["id"] for p in printed} == manufacturing.keys()
    picklist = []
    for p in printed:
        m = manufacturing[p["id"]]
        bind(m["current_stl"], m["current_stl_sha256"])
        held_only = p["id"] == "spin/hold-fork"
        assert (p["group"] == "hold") == held_only
        picklist.append({
            "instance_id": p["id"], "name": p["name"], "primary_assembly_group": primary_group(p),
            "material": m["material"], "inventory_quantity": 1,
            "work_installed_quantity": int(not held_only), "held_installed_quantity": 1,
            "source_stl": m["current_stl"], "source_stl_sha256": m["current_stl_sha256"],
            "selected_3mf": m["selected_3mf"], "candidate_3mf": m.get("candidate_3mf"),
            "process_status": m["process_status"], "pending_review": m["pending_review"],
            "note": "Primary group is a sorting aid, not proof of installation path or process release.",
        })
    assert sum(p["work_installed_quantity"] for p in picklist) == 55
    assert [p["instance_id"] for p in picklist if p["pending_review"]] == ["feeder/inlet-rear"]

    out = ROOT / "output/current-assembly-package/runs" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out.mkdir(parents=True)
    report = {
        "status": "CURRENT_ASSEMBLY_REQUIREMENTS_JOINED_NOT_A_PURCHASE_OR_RELEASE",
        "created_utc": datetime.now(timezone.utc).isoformat(), "source_sha256": identity,
        "sources_stable": all(sha(ROOT / p) == digest for p, digest in identity.items()),
        "bom": rows, "installed_occurrences": occurrences,
        "nonadditive_cable_children": children,
        "removed_baseline_instances": sorted(removed), "retained_shared_nut_instances": sorted(retained),
        "ignored_duplicate_retained_cable_records": [r["occurrence_id"] for r in cable_retained],
        "cable_procurement_options_not_additive": cable["procurement_roots_not_additive_with_members"],
        "printed_picklist": picklist,
        "counts": {"printed_inventory": 56, "printed_work_installed": 55, "printed_held_installed": 56,
                   "bom_specification_rows": len(rows), "printed_pending_instances": 1,
                   "mode_extra_fastener_instances": 2, "source_identities_verified": len(identity)},
        "scope": "Joined source-enumerated installation quantities and current print identities. Composite cable assemblies count as assembly items, not a claimed physical piece total. No owned-stock audit, supplier grade/torque/kit-content acceptance, collision rerun or purchase.",
        "open_items": base["limitations"] + cable["open_items"],
        "design_selections": data["selections"],
        "open_items_note": "Inherited audit limitations keep their original scope. output-m3-drive-envelope is now resolved only as an explicit BOM design choice; installed tool access, supplied part and torque remain unverified.",
        "manufacturing_release": False, "physical_acceptance": False,
        "purchased_in_this_run": False, "sent_to_printer": False,
    }
    assert report["sources_stable"]
    write_json(out / "manifest.json", report)
    with (out / "hardware.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        fields = ["spec_id", "description", "accounting", "work_quantity", "held_only_extra", "required_inventory_quantity", "purchase_quantity", "nominal_contracts"]
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row, nominal_contracts=json.dumps(row["nominal_contracts"], ensure_ascii=False)))
    with (out / "print-picklist.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(picklist[0]))
        writer.writeheader()
        writer.writerows(picklist)
    lines = ["# 当前装配五金需要量", "", "本表按当前源逐安装位置合并；数量是装配需要量，采购数仍未定。工作档与保持档不能相加。", "",
             "| 规格 | 工作档 | 保持档另加 | 两档共用备料 |", "|---|---:|---:|---:|"]
    for row in rows:
        if row["accounting"] == "separate_assembly_item":
            # Full dimensions and sourcing caveats stay in the JSON/CSV contract.
            detail = row["nominal_contracts"][0]["details"]
            nominal = detail.get("dimensions_mm", detail.get("nominal", {}))
            lines.append(f"| {row['description']} · `{json.dumps(nominal, ensure_ascii=False, separators=(',', ':'))}` | {row['work_quantity']} | {row['held_only_extra']} | {row['required_inventory_quantity']} |")
    lines += ["", "## 一套连续拉索的成员需要量", "", "以下是同一套拉索的功能成员。采购完整套件时先核随货清单，再补缺；不能完整套件加全部成员再买一遍。", "", "| 成员 | 装配需要 |", "|---|---:|"]
    for row in rows:
        if row["accounting"] == "kit_member_requirement":
            detail = row["nominal_contracts"][0]["details"]["nominal"]
            lines.append(f"| {row['description']} · `{json.dumps(detail,ensure_ascii=False,separators=(',', ':'))}` | {row['required_inventory_quantity']} |")
    lines += ["", "输出盖两颗M3×16在本次BOM中明确选择全牙DIN 912 / ISO 4762、2.5 mm内六角，头部名义外形不变；这是新增设计选型，原CAD提取没有画出驱动孔。供货参考为[Accu SSCF-M3-16-A2](https://www.accu.co.uk/metric-cap-head-screws/3822-SSCF-M3-16-A2)，未核库存或采购，实际工具与扭矩仍未验收。", "",
              "球头属于那一根钢芯；原厂M4夹丝螺钉属于端头组件，二者不再独立加购。四原M4安装螺母仅保留一次；四M4×60和四新位置垫片替换原短螺钉及旧位置垫片。捕获垫圈虽然与普通M4垫片名义尺寸相同，Type A边型和公差要求单列，不能无依据合并替换。", "",
              "56打印实例含退出保持叉，工作档装55；保持档另加该叉和上述一颗M3×16、一片M3垫片。55实例/41盘绑定与1实例/1盘候选状态不变。", "",
              "[机器清单](manifest.json) · [五金CSV](hardware.csv) · [56件取件表](print-picklist.csv)", "",
              "这里只整理当前装配需要量；孔槽工具、首件精度、摩擦、力学和气动验收未因此通过。"]
    (out / "README.md").write_text("\n".join(lines) + "\n")
    write_json(ROOT / "output/current-assembly-package/latest.json", {
        "directory": str(out.relative_to(ROOT)), "manifest": str((out / "manifest.json").relative_to(ROOT)),
        "manifest_sha256": sha(out / "manifest.json"), "status": report["status"],
        "manufacturing_release": False, "physical_acceptance": False,
    })
    print(json.dumps({"directory": str(out.relative_to(ROOT)), "counts": report["counts"], "status": report["status"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
