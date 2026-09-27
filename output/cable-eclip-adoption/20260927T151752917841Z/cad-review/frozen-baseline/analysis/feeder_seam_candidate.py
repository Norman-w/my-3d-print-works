#!/usr/bin/env python3
"""Bounded geometric review of ONE independent zero-gap seam candidate.

Exact convex pin sweeps and halfspace closing argument, with positive controls.
Nominal 2-D rigid locator bound is not a manufactured 3-D tolerance acceptance.
"""
from pathlib import Path
import concurrent.futures
import hashlib
import importlib.util
import json
import math
import re
import subprocess
from feeder_integration import classify

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/seam-candidate'
SCAD = ROOT/'cad/feeder-seam-candidate.scad'
EXE = '/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
SOURCES = ['cad/parameters.scad','cad/feeder-body.scad',
           'cad/feeder-seam-candidate.scad','analysis/feeder_seam_candidate.py',
           'analysis/feeder_integration.py']


def hashes():
    return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES}


def render(name,part,suffix='.stl',extra=()):
    target=OUT/(name+suffix)
    target.unlink(missing_ok=True)
    cmd=[EXE,'--render','--hardwarnings','--backend','Manifold','-o',str(target)]
    if suffix=='.stl': cmd+=['--export-format','asciistl']
    cmd+=['-D',f'seam_part={json.dumps(part)}',*extra,str(SCAD)]
    result=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
    log=result.stdout+result.stderr
    (OUT/(name+'.log')).write_text(log)
    if 'WARNING:' in log or 'ERROR:' in log: raise RuntimeError(log)
    empty='Current top level object is empty' in log
    if not target.exists() and not empty: raise RuntimeError(log)
    return {'name':name,'part':part,'returncode':result.returncode,
            'path':str(target.relative_to(ROOT)) if target.exists() else None,
            'empty':empty}


def probe(job):
    name,part,wants_solid=job
    row=render(name,part)
    if row['path']: row.update(classify(ROOT/row['path']))
    else: row.update({'components':[],'triangle_count':0,
                     'has_solid_or_unclassified_overlap':False})
    row['expected_solid_overlap']=wants_solid
    row['passed']=row['has_solid_or_unclassified_overlap']==wants_solid
    return row


def locator_bound(d):
    # Nominal smooth-circle model is a conservative relaxation of the inscribed
    # polygons used by SCAD. No printing/pin diameter tolerance is included.
    ay,by=d['locator_y']; az,bz=d['locator_z']
    span=math.hypot(by-ay,bz-az)
    fixed=(d['fixed_hole_d']-d['pin_d'])/2
    round_gap=(d['round_hole_d']-d['pin_d'])/2
    slot_gap=(d['slot_width']-d['pin_d'])/2
    c1=fixed+round_gap; c2=fixed+slot_gap
    along=fixed+(d['slot_length']-d['pin_d'])/2
    # q_B=t+(R(theta)-I)*AB. The slot normal rotates with the positive half.
    # |t|<=c1, |(R(theta)*n).q_B|<=c2 imply
    # |sin(theta)|<=(c1+c2)/L. Slot long-axis constraint excludes the branch
    # near pi because L*(1-cos(theta))<=c1+along << 2*L.
    theta=math.asin((c1+c2)/span)
    branch_limit=math.acos(1-(c1+along)/span)
    assert branch_limit<math.pi/2
    gates=[]
    for z in d['gate_z']:
        radius=math.hypot(ay,z-az)
        displacement=c1+2*radius*math.sin(theta/2)
        gates.append({'point_yz':[0,z],'distance_to_round_locator_mm':radius,
                      'relative_yz_norm_upper_bound_mm':displacement})
    return {'model':'Relative planar rigid pose of halves; ideal smooth holes/pins only.',
            'locator_span_mm':span,'first_locator_relative_radius_mm':c1,
            'second_transverse_relative_radius_mm':c2,
            'slot_long_direction_relative_limit_mm':along,
            'relative_rotation_upper_bound_rad':theta,
            'relative_rotation_upper_bound_deg':math.degrees(theta),
            'long_slot_branch_bound_deg':math.degrees(branch_limit),
            'gate_bounds':gates,
            'scope':'A conservative upper bound, not a attained counterexample or an extra allowance beyond the existing gate budget. No X-gap, tilt, pin deformation, print position, shrinkage, flatness or clamping deformation included.'}


