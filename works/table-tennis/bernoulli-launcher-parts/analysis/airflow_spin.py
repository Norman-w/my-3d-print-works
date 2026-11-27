#!/usr/bin/env python3
"""Reproducible nominal geometry ledger; not an airflow or spin-performance model."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "barrel_id", "hose_id", "ball_min_d", "ball_max_d", "guide_id",
    "guide_od", "guide_length", "transition_length", "body_id",
    "spin_guide_id", "spin_pad_width", "spin_pad_length",
    "spin_pad_thickness", "spin_adjustment_travel", "guide_clearance_budget",
)


def read_parameters(path: Path) -> tuple[dict[str, float], str]:
    """Read scalar literals only. Never execute SCAD or silently evaluate expressions."""
    raw = path.read_bytes()
    source = raw.decode("utf-8")
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    source = re.sub(r"//[^\n]*", "", source)
    values: dict[str, float] = {}
    for name in REQUIRED:
        matches = re.findall(rf"\b{re.escape(name)}\s*=\s*([^;]+);", source)
        if len(matches) != 1:
            raise ValueError(f"{name}: expected exactly one scalar assignment")
        try:
            value = float(matches[0].strip())
        except ValueError as exc:
            raise ValueError(f"{name}: expected a numeric literal, got {matches[0]!r}") from exc
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name}: expected a finite positive dimension")
        values[name] = value
    if values["ball_min_d"] > values["ball_max_d"]:
        raise ValueError("ball_min_d must not exceed ball_max_d")
    if not values["guide_id"] < values["guide_od"] < values["body_id"]:
        raise ValueError("require guide_id < guide_od < body_id for the annular bypass")
    return values, hashlib.sha256(raw).hexdigest()


def circle_area(diameter: float) -> float:
    return math.pi * diameter * diameter / 4.0


def annular_area(outer: float, inner: float) -> float:
    return max(0.0, circle_area(outer) - circle_area(inner))


def rounded(value: float) -> float:
    return round(value, 6)


def sample_ball(p: dict[str, float], diameter: float) -> dict:
    areas = {
        "hose_ball_equator": annular_area(p["hose_id"], diameter),
        "barrel_ball_equator": annular_area(p["barrel_id"], diameter),
        "guide_ball_equator": annular_area(p["guide_id"], diameter),
        "spin_guide_ball_equator_before_pad": annular_area(p["spin_guide_id"], diameter),
    }
    bypass = annular_area(p["body_id"], p["guide_od"])
    areas["nominal_bypass_before_solids"] = bypass
    areas["guide_plus_bypass_at_same_ball_equator_before_solids"] = (
        areas["guide_ball_equator"] + bypass
    )
    hose_gap = areas["hose_ball_equator"]
    barrel_gap = areas["barrel_ball_equator"]
    return {
        "ball_diameter_mm": rounded(diameter),
        "centered_radial_clearance_mm": {
            name: rounded((p[key] - diameter) / 2.0)
            for name, key in (
                ("hose", "hose_id"), ("barrel", "barrel_id"),
                ("guide", "guide_id"), ("spin_guide_before_pad", "spin_guide_id"),
            )
        },
        "nominal_cross_section_mm2": {key: rounded(value) for key, value in areas.items()},
        "geometry_ratios_not_flow_ratios": {
            "guide_ball_gap_to_hose_ball_gap": (
                rounded(areas["guide_ball_equator"] / hose_gap) if hose_gap > 0 else None
            ),
            "guide_ball_gap_to_barrel_ball_gap": (
                rounded(areas["guide_ball_equator"] / barrel_gap) if barrel_gap > 0 else None
            ),
        },
        "conditional_spin_reference": {
            "rpm_per_m_per_s_if_stationary_pad_no_slip": rounded(60000.0 / (math.pi * diameter)),
            "condition": "Ideal stationary contact, no slip, transverse spin axis; not a forecast or bound.",
        },
    }


def spin_throat_sensitivity(p: dict[str, float]) -> dict:
    """Screen a rigid transverse section, without assuming a contact force or safe squeeze."""
    smallest, largest = p["ball_min_d"], p["ball_max_d"]
    nominal_bore = p["spin_guide_id"]
    radial_budget = p["guide_clearance_budget"]
    travel = p["spin_adjustment_travel"]
    scenarios = []
    for name, radial_offset in (
        ("nominal", 0.0),
        ("hypothetical_radial_plus_budget", radial_budget),
        ("hypothetical_radial_minus_budget", -radial_budget),
    ):
        bore = nominal_bore + 2.0 * radial_offset
        if bore <= 0:
            raise ValueError("spin_guide_id minus twice guide_clearance_budget must be positive")
        smallest_contact_threshold = max(0.0, bore - smallest)
        largest_no_overlap_limit = bore - largest
        max_center_offset = max(0.0, (bore - smallest) / 2.0)
        candidate_intrusions = {travel * i / 4.0 for i in range(5)}
        candidate_intrusions.add(smallest_contact_threshold)
        if largest_no_overlap_limit >= 0:
            candidate_intrusions.add(largest_no_overlap_limit)
        sweep = []
        for intrusion in sorted(candidate_intrusions):
            throat = bore - intrusion
            sweep.append({
                "assumed_actual_pad_intrusion_mm": rounded(intrusion),
                "within_assumed_available_travel": intrusion <= travel + 1e-9,
                "effective_rigid_throat_mm": rounded(throat),
                "smallest_ball_signed_clearance_mm": rounded(throat - smallest),
                "smallest_ball_can_geometrically_avoid_pad": throat > smallest + 1e-9,
                "largest_ball_rigid_overlap_not_allowable_compression_mm": rounded(max(0.0, largest - throat)),
            })
        scenarios.append({
            "scenario": name,
            "hypothetical_radial_bore_offset_mm": rounded(radial_offset),
            "assumed_actual_bore_mm": rounded(bore),
            "centered_smallest_ball_first_tangency_intrusion_mm": rounded(max_center_offset),
            "smallest_ball_unavoidable_tangency_threshold_mm": rounded(smallest_contact_threshold),
            "largest_ball_no_rigid_overlap_intrusion_limit_mm": rounded(largest_no_overlap_limit),
            "fixed_intrusion_satisfies_both_geometry_conditions": (
                smallest_contact_threshold <= largest_no_overlap_limit + 1e-9
            ),
            "available_travel_shortfall_to_smallest_ball_tangency_mm": rounded(max(0.0, smallest_contact_threshold - travel)),
            "largest_ball_overlap_at_smallest_ball_tangency_threshold_mm": rounded(
                max(0.0, largest - (bore - smallest_contact_threshold))
            ),
            "finite_pad_width_check": {
                "assumed_centered_transverse_pad_width_mm": p["spin_pad_width"],
                "maximum_transverse_ball_center_offset_mm": rounded(max_center_offset),
                "pad_half_width_minus_center_offset_mm": rounded(p["spin_pad_width"] / 2.0 - max_center_offset),
                "covers_all_ball_center_projections_if_complete_circular_bore": p["spin_pad_width"] / 2.0 >= max_center_offset,
                "scope": "Section at the ball equator inside the usable axial pad length; actual alignment and CAD topology unverified.",
            },
            "intrusion_sweep": sweep,
        })
    conflict = any(
        not scenario["fixed_intrusion_satisfies_both_geometry_conditions"]
        or scenario["available_travel_shortfall_to_smallest_ball_tangency_mm"] > 0
        for scenario in scenarios
    )
    return {
        "status": (
            "GEOMETRY_CONFLICT_REQUIRES_MEASUREMENT_OR_REDESIGN"
            if conflict else "GEOMETRY_ONLY_CONTACT_FORCE_UNVERIFIED"
        ),
        "model": "One rigid planar pad opposed by a rigid low-friction guide, with effective throat T = B - p.",
        "assumptions": [
            "Actual unloaded radial face intrusion p equals adjustment travel; zero adjustment is flush with the reference bore.",
            "Pad width is transverse, centered and covers the relevant ball-center projections; ball equator traverses its usable axial length.",
            "A complete circular bore restricts transverse center offset to (B - D)/2; local rails or open slots require separate CAD analysis.",
            "Balls and guide are rigid; geometric overlap is a collision diagnostic, not an allowed deformation or load.",
        ],
        "bore_budget": {
            "source_parameter": "guide_clearance_budget",
            "radial_magnitude_mm": radial_budget,
            "interpretation": "Hypothetical signed radial bore variation only; not a measured print tolerance or automatic CAD compensation.",
            "diametral_effect": "Actual bore B = nominal spin_guide_id + 2 * hypothetical radial offset.",
        },
        "equations": {
            "effective_throat": "T = B - p",
            "centered_first_tangency": "p = (B - D) / 2",
            "unavoidable_tangency_allowing_eccentricity": "p >= B - D",
            "largest_ball_rigid_overlap": "max(0, D_max - (B - p))",
            "same_bore_fixed_setting_interval": "B - D_min <= p <= B - D_max; empty when D_max > D_min",
            "centered_finite_width_sufficient_section_check": "pad_width / 2 >= (B - D_min) / 2",
        },
        "scenarios": scenarios,
        "limits_and_required_evidence": [
            "Equality means tangency only; it does not establish a positive normal force, traction or measurable spin.",
            "The full diametral clearance B - D accounts for the ball shifting away; centered clearance cannot establish unavoidable contact.",
            "Finite-width coverage here does not prove actual pad alignment, entry geometry, edge contact or axial contact duration.",
            "Pad thickness is not automatically extra intrusion; its mounting datum, mechanism ratio, backlash and deformation must be measured.",
            "Measure the actual ball envelope and bore, actual face intrusion versus adjustment, and compliant contact behavior before setting stops.",
            "Do not accept a 1 mm geometric overlap as permitted ball compression; measure pad/ball deformation and damage or redesign guidance/compliance/stops.",
            "Increasing stroke to reach the smallest ball does not resolve the larger-ball overlap at that same setting.",
        ],
    }


def build_report(p: dict[str, float], digest: str, source_name: str) -> dict:
    lo, hi = p["ball_min_d"], p["ball_max_d"]
    diameters = sorted({lo + (hi - lo) * i / 4.0 for i in range(5)})
    bypass = annular_area(p["body_id"], p["guide_od"])
    return {
        "schema_version": 1,
        "analysis_kind": "nominal_section_geometry_only",
        "source": {"path": source_name, "sha256": digest},
        "units": {"length": "mm", "area": "mm2"},
        "parameters": p,
        "ball_envelope_is_measured": False,
        "physical_validation_status": "OPEN_NO_MEASUREMENTS",
        "claims_not_supported": [
            "airflow rate, pressure drop, available driving pressure, fan operating point",
            "Y-branch suction, reliable feed, single-shot rate, anti-pinch performance",
            "exit speed, spin speed, spin direction, monotonic pressure-to-spin adjustment",
            "first-print fit or first-assembly functional acceptance",
        ],
        "assumptions": [
            "Circular concentric nominal cross-sections; rigid spherical ball at its equator.",
            "Ball diameter range is a design sensitivity envelope, not measured manufacturing tolerance.",
            "Guide outer diameter is a continuous wall separating the guide from the annular bypass.",
            "Parallel-area sum is local geometry only; connected entrances and exits are not established here.",
            "Supports, gate fingers, slots, seals, joints and print error are not resolved by this script.",
            "No fan curve, airflow rate, pressure differential, friction coefficient or contact force is assumed.",
        ],
        "equations": {
            "circle_area": "pi * diameter_mm**2 / 4",
            "ball_equator_open_area": "max(0, pi * (bore_mm**2 - ball_mm**2) / 4)",
            "nominal_bypass_area": "pi * (body_id_mm**2 - guide_od_mm**2) / 4",
            "conditional_no_slip_rpm": "60000 * centre_speed_m_per_s / (pi * ball_diameter_mm)",
        },
        "empty_section_ledger_mm2": {
            "hose_full_bore": rounded(circle_area(p["hose_id"])),
            "barrel_full_bore": rounded(circle_area(p["barrel_id"])),
            "guide_full_bore": rounded(circle_area(p["guide_id"])),
            "body_full_bore_before_guide": rounded(circle_area(p["body_id"])),
            "nominal_bypass_before_solids": rounded(bypass),
            "guide_plus_bypass_before_solids": rounded(circle_area(p["guide_id"]) + bypass),
        },
        "empty_geometry_ratios_not_flow_ratios": {
            "guide_to_hose_full_bore": rounded((p["guide_id"] / p["hose_id"]) ** 2),
            "bypass_to_hose_full_bore": rounded(bypass / circle_area(p["hose_id"])),
        },
        "ball_diameter_sensitivity": [sample_ball(p, diameter) for diameter in diameters],
        "spin_throat_geometry_sensitivity": spin_throat_sensitivity(p),
        "cad_section_audit_required": [
            {"station": "upstream bypass entry", "cad_min_connected_area_mm2": None},
            {"station": "upper gate, all stroke positions", "cad_min_connected_area_mm2": None},
            {"station": "lower gate, all stroke positions", "cad_min_connected_area_mm2": None},
            {"station": "guide supports, joints and seal planes", "cad_min_connected_area_mm2": None},
            {"station": "reducer and downstream bypass return", "cad_min_connected_area_mm2": None},
            {"station": "spin pad and opposing guide, all settings", "cad_min_connected_area_mm2": None},
        ],
        "cad_audit_notes": [
            "Subtract the union of intruding solids, not overlapping part areas independently.",
            "Classify each slot as connected bypass, external leakage or blocked space; do not count every void as useful flow.",
            "Sweep axial sections and gate travel; a large mid-body annulus does not establish entry/exit area or continuity.",
            "A bypass can reduce ball driving differential and alter Y suction; larger area alone is not acceptance.",
            "Even a completed CAD area audit does not predict hydraulic resistance or validate real feeding.",
        ],
        "spin_notes": [
            "The stationary pad provides no energy source; measure exit speed together with rotation.",
            "Screw travel is not normal force, pad protrusion, friction coefficient or measured spin strength.",
            "Opposing-guide friction, ball compliance, eccentric contact and gravity can alter measured spin.",
            "The no-slip equation is a conditional kinematic reference; sliding contact can depart from it.",
        ],
        "ideal_passive_contact_example_not_performance_prediction": {
            "assumptions": [
                "Zero initial spin; thin spherical shell I = (2/3) m R**2.",
                "One stationary friction surface; no tangential force from the opposing guide.",
                "No continuing air work or other axial external impulse; deformation and impacts ignored.",
                "Contact persists until the initially sliding contact reaches zero relative velocity.",
            ],
            "impulse_equations": ["m * (v_in - v_out) = J", "I * abs(omega) = J * R"],
            "terminal_no_slip_condition": "v_out = abs(omega) * R",
            "conditional_result": "v_out = abs(omega) * R = (3/5) * v_in",
            "limitation": "Not a device speed prediction, fixed loss or bound; screw pressure alone cannot specify independent speed and spin.",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parameters", type=Path, default=ROOT / "cad" / "parameters.scad")
    parser.add_argument("--output", type=Path, default=ROOT / "output" / "analysis" / "airflow-spin.json")
    args = parser.parse_args()
    parameters_path = args.parameters.resolve()
    try:
        p, digest = read_parameters(parameters_path)
    except (OSError, UnicodeError, ValueError) as exc:
        parser.error(str(exc))
    try:
        source_name = parameters_path.relative_to(ROOT).as_posix()
    except ValueError:
        source_name = parameters_path.name
    report = build_report(p, digest, source_name)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output.resolve()}")
    print("Nominal geometry only; flow, single-shot function and spin performance remain OPEN.")


if __name__ == "__main__":
    main()
