#!/usr/bin/env python3
"""Screen a split-clamp Y=65 fork without promoting it to a printable assembly.

This checks static interference, straight service axes and topology. It does
not calculate PETG clamp force, creep, fatigue or actual bore closure.
"""

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CAD = ROOT / "cad/electric-rocker-clamped-fork-screen.scad"
MOUNT_CAD = ROOT / "cad/electric-rocker-pivot-mount-screen.scad"
PIN_REPORT = ROOT / "output/electric-rocker-pin-retention-screen/review.json"
JOINT_REPORT = ROOT / "output/electric-rocker-pivot-joint-screen/review.json"
DRIVE_REPORT = ROOT / "output/electric-drive-feasibility/report.json"
OUT = ROOT / "output/electric-rocker-clamped-fork-screen"
OPENSCAD = Path("/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
INSPECT = Path("/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py")
POSES = (0, .25, .5, .75, 1)
CLEAR_PROBES = (
    "bracket-moving", "bracket-moving-clearance-1mm", "bracket-fixed",
    "bracket-hardware", "bracket-rocker",
    "bracket-rocker-clearance-0p5", "bracket-bushing", "bracket-shaft",
    "rocker-bushing", "rocker-shaft", "bushing-shaft", "bracket-bridge",
    "bracket-motor", "bracket-switch", "fasteners-moving", "fasteners-fixed",
    "fasteners-bracket",
    "fasteners-rocker", "fasteners-bushing", "fasteners-bridge", "fasteners-motor",
    "fasteners-pin-ends",
)
SERVICE_PROBES = (
    "driver-moving", "driver-fixed", "driver-rocker", "driver-bridge",
    "driver-motor", "nut-moving", "nut-fixed", "nut-rocker",
    "nut-bridge", "nut-motor",
)


def sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def sources(path: Path, found: set[Path] | None = None) -> set[Path]:
    found = found if found is not None else set()
    path = path.resolve()
    if path in found:
        return found
    found.add(path)
    for name in re.findall(r"\b(?:use|include)\s*<([^>]+)>", path.read_text()):
        sources(path.parent / name, found)
    return found


def run_scad(part: str, destination: Path, *, pose: float = 0,
             probe: str = "") -> subprocess.CompletedProcess[str]:
    destination.unlink(missing_ok=True)
    cmd = [str(OPENSCAD), "--hardwarnings", "--backend", "Manifold",
           "-D", f'cf_part="{part}"', "-D", f"cf_t={pose}",
           "-D", f"rb_t={pose}", "-D", f"pr_t={pose}",
           "-D", "rb_plane_y=65", "-D", "pm_pivot_y=65"]
    if probe:
        cmd += ["-D", f'cf_probe="{probe}"']
    if destination.suffix == ".png":
        cmd += ["--render", "--imgsize=1400,1000",
                "--camera=36,48,14,66,0,145,215"]
    cmd += ["-o", str(destination), str(CAD)]
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                          timeout=180)


def inspect(path: Path) -> dict:
    run = subprocess.run(["python3", str(INSPECT), str(path), "--json"],
                         cwd=ROOT, capture_output=True, text=True, timeout=30)
    if run.returncode:
        return {"error": (run.stdout + run.stderr)[-800:]}
    row = json.loads(run.stdout)
    return {
        "volume_mm3": round(row["volume"], 5),
        "watertight": row["watertightByEdgeTopology"],
        "boundary_edges": row["boundaryEdgeCount"],
        "non_manifold_edges": row["nonManifoldEdgeCount"],
        "bounds": row["bounds"],
    }


