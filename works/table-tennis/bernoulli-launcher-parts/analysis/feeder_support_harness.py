#!/usr/bin/env python3
"""Nominal load-harness geometry. Does not validate load, seals or ergonomics."""
from pathlib import Path
import argparse
import concurrent.futures
import hashlib
import importlib.util
import json
import math
import subprocess
from feeder_integration import classify

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/feeder-support-harness'
SCAD=ROOT/'cad/feeder-support-harness.scad'
EXE='/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
SOURCES=['cad/parameters.scad','cad/cam-study.scad','cad/feeder-supports.scad',
 'cad/feeder-guide-revision.scad','cad/feeder-cam-guide-revision.scad',
 'cad/feeder-body.scad','cad/feeder-seam-candidate.scad',
 'cad/feeder-support-harness.scad','analysis/feeder_support_harness.py',
 'analysis/feeder_integration.py']

def hashes():return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()for p in SOURCES}

def render(name,defs,suffix='.stl',extra=()):
    target=OUT/f'{name}{suffix}';target.unlink(missing_ok=True)
    cmd=[EXE,'--render','--backend','Manifold','-o',str(target),*extra]
    if suffix=='.stl':cmd+=['--export-format','asciistl']
    for k,v in defs.items():cmd+=['-D',f'{k}={json.dumps(v)}']
    cmd.append(str(SCAD))
    p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
    log=p.stdout+p.stderr;(OUT/f'{name}.log').write_text(log)
    r={'name':name,'definitions':defs,'returncode':p.returncode,
       'path':str(target.relative_to(ROOT))if target.exists()else None,
       'empty':'Current top level object is empty'in log}
    if 'WARNING:'in log or 'ERROR:'in log or(not target.exists()and not r['empty']):
        r.update(error=log[-2500:],passed=False)
    return r

def probe(job):
    name,defs,expected=job
    r=render(name,{'sh_part':'probe',**defs})
    if 'error'in r:return r
    if r['path']:r.update(classify(ROOT/r['path']))
    else:r.update(components=[],has_solid_or_unclassified_overlap=False)
    r['expected_solid_overlap']=expected
    r['passed']=r['has_solid_or_unclassified_overlap']==expected
    return r

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--probes-only',action='store_true')
    a=ap.parse_args();OUT.mkdir(parents=True,exist_ok=True);before=hashes()
    jobs=[(k,{'sh_probe':k},k in ['root','bolt_control','finger_control','keeper_remove'])for k in
        ['fixed','frame_sweep','finger','old_tools','new_tools','hardware',
         'nuts_insert','beam_remove','keeper_remove','keeper_remove_beam_off','carrier_gib_remove','frame_lift',
         'finger_remove','cam_cover_remove','cam_gib_remove','bore','root','mount_contact',
         'bolt_control','finger_control']]
    jobs += [(f'motion-{i}',{'sh_probe':'motion','sh_t':t},False)
             for i,t in enumerate([0,.2,.4,.5,.6,.8,1])]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:
        rows=list(pool.map(probe,jobs))
    parts=[];pictures=[]
    if not a.probes_only:
        spec=importlib.util.spec_from_file_location('stl_check',
            '/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py')
        check=importlib.util.module_from_spec(spec);spec.loader.exec_module(check)
        for name,selector in [('positive-half','positive_half'),('negative-half','negative_half'),('beam-grip','beam')]:
            r=render(name,{'sh_part':selector})
            if r.get('path'):
                f=ROOT/r['path'];r.update(sha256=hashlib.sha256(f.read_bytes()).hexdigest(),mesh=check.inspect(f,1e-6))
                r['component_count']=len(classify(f)['components'])
                r['passed']=r['mesh']['watertightByEdgeTopology']and r['component_count']==1
            parts.append(r)
        for name,defs,camera in [
            ('assembly',{'sh_part':'assembly'},'15,-10,-38,65,0,32,540'),
            ('finger-path',{'sh_part':'finger_view'},'45,-25,-10,90,0,0,410'),
            ('exploded',{'sh_part':'exploded'},'15,-18,-38,65,0,30,570'),
            ('beam',{'sh_part':'beam'},'28,-51,-64,90,0,0,360')]:
            pictures.append(render(name,defs,'.png',['--imgsize=1400,1100',f'--camera={camera}','--viewall','--autocenter']))
    stable=before==hashes()
    passed=stable and all(r.get('passed',False)for r in rows+parts)and all(r.get('path')for r in pictures)
    report={'status':'NOMINAL_HARNESS_GEOMETRY_PASS_PHYSICAL_OPEN'if passed else'FAIL_OR_STALE',
        'sources_stable':stable,'source_sha256':before,'case_count':len(rows),
        'pass_count':sum(r.get('passed',False)for r in rows),'cases':rows,
        'parts':parts,'pictures':pictures,'probes_only':a.probes_only,
        'hardware':{'M4x20_socket_head':4,'M4_nut_AF7_H3.2':4,'washer_ID4.3_OD9_H0.8':4,
                    'textile_strap_width20_thickness_up_to1.5':'1, length set around actual hose; no clamp torque claimed'},
        'finger_clearance_analytic':{'probe_diameter_mm':16,'stroke_mm':20,
          'upper_arm_support_line_XZ':'2*x + 3*z = 184',
          'rest_finger_center_XZ':[76,24],
          'minimum_nominal_gap_mm':(2*76+3*24-184)/math.sqrt(13)-8,
          'scope':'Cross-section conservative upper support line; later +Z motion increases distance. No skin, glove or anthropometric model.'},
        'limits':['Nominal rigid geometry only; PETG strength, creep, layers and fastener torque OPEN.',
          'Seven full-mechanism poses; convex frame sweep is a conservative continuous enclosure.',
          'Finger path is a diameter16 geometric probe in the diameter18 ring, not hand-fit verification.',
          'The hose strap slots are modelled, but soft hose deformation, strap friction and drag rating are unverified.',
          'The original Y is deliberately not a support anchor; support load returns to the fixed handgrip.',
          'No inlet/outlet seal or PC clamp change is included. Parents must union shared additions/cuts into one host.',
          'Captive nut insertion is checked before beam installation. Remove harness screws/beam before splitting body.',
          'Keeper removal is intentionally blocked with the beam fitted (positive collision case); remove all four M4 screws and withdraw beam first. The beam-off keeper sweep must be clear.',
          'Thread engagement uses smooth envelope geometry, not thread strength or pullout simulation.']}
    (OUT/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({k:report[k]for k in ['status','case_count','pass_count','sources_stable']},indent=2))
    for r in rows+parts:
        if not r.get('passed',False):print('FAIL',r['name'],r.get('error')or r.get('components')or r)
    return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
