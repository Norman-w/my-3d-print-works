#!/usr/bin/env python3
"""Export seven local fit coupons and inspect their meshes. No printer operation."""
from __future__ import annotations
import argparse
import csv
import datetime
import hashlib
import json
from pathlib import Path
import runpy
import subprocess

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"output/fit-coupons"
SOURCE=ROOT/"cad/fit-coupons.scad"
SCAD="/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"
PARTS=("radial-pair","finger","slider-seat","slider-gib","slider-keeper","locator","seal")
ORIENTATION={
    "radial-pair":"Assembly +Z remains print +Z; two radial holes are horizontal, like an upright body.",
    "finger":"Ball-tip direction (-assembly X) is print +Z; actual finger retained above labelled root tab.",
    "slider-seat":"Assembly +Z remains print +Z; crop X43..67,Y-18..28,Z-15..15 plus outside label tab.",
    "slider-gib":"Actual retracted gib back face on bed; assembly +Y becomes print +Z.",
    "slider-keeper":"Actual keeper back face on bed; assembly +Y becomes print +Z.",
    "locator":"Seam face on bed; assembly +X becomes print +Z. Blind holes open toward bed.",
    "seal":"Negative-half seam face on bed; assembly -X becomes print +Z. Groove opens toward bed."}


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def scad_run(name,part,render=None):
    path=OUT/(name+(".png" if render else ".stl"))
    path.unlink(missing_ok=True)
    command=[SCAD,"--hardwarnings","--backend","Manifold","-o",str(path),"-D",f'coupon_part="{part}"']
    if render:
        command += ["--render","--imgsize","1500,950","--projection","o","--autocenter","--viewall",
                    "--camera",render,"--colorscheme","Tomorrow"]
    else: command += ["--export-format","binstl"]
    command.append(str(SOURCE))
    p=subprocess.run(command,cwd=ROOT,text=True,capture_output=True)
    log=p.stdout+p.stderr
    (OUT/(name+".log")).write_text(log)
    empty="Current top level object is empty" in log and not path.exists()
    if p.returncode and not empty: raise RuntimeError(log)
    return {"part":part,"path":str(path.relative_to(ROOT)),"command":command,"empty":empty}


