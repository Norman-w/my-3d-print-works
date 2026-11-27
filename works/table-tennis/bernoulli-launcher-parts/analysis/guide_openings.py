#!/usr/bin/env python3
"""Bound rigid-sphere eccentricity in the uncut guide with radial round holes.

The theorem covers every axial center position inside the guide and every
transverse direction in its interior connected component. Numerical checks
exercise the theorem; they do not substitute for its continuous proof.

Run: python3 -B analysis/guide_openings.py
Only standard-library modules are used. Manufacturing acceptance remains open.
"""

from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import math
import operator
from pathlib import Path
import re
import sys


OPS = {ast.Add: operator.add, ast.Sub: operator.sub,
       ast.Mult: operator.mul, ast.Div: operator.truediv}


def scalar(node: ast.AST, names: dict[str, float]) -> float:
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return float(node.value)
    if isinstance(node, ast.Name) and node.id in names:
        return names[node.id]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = scalar(node.operand, names)
        return -value if isinstance(node.op, ast.USub) else value
    if isinstance(node, ast.BinOp) and type(node.op) in OPS:
        return OPS[type(node.op)](scalar(node.left, names), scalar(node.right, names))
    raise ValueError("Unsupported scalar expression; no SCAD or Python code was executed")


def without_comments(source: str) -> str:
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
    return re.sub(r"//[^\n]*", "", source)


def read_scalar_parameters(path: Path) -> tuple[dict[str, float], bytes]:
    raw = path.read_bytes()
    values = {}
    for name, expression in re.findall(r"^\s*([A-Za-z_]\w*)\s*=\s*([^;]+);", without_comments(raw.decode("utf-8")), re.M):
        if name in values:
            raise ValueError(f"Duplicate scalar parameter: {name}")
        value = scalar(ast.parse(expression.strip(), mode="eval").body, values)
        if not math.isfinite(value):
            raise ValueError(f"Non-finite parameter: {name}")
        values[name] = value
    return values, raw


def module_body(source: str, name: str, arguments: str) -> str:
    matches = list(re.finditer(rf"\bmodule\s+{re.escape(name)}\s*\(\s*{re.escape(arguments)}\s*\)\s*\{{", source))
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one source module {name}({arguments})")
    match = matches[0]
    depth, start = 1, match.end()
    for index in range(start, len(source)):
        depth += (source[index] == "{") - (source[index] == "}")
        if depth == 0:
            return source[start:index]
    raise ValueError(f"Unclosed source module {name}")


def inspect_opening_contract(p: dict[str, float], source: str) -> dict:
    """Recognize this narrow CSG contract and reject silently changed openings.

    This is deliberately not a general OpenSCAD parser or a mesh inspection.
    Extra guide cutouts must trigger review instead of inheriting this theorem.
    """
    clean = without_comments(source)
    hole_body = re.sub(r"\s+", "", module_body(clean, "radial_hole", "z"))
    pattern = (r"translate\(\[([^,]+),0,z\]\)rotate\(\[0,90,0\]\)"
               r"cylinder\(h=([^,]+),r=([^;]+)\);")
    match = re.fullmatch(pattern, hole_body)
    if match is None:
        raise ValueError("radial_hole shape/axis contract changed; review before reusing the round-hole bound")
    if match.group(3) != "finger_tip_radius+radial_print_clearance":
        raise ValueError("radial_hole radius expression changed; review the new opening")
    start, length, radius = [scalar(ast.parse(expression, mode="eval").body, p)
                             for expression in match.groups()]
    expected_guide = (
        "difference(){"
        "translate([0,0,guide_start_z])cylinder(h=guide_length,d=guide_od);"
        "translate([0,0,guide_start_z-eps])cylinder(h=guide_length+2*eps,d=guide_id);"
        "radial_hole(0);radial_hole(-gate_spacing);}")
    guide_body = re.sub(r"\s+", "", module_body(clean, "guide", ""))
    if guide_body != expected_guide:
        raise ValueError("guide CSG contract changed or has additional cuts; this round-hole bound is not inherited")
    outer_radius = p["guide_od"] / 2
    if not (start <= -outer_radius and start + length >= outer_radius):
        raise ValueError("Expected an X-directed hole spanning both guide walls")
    return {
        "status": "RECOGNIZED_NARROW_CSG_CONTRACT",
        "hole_axis": "X",
        "hole_radius_expression": match.group(3),
        "hole_radius_mm": radius,
        "hole_axis_x_interval_mm": [start, start + length],
        "hole_axis_z_mm": [0.0, -p["gate_spacing"]],
        "guide_cut_count": 2,
        "wall_opening_count": 4,
        "scope": "The unsectioned guide() CSG dimensions/topology only. section_view=true deliberately removes material and is excluded. This is not an evaluated mesh or manufacturing inspection.",
    }


