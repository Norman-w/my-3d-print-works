#!/usr/bin/env python3
"""Bounded CSG checks for the independent right-master cam X guide.

No optimization or physical certification. Existing CAD is never edited.
"""
from pathlib import Path
import argparse
import concurrent.futures
import hashlib
import importlib.util
import json
import re
import subprocess
from feeder_integration import classify

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/feeder-cam-guide-revision'
SCAD=ROOT/'cad/feeder-cam-guide-revision.scad'
EXE='/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
SOURCES=['cad/parameters.scad','cad/cam-study.scad','cad/feeder-supports.scad',
         'cad/feeder-guide-revision.scad','cad/feeder-body.scad',
         'cad/feeder-seam-candidate.scad','cad/feeder-cam-guide-revision.scad',
         'analysis/feeder_cam_guide_revision.py','analysis/feeder_integration.py']
PARTS=[('right-support','right_support','右侧公共架 X 主导向支座',1),
       ('cam-gib','gib','公共架 X 调隙压条',1),
       ('cam-cover','cover','公共架 X 调节可拆外盖',1)]

def hashes():return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()for p in SOURCES}

def render(name,definitions,suffix='.stl',extra=()):
    target=OUT/f'{name}{suffix}';target.unlink(missing_ok=True)
    cmd=[EXE,'--render','--backend','Manifold','-o',str(target),*extra]
    if suffix=='.stl':cmd+=['--export-format','asciistl']
    for k,v in definitions.items():cmd+=['-D',f'{k}={json.dumps(v)}']
    cmd.append(str(SCAD))
    p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
    log=p.stdout+p.stderr;(OUT/f'{name}.log').write_text(log)
    r={'name':name,'definitions':definitions,'exit_code':p.returncode,
       'path':str(target.relative_to(ROOT))if target.exists()else None,
       'empty':'Current top level object is empty'in log}
    if 'WARNING:'in log or 'ERROR:'in log:r.update(error=log[-2000:],passed=False)
    elif not target.exists()and not r['empty']:r.update(error=log[-2000:],passed=False)
    return r

def probe(job):
    name,defs,expected=job
    r=render(name,{'cg_part':'probe',**defs})
    if 'error'in r:return r
    if r['path']:r.update(classify(ROOT/r['path']))
    elif r['empty']:r.update(has_solid_or_unclassified_overlap=False,components=[])
    r['expected_solid_overlap']=expected
    r['passed']=r.get('has_solid_or_unclassified_overlap',True)==expected
    return r

def artifacts():
    spec=importlib.util.spec_from_file_location('stl_check',
        '/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py')
    checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
    output=[]
    for name,selector,title,qty in PARTS:
        r=render(name,{'cg_part':selector})
        r.update(selector={'cg_part':selector},chinese_name=title,quantity=qty,units='mm')
        if r.get('path'):
            file=ROOT/r['path'];r['sha256']=hashlib.sha256(file.read_bytes()).hexdigest()
            r['mesh']=checker.inspect(file,1e-6)
            r['components']=len(classify(file)['components'])
            r['mesh_passed']=r['mesh']['watertightByEdgeTopology']and r['components']==1
        output.append(r)
    pictures=[]
    for name,defs,camera in [
        ('assembly',{'cg_show_body':False},'15,0,-12,62,0,30,380'),
        ('working-section',{'cg_part':'section','cg_show_body':False},'71,23.5,3.55,0,0,0,150'),
        ('support-front',{'cg_part':'right_support'},'55.25,4.5,-14.5,90,0,0,250'),
        ('support-top',{'cg_part':'right_support'},'55.25,4.5,-14.5,0,0,0,250'),
        ('support-iso',{'cg_part':'right_support'},'55.25,4.5,-14.5,65,0,35,280')]:
        pictures.append(render(name,defs,'.png',['--imgsize=1500,1100',f'--camera={camera}']))
    return output,pictures

def dimension_report():
    r=render('dimensions',{'cg_part':'dimensions'},'.echo')
    data=(ROOT/r['path']).read_text()
    line=next(s for s in data.splitlines()if s.startswith('ECHO: "CG_DIMENSIONS", '))
    d=dict(json.loads(line.split(', ',1)[1]))
    d['old_parallel_x_interval_mm']=[-d['old_half_gap'],d['old_half_gap']]
    d['new_parallel_x_interval_mm']=d['parallel_x_interval']
    d['old_parallel_backlash_mm']=2*d['old_half_gap']
    d['new_parallel_backlash_mm']=d['parallel_x_interval'][1]-d['parallel_x_interval'][0]
    d['scope']='Same nominal rigid parallel rail model; no rotation, print error or loaded deflection.'
    return d