def ray(path,axis,a,b):
    # Independent ray measurement from actual mesh; imported helper only parses STL.
    triangles=runpy.run_path(str(ROOT/"analysis/manufacturing_review.py"))["triangles"](path)
    i,j=[k for k in range(3) if k!=axis]
    hits=set()
    for v0,v1,v2 in triangles:
        ui,uj,vi,vj=v1[i]-v0[i],v1[j]-v0[j],v2[i]-v0[i],v2[j]-v0[j]
        determinant=ui*vj-uj*vi
        if abs(determinant)<1e-10: continue
        di,dj=a-v0[i],b-v0[j]
        s,t=(di*vj-dj*vi)/determinant,(ui*dj-uj*di)/determinant
        if s>=-1e-7 and t>=-1e-7 and s+t<=1+1e-7:
            hits.add(round(v0[axis]+s*(v1[axis]-v0[axis])+t*(v2[axis]-v0[axis]),5))
    return sorted(hits)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render",action="store_true")
    parser.add_argument("--inspect-existing-slice",action="store_true",
                        help="Record the existing local Bambu result; does not start a slicer or printer")
    args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    if args.inspect_existing_slice:
        report_path=OUT/"fit-coupons-report.json"
        current=json.loads(report_path.read_text())
        if not all(digest(ROOT/p["path"])==p["sha256"] for p in current["parts"]):
            raise SystemExit("Input STL drift: existing slice cannot be attached to this report")
        folder=OUT/"slicing"
        native=json.loads((folder/"result.json").read_text())
        summary={
            "status":"CANDIDATE_SLICING_COMPLETED_WITH_FLOATING_REGION_WARNING",
            "return_code":native["return_code"],
            "assumptions":{"machine":"X1 Carbon 0.4 nozzle (unconfirmed physical nozzle)",
                           "material":"Generic PETG (unconfirmed actual material)",
                           "plate":"Textured PEI Plate (unconfirmed actual plate)",
                           "process":"0.20mm Standard @BBL X1C", "supports_enabled":False},
            "warnings":[p.get("warning_message","") for p in native.get("sliced_plates",[]) if p.get("warning_message")],
            "input_stl_sha256":{p["path"]:p["sha256"] for p in current["parts"]},
            "artifacts":{p.name:digest(p) for p in (folder/"fit-coupons-candidate.3mf",folder/"plate_1.gcode",folder/"result.json",folder/"bambu-cli-third.log")},
            "profile_copies_sha256":{name:digest(folder/(name+".json")) for name in ("machine","process","filament")},
            "prior_attempts":[{"log":"bambu-cli-initial-cool-plate-rejection.log","reason":"Default Cool Plate/PETG combination rejected"},
                              {"log":"bambu-cli-second-abort.log","exit_code":134,"cause":"Not diagnosed"}],
            "layer_path_spot_check":{
                "seal_layer_1":"G-code object204, Z0.2: longitudinal groove wall centre lines Y108.550 and109.850, commanded width0.5; nominal path gap0.8 at the straight middle only.",
                "locator_layer_1":"G-code object193, Z0.2 contains separate closed round/capsule hole contours; this does not establish printed diameters or full depth.",
                "not_a_complete_toolpath_audit":True},
            "command":["/Applications/BambuStudio.app/Contents/MacOS/BambuStudio","--datadir",str(folder/"app-data"),
                       "--load-settings",str(folder/"machine.json")+";"+str(folder/"process.json"),
                       "--load-filaments",str(folder/"filament.json"),"--orient","0","--arrange","1","--ensure-on-bed",
                       "--slice","0","--export-3mf","fit-coupons-candidate.3mf","--outputdir",str(folder),
                       *[str(OUT/("fit-"+part+".stl")) for part in PARTS]],
            "user_profiles_read_or_changed":False,"printer_accessed":False,"sent_to_printer":False,
            "support_removal_validated":False,"print_ready":False}
        supported=folder/"seat-supported"
        if (supported/"result.json").exists():
            seat_native=json.loads((supported/"result.json").read_text())
            seat_warnings=[p.get("warning_message","") for p in seat_native.get("sliced_plates",[]) if p.get("warning_message")]
            support_review=json.loads((supported/"support-path-review.json").read_text())
            summary["seat_only_support_attempt"]={
                "return_code":seat_native["return_code"],"warnings":seat_warnings,
                "same_orientation":True,"other_six_parts_changed":False,
                "input_stl_sha256":digest(OUT/"fit-slider-seat.stl"),
                "config_changes":{"enable_support":"1","support_type":"tree(auto)","support_on_build_plate_only":"1"},
                "unchanged_clearances_mm":{"xy":0.35,"top_z":0.2,"bottom_z":0.2},
                "artifacts":{p.name:digest(p) for p in (supported/"fit-slider-seat-supported-candidate.3mf",supported/"plate_1.gcode",supported/"result.json",supported/"bambu-cli.log",supported/"process-supported.json",supported/"support-path-review.json")},
                "support_path_review":support_review,
                "removal_access":"Clean before gib/keeper assembly. Through radial channel open at +/-X and gib pocket open at -Y. Break supports into pieces; no one-piece withdrawal claim. Captive-nut entrances remain open.",
                "blind_hole_scope":"This seat-only crop has no 3.2-mm blind locator holes; those belong to a separate coupon and were not re-sliced.",
                "actual_removal_surface_damage_residue_and_sliding_fit":"OPEN",
                "command":["/Applications/BambuStudio.app/Contents/MacOS/BambuStudio","--datadir",str(supported/"app-data"),
                           "--load-settings",str(folder/"machine.json")+";"+str(supported/"process-supported.json"),
                           "--load-filaments",str(folder/"filament.json"),"--orient","0","--arrange","1","--ensure-on-bed",
                           "--slice","0","--export-3mf","fit-slider-seat-supported-candidate.3mf","--outputdir",str(supported),str(OUT/"fit-slider-seat.stl")]}
            if seat_native["return_code"]==0 and not seat_warnings:
                summary["status"]="INITIAL_MIXED_PLATE_WARNED_SEAT_ONLY_SUPPORTED_RETRY_SUCCEEDED"
        (folder/"slice-review.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n")
        current["slicing_review"]=summary
        current["sliced"]=native["return_code"]==0
        current["status"]="CANDIDATE_COUPONS_SLICED_PHYSICAL_ACCEPTANCE_OPEN"
        report_path.write_text(json.dumps(current,indent=2,ensure_ascii=False)+"\n")
        print(json.dumps({"sliced":current["sliced"],"print_ready":False,
                          "initial_plate_warnings":summary["warnings"],
                          "seat_supported_warnings":summary.get("seat_only_support_attempt",{}).get("warnings")},indent=2))
        return
    helper=runpy.run_path(str(ROOT/"analysis/spin_head_geometry.py"))
    inspect=helper["inspect_mesh"]
    reports=[]
    for part in PARTS:
        r=scad_run("fit-"+part,part)
        r["mesh"]=inspect(ROOT/r["path"])
        r["sha256"]=digest(ROOT/r["path"])
        r["candidate_print_direction"]=ORIENTATION[part]
        reports.append(r)
    ref=scad_run("fit-radial-reference-xor","radial-reference-xor")
    if not ref["empty"]:
        ref["mesh"]=inspect(ROOT/ref["path"])
    # Coplanar curved surfaces may leave zero-thickness XOR output. Do not call
    # a small signed volume a containment proof: compare separate mesh sections.
    reference_exports=[scad_run("fit-radial-reference-"+kind,"radial-reference-"+kind)
                       for kind in ("actual","derived")]
    section_cases=[]
    for axis,a,b in ([(0,y,z) for y in (-5,-2,0,2,5) for z in (-6,-2.15,.13,2.15,6)] +
                     [(2,x,y) for x in (21.6,22.5,32.5) for y in (-2,.13,2)]):
        actual=ray(OUT/"fit-radial-reference-actual.stl",axis,a,b)
        derived=ray(OUT/"fit-radial-reference-derived.stl",axis,a,b)
        match=len(actual)==len(derived) and all(abs(x-y)<2e-5 for x,y in zip(actual,derived))
        section_cases.append({"axis":axis,"coordinates":[a,b],"actual":actual,"derived":derived,"match":match})
    reference_match=all(c["match"] for c in section_cases)
    measured={
        "radial_midwall_ray_x_at_y25_z15":ray(OUT/"fit-radial-pair.stl",0,25,15),
        "radial_53_hole_ray_z_at_x4_y7":ray(OUT/"fit-radial-pair.stl",2,4,7),
        "radial_55_hole_ray_z_at_x4_y25":ray(OUT/"fit-radial-pair.stl",2,4,25),
        "radial_57_hole_ray_z_at_x4_y43":ray(OUT/"fit-radial-pair.stl",2,4,43),
        "locator_31_blind_bottom_z_at_x7_y8":ray(OUT/"fit-locator.stl",2,7,8),
        "locator_32_blind_bottom_z_at_x7_y26":ray(OUT/"fit-locator.stl",2,7,26),
        "locator_slot_blind_bottom_z_at_x7_y44":ray(OUT/"fit-locator.stl",2,7,44),
        "seal_depth_ray_z_at_x16_y4_7":ray(OUT/"fit-seal.stl",2,16,4.7),
        "seal_left_land_ray_z_at_x16_y4_0":ray(OUT/"fit-seal.stl",2,16,4.0),
        "seal_right_land_ray_z_at_x16_y5_4":ray(OUT/"fit-seal.stl",2,16,5.4),
    }
    spring_source=json.loads((ROOT/"output/analysis/spin-head-geometry.json").read_text())
    spring_source_hashes=spring_source.get("source_sha256",{})
    spring={"existing_entity_report_sha256":digest(ROOT/"output/analysis/spin-head-geometry.json"),
        "existing_entity_report_source_matches_current":all(digest(ROOT/p)==h for p,h in spring_source_hashes.items()),
        "geometry":spring_source["spring_geometry_only"],
        "identity":"L=16.75-preload(0..4)-float(0..3), mm; geometry only",
        "must_measure":["free length and end form","solid height with reserve below 9.75 mm",
                        "force over full 9.75..16.75 mm installed-length window",
                        "ID clearance to nominal D6 pilots and OD growth/buckling within D10.5 envelope",
                        "hysteresis, set, fatigue and actual seat fit"],
        "spring_selected":False}
    sources=["cad/fit-coupons.scad","cad/parameters.scad","cad/cam-study.scad",
             "cad/feeder-body.scad","cad/feeder-supports.scad","cad/feeder-guide-revision.scad",
             "cad/spin-head.scad","cad/spin-parameters.scad"]
    if (ROOT/"cad/feeder-seam-candidate.scad").exists():sources.append("cad/feeder-seam-candidate.scad")
    result={"status":"CANDIDATE_COUPONS_PHYSICAL_AND_SLICING_ACCEPTANCE_OPEN",
            "created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "source_sha256":{p:digest(ROOT/p) for p in sources},
            "source_units":"mm; STL itself has no units", "part_count":len(reports),
            "parts":reports,"all_watertight":all(p["mesh"]["watertight"] for p in reports),
            "all_single_component":all(p["mesh"]["connected_components"]==1 for p in reports),
            "radial_55_real_body_xor":ref,
            "xor_coplanar_residue_is_not_a_containment_proof":not ref["empty"],
            "radial_55_reference_exports":reference_exports,
            "radial_55_sampled_sections":section_cases,"radial_55_sampled_reference_match":reference_match,
            "mesh_section_readbacks":measured,"spring_window":spring,
            "material":None,"actual_nozzle":None,"actual_printer_errors":None,
            "sliced":False,"printed":False,"physical_fit_passed":False,
            "baseline_parameters_changed":False}
    # Keep a valid earlier slice visible after a geometry-only rerun; never attach
    # it to changed STL bytes. Changing sources still requires geometry review.
    slice_path=OUT/"slicing/slice-review.json"
    if slice_path.exists():
        old_slice=json.loads(slice_path.read_text())
        unchanged=all(old_slice.get("input_stl_sha256",{}).get(p["path"])==p["sha256"] for p in reports)
        result["earlier_slice_inputs_still_match"]=unchanged
        if unchanged:
            result["slicing_review"]=old_slice
            result["sliced"]=old_slice["return_code"]==0
            result["status"]="CANDIDATE_COUPONS_SLICED_PHYSICAL_ACCEPTANCE_OPEN"
    if args.render:
        result["views"]=[scad_run("fit-view-"+name,"layout",camera) for name,camera in
                        (("iso","170,-160,190,65,30,5"),
                         ("top","65,30,250,65,30,0"),
                         ("front","65,-230,30,65,30,10"))]
    (OUT/"fit-coupons-report.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    csv_path=OUT/"measurement-record-blank.csv"
    if not csv_path.exists():
        with csv_path.open("w",newline="") as f:
            writer=csv.writer(f)
            writer.writerow(["coupon","feature","nominal_mm","actual_mm","direction_material_profile_id","as_printed_or_finished","fit_force_or_binding","result_notes"])
            for row in [("radial-pair","holes53/55/57","5.3/5.5/5.7"),
                        ("finger","rod_D / carrier_YxZ","5 / 9x8"),
                        ("slider-seat","fixed face / axial opening","Y4.5 / 8.4"),
                        ("slider-gib","working gap at chosen setting","measure; 0.1 display candidate"),
                        ("locator","round31 / round32 / slot / depth","3.1 / 3.2 / 3.2x4.2 / 3.2"),
                        ("seal","wall / groove width / depth / lands","2 / 0.8 / 0.2 / 0.6 each"),
                        ("spring","free length / solid height / OD / ID / F(L)","UNSELECTED")]:
                writer.writerow([*row,"","","","",""])
    print(json.dumps({"report":str(OUT/"fit-coupons-report.json"),
         "watertight":result["all_watertight"],"single_component":result["all_single_component"],
         "nominal_radial_reference_match":reference_match,"sections":measured},indent=2))
    if not (result["all_watertight"] and result["all_single_component"] and reference_match):
        raise SystemExit("Coupon mesh or real-reference check failed")


if __name__=="__main__":main()
