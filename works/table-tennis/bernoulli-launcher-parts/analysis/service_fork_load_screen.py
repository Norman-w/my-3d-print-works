#!/usr/bin/env python3
"""Bound the service fork's ideal beam load and expose unresolved joint load path."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
CAD = ROOT / "cad/electric-rocker-service-fork-screen.scad"
ROCKER = ROOT / "cad/electric-rocker-bridge-screen.scad"
GEOMETRY = ROOT / "output/electric-rocker-service-fork-screen/review.json"
SLICE = ROOT / "output/electric-rocker-service-fork-screen/slice-review.json"
PREVIOUS = ROOT / "output/electric-rocker-clamped-fork-screen/review.json"
OUT = ROOT / "output/electric-rocker-service-fork-screen/load-screen.json"


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def number(source: str, name: str) -> float:
    match = re.search(rf"\b{re.escape(name)}\s*=\s*([+-]?(?:\d+\.?\d*|\.\d+))\s*;", source)
    if not match:
        raise ValueError(f"Missing or changed SCAD scalar: {name}")
    return float(match.group(1))


def rounded(value: float) -> float:
    return round(value, 3)


def main() -> None:
    cad = CAD.read_text()
    rocker = ROCKER.read_text()
    geometry = json.loads(GEOMETRY.read_text())
    sliced = json.loads(SLICE.read_text())
    previous = json.loads(PREVIOUS.read_text())
    if geometry["status"] != "SERVICE_FORK_NOMINAL_ASSEMBLY_PATH_ONLY":
        raise ValueError("Service fork geometry review is not current")
    if sliced["geometry_review_sha256"] != digest(GEOMETRY):
        raise ValueError("Service fork slice review is stale")
    if previous["beam_load_scenario_only"]["deepened_nominal_height_z_mm"] != 11:
        raise ValueError("Predecessor beam section changed")

    beam_match = re.search(
        r"sf_box\(7,10,40,68,-18,-7\);", cad)
    if not beam_match:
        raise ValueError("Service fork beam geometry changed; review load path")
    if "rb_output_r = rb_input_r*2/3;" not in rocker:
        raise ValueError("Rocker output radius relationship changed")
    input_arm = number(rocker, "rb_input_r")
    output_arm = input_arm * 2 / 3
    if input_arm != 75 or output_arm != 50:
        raise ValueError("Rocker lever dimensions changed")
    if number(cad, "sf_base_mating_y") != 68:
        raise ValueError("Service fork mating plane changed")
    if "sf_bolt_z = [-14, 2];" not in cad and "sf_bolt_z = [-14,2];" not in cad:
        raise ValueError("Service fork bolt centers changed")
    if "pm_ycyl(y0,y1,sf_bolt_x,z,3.4);" not in cad or \
            "pm_ycyl(64,76,sf_bolt_x,z,3);" not in cad:
        raise ValueError("Service fork bolt/clearance sizes changed")

    width_x = 3.0
    height_z = 11.0
    span_y = 25.0  # Existing shell anchor at Y=40 to pivot at Y=65.
    section_modulus_x = width_x * height_z ** 2 / 6
    section_modulus_z = height_z * width_x ** 2 / 6
    cases = []
    for kgf in (4, 5):
        input_n = kgf * 9.80665
        output_n = input_n * input_arm / output_arm
        pivot_n = output_n - input_n
        moment_nmm = pivot_n * span_y
        cases.append({
            "seller_claim_kgf": kgf,
            "ideal_input_n": rounded(input_n),
            "ideal_opposing_output_n": rounded(output_n),
            "ideal_vertical_pivot_reaction_n": rounded(pivot_n),
            "whole_reaction_on_one_cheek_n": rounded(pivot_n),
            "beam_vertical_bending_moment_nmm": rounded(moment_nmm),
            "isolated_beam_vertical_nominal_stress_mpa":
                rounded(moment_nmm / section_modulus_x),
            "same_magnitude_x_side_load_sensitivity_mpa":
                rounded(moment_nmm / section_modulus_z),
        })
    if [r["isolated_beam_vertical_nominal_stress_mpa"] for r in cases] != \
            [r["deepened_nominal_straight_beam_stress_mpa"]
             for r in previous["beam_load_scenario_only"]["scenario_rows"]]:
        raise ValueError("Ideal beam calculation differs from predecessor")

    key_side_gap = number(cad, "sf_key_clearance")
    bolt_hole_d = 3.4
    bolt_d = 3.0
    bolt_radius_gap = (bolt_hole_d - bolt_d) / 2
    joint = {
        "key_nominal_one_side_gap_z_mm": key_side_gap,
        "m3_hole_d_mm": bolt_hole_d,
        "m3_shank_proxy_d_mm": bolt_d,
        "m3_shank_radial_gap_in_each_hole_mm": rounded(bolt_radius_gap),
        "m3_pair_possible_relative_float_mm": rounded(2 * bolt_radius_gap),
        "first_shear_contact_determinable_from_nominal_cad": False,
        "reason": "Depending on bolt position and clamp friction, shank contact can occur before or after the 0.3 mm key face gap closes; PETG print tolerances and preload are unknown.",
    }
    base_rotation = sliced["orientations"]["base-x-plus-90-tree"]["rotation_x_deg"]
    if base_rotation != 90:
        raise ValueError("Base print orientation changed")
    report = {
        "status": "SERVICE_FORK_LOAD_PATH_UNRELEASED",
        "source_sha256": {
            str(path.relative_to(ROOT)): digest(path)
            for path in (Path(__file__), CAD, ROCKER, GEOMETRY, SLICE, PREVIOUS)
        },
        "beam_nominal_mm": {
            "width_x": width_x,
            "height_z": height_z,
            "pivot_to_shell_anchor_span_y": span_y,
            "vertical_section_modulus_mm3": rounded(section_modulus_x),
            "x_side_load_section_modulus_mm3": rounded(section_modulus_z),
        },
        "seller_claim_static_idealization_only": cases,
        "joint_nominal_play": joint,
        "base_print_orientation": {
            "rotation_x_deg": base_rotation,
            "source_y_beam_axis_maps_to_build_z": True,
            "layer_bond_tension_at_beam_root_possible": True,
            "layer_strength_measured": False,
        },
        "limitations": [
            "Seller 4-5 kgf force is unverified for the purchased BY141-3 SKU and is not a full-stroke load curve.",
            "Ideal vertical input/output opposition and load sharing between cheeks are assumptions, not measured behavior.",
            "Straight-beam stress omits root notches, bolt-hole effects, key-root stress, clamp preload, shell-boss strength, impacts, fatigue and creep.",
            "X-side-load case is only a same-force sensitivity; actual side force is unknown.",
            "No allowable PETG stress or safety factor is asserted without the printed orientation and actual material/process data.",
        ],
        "rear_joint_strength_verified": False,
        "structural_release": False,
        "manufacturing_release": False,
        "physical_acceptance": False,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"{report['status']}: {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
