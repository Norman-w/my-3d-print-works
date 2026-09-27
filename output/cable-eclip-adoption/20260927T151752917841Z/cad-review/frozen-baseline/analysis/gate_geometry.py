#!/usr/bin/env python3
"""Screen a two-gate ball escapement; this is not dynamic or physical acceptance.

Only the Python standard library is used. Source dimensions are read from SCAD,
not duplicated here. Sphere/capsule exclusion is exact for the stated ideal
shapes. Conservative interval bounds cover all ball diameters and lateral
positions in the declared envelope; a separate sampled mixed-ball sweep helps
find model/implementation mistakes and supplies inspectable witness states.

Run: python3 analysis/gate_geometry.py
Exit 0: covered static checks have no counterexample; physical gates remain open.
Exit 1: a covered static check fails. Exit 2: malformed input or analysis error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
from datetime import datetime, timezone

try:
    from .guide_openings import center_offset_bound, opening_report, read_scalar_parameters
except ImportError:
    from guide_openings import center_offset_bound, opening_report, read_scalar_parameters


REQUIRED = (
    "ball_min_d", "ball_max_d", "guide_id", "guide_od", "guide_start_z", "guide_length",
    "finger_tip_radius", "finger_closed_center_r", "finger_open_center_r",
    "gate_spacing", "gate_overlap_fraction", "cam_stroke",
    "guide_clearance_budget", "gate_position_budget", "radial_print_clearance",
)


def read_parameters(path: Path) -> tuple[dict[str, float], bytes]:
    values, raw = read_scalar_parameters(path)
    missing = set(REQUIRED) - values.keys()
    if missing:
        raise ValueError(f"Missing parameters: {sorted(missing)}")
    if not all(math.isfinite(v) for v in values.values()):
        raise ValueError("Non-finite parameter")
    if not (0 < values["ball_min_d"] <= values["ball_max_d"]):
        raise ValueError("Invalid ball diameter envelope")
    if not 0 <= values["gate_overlap_fraction"] < 1:
        raise ValueError("gate_overlap_fraction must be in [0, 1)")
    for key in REQUIRED:
        if key not in ("guide_start_z", "gate_overlap_fraction", "guide_clearance_budget", "gate_position_budget", "radial_print_clearance") and values[key] <= 0:
            raise ValueError(f"Expected positive parameter: {key}")
    if min(values["guide_clearance_budget"], values["gate_position_budget"], values["radial_print_clearance"]) < 0:
        raise ValueError("Budgets must be nonnegative")
    if values["finger_open_center_r"] <= values["finger_closed_center_r"]:
        raise ValueError("Open finger center must be farther from axis than closed")
    return values, raw


def root_nonnegative(value: float) -> float:
    return math.sqrt(max(0.0, value))


def escape_witness(e: float, positive: float, negative: float) -> tuple[float, tuple[float, float]]:
    """Largest nearest-tip distance on the ball-center disk at a gate plane.

    Tip centers are (+positive, 0) and (-negative, 0) in the y,z plane.
    For each y the largest clearance is on the disk boundary. The two linear
    branches there meet at y=(positive-negative)/2, clipped to the disk.
    This includes off-axis escape orthogonal to the line joining the fingers.
    """
    y = max(-e, min(e, (positive - negative) / 2))
    z = root_nonnegative(e * e - y * y)
    nearest_sq = min((y - positive) ** 2 + z * z,
                     (y + negative) ** 2 + z * z)
    return math.sqrt(nearest_sq), (y, z)


def stop_depth(radius: float, tip_radius: float, point: tuple[float, float],
               tips: tuple[float, float]) -> float:
    """Axial distance from gate plane at first contact for fixed lateral center."""
    y, z = point
    distance_sq = min((y - tips[0]) ** 2 + z * z,
                      (y + tips[1]) ** 2 + z * z)
    return root_nonnegative((radius + tip_radius) ** 2 - distance_sq)


def lateral_points(e: float) -> list[tuple[float, float]]:
    points = [(0.0, 0.0)]
    for fraction, count in ((0.5, 8), (1.0, 16)):
        for i in range(count):
            angle = 2 * math.pi * i / count
            points.append((fraction * e * math.cos(angle), fraction * e * math.sin(angle)))
    return points


def sample_mixed_pairs(p: dict[str, float], hole_radius: float) -> dict:
    """Rigid, touching spheres already parked at the downstream gate.

    Directly check every sampled sphere against each rear tip at each spacing.
    The rear tips translate radially inward and stay outside all ball-center
    radial positions; their final position is the closest point in that sweep.
    Thus final clearance suffices for this specific radial insertion motion.
    """
    rlo, rhi = p["ball_min_d"] / 2, p["ball_max_d"] / 2
    radii = sorted({rlo, (rlo + rhi) / 2, rhi})
    budget = p["gate_position_budget"]
    closed = p["finger_closed_center_r"]
    centers = sorted({closed - budget, closed + budget})
    tips = [(a, b) for a in centers for b in centers]
    guide_radii = sorted({p["guide_id"] / 2 - p["guide_clearance_budget"],
                          p["guide_id"] / 2,
                          p["guide_id"] / 2 + p["guide_clearance_budget"]})
    spacings = sorted({p["gate_spacing"] - 2 * budget, p["gate_spacing"],
                       p["gate_spacing"] + 2 * budget})
    count, failures = 0, 0
    min_clearance = math.inf
    witness = None
    counterexamples = []
    tip_radius = p["finger_tip_radius"]
    for a in guide_radii:
        for r1 in radii:
            for r2 in radii:
                if a < max(r1, r2):
                    continue  # Fit failure is separately and explicitly reported.
                for q1 in lateral_points(center_offset_bound(a, r1, hole_radius)):
                    for q2 in lateral_points(center_offset_bound(a, r2, hole_radius)):
                        lateral_sq = (q1[0] - q2[0]) ** 2 + (q1[1] - q2[1]) ** 2
                        pitch = root_nonnegative((r1 + r2) ** 2 - lateral_sq)
                        for front in tips:
                            h = stop_depth(r1, tip_radius, q1, front)
                            for rear in tips:
                                for spacing in spacings:
                                    state_margin = math.inf
                                    for radius, q, distance in (
                                        (r1, q1, spacing - h),
                                        (r2, q2, h + pitch - spacing),
                                    ):
                                        for tip_y in (rear[0], -rear[1]):
                                            separation = math.sqrt(distance ** 2 + (q[0] - tip_y) ** 2 + q[1] ** 2)
                                            state_margin = min(state_margin, separation - radius - tip_radius)
                                    count += 1
                                    state = None
                                    if state_margin < min_clearance or (state_margin < -1e-9 and len(counterexamples) < 12):
                                        state = {
                                            "ball_diameters_mm": [2 * r1, 2 * r2],
                                            "guide_id_mm": 2 * a,
                                            "first_center_yz_mm": list(q1),
                                            "second_center_yz_mm": list(q2),
                                            "front_tip_centers_radial_mm": list(front),
                                            "rear_tip_centers_radial_mm": list(rear),
                                            "spacing_mm": spacing,
                                            "axial_ball_pitch_mm": pitch,
                                            "first_center_x_mm": -h,
                                            "second_center_x_mm": -h - pitch,
                                            "min_tip_to_ball_surface_clearance_mm": state_margin,
                                        }
                                    if state_margin < min_clearance:
                                        min_clearance, witness = state_margin, state
                                    if state_margin < -1e-9:
                                        failures += 1
                                        if len(counterexamples) < 12:
                                            counterexamples.append(state)
    return {
        "method": "Direct sphere versus both spherical tips, including unequal left/right tip offsets, touching mixed-size balls, and boundary/interior centers of the side-hole-expanded enclosing disks.",
        "diameters_sampled_mm": [2 * r for r in radii],
        "lateral_points_per_ball": 25,
        "sampled_states": count,
        "intersecting_states": failures,
        "min_surface_clearance_mm": min_clearance if count else None,
        "worst_sample": witness,
        "counterexamples": counterexamples,
        "scope": "Sampled cross-check only; continuous coverage is provided by the separate conservative interval bound. Requires the first ball to be seated at the front gate. The expanded disks are a superset of physical center positions; any intersection reported in them alone is a conservative-screen failure, not a proven physically reachable collision.",
    }


def cam_positions(t: float, p: dict[str, float]) -> tuple[float, float]:
    """Analytical candidate profile; no assertion that a solid cam implements it."""
    move = (1 - p["gate_overlap_fraction"]) / 2
    front_start = 1 - move
    closed, opened = p["finger_closed_center_r"], p["finger_open_center_r"]
    rear = opened + (closed - opened) * min(1.0, max(0.0, t / move))
    front = closed + (opened - closed) * min(1.0, max(0.0, (t - front_start) / move))
    return front, rear


def cam_analysis(p: dict[str, float], amax: float, rmin: float, hole_radius: float) -> dict:
    e = center_offset_bound(amax, rmin, hole_radius)
    # Use the smaller intact-bore disk for escape counterexample witnesses;
    # arbitrary off-axis points of the expanded disk may not be reachable.
    witness_e = amax - rmin
    tip_radius, budget = p["finger_tip_radius"], p["gate_position_budget"]
    threshold = root_nonnegative((rmin + tip_radius) ** 2 - e ** 2)
    move = (1 - p["gate_overlap_fraction"]) / 2
    failures = []
    min_margin = math.inf
    for i in range(1001):
        t = i / 1000
        front, rear = cam_positions(t, p)
        margin = max(threshold - front - budget, threshold - rear - budget)
        min_margin = min(min_margin, margin)
        if margin <= 0 and len(failures) < 12:
            failures.append({"trigger_fraction": t, "front_center_mm": front,
                             "rear_center_mm": rear, "best_gate_blocking_margin_mm": margin})
    # A late ball at the rear plane can stop the rear finger before closure.
    contact_center = rmin + tip_radius + e
    closed, opened = p["finger_closed_center_r"], p["finger_open_center_r"]
    obstructed_fraction = move * (opened - contact_center) / (opened - closed)
    rigid_front, rigid_rear = cam_positions(max(0.0, min(1.0, obstructed_fraction)), p)
    eventual_front, _ = cam_positions(1.0, p)
    escape, escape_point = escape_witness(witness_e, contact_center, contact_center)
    one_lag_escape, one_lag_point = escape_witness(witness_e, contact_center, closed + budget)
    return {
        "profile_status": "ANALYSIS_CANDIDATE_ONLY_NOT_SOLID_CAM_VERIFICATION",
        "profile": {
            "press_rear_closes_trigger_mm": [0, move * p["cam_stroke"]],
            "press_both_closed_trigger_mm": [move * p["cam_stroke"], (1 - move) * p["cam_stroke"]],
            "press_front_opens_trigger_mm": [(1 - move) * p["cam_stroke"], p["cam_stroke"]],
            "return": "Traverse exactly the same position curve in reverse; partial reversal remains on that curve only with positive captive linkage.",
        },
        "geometric_invariant": "For every trigger position, at least one actual gate center radius is below the worst-case blocking threshold; this is about actual positions, not commanded timing.",
        "critical_actual_center_radius_mm": threshold,
        "minimum_blocking_center_radius_margin_mm": min_margin,
        "sampled_trigger_positions": 1001,
        "sample_counterexamples": failures,
        "continuous_argument": "With nonnegative overlap, at least one commanded gate remains fully closed throughout each linear segment and the central dwell; include the stated outward center-position budget in its blocking test.",
        "conditioned_result": "HOLDS_FOR_STATED_POSITION_CURVE" if not failures else "FAILS",
        "required_physical_constraints": [
            "Each of four sliders must follow its actual closed-track cam; obstruction of either slider must prevent further common trigger travel before the other gate opens.",
            "No follower escape, spring override, unbudgeted groove clearance, sliding pin, linkage buckling or housing deflection may let the trigger bypass a stalled gate.",
            "A gate means both opposed fingers and their guide restrictions, not the average position of two independent fingers.",
            "One-ball pocket capacity and departure/arrival state must be separately demonstrated; this invariant alone is not an exactly-one release proof.",
        ],
        "asynchronous_counterexamples": [
            {
                "case": "Late ball centered on the rear gate plane during closure",
                "ball_diameter_mm": 2 * rmin,
                "ball_center_yz_mm": [e, 0],
                "rear_finger_first_contact_center_mm": contact_center,
                "ideal_rigid_trigger_stall_fraction": obstructed_fraction,
                "front_center_at_that_fraction_mm": rigid_front,
                "rear_profile_center_at_that_fraction_mm": rigid_rear,
                "outcome_with_positive_rigid_cam": "The trigger stalls with the front gate still closed; no claim of smooth cycling or absence of ball damage.",
                "outcome_if_linkage_can_override": {
                    "front_eventually_open_center_mm": eventual_front,
                    "rear_left_behind_center_mm": contact_center,
                    "rear_off_axis_escape_center_yz_mm": list(escape_point),
                    "escape_witness_uses_intact_bore_disk_radius_mm": witness_e,
                    "rear_escape_surface_clearance_mm": escape - rmin - tip_radius,
                    "only_one_rear_finger_lags_other_at_closed_outward_budget": {
                        "tip_center_radii_mm": [contact_center, closed + budget],
                        "escape_center_yz_mm": list(one_lag_point),
                        "escape_surface_clearance_mm": one_lag_escape - rmin - tip_radius,
                    },
                    "meaning": "A geometrically open path exists if both rear fingers remain retracted here while the front opens. This is a counterexample to timing-only assurance, not a simulated double shot.",
                },
            },
            {
                "case": "Trigger pressed before any ball is seated",
                "outcome": "Rear can close and front open around an empty pocket; an arriving ball remains upstream. Exactly one shot per press is impossible without a ready condition or a wait/arming mechanism.",
            },
            {
                "case": "Return starts while released ball still intersects the front gate closing sweep",
                "outcome": "A rigid cam can stall or load the ball shell. Feed speed, trigger reversal and spin-pad drag are absent from this static calculation.",
            },
        ],
    }


def analyze(p: dict[str, float], source: Path, raw: bytes, geometry_path: Path | None = None) -> dict:
    geometry_path = geometry_path or source.parent / "kinematic-study.scad"
    openings = opening_report(p, source, raw, geometry_path, geometry_path.read_bytes(), run_cross_check=False)
    hole_radius = openings["source_contract"]["hole_radius_mm"]
    rmin, rmax = p["ball_min_d"] / 2, p["ball_max_d"] / 2
    a = p["guide_id"] / 2
    amin, amax = a - p["guide_clearance_budget"], a + p["guide_clearance_budget"]
    budget, tip = p["gate_position_budget"], p["finger_tip_radius"]
    closed_lo, closed_hi = p["finger_closed_center_r"] - budget, p["finger_closed_center_r"] + budget
    open_lo = p["finger_open_center_r"] - budget
    spacing_interval = [p["gate_spacing"] - 2 * budget, p["gate_spacing"] + 2 * budget]
    emax = center_offset_bound(amax, rmin, hole_radius)
    if amin <= 0 or closed_lo <= emax:
        raise ValueError("Model requires positive guide radius and tip centers outside the ball-center disk")
    if amax < rmax:
        raise ValueError("No admissible guide fit for the full ball envelope")
    escape_distance, escape_point = escape_witness(emax, closed_hi, closed_hi)
    closed_margin = rmin + tip - escape_distance
    open_margin = open_lo - rmin - emax - tip
    hmin = root_nonnegative((rmin + tip) ** 2 - closed_hi ** 2 - emax ** 2)
    hmax = max(root_nonnegative((radius + tip) ** 2 - (closed_lo - center_offset_bound(amax, radius, hole_radius)) ** 2)
               for radius in (rmin, rmax))
    pitch_min = root_nonnegative((2 * rmin) ** 2 - (2 * emax) ** 2)
    robust_window = [2 * hmax, hmin + pitch_min - hmax]
    spacing_margin = min(spacing_interval[0] - robust_window[0], robust_window[1] - spacing_interval[1])
    nominal_hmin = root_nonnegative((rmin + tip) ** 2 - p["finger_closed_center_r"] ** 2)
    nominal_hmax = root_nonnegative((rmax + tip) ** 2 - p["finger_closed_center_r"] ** 2)
    closed_pocket_center_span = spacing_interval[1] - 2 * hmin
    pocket_capacity_margin = pitch_min - closed_pocket_center_span
    # Coordinate x in the pair derivation is CAD z: front plane 0, rear -L.
    # The maxima below deliberately combine independent extrema; containment
    # of this larger interval covers every mixed-size/offset parked pair.
    guide_start = p["guide_start_z"]
    guide_end = guide_start + p["guide_length"]
    parked_pair_min = -budget - hmax - 2 * rmax - rmax
    parked_pair_max = budget - hmin + rmax
    guide_margins = [parked_pair_min - guide_start, guide_end - parked_pair_max]
    sampled = sample_mixed_pairs(p, hole_radius)
    cam = cam_analysis(p, amax, rmin, hole_radius)
    checks = {
        "guide_fit_positive": 2 * amin - 2 * rmax > 0,
        "guide_axially_contains_full_parked_pair_envelope": min(guide_margins) > 0,
        "closed_gate_blocks_all_declared_lateral_centers": closed_margin > 0,
        "open_gate_clears_all_declared_lateral_centers": open_margin > 0,
        "spacing_inside_conservative_parked_pair_window": spacing_margin > 0,
        "closed_pocket_cannot_contain_two_rigid_ball_centers": closed_margin > 0 and pocket_capacity_margin > 0,
        "sampled_mixed_pair_insertions_have_no_intersections": sampled["intersecting_states"] == 0,
        "candidate_cam_position_curve_maintains_one_blocking_gate": cam["conditioned_result"] == "HOLDS_FOR_STATED_POSITION_CURVE",
    }
    return {
        "schema_version": 2,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {"path": str(source.resolve()), "sha256": hashlib.sha256(raw).hexdigest()},
        "guide_opening_source": openings["sources"]["guide_csg"],
        "units": "mm except stated dimensionless fractions",
        "overall_physical_acceptance": "OPEN_NOT_EVALUATED",
        "static_screen_status": "NO_COUNTEREXAMPLE_WITHIN_STATED_STATIC_MODEL" if all(checks.values()) else "STATIC_REQUIREMENT_FAILURE",
        "checks": checks,
        "parameters_used": {name: p[name] for name in REQUIRED},
        "budget_interpretation": {
            "guide_clearance_budget": "Independent +/- radial guide-radius budget, not diameter budget and not a measured printer tolerance.",
            "gate_position_budget": "Each finger has independent +/- radial center error; each gate plane has independent +/- axial error, giving twice this budget in relative gate spacing.",
            "other_print_clearances": "radial_print_clearance enlarges the nominal radial-hole radius according to its CAD expression; it is not additionally counted as a hole-size manufacturing tolerance. axial_print_clearance is an assembly design gap, not automatically a manufacturing error.",
            "tip_radius": "Exact spherical cap radius from SCAD; no separate tip-size, wear, seam, ovality or angular-misalignment tolerance has been supplied.",
            "guide_axial_endpoints": "Nominal start and length from SCAD; the gate axial-position budget is included in the ball envelope, but no additional measured guide-length/placement tolerance has been supplied.",
            "ball_envelope": "40-41 mm is a selected analysis envelope read from parameters; not a statement of the user's measured balls or a sport standard.",
        },
        "model_assumptions": [
            "Rigid perfect spheres; the recognized cylindrical guide with aligned round side holes constrains centers to the enclosing disk e=sqrt(A^2-hole_radius^2)-sqrt(R^2-hole_radius^2). This holds for all lateral directions in the interior connected component, not just centers aligned with a hole.",
            "Opposed spherical caps of equal radius have centers in one gate plane; radial cylindrical shanks extend outward and do not protrude farther into the ball-center disk.",
            "The two X-directed through-holes (four wall openings) are included by a recognized CSG source contract and a continuous enclosing bound. Additional bypass ports, seams, joints, slots or guide-end escape paths are not inherited. Outward cylindrical rods are covered only by the ideal radial capsule condition, not by a parsed assembled solid model.",
            "Insertion proof starts with the first ball parked against the closed front gate and a second ball touching it, with no shell deformation.",
            "Every lateral ball center is allowed anywhere in its side-hole-expanded enclosing disk, a deliberately larger domain than the true anisotropic feasible set. This includes unequal mixed-diameter balls and opposite-wall offsets.",
            "The candidate cam law is explicitly defined in this report; parameters alone do not specify or prove manufactured cam tracks.",
        ],
        "guide_fit": {
            "guide_id_interval_mm": [2 * amin, 2 * amax],
            "minimum_diametral_clearance_mm": 2 * amin - 2 * rmax,
            "maximum_ball_center_eccentricity_mm": emax,
            "uncut_bore_maximum_eccentricity_mm": amax - rmin,
            "additional_eccentricity_from_nominal_side_holes_mm": emax - (amax - rmin),
            "guide_length_mm": p["guide_length"],
            "cad_axis_convention": "CAD z is the feed axis; front gate nominal z=0 and rear gate nominal z=-gate_spacing. The pair derivation uses x for the same axis.",
            "guide_axial_interval_mm": [guide_start, guide_end],
            "conservative_full_parked_pair_axial_envelope_mm": [parked_pair_min, parked_pair_max],
            "axial_envelope_formula": "upstream=-gate_budget-h_max-2*R_max-R_max; downstream=+gate_budget-h_min+R_max. Full sphere extents, all diameter mixtures and bounded lateral offsets are included conservatively.",
            "upstream_and_downstream_containment_margins_mm": guide_margins,
            "axial_placement_caveat": "Full stationary parked-pair extents fit only if both reported margins are positive. Nominal round-hole eccentricity is included; moving arrival/departure through ends, entrance transitions, hole manufacturing error and additional bypass/slot cuts remain unverified.",
        },
        "guide_openings": {
            "source_contract": openings["source_contract"],
            "continuous_proof": openings["proof"],
            "standalone_check": "python3 -B analysis/guide_openings.py; output/analysis/guide-openings.json",
            "manufacturing_hole_size_tolerance": "NOT_SUPPLIED_OPEN",
        },
        "gate_blocking": {
            "formula": "max_(y^2+z^2<=e^2) min(|(y,z)-(c_plus,0)|, |(y,z)-(-c_minus,0)|) < R+r; for symmetric tips this is sqrt(c^2+e^2)<R+r.",
            "closed_worst_ball_diameter_mm": 2 * rmin,
            "closed_worst_tip_center_radius_mm": closed_hi,
            "closed_worst_ball_center_yz_mm": list(escape_point),
            "closed_witness_scope": "Worst point of the expanded enclosing disk; this particular off-axis point need not be physically reachable in the perforated guide. Its positive margin is a sufficient all-position bound.",
            "closed_minimum_configuration_space_overlap_mm": closed_margin,
            "closed_squared_margin_mm2": (rmin + tip) ** 2 - escape_distance ** 2,
            "open_formula": "c_open_min-R_min-e(A_max,R_min,hole_radius)-tip_radius>0. R+e(A,R,h) decreases with R, so the smallest sphere supplies the largest radial reach.",
            "open_minimum_surface_clearance_mm": open_margin,
        },
        "coaxial_touching_ball_window": {
            "formula_equal_balls": "h=sqrt((R+r)^2-c^2); 2*h <= L <= 2*R. Equality is contact, not design margin.",
            "formula_mixed_balls": "h1+h_rear1 <= L <= h1+(R1+R2)-h_rear2; equal front/rear geometries give 2*h1 <= L <= h1+R1+R2-h2.",
            "conservative_nominal_window_over_all_mixed_diameters_mm": [2 * nominal_hmax, nominal_hmin + 2 * rmin - nominal_hmax],
            "nominal_fixed_spacing_mm": p["gate_spacing"],
        },
        "eccentric_touching_ball_window": {
            "continuous_bound": "h_min <= each front stop depth <= h_max; axial touching pitch >= p_min. Sufficient interval: 2*h_max <= L <= h_min+p_min-h_max. Independent worst cases make this conservative, not a necessary condition.",
            "extrema_basis": "Use E(R)=sqrt(A_max^2-hole_radius^2)-sqrt(R^2-hole_radius^2). h_min^2=(R+tip)^2-c_max^2-E(R)^2 increases with R. For h_max^2, put C=sqrt(A_max^2-hole_radius^2), q=c_min-C: h_max^2=hole_radius^2+2*R*tip+tip^2-q^2-2*q*sqrt(R^2-hole_radius^2). If q<=0 this increases; if q>0 it is convex, so a maximum is always at a radius endpoint. Mixed-pair pitch is bounded by sqrt((2*R_min)^2-(2*E(R_min))^2). These arguments cover continuous mixtures, not just sampled diameters.",
            "global_stop_depth_interval_mm": [hmin, hmax],
            "minimum_touching_pair_axial_pitch_mm": pitch_min,
            "sufficient_spacing_window_mm": robust_window,
            "actual_spacing_budget_interval_mm": spacing_interval,
            "minimum_spacing_margin_mm": spacing_margin,
            "full_sweep_condition": "Radial closure is monotone and both tip centers remain radially outside the allowed ball-center disk. Under that condition the final tip positions are closest to each stationary ball.",
            "sampled_cross_check": sampled,
        },
        "static_closed_pocket_capacity": {
            "formula": "Any ball center between both closed gate planes must lie at least h_min from each. Its axial interval has length <= L_max-2*h_min. Two nonintersecting spheres need axial center spacing >= p_min.",
            "maximum_between_gate_center_span_mm": closed_pocket_center_span,
            "minimum_two_ball_axial_pitch_mm": pitch_min,
            "two_ball_exclusion_margin_mm": pocket_capacity_margin,
            "scope": "This excludes two rigid balls wholly between two closed blocking gates. It does not prove successful loading, departing-ball clearance, or a full dynamic cycle.",
        },
        "cam_and_actual_position_interlock": cam,
        "not_covered": [
            "Dynamic arrival, feed pauses, rebounding, changing lateral positions while inserting a finger, trigger velocity and arbitrary partial-cycle timing.",
            "Exactly-one output, pocket occupancy through the moving portions of the cycle, and exit clearance before gate return.",
            "Ball shell stiffness, denting, buckling, seams, real ovality, wear, dirt or sphere-size distribution outside the candidate envelope.",
            "Finger/cam/follower/housing stiffness, finite follower size, groove undercut, contact stress, friction, spring force and mechanical return reliability.",
            "Complete assembled shanks/slots/fasteners, guide-end transition motion, unrecognized extra openings, actual hole-size/shape tolerance, assembly access and printability.",
            "Air bypass pressure loss, pneumatic force, feeder hose bends, guide transitions and adjustable spin-pad drag.",
            "Printer calibration, measured dimensions, physical assembly, damage inspection and repeated end-to-end firing.",
        ],
        "interpretation": "A useful static candidate screen only. No CAD mechanism completion, simulation of motion/contact/airflow, physical reliability or first-print guarantee is claimed.",
    }


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parameters", type=Path, default=root / "cad/parameters.scad")
    parser.add_argument("--geometry", type=Path, default=root / "cad/kinematic-study.scad")
    parser.add_argument("--output", type=Path, default=root / "output/analysis/gate-geometry.json")
    args = parser.parse_args()
    try:
        params, raw = read_parameters(args.parameters)
        report = analyze(params, args.parameters, raw, args.geometry)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    except (OSError, ValueError, ZeroDivisionError) as error:
        print(f"ANALYSIS_ERROR: {error}", file=sys.stderr)
        return 2
    print(report["static_screen_status"])
    print("Physical acceptance: OPEN_NOT_EVALUATED")
    blocking = report["gate_blocking"]
    pair = report["eccentric_touching_ball_window"]
    print(f"Closed configuration-space overlap: {blocking['closed_minimum_configuration_space_overlap_mm']:.6f} mm")
    print(f"Open surface clearance: {blocking['open_minimum_surface_clearance_mm']:.6f} mm")
    print("Sufficient parked-pair spacing window: " + ", ".join(f"{v:.6f}" for v in pair["sufficient_spacing_window_mm"]) + " mm")
    print("Actual spacing budget interval: " + ", ".join(f"{v:.6f}" for v in pair["actual_spacing_budget_interval_mm"]) + " mm")
    print(f"Sampled pair states: {pair['sampled_cross_check']['sampled_states']}; intersections: {pair['sampled_cross_check']['intersecting_states']}")
    print(f"Report: {args.output.resolve()}")
    return 0 if all(report["checks"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
