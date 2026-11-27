#!/usr/bin/env python3
"""Supplementary spin-head fastener, access and retaining-load-path review.

No print submission. This checks real nominal fastener solids and bounded tool
envelopes, not threads, clamp force, printed strength or dynamic spin.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import struct
import subprocess
import numpy as np
from feeder_body_geometry import read_mesh, mesh_topology

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/spin-complete-hardware'
CAD=ROOT/'cad/spin-complete-hardware.scad'
EXE='/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
def sources():
    result={};pending=[CAD]
    while pending:
        p=pending.pop().resolve();key=str(p.relative_to(ROOT))
        if key in result:continue
        result[key]=sha(p)
        pending.extend(p.parent/d for d in re.findall(r'\b(?:use|include)\s*<([^>]+)>',p.read_text()))
    return dict(sorted(result.items()))

def bearing_planes(f,p):
    return {0:[-34.5,-31.5,-31,-27.5,-24.5,-22.1,-21.5,47,49.3,51.7,55,55.5,55.8,58.2,59,62,65,68.2,71,71.5,74.5,52.75-p,
               27.55+f,29.95+f,65.75+f,72.25+f,75.25+f],
            1:[-11,-6.9,-3.7,5,9],2:[55,57.1,59.5,63.3,63.5,65]}

def classify(path,f,p):
    if not path.exists():return {'empty':True,'solid_or_unclassified':False}
    t,_=read_mesh(path);info=mesh_topology(t)
    raw=path.read_bytes()
    binary=len(raw)>=84 and len(raw)==84+50*struct.unpack_from('<I',raw,80)[0]
    # Binary STL rounds each coordinate independently to float32. Bound that
    # representation error explicitly; this is not a manufacturing allowance.
    delta=float(np.max(abs(np.spacing(t.astype(np.float32)))))/2 if binary else 0.
    plane_tolerance=1e-7+3*delta
    volume_tolerance=float(1e-7+info['surface_area_mm2']*np.sqrt(3)*delta)
    # A triangle must lie completely in a listed actual axial bearing plane.
    # No arbitrary tiny volume is accepted on its own.
    matched=np.zeros(len(t),dtype=bool);planes=bearing_planes(f,p);used=[]
    for axis,values in planes.items():
        for v in values:
            hit=(abs(t[:,:,axis]-v)<plane_tolerance).all(axis=1)
            if hit.any():used.append([axis,v,int(hit.sum())]);matched|=hit
    cone_faces=0
    for cy in [-7,7]:
        for k in range(72):
            a=2*np.pi*(k+.5)/72;c=np.cos(np.pi/72)
            distance=(t[:,:,0]-26.75-f)*np.cos(a)+(t[:,:,1]-cy)*np.sin(a)-(t[:,:,2]-61.75)*c
            hit=(abs(distance)<plane_tolerance).all(axis=1)
            # Only finite 90-degree seat faces, never their infinite extensions.
            hit&=(t[:,:,2].min(axis=1)>=63.45-plane_tolerance)&(t[:,:,2].max(axis=1)<=65.02+plane_tolerance)
            cone_faces+=int((hit&~matched).sum());matched|=hit
    contact=bool(matched.all() and abs(info['signed_volume_mm3'])<volume_tolerance)
    return {'empty':False,'sha256':sha(path),'mesh':info,
            'all_triangles_on_named_axial_bearing_planes':bool(matched.all()),
            'bearing_planes':[{'axis':a,'coordinate_mm':v,'triangles':n}for a,v,n in used],
            'unmatched_triangles':int((~matched).sum()),'zero_thickness_bearing_contact':contact,
            'triangles_on_DIN7991_seating_cone':cone_faces,
            'binary_stl_half_ulp_mm':delta,'representation_plane_tolerance_mm':plane_tolerance,
            'representation_volume_bound_mm3':volume_tolerance,
            'solid_or_unclassified':not contact}

def invoke(name,defs,expect_solid=False,render=False,artifact=False):
    target=OUT/(name+('.png'if render else'.stl'));target.unlink(missing_ok=True)
    cmd=[EXE,'--hardwarnings','--backend','Manifold']
    if render:cmd+=['--render','--imgsize=1400,1100','--projection=o','--camera=4,0,26,64,0,30,420','--viewall','--autocenter']
    else:cmd+=['--export-format','asciistl']
    for k,v in defs.items():cmd+=['-D',f'{k}={json.dumps(v)}']
    cmd+=['-o',str(target),str(OUT/'snapshot/cad/spin-complete-hardware.scad')]
    r=subprocess.run(cmd,capture_output=True,text=True,cwd=ROOT);log=r.stdout+r.stderr
    (OUT/(name+'.log')).write_text(log)
    empty='Current top level object is empty'in log and not target.exists()
    ok='WARNING:'not in log and'ERROR:'not in log and(r.returncode==0 or(r.returncode==1 and empty))
    if not ok:raise RuntimeError(name+'\n'+log)
    if render:return {'name':name,'sha256':sha(target),'path':str(target.relative_to(ROOT))}
    if artifact:
        t,_=read_mesh(target)
        return {'name':name,'sha256':sha(target),'path':str(target.relative_to(ROOT)),
                'role':'purchased-reference','state':'held'if defs.get('sch_held')else'work',
                'definitions':defs,'mesh':mesh_topology(t),
                'note':'Catalogue spring installation envelope, not coils'if defs.get('sch_part')=='spring'else'Nominal metal external solids, no helical thread geometry; never print'}
    info=classify(target,defs.get('sch_float',0),defs.get('sch_preload',0))
    result={'name':name,'definitions':defs,'command':cmd,'expected_solid_or_unclassified':expect_solid,
            'passed':info['solid_or_unclassified']==expect_solid,**info}
    print(name,'PASS'if result['passed']else'FLAG',flush=True)
    return result

def stackups():
    # Axial coordinates at nut load seats, not arbitrary pocket midpoints.
    entries=[('cover_M3x12',6,[47,59],[49.3,51.7],'+X',True),
             ('guide_M3x10_with_0.5_washer',2,[-31.5,-21.5],[-24.5,-22.1],'-X',True),
             ('keeper_DIN7991_M3x10',2,[54.75,63.25],[57.1,59.5],'+Z',True),
             ('pull_M3x45',1,[27.25,72.25],[27.55,29.95],'+X',True),
             ('latch_M3x16_with_0.5_washer',1,[55.5,71.5],[55.8,58.2],'+X',True),
             ('clamp_M4x16',1,[-11,5],[-6.9,-3.7],'+Y',True),
             ('preload_DIN464_M4x25_at_maximum_preload',1,[48.75,73.75],[55.8,59],'+X',True),
             ('preload_external_M4_locknut',1,[48.75,73.75],[65,68.2],'-X',True)]
    rows=[]
    for name,n,shaft,nut,pull,retained in entries:
        rows.append({'id':name,'count':n,'shaft_interval_mm':shaft,'nut_interval_mm':nut,
                     'nut_axial_overlap_mm':max(0,min(shaft[1],nut[1])-max(shaft[0],nut[0])),
                     'full_nut_height_in_nominal_shaft':shaft[0]<=nut[0]and shaft[1]>=nut[1],
                     'nut_tightening_pull_direction':pull,'host_reaction_shoulder_present':retained})
    return rows

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--render',action='store_true');args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);identity=sources()
    for p in identity:
        dest=OUT/'snapshot'/p;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/p,dest)
    dump(OUT/'snapshot-manifest.json',identity)
    if not(OUT/'baseline').exists():
        shutil.copytree(OUT/'snapshot',OUT/'baseline');dump(OUT/'baseline/manifest.json',identity)
    cases=[]
    for group in ['cover','cage','guide','keeper','pull','latch','clamp','preload']:
        cases.append(invoke('metal-fit-'+group,{'sch_part':'fit','sch_group':group,'sch_held':True,'sch_float':5,'sch_preload':4}))
        cases.append(invoke('nut-entry-'+group,{'sch_part':'nut-feed','sch_group':group}))
    for f,p,held in [(0,0,False),(5.25,4,False),(5,4,True)]:
        cases.append(invoke(f'all-metal-fit-f{f}-p{p}',{'sch_part':'fit','sch_group':'all','sch_float':f,'sch_preload':p,'sch_held':held}))
    for group in ['cover','cage','guide','pull','latch','clamp']:
        cases.append(invoke('driver-'+group,{'sch_part':'driver','sch_group':group,'sch_float':5,'sch_preload':4,'sch_held':True}))
    cases.append(invoke('keeper-driver-carriage-removed',{'sch_part':'keeper-driver'}))
    cases.append(invoke('keeper-driver-wrong-sequence',{'sch_part':'driver','sch_group':'keeper'},True))
    cases.append(invoke('preload-nut-wrong-sequence',{'sch_part':'wrong-preload-sequence'},True))
    for angle in [-5,0,5]:
        for f in [0,5.25]:
            cases.append(invoke(f'lock-wrench-a{angle}-f{f}',{'sch_part':'wrench','sch_angle':angle,'sch_float':f,'sch_preload':4}))
    # These are intentionally expected to RESIST outward displacement. Empty
    # results are retained as the failed retaining-load-path counterexample.
    for d in [-.1,-1]:
        cases.append(invoke(f'guide-retention-d{d}',{'sch_part':'guide-withdrawal','sch_delta':d},True))
    cases.append(invoke('guide-inward-stop-control',{'sch_part':'guide-withdrawal','sch_delta':.3},True))
    cases.append(invoke('guide-full-shoulder-bearing',{'sch_part':'guide-bearing'},True))
    cases.append(invoke('metal-offset-control',{'sch_part':'fault'},True))
    images=[]
    if args.render:
        images.append(invoke('hardware-assembly',{'sch_part':'assembly','sch_float':5,'sch_preload':4,'sch_held':True},render=True))
        images.append(invoke('guide-retention-counterexample',{'sch_part':'guide-withdrawal-view','sch_delta':-5},render=True))
        images.append(invoke('external-locknut-wrench',{'sch_part':'wrench-view','sch_float':0,'sch_preload':4},render=True))
        images.append(invoke('hardware-working-exterior',{'sch_part':'assembly','sch_float':0,'sch_preload':0,'sch_held':False,'sch_opaque':True},render=True))
    artifacts=[]
    for state,f,p,held in [('work',0,0,False),('held',5,4,True)]:
        for name,part in [('hardware','hardware'),('spring','spring')]:
            artifacts.append(invoke(f'{name}-{state}'+('-envelope'if name=='spring'else''),
                {'sch_part':part,'sch_group':'all','sch_float':f,'sch_preload':p,'sch_held':held},artifact=True))
    stable=sources()==identity
    blockers=[v['name']for v in cases if not v['passed']]
    report={'status':'BOUNDED_HARDWARE_REVIEW_PASS'if stable and not blockers else'DESIGN_OPEN_OR_SOURCE_MOVED',
            'source_sha256':identity,'sources_stable':stable,'analysis_sha256':sha(Path(__file__)),
            'cases':cases,'open_case_names':blockers,'nominal_thread_stackups':stackups(),'pictures':images,'artifacts':artifacts,
            'selected_thumb_screw':{'manufacturer':'ELESA+GANTER','designation':'DIN464-M4-25','head_d_mm':16,'shoulder_d_mm':8,'total_head_height_mm':9.5,'knurl_height_mm':3.5,'thread_length_mm':25,
                                    'source':'https://www.elesa-ganter.si/siteassets/PDF/EN/DIN%20464.pdf'},
            'limits':['Nominal screw/nut external dimensions; threads, fillets, purchased tolerances and tightening forces are not simulated.',
                      '7mm open-end wrench is a conditional envelope using GEDORE R09100070 catalogue head width15.5, thickness3.7, overall length105; not a supplier full CAD or proof for all 7mm wrenches.',
                      'Wrench is only checked at -5/0/+5 degree orientations; no unrestricted swing claim.',
                      'Nut entry hulls are conservative continuous translational envelopes for their specified preassembly order.',
                      'No dynamic ball, torque, clamp crush, material friction or complete physical acceptance.',
                      'No slicing and no printing in this hardware review.'],
            'sent_to_printer':False,'manufacturing_release':False}
    dump(OUT/'report.json',report)
    print(json.dumps({'status':report['status'],'open_case_names':blockers},indent=2))
    return 0 if stable and not blockers else 1

if __name__=='__main__':raise SystemExit(main())