def center_offset_bound(guide_radius: float, ball_radius: float, hole_radius: float) -> float:
    if not 0 <= hole_radius < ball_radius <= guide_radius:
        raise ValueError("Round-hole theorem requires 0 <= hole_radius < ball_radius <= guide_radius")
    return math.sqrt(guide_radius ** 2 - hole_radius ** 2) - math.sqrt(ball_radius ** 2 - hole_radius ** 2)


def directional_limit(a: float, r: float, h: float, axial_offset: float, theta: float) -> float:
    """Necessary equatorial-rim bound; other axial slices can only restrict it."""
    k = math.sqrt(max(0.0, h * h - axial_offset * axial_offset)) if abs(axial_offset) < h else 0.0
    angle = abs((theta + math.pi / 2) % math.pi - math.pi / 2)
    alpha = math.asin(k / a)
    if angle >= alpha:
        return a - r
    delta = alpha - angle
    return a * math.cos(delta) - math.sqrt(r * r - a * a * math.sin(delta) ** 2)


def rim_clearance(a: float, r: float, h: float, axial_offset: float,
                  eccentricity: float, theta: float) -> float:
    """Compute Euclidean distance to surviving circle arcs, without the bound formula."""
    k = math.sqrt(max(0.0, h * h - axial_offset * axial_offset)) if abs(axial_offset) < h else 0.0
    x, y = eccentricity * math.cos(theta), eccentricity * math.sin(theta)
    # Four opening rim endpoints survive. Include the radial nearest point if
    # its position is on an intact arc. Infinitesimally adjacent material also
    # excludes any strict penetration at an opening boundary.
    rim_x = math.sqrt(a * a - k * k)
    distances = [math.hypot(x - sx * rim_x, y - sy * k)
                 for sx in (-1, 1) for sy in (-1, 1)]
    if abs(a * math.sin(theta)) >= k:
        distances.append(abs(a - eccentricity))
    return min(distances) - r


def numeric_limit(a: float, r: float, h: float, axial_offset: float, theta: float) -> float:
    k = math.sqrt(max(0.0, h * h - axial_offset * axial_offset)) if abs(axial_offset) < h else 0.0
    angle = abs((theta + math.pi / 2) % math.pi - math.pi / 2)
    delta = max(0.0, math.asin(k / a) - angle)
    lo, hi = 0.0, a * math.cos(delta)
    if rim_clearance(a, r, h, axial_offset, hi, theta) >= 0:
        raise ValueError("Numerical bound check could not bracket the interior collision boundary")
    for _ in range(65):
        midpoint = (lo + hi) / 2
        if rim_clearance(a, r, h, axial_offset, midpoint, theta) >= 0:
            lo = midpoint
        else:
            hi = midpoint
    return (lo + hi) / 2


def numerical_cross_check(p: dict[str, float], h: float) -> dict:
    a0, da = p["guide_id"] / 2, p["guide_clearance_budget"]
    rlo, rhi = p["ball_min_d"] / 2, p["ball_max_d"] / 2
    cases, maximum_error, violations = 0, 0.0, []
    axis_clearance_min, positive_control_count = math.inf, 0
    for a in sorted({a0 - da, a0, a0 + da}):
        for r in sorted({rlo, (rlo + rhi) / 2, rhi}):
            bound = center_offset_bound(a, r, h)
            for fraction in (-1.25, -1, -.75, -.5, -.25, 0, .25, .5, .75, 1, 1.25):
                dz = fraction * h
                alpha = math.asin(math.sqrt(max(0.0, h * h - dz * dz)) / a) if abs(dz) < h else 0.0
                angles = sorted({0.0, alpha / 4, alpha / 2, 3 * alpha / 4,
                                 alpha, alpha + .05, math.pi / 4, math.pi / 2})
                for theta in angles:
                    formula = directional_limit(a, r, h, dz, theta)
                    bisected = numeric_limit(a, r, h, dz, theta)
                    error = abs(formula - bisected)
                    maximum_error = max(maximum_error, error)
                    cases += 1
                    if error > 1e-9 or formula > bound + 1e-9:
                        violations.append({"A": a, "R": r, "axial_offset": dz,
                                           "theta": theta, "formula": formula,
                                           "numerical": bisected, "global_bound": bound})
            # Full 3-D single-hole wall check for the extremal axis-aligned
            # center: at every y, the closest surviving z is at the hole rim
            # or z=0. Include the exact minimizer y=h as well as a dense grid.
            for y in sorted({h} | {a * i / 2000 for i in range(2001)}):
                x = math.sqrt(max(0.0, a * a - y * y))
                z = math.sqrt(max(0.0, h * h - y * y))
                clearance = math.sqrt((x - bound) ** 2 + y * y + z * z) - r
                axis_clearance_min = min(axis_clearance_min, clearance)
            # A center just beyond the bound must penetrate surviving rim.
            if rim_clearance(a, r, h, 0.0, bound + 1e-4, 0.0) < 0:
                positive_control_count += 1
            else:
                violations.append({"A": a, "R": r, "case": "outside-bound positive control not detected"})
    return {
        "role": "Regression cross-check of the continuous proof, not a sampled substitute for all-direction coverage.",
        "axial_and_directional_cases": cases,
        "maximum_formula_vs_euclidean_bisection_error_mm": maximum_error,
        "axis_aligned_full_wall_sample_min_clearance_mm": axis_clearance_min,
        "outside_bound_positive_controls_detected": positive_control_count,
        "counterexamples": violations,
        "passed": not violations and axis_clearance_min >= -1e-9,
    }


