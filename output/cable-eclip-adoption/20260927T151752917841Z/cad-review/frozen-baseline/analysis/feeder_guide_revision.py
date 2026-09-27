#!/usr/bin/env python3
"""Bounded actual-CSG review of the independent adjustable-gib revision."""
from pathlib import Path
import concurrent.futures
import hashlib
import importlib.util
import json
import math
import subprocess
from feeder_integration import classify

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/guide-revision'
SCAD=ROOT/'cad/feeder-guide-revision.scad'
EXE='/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
SOURCES=['cad/parameters.scad','cad/cam-study.scad','cad/feeder-supports.scad',
         'cad/feeder-body.scad','cad/feeder-guide-revision.scad',
         'analysis/feeder_guide_revision.py','analysis/feeder_integration.py']

def hashes():return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES}

def render(label,definitions,suffix='.stl',extra=()):
    target=OUT/f'{label}{suffix}';target.unlink(missing_ok=True)
    cmd=[EXE,'--render','--backend','Manifold','-o',str(target),*extra]
    if suffix=='.stl':cmd+=['--export-format','asciistl']
    for k,v in definitions.items():cmd+=['-D',f'{k}={json.dumps(v)}']
    cmd.append(str(SCAD));p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
    log=p.stdout+p.stderr;(OUT/f'{label}.log').write_text(log)
    if 'WARNING:' in log or 'ERROR:' in log:return {'name':label,'error':log[-1800:],'passed':False}
    return {'name':label,'definitions':definitions,'exit_code':p.returncode,'path':str(target.relative_to(ROOT)) if target.exists() else None,'empty':'Current top level object is empty' in log}

def probe(job):
    name,defs,expect_overlap=job
    r=render(name,{'revision_part':'probe',**defs})
    if 'error' in r:return r
    if r['path']:r.update(classify(ROOT/r['path']))
    elif r['empty']:r.update({'has_solid_or_unclassified_overlap':False,'components':[]})
    else:r.update({'has_solid_or_unclassified_overlap':True,'error':'No classified output'})
    r['expected_overlap']=expect_overlap
    r['passed']=r['has_solid_or_unclassified_overlap']==expect_overlap
    return r

