#!/usr/bin/env python3
"""Check a real catalogue pivot pin's direction and the existing fork fit.

The screen envelopes bound nominal hardware placement. It deliberately does
not turn a PETG Ø6.4 bore into a qualified Ø6 bearing or approve E-clip tooling.
"""

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import re
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CAD = ROOT / "cad/electric-rocker-pin-retention-screen.scad"
MOUNT_CAD = ROOT / "cad/electric-rocker-pivot-mount-screen.scad"
JOINT_REPORT = ROOT / "output/electric-rocker-pivot-joint-screen/review.json"
OUT = ROOT / "output/electric-rocker-pin-retention-screen"
OPENSCAD = Path("/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
INSPECT = Path("/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py")
POSES = (0, .25, .5, .75, 1)
FINE_POSES = tuple(i / 20 for i in range(21))
PROBES = (
    "front-head-moving", "front-head-moving-clearance-1mm", "front-head-fixed",
    "rear-ring-moving", "rear-ring-moving-clearance-1mm", "rear-ring-fixed",
)
SERVICE_PROBES = (
    "mount-tool-moving", "mount-tool-bridge",
    "mount-tool-preassembled-pivot",
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


def inspect(path: Path) -> dict:
    run = subprocess.run(["python3", str(INSPECT), str(path), "--json"],
                         cwd=ROOT, capture_output=True, text=True, timeout=30)
    if run.returncode:
        return {"error": (run.stdout + run.stderr)[-800:]}
    row = json.loads(run.stdout)
    return {"volume_mm3": round(row["volume"], 5),
            "watertight": row["watertightByEdgeTopology"]}


def probe(kind: str, t: float) -> dict:
    destination = OUT / "probes" / f"{kind}-t{t:.2f}.stl"
    destination.unlink(missing_ok=True)
    cmd = [str(OPENSCAD), "--hardwarnings", "--backend", "Manifold",
           "-D", 'pr_part="probe"', "-D", f'pr_probe="{kind}"',
           "-D", f"pr_t={t}", "-D", f"rb_t={t}",
           "-D", "rb_plane_y=65", "-D", "pm_pivot_y=65",
           "-o", str(destination), str(CAD)]
    run = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                         timeout=120)
    log = run.stdout + run.stderr
    if run.returncode == 1 and "Current top level object is empty" in log \
            and "WARNING:" not in log and "ERROR:" not in log:
        return {"occupied": False, "volume_mm3": 0}
    if run.returncode or "WARNING:" in log or "ERROR:" in log \
            or not destination.is_file():
        return {"error": log[-800:]}
    row = inspect(destination)
    return {"occupied": row.get("volume_mm3", 0) > 1e-6,
            "volume_mm3": row.get("volume_mm3", 0),
            "error": row.get("error")}


def render() -> dict:
    path = OUT / "front-head-rear-ring-mid.png"
    path.unlink(missing_ok=True)
    cmd = [str(OPENSCAD), "--hardwarnings", "--backend", "Manifold",
           "--render", "--imgsize=1400,1000",
           "--camera=36,48,14,66,0,145,215",
           "-D", 'pr_part="context"', "-D", "pr_t=0.5",
           "-D", "rb_t=0.5", "-D", "rb_plane_y=65",
           "-D", "pm_pivot_y=65",
           "-o", str(path), str(CAD)]
    run = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                         timeout=120)
    raw = path.read_bytes() if path.exists() else b""
    log = run.stdout + run.stderr
    if run.returncode or "WARNING:" in log or "ERROR:" in log \
            or raw[:8] != b"\x89PNG\r\n\x1a\n" \
            or struct.unpack(">II", raw[16:24]) != (1400, 1000):
        return {"error": log[-800:] or "Invalid PNG"}
    return {"path": str(path.relative_to(ROOT)), "sha256": sha(path)}