def opening_report(p: dict[str, float], parameter_path: Path, parameter_raw: bytes,
                   geometry_path: Path, geometry_raw: bytes, run_cross_check: bool = True) -> dict:
    contract = inspect_opening_contract(p, geometry_raw.decode("utf-8"))
    h = contract["hole_radius_mm"]
    a0, da = p["guide_id"] / 2, p["guide_clearance_budget"]
    rlo, rhi = p["ball_min_d"] / 2, p["ball_max_d"] / 2
    if da < 0 or not 0 < h < rlo <= rhi < a0 - da:
        raise ValueError("The supplied envelope does not meet the round-hole theorem and positive guide-fit conditions")
    if p["guide_od"] / 2 <= a0 + da:
        raise ValueError("The budgeted inner radius reaches the nominal outer wall; no complete guide-wall bound is available")
    start, end = p["guide_start_z"], p["guide_start_z"] + p["guide_length"]
    axes = contract["hole_axis_z_mm"]
    if not all(start + h < z < end - h for z in axes):
        raise ValueError("A radial hole reaches a guide end; the present interior-hole source contract needs review")
    rows = []
    for a in sorted({a0 - da, a0, a0 + da}):
        for r in sorted({rlo, rhi}):
            bound = center_offset_bound(a, r, h)
            rows.append({"guide_id_mm": 2 * a, "ball_diameter_mm": 2 * r,
                         "uncut_bore_offset_mm": a - r,
                         "round_hole_maximum_offset_mm": bound,
                         "additional_offset_mm": bound - (a - r)})
    a = a0 + da
    bound = center_offset_bound(a, rlo, h)
    midpoint = (a - rlo + bound) / 2
    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "analysis_kind": "continuous_rigid_sphere_round_side_hole_eccentricity_bound",
        "sources": {
            "parameters": {"path": str(parameter_path.resolve()), "sha256": hashlib.sha256(parameter_raw).hexdigest()},
            "guide_csg": {"path": str(geometry_path.resolve()), "sha256": hashlib.sha256(geometry_raw).hexdigest()},
        },
        "source_contract": contract,
        "geometric_status": "CONTINUOUS_BOUND_CONDITIONAL_ON_RECOGNIZED_GUIDE_GEOMETRY",
        "physical_acceptance": "OPEN_NOT_EVALUATED",
        "proof": {
            "domain": "Rigid perfect sphere center in the guide's interior connected component, with its equatorial plane inside the unsectioned cylindrical guide.",
            "global_bound": "e <= sqrt(A^2-h^2)-sqrt(R^2-h^2), with 0<=h<R<=A.",
            "parameter_envelope": "The bound increases with guide radius A and hole radius h, and decreases with sphere radius R. Thus A_max and R_min bound the whole declared continuous parameter envelope; h is nominal because no manufacturing allowance for hole radius was supplied.",
            "equatorial_slice": "At axial center z, a round X-directed hole removes only arcs with |Y|<k, where k=sqrt(max(0,h^2-(z-z_hole)^2))<=h. With two aligned holes, use the largest k at that slice; their union does not widen this Y band.",
            "directional_bound": "Let alpha=asin(k/A), and theta be the direction from the nearer +/-X axis. If |theta|>=alpha, e<=A-R. Otherwise delta=alpha-|theta| and e<=A*cos(delta)-sqrt(R^2-A^2*sin(delta)^2).",
            "all_direction_argument": "The directional limit increases with delta when A>R and k<R. Thus its maximum is on the hole axis (theta=0), and then increases with k up to h. This establishes the bound for all lateral directions and all interior axial positions.",
            "three_dimensional_attainment": "For center (e,0,0) on one hole axis, the closest surviving wall has X=sqrt(A^2-Y^2), Z^2=max(0,h^2-Y^2). Squared distance decreases with Y^2 up to h^2 and increases thereafter; its minimum is at Y=+/-h,Z=0. The global bound is attained there for a single round hole. Additional aligned holes only remove material; the equatorial necessary bound still applies.",
            "disconnected_exterior": "Ball centers already outside the tube are a different feasible component. This theorem does not assert a bound on arbitrary points in exterior space or prevent entering around an open tube end.",
        },
        "guide_axial_interval_mm": [start, end],
        "hole_axis_separation_mm": abs(axes[0] - axes[1]),
        "hole_axial_window_gap_mm": abs(axes[0] - axes[1]) - 2 * h,
        "envelope_rows": rows,
        "largest_continuous_enclosing_disk_radius_mm": bound,
        "largest_additional_offset_mm": bound - (a - rlo),
        "counterexample_to_using_uncut_bore_offset": {
            "guide_id_mm": 2 * a, "ball_diameter_mm": 2 * rlo,
            "center_on_hole_axis_offset_mm": midpoint,
            "excess_over_A_minus_R_mm": midpoint - (a - rlo),
            "minimum_remaining_wall_clearance_mm": rim_clearance(a, rlo, h, 0, midpoint, 0),
            "meaning": "This ideal rigid ball fits the perforated guide beyond A-R, so treating the perforated guide as an uncut bore is not exact. This is a guide-only geometric witness, not a ball position satisfying every assembled gate component.",
        },
        "integration_rule": "Use e(A,R,h) as an enclosing disk for gate proofs. Off-axis points on that larger disk need not be physically reachable; an intersection there alone is a conservative-bound failure, not a demonstrated physical collision.",
        "shape_constraints_for_other_work": [
            "Preserve the inner circular-wall material outside the same |Y|<=h band at every tested ball-center axial plane.",
            "A wider tangential opening, another circumferential cut, a connected seam, or an opening into the end can invalidate the bound and requires a new source contract/proof.",
            "A purely axial slot confined to the same narrow Y band can admit a related upper-bound proof, but this script recognizes only the current two-round-hole source contract.",
            "Outer cam/slider/support cuts are irrelevant only if they do not intersect or remove the guide's bounding inner-wall material.",
        ],
        "open_items": [
            "No hole-size manufacturing tolerance, measured roundness, ball shell compliance or wear budget has been supplied; nominal hole radius is not a measured tolerance.",
            "Guide entry/exit motion, connected exterior passage, arbitrary extra cutouts and section_view=true are excluded.",
            "Contact forces, dynamic arrival, friction, deformation, actual printing and complete mechanism reliability are not analyzed.",
            "CSG contract recognition does not replace full assembly/mesh inspection; additional unrecognized geometry must not inherit this result.",
        ],
        "numerical_cross_check": numerical_cross_check(p, h) if run_cross_check else {"status": "NOT_RUN_IN_EMBEDDED_REPORT"},
    }


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parameters", type=Path, default=root / "cad/parameters.scad")
    parser.add_argument("--geometry", type=Path, default=root / "cad/kinematic-study.scad")
    parser.add_argument("--output", type=Path, default=root / "output/analysis/guide-openings.json")
    args = parser.parse_args()
    try:
        p, raw = read_scalar_parameters(args.parameters)
        result = opening_report(p, args.parameters, raw, args.geometry, args.geometry.read_bytes())
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    except (OSError, ValueError, KeyError, ZeroDivisionError) as error:
        print(f"OPENING_ANALYSIS_ERROR: {error}", file=sys.stderr)
        return 2
    print(result["geometric_status"])
    print(f"Maximum enclosing offset: {result['largest_continuous_enclosing_disk_radius_mm']:.9f} mm")
    print(f"Extra offset from side holes: {result['largest_additional_offset_mm']:.9f} mm")
    print(f"Directional/axial cross-check cases: {result['numerical_cross_check']['axial_and_directional_cases']}")
    print("Physical acceptance: OPEN_NOT_EVALUATED")
    print(args.output.resolve())
    return 0 if result["numerical_cross_check"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
