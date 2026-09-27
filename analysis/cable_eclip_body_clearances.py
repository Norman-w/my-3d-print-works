#!/usr/bin/env python3
"""Nominal metal/service envelopes against current body extrusion layer slabs.

Read-only. Conservative swept-bead projection flags are not measured collisions.
"""
from pathlib import Path
import argparse, hashlib, json, math, sys
import numpy as np
from shapely.geometry import Point, Polygon, LineString, box

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'analysis')]
import cable_input_slice_review as parser
from cable_slice_contract import frozen_scene, input_matrix

SOURCE_SHA='cf2dc90ecea43e0bb5bf3b6fe68f9cf7adb8d47145b4b15577e5dd40f1679d8d'
ERROR=parser.ARC_ERROR+parser.BUFFER_ERROR
NONMODEL={'Custom','Brim','Skirt','Prime tower','Prime tower infill','Flush','Undefined',''}
def path(p):
    p=Path(p);return p if p.is_absolute() else ROOT/p
def sha(p):return hashlib.sha256(path(p).read_bytes()).hexdigest()
def load(p):return json.loads(path(p).read_text())

def projection(s,lo,hi):
    if s['kind']=='zcylinder':
        if min(hi,s['z'][1])<=max(lo,s['z'][0])+1e-9:return Polygon()
        return Point(s['xy']).buffer(s['r']/math.cos(math.pi/256),quad_segs=64)
    lo=max(lo,s['cz']-s['r']);hi=min(hi,s['cz']+s['r'])
    if hi<=lo+1e-9:return Polygon()
    if s['kind']=='xcylinder':
        dz=max(lo-s['cz'],s['cz']-hi,0)
        radius=math.sqrt(max(0,s['r']**2-dz**2))
        return box(s['x'][0],s['cy']-radius,s['x'][1],s['cy']+radius)
    a=np.arange(6)*math.pi/3+math.pi/6
    yz=Polygon(np.column_stack([s['cy']+s['r']*np.sin(a),s['cz']-s['r']*np.cos(a)]))
    p=yz.intersection(box(-1000,lo,1000,hi))
    return box(s['x'][0],p.bounds[0],s['x'][1],p.bounds[2]) if not p.is_empty else Polygon()

def review(folder):
    folder=path(folder).resolve();inv=load(folder/'invocation.json')
    assert inv['part']=='cable-input-body'
    ar=load(folder/'artifact-review.json')
    assert ar['status']=='CURRENT_ECLIP_SLICE_ARTIFACT_IDENTITY_PASS'
    assert all(sha(p)==h for p,h in ar['evidence_sha256'].items())
    scene,contract=frozen_scene(inv)
    assert contract['input_cad_sha256']==SOURCE_SHA
    L=input_matrix(scene);ci=scene['ci']
    assert ci['stop_axis_local_yz']==[-24,2]
    assert ci['adjuster_seat_x']==[-45,-37] and ci['adjuster_shank_d']==6
    specs=[
        {'name':'M6 adjuster shank through fixed seat','kind':'xcylinder','x':[-45,-37],'cy':60,'cz':2,'r':3},
        {'name':'M3 stop shank at exit','kind':'xcylinder','x':[-32.6,-29],'cy':-24,'cz':2,'r':1.5},
        {'name':'M3 captured stop nut nominal SW5.5','kind':'xhex','x':[-35,-32.6],'cy':-24,'cz':2,'r':5.5/math.sqrt(3)},
        {'name':'Stop socket head service passage D5.5','kind':'xcylinder','x':[-64,-38.3],'cy':-24,'cz':2,'r':2.75},
    ]
    for i,p in enumerate(ci['mount_holes_cad']):
        q=parser.affine(p,np.linalg.inv(L))
        specs.append({'name':'Host M4 shank '+str(i+1),'kind':'zcylinder','xy':q[:2].tolist(),'z':[-15,36],'r':2})
    summaries=[{**s,'examined_model_commands':0,'minimum_clearance_lower_mm':None,
        'possible_intrusion_commands':0,'examples':[]} for s in specs]
    inverse=np.linalg.inv(np.array(ar['input_local_to_command']))
    counts={};maxheight=0
    for rec in parser.extrusion_paths((folder/'plate_1.gcode').open()):
        counts[rec.feature]=counts.get(rec.feature,0)+1
        if rec.feature in NONMODEL or rec.feature.startswith('Support'):continue
        assert np.allclose(rec.points[:,2],rec.layer,atol=1e-5)
        q=parser.affine(rec.points,inverse)
        shift=(inverse[:3,:3]@np.array([0,0,-rec.height]))[2]
        lo,hi=sorted([float(q[0,2]),float(q[0,2]+shift)])
        line=LineString(q[:,:2]);maxheight=max(maxheight,rec.height)
        for s,r in zip(specs,summaries):
            roi=projection(s,lo,hi)
            if roi.is_empty:continue
            distance=line.distance(roi)
            if distance>3:continue
            gap=distance-rec.width/2-ERROR
            r['examined_model_commands']+=1
            old=r['minimum_clearance_lower_mm']
            r['minimum_clearance_lower_mm']=gap if old is None else min(gap,old)
            if gap<0:
                r['possible_intrusion_commands']+=1
                if len(r['examples'])<8:r['examples'].append({'line':rec.line,'feature':rec.feature,
                    'print_top_mm':rec.layer,'local_z_slab':[lo,hi],'clearance_lower_mm':gap})
    assert all(r['examined_model_commands'] for r in summaries)
    flags=[r['name'] for r in summaries if r['possible_intrusion_commands']]
    result={'status':'BOUNDED_BODY_NOMINAL_ENVELOPES_FLAGGED' if flags else 'BOUNDED_BODY_NOMINAL_ENVELOPES_CLEAR',
        'part':inv['part'],'flags':flags,'envelopes':summaries,'feature_counts':counts,
        'max_emitted_bead_height_mm':maxheight,'bead_xy_error_bound_mm':ERROR,
        'artifact_review':str(folder/'artifact-review.json'),'artifact_review_sha256':sha(folder/'artifact-review.json'),
        'source_sha256':SOURCE_SHA,'source_contract':contract,
        'evidence_sha256':{str(folder/'artifact-review.json'):sha(folder/'artifact-review.json'),
            str(folder/'plate_1.gcode'):sha(folder/'plate_1.gcode'),str(Path(__file__).resolve()):sha(__file__),
            str(ROOT/'analysis/cable_input_slice_review.py'):sha(ROOT/'analysis/cable_input_slice_review.py')},
        'limits':['Evaluates nominal shank/nut/head service envelopes, not supplier tolerances, printed dimensions or real tools.',
            'Each actual extrusion bead occupies its declared constant-height slab; hardware projections span that slab. Negative lower bounds are possible overlaps under this conservative projection, not measured interference.',
            'Support is excluded here and must be removed as separately reviewed. Roof sag, surface finish, strength and torque remain unverified.'],
        'manufacturing_release':False,'physical_acceptance':False,'sent_to_printer':False}
    (folder/'body-clearance-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'part':inv['part'],'status':result['status'],'flags':flags,
        'minimum_clearances':[(r['name'],r['minimum_clearance_lower_mm']) for r in summaries]},ensure_ascii=False))
    return result

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--folder',type=Path,required=True)
    review(ap.parse_args().folder)