def geometry(d):
    fn=d['body_polygon_fn']; depth=d['groove_depth']; half=d['groove_width']/2
    wall_rows=[]
    # At the X=0 vertex of the actual regular polygon, moving into -X by depth
    # reduces the outer Y edge by depth*tan(pi/fn), while still on its first edge.
    for label,inner,outer in [
        ('inlet straight',d['spigot_bore']/2,d['inlet_od']/2),
        ('central shell',d['body_id']/2,d['body_od']/2),
        ('outlet socket',d['socket_id']/2,d['socket_od']/2)]:
        center=(inner+outer)/2
        inner_land=center-half-inner
        smooth_outer=math.sqrt(outer**2-depth**2)-center-half
        polygon_outer=outer-depth*math.tan(math.pi/fn)-center-half
        wall_rows.append({'section':label,'wall_mm':outer-inner,
                          'groove_center_y_abs_mm':center,
                          'inner_land_lower_bound_mm':inner_land,
                          'outer_land_smooth_at_bottom_mm':smooth_outer,
                          'outer_land_polygon_at_bottom_mm':polygon_outer})
    root_overlap=math.sqrt((d['body_od']/2)**2-d['ear_half_x']**2)-d['foot_y_inner']
    # Safer actual polygon bound: inscribed-radius circle lies inside the shell.
    root_overlap_poly=math.sqrt(((d['body_od']/2)*math.cos(math.pi/fn))**2
                               -d['ear_half_x']**2)-d['foot_y_inner']
    slot_radius=d['slot_length']/2
    return {'nominal_split_gap_mm':d['nominal_split_gap'],
            'blind_bottom_thickness_mm':d['ear_half_x']-d['hole_depth'],
            'pin_total_axial_slack_mm':2*d['hole_depth']-d['pin_length'],
            'pin_exposure_when_seated_in_negative_half_mm':d['pin_length']-d['hole_depth'],
            'opposite_bottom_slack_when_seated_mm':2*d['hole_depth']-d['pin_length'],
            'ear_round_hole_smooth_radial_land_mm':d['ear_radius']-d['round_hole_d']/2,
            'ear_round_hole_polygon_land_lower_bound_mm':d['ear_radius']*math.cos(math.pi/72)-d['round_hole_d']/2,
            'ear_slot_end_smooth_radial_land_mm':d['ear_radius']-slot_radius,
            'ear_slot_end_polygon_land_lower_bound_mm':d['ear_radius']*math.cos(math.pi/72)-slot_radius,
            'ear_root_to_bypass_cavity_min_radial_clearance_mm':d['foot_y_inner']-d['body_id']/2,
            'ear_foot_shell_overlap_smooth_mm':root_overlap,
            'ear_foot_shell_overlap_polygon_lower_bound_mm':root_overlap_poly,
            'ear_outer_y_mm':max(abs(y) for y in d['locator_y'])+d['ear_radius'],
            'existing_split_boss_outer_y_mm':45,
            'groove_straight_wall_lands':wall_rows,
            'groove_z_extents':[s[:2] for s in d['segments']],
            'taper_lands_scope':'Capsule width is normal to its sloping centerline. Bounds above are for the three straight sections; actual complete taper groove cuts are covered by solid-body STL and protected-cavity checks, not a claimed universal numerical wall-thickness minimum.',
            'load_path':'Locator bore -> 4 mm-thick half ear -> volumetric root -> central outer shell; original M3 clamps supply closing force. Pin shear, root bending, print anisotropy and required clamp force remain untested.'}


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    before=hashes()
    dims_art=render('dimensions','dimensions','.echo')
    line=next(x for x in (ROOT/dims_art['path']).read_text().splitlines()
              if x.startswith('ECHO: "SEAM_DIMENSIONS", '))
    dims=dict(json.loads(line.split(', ',1)[1]))
    original=(ROOT/'cad/feeder-body.scad').read_text()
    # Explicit dependency contract instead of silently drifting copied scalars.
    for var,value in [('body_spigot_bore',dims['spigot_bore']),('body_outlet_stop',2)]:
        match=re.search(rf'^\s*{var}\s*=\s*([\d.]+)\s*;',original,re.M)
        assert match and float(match.group(1))==value,(var,'source contract changed')
    jobs=[
        ('halves-interference','halves_interference',False),
        ('pins-interference','pins_interference',False),
        ('pin-insertion-sweep','pin_insertion',False),
        ('cover-insertion-sweep','cover_insertion',False),
        ('ear-root-connection','ear_connection',True),
        ('cavity-intrusion','cavity_intrusion',False),
        ('dry-stops-unchanged','dry_stop_cut',False),
        ('grooves-contained-in-pressure-wall','groove_breakthrough',False),
        ('original-fasteners-not-refilled','original_fasteners_refilled',False),
        ('guide-unchanged','guide_changed',False),
        ('overclose-positive-control','overclose_control',True),
        ('long-pin-positive-control','long_pin_control',True),
        ('offset-pin-positive-control','offset_pin_control',True)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        cases=list(pool.map(probe,jobs))
    stls=[render('negative-half','negative_half'),render('positive-half','positive_half')]
    spec=importlib.util.spec_from_file_location('stl_inspector',
        '/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py')
    inspector=importlib.util.module_from_spec(spec); spec.loader.exec_module(inspector)
    for row in stls:
        row['mesh']=inspector.inspect(ROOT/row['path'],tolerance=1e-5)
        row['classification']=classify(ROOT/row['path'])
        row['single_component']=len(row['classification']['components'])==1
    images=[
        render('negative-face','negative_face','.png',
               ['--imgsize=1100,1600','--projection=o','--viewall','--autocenter',
                '--camera=260,0,-28,0,0,-28']),
        render('exploded','exploded','.png',
               ['--imgsize=1400,1400','--projection=o','--viewall','--autocenter',
                '--camera=230,-280,180,0,0,-28'])]
    stable=before==hashes()
    connected=next(r for r in cases if r['part']=='ear_connection')
    two_roots=len(connected['components'])==2 and all(
        r['volume_mm3']>1 for r in connected['components'])
    passed=stable and two_roots and all(r['passed'] for r in cases) and all(
        r['mesh']['watertightByEdgeTopology'] and r['single_component'] for r in stls)
    report={'status':'INDEPENDENT_CANDIDATE_NOMINAL_GEOMETRY_PASS' if passed else 'FAIL_OR_STALE',
            'adopted_into_main_assembly':False,'manufacturing_release':False,
            'source_sha256':before,'sources_stable_during_checks':stable,
            'dimensions_from_scad':dims,'geometry':geometry(dims),
            'locator_nominal_free_play':locator_bound(dims),'checks':cases,
            'two_independent_root_connections':two_roots,'halves':stls,'previews':images,
            'closure_path_proof':'Negative half is restricted to X<=0; translated positive half lies at X>=a for all a>=0. Therefore pure +X-to-zero closing cannot create solid half/half overlap. Pins are checked separately using exact convex continuous sweeps. Adhesive film is not represented by this proof.',
            'open':['Official evidence for exact PETG substrate and film joint is absent.',
                    'Seal membrane continuation at steps and actual hose/Y interfaces is unresolved.',
                    'As-printed dimensional fit, flatness, clamping distortion, load strength and leak rate are untested.',
                    'The gate locator bound must enter the complete mechanism tolerance chain; it is not added permission beyond 1 mm.',
                    'Nominal checks do not establish printing, slicing, assembly or physical one-ball function.']}
    target=OUT/'seam-candidate-report.json'
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(report['status'],f'{sum(r["passed"] for r in cases)}/{len(cases)} checks')
    print('gate bounds',report['locator_nominal_free_play']['gate_bounds'])
    for r in cases:
        if not r['passed']: print('FAIL',r['name'],r['components'])
    return 0 if passed else 1


if __name__=='__main__': raise SystemExit(main())