def classify_known_limit_planes(case,dimensions):
    """Two meeting stop faces can be one nonplanar zero-volume component.

    Accept only when EVERY output triangle lies on an explicit CAD stop plane,
    with negligible total enclosed volume. Keep the original component evidence.
    This is confined to the all-advanced, +/- .2 axial boundary contacts.
    """
    d=case['definitions']
    if not (d.get('cg_probe')=='gib_fit'and d.get('cg_setting')==1
            and abs(d.get('cg_gib_dz',0))==.2
            and case.get('has_solid_or_unclassified_overlap')and case.get('path')):return
    vertices=[tuple(map(float,m.groups()))for m in re.finditer(
        r'^\s*vertex\s+([-+\deE.]+)\s+([-+\deE.]+)\s+([-+\deE.]+)',
        (ROOT/case['path']).read_text(),re.M)]
    planes=dimensions['known_gib_limit_planes']
    residuals=[min(max(abs(v[a]-p)for v in vertices[i:i+3])for a,p in planes)
        for i in range(0,len(vertices),3)]
    volume=sum(c['volume_mm3']for c in case['components'])
    verified=bool(residuals)and max(residuals)<1e-7 and volume<1e-7
    case['known_stop_plane_union']={'verified':verified,'planes_axis_coordinate_mm':planes,
        'every_triangle_on_a_known_plane':max(residuals)<1e-7,
        'max_triangle_plane_residual_mm':max(residuals),'enclosed_volume_mm3':volume,
        'original_component_classification_preserved':True}
    if verified:
        case['has_solid_or_unclassified_overlap']=False
        case['passed']=not case['expected_solid_overlap']

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--preview-only',action='store_true')
    parser.add_argument('--checks-only',action='store_true')
    args=parser.parse_args();OUT.mkdir(parents=True,exist_ok=True);before=hashes()
    if args.checks_only:
        old=json.loads((OUT/'preview-manifest.json').read_text())
        parts,pictures=old['printable_parts'],old['previews']
        assert old['source_sha256']==before,'Preview identity must be current'
    else:parts,pictures=artifacts()
    dimensions=dimension_report()
    if args.preview_only:
        (OUT/'preview-manifest.json').write_text(json.dumps({'source_sha256':before,
            'printable_parts':parts,'previews':pictures,'dimensions':dimensions,
            'status':'PREVIEW_ONLY_CHECKS_PENDING'},ensure_ascii=False,indent=2)+'\n')
        print('PREVIEW_READY',OUT);return 0
    jobs=[]
    for i,t in enumerate([0,.2,.4,.5,.6,.8,1]):
        jobs.append((f'motion-{i}',{'cg_t':t},False))
        jobs.append((f'cam-followers-{i}',{'cg_t':t,'cg_probe':'cam_followers'},False))
    for s in [0,.9,1]:
        for kind in ['gib_fit','hardware']:
            jobs.append((f'{kind}-{s}',{'cg_setting':s,'cg_probe':kind},False))
    for t in [0,1]:
        for kind in ['tools','old_tools']:
            jobs.append((f'{kind}-{t}',{'cg_t':t,'cg_probe':kind},False))
    for kind in ['gib_remove','cover_remove','lift_frame']:
        for d in [0,.1,1,5,15,40 if kind!='lift_frame' else 65]:
            jobs.append((f'{kind}-{d}',{'cg_probe':kind,'cg_remove':d},False))
    for kind in ['old_hardware','mount_nut_insert','jack_nut_insert','old_nut_insert']:
        jobs.append((kind,{'cg_probe':kind},False))
    for dx in [0,.1]:
        jobs.append((f'bearing-continuous-sweep-{dx}',{'cg_probe':'sweep','cg_fault_x':dx},False))
    for dz in [-.2,.2]:
        for t in [0,1]:
            jobs.append((f'axial-float-endpoint-{dz}-{t}',{'cg_gib_dz':dz,'cg_t':t},False))
        for dx in [0,.1]:
            jobs.append((f'axial-float-continuous-sweep-{dz}-{dx}',
                {'cg_probe':'sweep','cg_gib_dz':dz,'cg_fault_x':dx},False))
        for s in [0,.9,1]:
            jobs.append((f'axial-float-pocket-{dz}-{s}',
                {'cg_probe':'gib_fit','cg_gib_dz':dz,'cg_setting':s},False))
        jobs.append((f'axial-float-hardware-{dz}',{'cg_probe':'hardware','cg_gib_dz':dz},False))
        jobs.append((f'legacy-full-length-endpoint-control-{dz}',
            {'cg_probe':'legacy_gib_endpoint','cg_gib_dz':dz,'cg_t':0 if dz>0 else 1},True))
        jobs.append((f'axial-ear-overtravel-control-{dz}',
            {'cg_probe':'gib_fit','cg_gib_dz':dz*1.1},True))
    for name,defs in [
        ('advance-stop-control',{'cg_probe':'advance_stop'}),
        ('retract-stop-control',{'cg_probe':'retract_stop'}),
        ('old-inward-frame-control',{'cg_probe':'sweep','cg_fault_x':-.199}),
        ('old-outward-frame-control',{'cg_probe':'sweep','cg_fault_x':.199}),
        ('wrong-nut-install-order-control',{'cg_probe':'bad_nut_sequence'})]:
        jobs.append((name,defs,True))
    witness_report=ROOT/'output/guide-revision/tolerance/report.json'
    wr=json.loads(witness_report.read_text());witness_identity={}
    for p,digest in wr['source_sha256'].items():
        actual=hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
        assert actual==digest,f'Stale old witness dependency: {p}'
    for witness in wr['csg_witnesses']:
        path=ROOT/witness['source']['path']
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest==witness['source']['sha256'],'Old witness source changed'
        matrix=json.loads(re.search(r'module moving_frame\(\)\{multmatrix\((\[.*?\])\) feeder_carriage',path.read_text()).group(1))
        witness_identity[witness['name']]={'source':str(path.relative_to(ROOT)),
            'sha256':digest,'matrix':matrix,'stroke_mm':witness['stroke_mm'],
            'baseline_pose_csg_verified':witness['pose_csg_verified']}
        jobs.append((f"old-exact-{witness['name']}-frame-control",
            {'cg_probe':'old_witness','cg_witness_matrix':matrix,'cg_t':witness['stroke_mm']/dimensions['stroke']},True))
    with concurrent.futures.ThreadPoolExecutor(max_workers=3)as pool:
        cases=list(pool.map(probe,jobs))
    for case in cases:classify_known_limit_planes(case,dimensions)
    connections=[probe((kind,{'cg_probe':kind},True))for kind in ['datum_embed','case_embed']]
    stop_bearings=[]
    for t in [0,1]:
        for dx in [0,.1]:
            b=probe((f'fixed-datum-bearing-{t}-{dx}',
                {'cg_probe':'fixed_stop_bearing','cg_t':t,'cg_fault_x':dx},True))
            b['fixed_contact_area_lower_bound_mm2']=sum(c['volume_mm3']for c in b.get('components',[]))/.01
            b['passed']=b['passed']and b['fixed_contact_area_lower_bound_mm2']>=2.7-1e-6
            stop_bearings.append(b)
    stable=before==hashes()
    passed=stable and all(c['passed']for c in cases+connections+stop_bearings)and all(p.get('mesh_passed',False)for p in parts)and all(p.get('path')for p in pictures)
    report={'status':'NOMINAL_GEOMETRY_PASS_PHYSICAL_AND_TOTAL_ERROR_OPEN'if passed else'FAIL_OR_STALE',
        'source_sha256':before,'sources_stable':stable,'printable_parts':parts,'previews':pictures,
        'dimensions':dimensions,'case_count':len(cases),'pass_count':sum(c['passed']for c in cases),
        'old_exact_witnesses':witness_identity,
        'cases':cases,'load_path_connections':connections,'fixed_stop_bearings':stop_bearings,
        'hardware_added':{'M3x16_socket_head_screw':4,'M3_hex_nut_AF5.5_H2.4':6,'M3_washer_OD7_H0.5':4},
        'limits':['Only the right rail is the X master; nominal parallel motion is [0,+0.10], not +/-0.05 mm.',
            'The continuous bearing sweep covers exact rail/end-stop primitives; full cam/finger motion uses seven samples.',
            'Existing carrier gibs and split-body candidates are included. Eight body seam M3 sets and body-mount captive nuts remain unmodelled.',
            'Pure +/-0.199 translation controls and two exact saved tilted-frame witnesses are excluded by new contact solids; this is not a global bound.',
            'Rotation about X from the unmodified Y guide clearance remains; no global 3D gate-error budget has passed.',
            'Moving gib ends recess .4 mm; unchanged ear pocket permits +/- .2 mm axial translation, leaving .2 mm minimum end gap in this parallel model.',
            'Two jack screws are represented by one parallel setting; differential adjustment/tilt is not certified.',
            'New nuts must be inserted before the gib/cover. Thread form, torque, friction, PETG creep and screw pressure remain physical gates.',
            'Removal cases are static samples. The two new nut feeds and the old cap-nut feed use continuous convex sweeps.',
            'Printing orientations, support removability and loaded function are not established by these STL/CSG checks.']}
    (OUT/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    (OUT/'preview-manifest.json').write_text(json.dumps({
        k:report[k]for k in ['status','source_sha256','printable_parts','previews','dimensions']
    },ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:report[k]for k in ['status','case_count','pass_count','sources_stable']},indent=2))
    for c in cases+connections+stop_bearings:
        if not c['passed']:print('FAIL',c['name'],c.get('error')or c.get('components'))
    return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