def ascii_mesh_components(path: Path) -> int:
    """A watertight STL may still contain multiple disconnected solids."""
    data = path.read_text()
    vertices = [tuple(round(float(value), 5) for value in match)
                for match in re.findall(
                    r"vertex\s+([-0-9.eE]+)\s+([-0-9.eE]+)\s+([-0-9.eE]+)",
                    data)]
    if not data.lstrip().startswith("solid") or len(vertices) % 3:
        raise ValueError("Expected ASCII triangle STL")
    parents = list(range(len(vertices) // 3))
    first_by_vertex = {}

    def root(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    for face in range(len(parents)):
        for point in vertices[3 * face:3 * face + 3]:
            other = first_by_vertex.get(point)
            if other is None:
                first_by_vertex[point] = face
            else:
                parents[root(face)] = root(other)
    return len({root(index) for index in range(len(parents))})


def probe(kind: str, t: float) -> dict:
    destination = OUT / "probes" / f"{kind}-t{t:.2f}.stl"
    run = run_scad("probe", destination, pose=t, probe=kind)
    log = run.stdout + run.stderr
    if run.returncode == 1 and "Current top level object is empty" in log \
            and "WARNING:" not in log and "ERROR:" not in log:
        return {"occupied": False, "volume_mm3": 0}
    if run.returncode or "WARNING:" in log or "ERROR:" in log \
            or not destination.is_file():
        return {"error": log[-800:]}
    result = inspect(destination)
    return {"occupied": result.get("volume_mm3", 0) > 1e-6,
            "volume_mm3": result.get("volume_mm3", 0),
            "error": result.get("error")}


def render(part: str, name: str, pose: float) -> dict:
    destination = OUT / name
    run = run_scad(part, destination, pose=pose)
    log = run.stdout + run.stderr
    raw = destination.read_bytes() if destination.is_file() else b""
    if run.returncode or "WARNING:" in log or "ERROR:" in log \
            or raw[:8] != b"\x89PNG\r\n\x1a\n" \
            or struct.unpack(">II", raw[16:24]) != (1400, 1000):
        return {"error": log[-800:] or "Invalid PNG"}
    return {"path": str(destination.relative_to(ROOT)),
            "sha256": sha(destination)}


def main() -> int:
    pin = json.loads(PIN_REPORT.read_text())
    joint = json.loads(JOINT_REPORT.read_text())
    drive = json.loads(DRIVE_REPORT.read_text())
    if pin["status"] != "HCDG6_16_FRONT_HEAD_LAYOUT_CLEAR_FORK_FIT_OPEN" \
            or pin["manufacturing_release"] or pin["failures"]:
        raise RuntimeError("Predecessor pin geometry is no longer the open fork fit")
    if pin["fork_bore_issue"]["printed_cad_nominal_bore_d_mm"] != 6.4:
        raise RuntimeError("Fork bore changed; re-evaluate clamp travel")
    if joint["status"] != "Y62_RETAINER_COLLISION_Y65_LAYOUT_SCREEN_ONLY" \
            or joint["plane_comparison"]["y65_promoted_to_selected_assembly"] \
            or joint["failures"]:
        raise RuntimeError("The through-bored rocker is no longer the open Y65 candidate")
    if drive["status"] != "NECESSARY_LOAD_BOUND_ONLY_MOTOR_NOT_APPROVED" \
            or drive["archived_seller_gallery_unverified"]["image_06_claims"]["push_claim_kgf"] != [4, 5]:
        raise RuntimeError("Seller force scenario changed; re-evaluate beam budget")
    text = CAD.read_text()
    for literal in ("cf_ears = [[58,61],[69,73]];",
                    "cf_slit_width = 1.2;", "cf_bolt_z = 36.5;",
                    "cf_bolt_clearance_d = 2.25;",
                    "cf_nut_trap_af = 4.3;",
                    "cf_beam_extra_bottom = -18;"):
        if literal not in text:
            raise RuntimeError(f"Review contract changed: {literal}")
    if "pm_box(7,10,40,pm_pivot_y+8,-14,-7);" not in MOUNT_CAD.read_text():
        raise RuntimeError("Original 3 x 7 mm low beam changed")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "probes").mkdir(exist_ok=True)
    tracked = sources(CAD) | {Path(__file__).resolve()}
    before = {str(path.relative_to(ROOT)): sha(path) for path in sorted(tracked)}
    bracket = OUT / "bracket.stl"
    mesh_run = run_scad("bracket", bracket)
    mesh_log = mesh_run.stdout + mesh_run.stderr
    mesh = inspect(bracket) if bracket.is_file() and not mesh_run.returncode \
        and "WARNING:" not in mesh_log and "ERROR:" not in mesh_log \
        else {"error": mesh_log[-800:]}
    if not mesh.get("error"):
        try:
            mesh["connected_components"] = ascii_mesh_components(bracket)
        except ValueError as exc:
            mesh["error"] = str(exc)
    clear_cases = [(kind, t) for kind in CLEAR_PROBES for t in POSES]
    service_cases = [(kind, t) for kind in SERVICE_PROBES for t in POSES]
    controls = [(kind, t) for kind in
                ("positive-control", "raw-rocker-shaft-positive-control")
                for t in POSES]
    with ThreadPoolExecutor(max_workers=4) as pool:
        clear = dict(zip((f"{k}-t{t:.2f}" for k, t in clear_cases),
                         pool.map(lambda item: probe(*item), clear_cases)))
        service = dict(zip((f"{k}-t{t:.2f}" for k, t in service_cases),
                           pool.map(lambda item: probe(*item), service_cases)))
        positive = dict(zip((f"{k}-t{t:.2f}" for k, t in controls),
                            pool.map(lambda item: probe(*item), controls)))
    images = {
        "home.png": render("context", "home.png", 0),
        "mid.png": render("context", "mid.png", .5),
        "full.png": render("context", "full.png", 1),
        "detail.png": render("detail", "detail.png", .5),
    }
    phase_meshes = {}
    for t in (0, 1):
        path = OUT / f"rocker-phase-t{t:.2f}.stl"
        run = run_scad("rocker-phase", path, pose=t)
        log = run.stdout + run.stderr
        phase_meshes[f"t{t:.2f}"] = (
            inspect(path) if path.exists() and run.returncode == 0
            and "WARNING:" not in log and "ERROR:" not in log
            else {"error": log[-800:]})
    after = {str(path.relative_to(ROOT)): sha(path) for path in sorted(tracked)}
    failures = [name for name, row in clear.items()
                if row.get("error") or row.get("occupied")]
    failures += [name for name, row in service.items() if row.get("error")]
    failures += [name for name, row in positive.items()
                 if row.get("error") or not row.get("occupied")]
    failures += [name for name, row in images.items() if row.get("error")]
    if mesh.get("error") or not mesh.get("watertight") \
            or mesh.get("boundary_edges") or mesh.get("non_manifold_edges") \
            or mesh.get("connected_components") != 1:
        failures.append("mesh")
    if before != after:
        failures.append("source-changed")
    if any(row.get("error") or not row.get("watertight")
           for row in phase_meshes.values()):
        failures.append("rocker-phase-mesh")
        rocker_phase_z_delta = None
    else:
        rocker_phase_z_delta = round(
            phase_meshes["t1.00"]["bounds"]["max"][2]
            - phase_meshes["t0.00"]["bounds"]["max"][2], 4)
        if not 9 < rocker_phase_z_delta < 12:
            failures.append("rocker-did-not-sweep")
    service_obstructions = [name for name, row in service.items()
                            if row.get("occupied")]
    driver_obstructions = [name for name in service_obstructions
                           if name.startswith("driver-")]
    if driver_obstructions:
        failures += driver_obstructions
    fork_gap = pin["fork_bore_issue"]["pin_to_nominal_fork_diametral_clearance_mm"]
    remaining_slit = [round(1.2-fork_gap[1], 3),
                      round(1.2-fork_gap[0], 3)]
    # The OpenSCAD 6-gon has its flats parallel to Y, so the Y half-width is
    # AF/2 and the Z half-width is the circumradius.
    nut_y_half = 4.3 / 2
    nut_z_half = 4.3 / (2 * math.cos(math.pi / 6))
    nut_wall_min = min(
        59.5 - nut_y_half - 56, 63 - (59.5 + nut_y_half),
        71 - nut_y_half - 67, 76 - (71 + nut_y_half),
        36.5 - nut_z_half - 33, 42 - (36.5 + nut_z_half),
        21.8 - 18,
    )
    if nut_wall_min < 1:
        failures.append("nut-trap-wall-under-1mm-nominal")
    section_width_x = 3
    original_height_z = 7
    reinforced_height_z = 11
    span_y = 25
    arm_input, arm_output = 75, 50
    section_old = section_width_x * original_height_z ** 2 / 6
    section_new = section_width_x * reinforced_height_z ** 2 / 6
    scenario = []
    for kgf in (4, 5):
        input_force = kgf * 9.80665
        output_force = input_force * arm_input / arm_output
        pivot_reaction = output_force - input_force
        root_moment = pivot_reaction * span_y
        scenario.append({
            "seller_push_claim_kgf": kgf,
            "input_force_n": round(input_force, 3),
            "ideal_output_force_n": round(output_force, 3),
            "ideal_pivot_reaction_n": round(pivot_reaction, 3),
            "pivot_to_anchor_moment_nmm": round(root_moment, 3),
            "original_nominal_straight_beam_stress_mpa":
                round(root_moment / section_old, 3),
            "deepened_nominal_straight_beam_stress_mpa":
                round(root_moment / section_new, 3),
        })
    report = {
        "status": "FAIL" if failures else "SPLIT_CLAMP_FORK_STATIC_SCREEN_ONLY",
        "source_sha256": before,
        "predecessor_pin_report_sha256": sha(PIN_REPORT),
        "predecessor_joint_report_sha256": sha(JOINT_REPORT),
        "drive_feasibility_report_sha256": sha(DRIVE_REPORT),
        "geometry_contract": {
            "pivot_y_mm": 65,
            "two_cheek_y_intervals_mm": [[58, 61], [69, 73]],
            "nominal_fork_bore_d_mm": 6.4,
            "catalogue_pin_d_mm": [5.988, 5.996],
            "pin_to_fork_diametral_gap_mm": fork_gap,
            "slit_width_mm": 1.2,
            "idealized_slit_remaining_after_diametral_takeup_mm": remaining_slit,
            "clamp_screw_count": 2,
            "clamp_screw_nominal_d_mm": 2,
            "clamp_screw_catalogue_reference": "Accu SSC-M2-25-A2",
            "clamp_screw_catalogue_url":
                "https://www.accu.co.uk/metric-cap-head-screws/2777-SSC-M2-25-A2",
            "screw_head_side": "-X; drive from -X",
            "steel_hex_nut_catalogue_reference": "MISUMI NATTO-2-4-1.6",
            "steel_hex_nut_catalogue_url":
                "https://sg.misumi-ec.com/vona2/detail/110500137250/?HissuCode=NATTO-2-4-1.6",
            "nominal_underhead_screw_length_mm": 25,
            "nominal_nut_across_flats_mm": 4,
            "nominal_nut_thickness_mm": 1.6,
            "nut_trap_af_nominal_mm": 4.3,
            "nut_trap_x_interval_mm": [21.8, 24.1],
            "minimum_analytical_nut_trap_wall_mm": round(nut_wall_min, 3),
            "clearance_hole_d_mm": 2.25,
            "screw_axis_z_mm": 36.5,
            "head_envelope_d_mm": 4.5,
            "nut_wrench_envelope_d_mm": 5,
            "hardware_catalogue_reference_only_not_received": True,
        },
        "bracket_mesh": {**mesh, "sha256": sha(bracket) if bracket.exists() else None},
        "through_bored_rocker_phase_meshes": phase_meshes,
        "through_bored_rocker_top_z_delta_mm": rocker_phase_z_delta,
        "beam_load_scenario_only": {
            "source": "shared seller gallery force claim; not delivered SKU measurement",
            "static_same_side_rocker_input_arm_mm": arm_input,
            "static_same_side_rocker_output_arm_mm": arm_output,
            "pivot_y_to_anchor_y_span_mm": span_y,
            "straight_beam_width_x_mm": section_width_x,
            "original_nominal_height_z_mm": original_height_z,
            "deepened_nominal_height_z_mm": reinforced_height_z,
            "original_section_modulus_mm3": round(section_old, 3),
            "deepened_section_modulus_mm3": round(section_new, 3),
            "scenario_rows": scenario,
            "stress_concentrations_and_layer_orientation_included": False,
            "shell_boss_and_screw_preload_checked": False,
            "petg_strength_creep_and_fatigue_verified": False,
            "structural_release": False,
        },
        "static_clearance_probes": clear,
        "service_axis": {
            "driver_minus_x_d_mm": 4.5,
            "nut_wrench_plus_x_d_mm": 5,
            "straight_axis_only": True,
            "probes": service,
            "occupied_axes": service_obstructions,
            "driver_axes_clear_at_all_poses_nominal": not driver_obstructions,
            "nut_wrench_axis_clear_at_all_poses_nominal":
                not any(name.startswith("nut-") for name in service_obstructions),
            "nut_trap_makes_wrench_unnecessary_in_nominal_model": True,
            "nut_must_be_loaded_before_motor_installation": True,
            "hand_and_tool_swing_envelope_verified": False,
        },
        "positive_controls": positive,
        "images": images,
        "shaft_clamp_force_verified": False,
        "real_rocker_bore_and_bushing_included_in_screen": True,
        "rocker_bushing_petg_fit_verified": False,
        "printed_bore_closure_verified": False,
        "petg_creep_and_fatigue_verified": False,
        "pin_slip_under_motor_load_verified": False,
        "motor_interface_and_load_verified": False,
        "selected_assembly_promoted": False,
        "manufacturing_release": False,
        "physical_acceptance": False,
        "failures": failures,
    }
    (OUT / "review.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(report["status"], len(clear), "static", len(service), "service",
          len(service_obstructions), "nut/tool obstructions",
          len(failures), "failures")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
