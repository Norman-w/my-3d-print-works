#!/usr/bin/env python3
"""Outlet retention: actual CSG, mesh sections and controls; no clamp-force claim."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import struct
from spin_head_geometry import inspect_mesh, x_surface_intersections

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/outlet-retention'
SOURCE=ROOT/'cad/outlet-retention.scad'
SCAD='/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
PRINT_PARTS=('capture-positive','capture-negative','pipe-clamp-positive','pipe-clamp-negative','liner')

def y_surface_intersections(path,x,z):
    """Read actual STL triangles for an independent Y-directed flat-face check."""
    raw=path.read_bytes(); hits=set()
    for i in range(struct.unpack_from('<I',raw,80)[0]):
        row=struct.unpack_from('<12f',raw,84+50*i)
        a,b,c=[row[j:j+3] for j in (3,6,9)]
        ux,uz,vx,vz=b[0]-a[0],b[2]-a[2],c[0]-a[0],c[2]-a[2]
        det=ux*vz-uz*vx
        if abs(det)<1e-10: continue
        dx,dz=x-a[0],z-a[2]
        u,v=(dx*vz-dz*vx)/det,(ux*dz-uz*dx)/det
        if u>=-1e-7 and v>=-1e-7 and u+v<=1+1e-7:
            hits.add(round(a[1]+u*(b[1]-a[1])+v*(c[1]-a[1]),5))
    return sorted(hits)

def run(name, part, definitions=None, empty=False):
    path=OUT/(name+'.stl')
    path.unlink(missing_ok=True)
    command=[SCAD,'--hardwarnings','--backend','Manifold','--export-format','binstl','-o',str(path),'-D',f'or_part="{part}"']
    for key,value in (definitions or {}).items(): command+=['-D',f'{key}={value}']
    command.append(str(SOURCE))
    r=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
    log=r.stdout+r.stderr
    (OUT/(name+'.log')).write_text(log)
    is_empty='Current top level object is empty' in log and not path.exists()
    if r.returncode and not is_empty: raise RuntimeError(name+'\n'+log)
    result={'name':name,'part':part,'definitions':definitions or {},'expected_empty':empty,'empty':is_empty,'command':command}
    if path.exists():
        m=inspect_mesh(path);result['mesh']=m
        planar=m['volume_mm3']<1e-6 and all(min(x['size'])<1e-6 for x in m['component_bounds_mm'])
        result['planar_contact_only']=planar
        is_empty=is_empty or planar
    result['matches_expectation']=is_empty==empty
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--render',action='store_true')
    args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    parts=[run('outlet-'+p,p) for p in PRINT_PARTS]
    reference=run('outlet-host-positive','host-positive')
    tests=[]
    for p in ('capture-host-collision','capture-halves-collision','liner-host-pipe-collision','crossed-hardware','ballway-collision','seal-access-collision','nut-insertion'):
        tests.append(run(p,p,empty=True))
    for c in (0,0.1,0.2,0.3,0.4):
        for p in ('clamp-halves-collision','hardware-collision','tools-collision'):
            tests.append(run(f'{p}-c{c:g}',p,{'or_closure':c},True))
        # Closing the rigid CAD clamp onto the undeformed pipe MUST register.
        tests.append(run(f'pipe-contact-c{c:g}','clamp-pipe-contact',{'or_closure':c},c<0.3))
    for d in (0,2,5,10,20,40):
        for p in ('capture-removal','pipe-clamp-removal','liner-insertion','pipe-insertion'):
            tests.append(run(f'{p}-{d:g}',p,{'or_service':d},True))
        for p in ('capture-removal','pipe-clamp-removal'):
            tests.append(run(f'{p}-negative-{d:g}',p,{'or_service':d,'or_service_positive':'false'},True))
    for d in (-0.8,0.8):
        tests.append(run(f'flange-retention-control-{d:g}','flange-stop',{'or_service':d},False))
    tests.append(run('control-ear-stop-overrun','clamp-halves-collision',{'or_closure':0.6},False))
    tests.append(run('control-old-collar-seal-overlap','old-collar-band-control',empty=False))
    tests.append(run('control-rod-axis-offset','old-rod-axis-control',empty=False))
    tests.append(run('control-liner-upstream-overrun','liner-insertion',{'or_service':-0.2},False))
    tests.append(run('control-pipe-through-liner-shoulder','pipe-insertion',{'or_service':-0.2},False))
    for angle in (-5,-1,0,1,5):
        tests.append(run(f'flange-rotation-{angle:g}','flange-rotation',{'or_angle':angle},abs(angle)<=1))
    mesh={p['part']:p['mesh'] for p in parts}
    def section(part,y,z): return x_surface_intersections(OUT/('outlet-'+part+'.stl'),y,z)
    sections={
        'liner_mid_y0_z102':section('liner',0,102),
        'liner_tip_y0_z117p9':section('liner',0,117.9),
        'capture_recess_y0_z46':section('capture-positive',0,46),
        'capture_upper_lip_y0_z51':section('capture-positive',0,51),
        'capture_lower_y0_z40p5':section('capture-positive',0,40.5),
        'host_flange_y0_z46':x_surface_intersections(OUT/'outlet-host-positive.stl',0,46),
        'host_lower_y0_z40p5':x_surface_intersections(OUT/'outlet-host-positive.stl',0,40.5),
        'pipe_clamp_y0_z102':section('pipe-clamp-positive',0,102),
        'pipe_ear_stop_y60_z102':section('pipe-clamp-positive',60,102),
        'pipe_rod_slot_y45_z102':section('pipe-clamp-positive',45,102),
    }
    values={
        'liner_id_mid_mm':2*sections['liner_mid_y0_z102'][2],
        'liner_wall_mid_mm':sections['liner_mid_y0_z102'][3]-sections['liner_mid_y0_z102'][2],
        'flange_recess_radial_clearance_mm':sections['capture_recess_y0_z46'][0]-sections['host_flange_y0_z46'][-1],
        'capture_lower_radial_clearance_mm':sections['capture_lower_y0_z40p5'][0]-sections['host_lower_y0_z40p5'][-1],
        'pipe_clamp_open_x_diameter_mm':2*sections['pipe_clamp_y0_z102'][0],
        'pipe_clamp_closed_x_diameter_mm':2*(sections['pipe_clamp_y0_z102'][0]-sections['pipe_ear_stop_y60_z102'][0]),
        'rod_slot_closed_half_width_mm':sections['pipe_rod_slot_y45_z102'][0]-sections['pipe_ear_stop_y60_z102'][0],
        'seal_to_capture_axial_gap_mm':54-mesh['capture-positive']['bounds_max_mm'][2],
        'seal_to_pipe_clamp_axial_gap_mm':mesh['pipe-clamp-positive']['bounds_min_mm'][2]-89,
        'liner_end_margin_beyond_pipe_clamp_mm':mesh['liner']['bounds_max_mm'][2]-mesh['pipe-clamp-positive']['bounds_max_mm'][2],
    }
    host_y=y_surface_intersections(OUT/'outlet-host-positive.stl',1,46)
    capture_y=y_surface_intersections(OUT/'outlet-capture-positive.stl',1,46)
    values['flange_flat_positive_y_mm']=max(host_y)
    values['recess_flat_positive_y_mm']=min(y for y in capture_y if y>0)
    values['anti_rotation_flat_clearance_mm']=values['recess_flat_positive_y_mm']-values['flange_flat_positive_y_mm']
    checks={
        'liner_bore_44p4':abs(values['liner_id_mid_mm']-44.4)<1e-4,
        'liner_mid_wall_1p6':abs(values['liner_wall_mid_mm']-1.6)<1e-4,
        'flange_radial_clearance_0p3':abs(values['flange_recess_radial_clearance_mm']-0.3)<1e-4,
        'lower_host_taper_has_clearance':values['capture_lower_radial_clearance_mm']>0.3,
        'clamp_open_50p6':abs(values['pipe_clamp_open_x_diameter_mm']-50.6)<1e-4,
        'clamp_limit_49p8':abs(values['pipe_clamp_closed_x_diameter_mm']-49.8)<1e-4,
        'rod_at_max_close_has_radial_clearance':values['rod_slot_closed_half_width_mm']>2.2,
        'seal_band_not_occupied':values['seal_to_capture_axial_gap_mm']>=1 and values['seal_to_pipe_clamp_axial_gap_mm']>=1,
        'liner_support_extends_past_clamp':values['liner_end_margin_beyond_pipe_clamp_mm']>=4,
        'host_flat_y30':abs(values['flange_flat_positive_y_mm']-30)<1e-4,
        'capture_flat_y30p3':abs(values['recess_flat_positive_y_mm']-30.3)<1e-4,
    }
    report={
        'status':'CANDIDATE_GEOMETRY_ONLY_PHYSICAL_CLAMP_AND_SEAL_OPEN',
        'source_sha256':{str(p):hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in map(Path,('cad/parameters.scad','cad/feeder-body.scad','cad/outlet-retention.scad','analysis/outlet_retention.py','analysis/spin_head_geometry.py'))},
        'parts':parts,'host_reference':reference,'entity_intersections':tests,
        'all_expected_intersections_match':all(t['matches_expectation'] for t in tests),
        'all_part_meshes_watertight':all(p['mesh']['watertight'] for p in parts),
        'all_parts_single_component':all(p['mesh']['connected_components']==1 for p in parts),
        'mesh_sections_x_mm':sections,'anti_rotation_mesh_sections_y_mm':{'host_at_x1_z46':host_y,'capture_at_x1_z46':capture_y},'independent_dimensions_from_meshes':values,'section_checks':checks,
        'hardware_nominal':{'M4x100_fully_threaded_rod':2,'rod_M4_hex_nut_AF7_h3p2':8,'rod_washer_OD12_ID4p3_t0p8':8,'split_M4x30_socket_screw_head_D7_h4':4,'split_M4_captive_hex_nut_AF7_h3p2':4,'split_washer_OD12_ID4p3_t0p8':4},
        'mechanical_limits':{'capture_is_positive_flange_retention':True,'host_rotation_has_matching_flat_stops':True,'anti_rotation_zero_backlash_claimed':False,'pipe_clamp_is_friction_only':True,'pipe_contact_force_predicted':False,'pipe_closed_interference_is_intended_undeformed_geometry':True,'per_half_closure_before_contact_mm':0.3,'per_half_hard_stop_mm':0.4,'sealing_tape_load_bearing':False,'main_machine_weight_requires_independent_support':True},
        'seal_band':{'z_mm':[54,89],'module_land_mm':[54,69],'PC_land_mm':[69,89],'outer_work_diameter_mm':64,'physical_tape_not_modeled':True,'full_roll_wrap_access_verified':False,'cut_strip_threading_required':True},
        'open':['PC ovalization, grip friction, axial pullout and tightening torque','liner and capture lip strength and creep','FDM tolerance and first-article fit','seal material installation and leakage','real tools and hand access','weight-bearing handle/support integration','dynamic airflow and ball transit'],
    }
    if args.render:
        report['rendered_views']=[]
        for name,part,camera in (
            ('outlet-isometric','assembly','180,-210,185,0,0,79'),
            ('outlet-front','assembly','190,0,80,0,0,80'),
            ('outlet-top','assembly','0,0,300,0,0,79'),
            ('outlet-section','section','200,0,80,0,0,80'),
            ('outlet-axial-slice','axial-slice','200,0,80,0,0,80'),
            ('outlet-exploded','exploded','230,-260,200,0,0,79')):
            path=OUT/(name+'.png')
            cmd=[SCAD,'--hardwarnings','--backend','Manifold','--render','--projection','o','--viewall','--imgsize','1300,1000','--camera',camera,'-D',f'or_part="{part}"','-o',str(path),str(SOURCE)]
            subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,check=True)
            report['rendered_views'].append({'file':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'part':part,'closure':0})
    path=OUT/'outlet-retention-report.json'
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    failures=[t['name'] for t in tests if not t['matches_expectation']]
    print(json.dumps({'report':str(path),'cases':len(tests),'unexpected_intersections':failures,'section_checks':checks,'watertight':report['all_part_meshes_watertight'],'single_components':report['all_parts_single_component']},ensure_ascii=False))
    if failures or not all(checks.values()) or not report['all_part_meshes_watertight'] or not report['all_parts_single_component']: raise SystemExit(2)

if __name__=='__main__': main()