def main() -> int:
    joint = json.loads(JOINT_REPORT.read_text())
    if joint["status"] != "Y62_RETAINER_COLLISION_Y65_LAYOUT_SCREEN_ONLY" \
            or joint["plane_comparison"]["y65_promoted_to_selected_assembly"]:
        raise RuntimeError("Current Y65 predecessor is not an unreleased candidate")
    mount_source = MOUNT_CAD.read_text()
    match = re.search(r"\bpm_pivot_bore_d\s*=\s*([0-9.]+)\s*;", mount_source)
    if not match or "[pm_pivot_y-7,pm_pivot_y-4]" not in mount_source \
            or "[pm_pivot_y+4,pm_pivot_y+8]" not in mount_source:
        raise RuntimeError("Fork bore or cheek geometry changed")
    bracket_bore = float(match.group(1))
    if bracket_bore != 6.4:
        raise RuntimeError("Recalculate the reported catalogue pin clearance")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "probes").mkdir(exist_ok=True)
    tracked = sources(CAD) | {Path(__file__).resolve()}
    before = {str(path.relative_to(ROOT)): sha(path) for path in sorted(tracked)}
    rows = [(kind, t) for kind in PROBES for t in POSES]
    fine_rows = [(kind, t) for kind in
                 ("front-head-moving", "rear-ring-moving")
                 for t in FINE_POSES if t not in POSES]
    service_rows = [(kind, t) for kind in SERVICE_PROBES for t in POSES]
    controls = [("front-head-positive-control", 0),
                ("rear-ring-positive-control", 0)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        checked = dict(zip((f"{k}-t{t:.2f}" for k, t in rows),
                           pool.map(lambda row: probe(*row), rows)))
        fine = dict(zip((f"{k}-t{t:.2f}" for k, t in fine_rows),
                        pool.map(lambda row: probe(*row), fine_rows)))
        service = dict(zip((f"{k}-t{t:.2f}" for k, t in service_rows),
                           pool.map(lambda row: probe(*row), service_rows)))
        positive = dict(zip((k for k, _ in controls),
                            pool.map(lambda row: probe(*row), controls)))
    image = render()
    after = {str(path.relative_to(ROOT)): sha(path) for path in sorted(tracked)}

    shaft_min, shaft_max = 5.988, 5.996  # MISUMI HCDG6 g6 D6
    bushing_id_min, bushing_id_max = 6.020, 6.068  # after steel H7 press-fit
    shaft_recommended_min, shaft_recommended_max = 5.970, 6.000
    fork_outer_span = (65+8)-(65-7)
    head_to_groove_near = (16.0, 16.1)
    bushing_clearance = (bushing_id_min-shaft_max,
                         bushing_id_max-shaft_min)
    fork_clearance = (bracket_bore-shaft_max, bracket_bore-shaft_min)
    failures = [name for name, row in {**checked, **fine}.items()
                if row.get("error") or row.get("occupied")]
    failures += [name for name, row in positive.items()
                 if row.get("error") or not row.get("occupied")]
    expected_tool_obstructions = {
        "mount-tool-moving": (True, True, False, False, False),
        "mount-tool-bridge": (True, True, True, False, False),
        "mount-tool-preassembled-pivot": (False,) * len(POSES),
    }
    for kind, expected in expected_tool_obstructions.items():
        for t, occupied in zip(POSES, expected):
            name = f"{kind}-t{t:.2f}"
            row = service[name]
            if row.get("error") or row.get("occupied") != occupied:
                failures.append(name)
    if image.get("error"):
        failures.append("image")
    if not (shaft_recommended_min <= shaft_min <= shaft_max <= shaft_recommended_max):
        failures.append("shaft-outside-bushing-recommendation")
    if not (head_to_groove_near[0] > fork_outer_span
            and head_to_groove_near[1]-fork_outer_span < 1.2):
        failures.append("axial-groove-position")
    if before != after:
        failures.append("source-changed")

    report = {
        "status": "FAIL" if failures else "HCDG6_16_FRONT_HEAD_LAYOUT_CLEAR_FORK_FIT_OPEN",
        "source_sha256": before,
        "predecessor_joint_report_sha256": sha(JOINT_REPORT),
        "manufacturer_sources": {
            "pin_family_pdf": "https://us.c.misumi-ec.com/book/usa_2019_msm_fa/pdf/0957.pdf",
            "exact_pin_page": "https://uk.misumi-ec.com/vona2/detail/110300095750/?HissuCode=HCDG6-16",
            "e_ring_reference_pdf": "https://us.misumi-ec.com/pdf/tech/mech/US2010_fa_p3553_3554.pdf",
            "bushing_pdf": "https://www.igus.com/ContentData/Products/Downloads/iglide_G300_FM_USen.pdf",
        },
        "catalogue_pin": {
            "part": "MISUMI HCDG6-16", "supplied_ring": "NETW5 E-type No.5",
            "shaft_g6_diameter_mm": [shaft_min, shaft_max],
            "head_diameter_nominal_mm": 9,
            "head_axial_nominal_mm": 1.5,
            "L_underhead_to_groove_near_wall_mm": list(head_to_groove_near),
            "groove_width_mm": [0.7, 0.8],
            "tail_from_groove_near_wall_nominal_mm": 2,
            "ring_free_outer_diameter_reference_mm": 11,
            "ring_and_tail_actual_installed_shape_verified": False,
            "ordered_or_received": False,
        },
        "catalogue_bushing": {
            "part": "igus GFM-0608-06",
            "recommended_shaft_diameter_mm": [shaft_recommended_min,
                                               shaft_recommended_max],
            "installed_id_after_steel_h7_pressfit_mm": [bushing_id_min,
                                                          bushing_id_max],
            "pin_to_bushing_diametral_clearance_mm":
                [round(v, 3) for v in bushing_clearance],
            "petg_pressfit_and_installed_id_verified": False,
        },
        "geometry_contract": {
            "pivot_y_mm": 65,
            "front_fork_outer_y_mm": 58,
            "rear_fork_outer_y_mm": 73,
            "fork_outer_span_nominal_mm": fork_outer_span,
            "head_to_ring_near_wall_nominal_axial_float_mm":
                [round(v-fork_outer_span, 3) for v in head_to_groove_near],
            "pin_orientation": "head-front-y<58, NETW5-rear-y>73",
            "front_head_screen_envelope": {"diameter_mm": 16,
                                           "y_interval_mm": [55, 58]},
            "rear_ring_and_tip_screen_envelope": {"diameter_mm": 16,
                                                  "y_interval_mm": [73, 77]},
            "actual_e_ring_install_tool_and_sequence_verified": False,
        },
        "fork_bore_issue": {
            "printed_cad_nominal_bore_d_mm": bracket_bore,
            "pin_to_nominal_fork_diametral_clearance_mm":
                [round(v, 3) for v in fork_clearance],
            "pin_to_nominal_fork_radial_clearance_mm":
                [round(v/2, 3) for v in fork_clearance],
            "qualified_bearing_or_finished_fork_hole_designed": False,
            "dynamic_pivot_location_error_budget_verified": False,
        },
        "coarse_probes": checked,
        "fine_probes": fine,
        "serviceability_screen": {
            "screwdriver_axis_diameter_mm": 4,
            "straight_axis_only": True,
            "probe_results": service,
            "both_screwdriver_axes_clear_at_full_stroke_nominal": True,
            "carriage_can_be_safely_parked_at_full_stroke_verified": False,
            "ring_install_tool_and_service_sequence_verified": False,
        },
        "positive_controls": positive,
        "image": image,
        "selected_assembly_promoted": False,
        "motor_mount_designed": False,
        "manufacturing_release": False,
        "physical_acceptance": False,
        "failures": failures,
    }
    (OUT / "review.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(report["status"], len(checked), "coarse", len(fine), "fine",
          len(service), "service",
          len(failures), "failures")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