def main():
    OUT.mkdir(parents=True,exist_ok=True);before=hashes();jobs=[]
    for i,t in enumerate([0,.2,.4,.5,.6,.8,1]):jobs.append((f'motion-{i}',{'revision_t':t},False))
    for s in [0,.9,1]:jobs.append((f'gib-fit-{s}',{'revision_probe':'gib_fit','revision_setting':s},False))
    for t in [0,1]:jobs.append((f'max-setting-motion-{t}',{'revision_setting':1,'revision_t':t},False))
    for s in [0,1]:jobs.append((f'hardware-{s}',{'revision_probe':'hardware','revision_setting':s},False))
    for kind in ['keeper_remove','gib_remove']:
        for i,r in enumerate([0,.1,.5,1]):jobs.append((f'{kind}-{i}',{'revision_probe':kind,'revision_removal':r},False))
    for kind in ['remove_pins','lift_frame','extract_fingers']:
        for i,r in enumerate([0,.1,.5,1]):jobs.append((f'{kind}-{i}',{'revision_probe':kind,'revision_removal':r},False))
    jobs += [('tools',{'revision_probe':'tools'},False),
             ('datum-sweep',{'revision_probe':'datum_sweep'},False),
             ('datum-intrusion-control',{'revision_probe':'datum_intrusion_control'},True),
             ('advance-stop-control',{'revision_probe':'overtravel'},True),
             ('retract-stop-control',{'revision_probe':'overtravel_back'},True)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4)as pool:cases=list(pool.map(probe,jobs))
    artifacts=[]
    for part in ['right_support','left_support','gib','keeper']:
        artifacts.append(render(part,{'revision_part':part}))
    for name,defs in [('assembly',{}),('exploded',{'revision_exploded':True})]:
        artifacts.append(render(name,{'revision_show_body':False,**defs},'.png',['--imgsize=1500,1100','--camera=0,-12,-12,65,0,35,370']))
    for name,camera in [('support-front','51,0,-14,90,0,0,220'),
                        ('support-top','51,0,-14,0,0,0,220'),
                        ('support-iso','51,0,-14,65,0,35,220')]:
        artifacts.append(render(name,{'revision_part':'right_support'},'.png',
            ['--imgsize=1200,950',f'--camera={camera}']))
    dims_result=render('dimensions',{'revision_part':'dimensions'},'.echo')
    dims_path=ROOT/dims_result['path'] if dims_result.get('path') else None
    dims_text=dims_path.read_text() if dims_path else ''
    dims_line=next((x for x in dims_text.splitlines() if x.startswith('ECHO: "REVISION_DIMENSIONS", ')),None)
    if dims_line is None:raise RuntimeError('No source-derived geometry dimensions')
    dims=dict(json.loads(dims_line.split(', ',1)[1]))
    min_y=dims['display_gib_y']+dims['carrier_width']/2
    max_y=dims['datum_y']-dims['carrier_width']/2
    dims.update({'nominal_carrier_y_interval':[min_y,max_y],
        'rod_clearance_scope':'Smooth circular nominal radii, parallel translation only; not a measured STL minimum distance or manufacturing tolerance.',
        'running_gap_mm':max_y-min_y,
        'rod_clearance_display_mm':dims['sidehole_radius']-dims['rod_radius']-abs(dims['display_carrier_y']),
        'rod_clearance_nominal_parallel_float_mm':dims['sidehole_radius']-dims['rod_radius']-max(abs(min_y),abs(max_y)),
        'band_to_window_gap_mm':dims['datum_z0']-dims['pin_window_half_z'],
        'integral_front_wall_thickness_mm':dims['front_wall_outer_y']-dims['datum_y'],
        'minimum_flat_contact_length_mm':dims['closed_carrier_x1']-dims['datum_x0']-dims['datum_lead'],
        'effective_contact_strip_width_mm':min(dims['carrier_half_z'],dims['datum_z1'])-dims['datum_z0']})
    embed=probe(('datum-embed',{'revision_probe':'datum_embed'},True))
    embed['expected_volume_mm3']=4*(dims['datum_x1']-dims['datum_x0'])*dims['datum_embed']*(dims['datum_z1']-dims['datum_z0'])
    embed['actual_volume_mm3']=sum(c['volume_mm3']for c in embed.get('components',[]))
    embed['passed']=embed.get('passed',False) and len(embed.get('components',[]))==4 and math.isclose(embed['actual_volume_mm3'],embed['expected_volume_mm3'],abs_tol=1e-4)
    # One bounded check against the previously verified ORIGINAL-support
    # counterexample; rejection of that pose is not a new total-error proof.
    prior_path=ROOT/'output/analysis/feeder-tolerance.json'
    prior=json.loads(prior_path.read_text());matrix=prior['witness']['carrier_transform']
    witness_path=OUT/'old-witness-against-gib.scad'
    witness_path.write_text('revision_library_mode=true;\ninclude <../../cad/feeder-guide-revision.scad>\nintersection(){revision_gibs();multmatrix('+json.dumps(matrix)+')cam_finger_local();}\n')
    target=OUT/'old-witness-against-gib.stl';target.unlink(missing_ok=True)
    proc=subprocess.run([EXE,'--render','--backend','Manifold','--export-format','asciistl','-o',str(target),str(witness_path)],cwd=ROOT,capture_output=True,text=True)
    (OUT/'old-witness-against-gib.log').write_text(proc.stdout+proc.stderr)
    old_witness_check=classify(target) if target.exists() else {'has_solid_or_unclassified_overlap':False}
    old_witness_check.update({'original_report_path':str(prior_path.relative_to(ROOT)),
        'original_report_sha256':hashlib.sha256(prior_path.read_bytes()).hexdigest(),
        'scope':'Original-support verified pose versus revised gib only; no new tolerance certification.'})
    spec=importlib.util.spec_from_file_location('stl_inspect','/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py')
    checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
    for a in artifacts:
        if a.get('path'):
            path=ROOT/a['path'];a['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
            if path.suffix=='.stl':
                a['mesh']=checker.inspect(path,1e-6)
                a['solid_component_count']=len(classify(path)['components'])
                a['mesh_passed']=a['mesh']['watertightByEdgeTopology'] and a['solid_component_count']==1
    stable=before==hashes();passed=stable and all(c['passed']for c in cases) and embed['passed'] and all(a.get('path')and a.get('mesh_passed',True)for a in artifacts)
    report={'status':'NOMINAL_CANDIDATE_SAMPLES_PASS_PHYSICAL_OPEN'if passed else'FAIL_OR_STALE','source_sha256':before,'sources_stable':stable,'case_count':len(cases),'pass_count':sum(c['passed']for c in cases),'cases':cases,'artifacts':artifacts,'dimensions':dims,'datum_connection':embed,'old_witness_check':old_witness_check,'limits':['Limited nominal assembly and removal samples, not a continuous tolerance or load proof.','The new datum-only convex sweep covers all pure radial finger translations and nominal parallel Y float; it does not cover carrier tilt, pin lean or full-body continuous motion.','The display is restored to Y=0; nominal parallel carrier float [-0.1,0]mm still consumes rod-hole clearance, and total gate-error acceptance is not inherited.','Setting and locknut behavior require actual hardware and measured running clearance.','No 3D total error, friction, spring, mass target or printing-strength acceptance.']}
    (OUT/'check.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({k:report[k]for k in ['status','case_count','pass_count','sources_stable']},indent=2))
    for r in cases:
        if not r['passed']:print(r['name'],r.get('error')or r.get('components'))
    if not embed['passed']:print('datum connection failed',embed)
    return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
