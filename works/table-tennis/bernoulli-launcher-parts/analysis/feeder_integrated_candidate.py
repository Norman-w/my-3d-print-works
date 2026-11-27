#!/usr/bin/env python3
"""Current combined host + interfaces; no physical or total-tolerance approval."""
from pathlib import Path
import concurrent.futures
import hashlib
import importlib.util
import json
import re
import subprocess
from feeder_integration import classify

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/feeder-integrated-candidate'
CAD=ROOT/'cad/feeder-integrated-candidate.scad'
EXE='/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
def sources():
    paths={Path(__file__).resolve(),ROOT/'analysis/feeder_integration.py'};pending=[CAD]
    while pending:
        p=pending.pop().resolve()
        if p in paths:continue
        paths.add(p)
        for dep in re.findall(r'\b(?:use|include)\s*<([^>]+)>',p.read_text()):pending.append(p.parent/dep)
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths}
def run(name,defs,suffix='.stl',extra=()):
    target=OUT/(name+suffix);target.unlink(missing_ok=True)
    cmd=[EXE,'--hardwarnings','--backend','Manifold']
    if suffix=='.stl':cmd+=['--export-format','asciistl']
    for k,v in defs.items():cmd+=['-D',f'{k}={json.dumps(v)}']
    cmd+=list(extra)+['-o',str(target),str(CAD)]
    r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True);log=r.stdout+r.stderr
    (OUT/(name+'.log')).write_text(log)
    if 'WARNING:'in log or 'ERROR:'in log:raise RuntimeError(log)
    empty='Current top level object is empty'in log
    # OpenSCAD returns 1 for an explicitly empty STL intersection. No other
    # nonzero exit or missing output can become a successful collision test.
    if r.returncode and not(suffix=='.stl'and empty and not target.exists()):
        raise RuntimeError(f'{name}: OpenSCAD exit {r.returncode}\n{log}')
    if not target.exists()and not(suffix=='.stl'and empty):raise RuntimeError(log)
    if target.exists()and target.stat().st_size==0:raise RuntimeError(f'{name}: zero-byte output')
    return target
def probe(job):
    name,defs,expected=job
    # frame-sweep.stl is an input imported by CAD. A diagnostic with that same
    # name used to unlink its own input before OpenSCAD could read it.
    output_name='frame-sweep-overlap'if name=='frame-sweep'else name
    p=run(output_name,{'ic_part':'probe',**defs})
    info=classify(p)if p.exists()else{'components':[],'has_solid_or_unclassified_overlap':False}
    return {'name':name,'output_path':str(p.relative_to(ROOT)),'definitions':defs,'expected_overlap':expected,
        'passed':info['has_solid_or_unclassified_overlap']==expected,**info}
def frame_sweep():
    # For a translational sweep of a closed polyhedron, its starting solid plus
    # the segment sweep of every boundary triangle covers exactly the swept set.
    # Unlike a hull around the entire frame, this preserves its large concavities.
    start=run('frame-start',{'ic_part':'frame-start'})
    vertices=[list(map(float,m.groups()))for m in re.finditer(
        r'^\s*vertex\s+([-+\deE.]+)\s+([-+\deE.]+)\s+([-+\deE.]+)',start.read_text(),re.M)]
    if not vertices or len(vertices)%3:raise RuntimeError('Frame export is not a nonempty ASCII triangle mesh')
    stroke=float(re.search(r'^cam_stroke\s*=\s*([^;]+)',(ROOT/'cad/parameters.scad').read_text(),re.M).group(1))
    code=['// Exact linear sweep of the exported frame, mm. Generated, not a print part.',
          'union(){import("frame-start.stl");'];count=0
    for i in range(0,len(vertices),3):
        a,b,c=vertices[i:i+3]
        nz=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
        if abs(nz)<1e-10:continue
        if nz<0:b,c=c,b
        points=[a,b,c]+[[v[0],v[1],v[2]+stroke]for v in [a,b,c]]
        code.append('polyhedron(points='+json.dumps(points)+',faces=[[2,1,0],[3,4,5],[0,1,4,3],[1,2,5,4],[2,0,3,5]]);')
        count+=1
    code.append('}')
    source=OUT/'frame-sweep.scad';source.write_text('\n'.join(code)+'\n');target=OUT/'frame-sweep.stl'
    target.unlink(missing_ok=True)
    p=subprocess.run([EXE,'--hardwarnings','--backend','Manifold','--export-format','asciistl','-o',str(target),str(source)],cwd=ROOT,capture_output=True,text=True)
    log=p.stdout+p.stderr;(OUT/'frame-sweep-build.log').write_text(log)
    if p.returncode or 'WARNING:'in log or 'ERROR:'in log:raise RuntimeError(log)
    if not target.is_file()or not target.stat().st_size:raise RuntimeError('Continuous frame sweep was not exported')
    return {'method':'initial solid union every nonparallel boundary triangle swept by the 20mm translation segment',
        'stroke_mm':stroke,'triangular_prisms':count,'frame_sha256':hashlib.sha256(start.read_bytes()).hexdigest(),
        'sweep_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'scope':'Exact for this exported polyhedral frame and pure translation; not deformation or fingers.'}
def main():
    OUT.mkdir(parents=True,exist_ok=True);before=sources()
    sweep=frame_sweep()
    cases=[(f'motion-{t}',{'ic_probe':'motion','ic_t':t},False)for t in [0,.2,.4,.5,.6,.8,1]]
    cases +=[(kind,{'ic_probe':kind},False)for kind in [
        'frame-sweep','new-vs-fixed','new-vs-old-hardware','harness-vs-outlet',
        'extra-hardware-fit','seam-tools-before-frame','seam-nut-feed','mount-nut-feed',
        'finger-path','old-tools-vs-new','new-tools-vs-other','band-workspace',
        'frame-lift','body-corridor']]
    cases += [('body-root',{'ic_probe':'body-root'},True),
              ('wrong-disassembly-order',{'ic_probe':'body-half-remove'},True),
              ('seam-tools-harness-obstruction',{'ic_probe':'seam-tools-harness-obstruction'},True),
              ('outlet-tools-harness-obstruction',{'ic_probe':'outlet-tools-harness-obstruction'},True),
              ('harness-misplacement-control',{'ic_probe':'fault-control','ic_fault':35},True)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3)as pool:rows=list(pool.map(probe,cases))
    spec=importlib.util.spec_from_file_location('mesh','/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py')
    mesh=importlib.util.module_from_spec(spec);spec.loader.exec_module(mesh)
    parts=[]
    for name in ['positive-half','negative-half']:
        p=run(name,{'ic_part':name});m=mesh.inspect(p,1e-6);components=len(classify(p)['components'])
        parts.append({'name':name,'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
            'mesh':m,'components':components,'passed':m['watertightByEdgeTopology']and components==1})
    pictures=[]
    for name,cam in [('assembly','12,0,-5,64,0,28,710'),('front','12,-4,-5,90,0,0,670'),('top','0,0,-4,0,0,0,640')]:
        p=run(name,{'ic_part':'assembly'},'.png',['--render','--imgsize=1500,1250','--projection=o',f'--camera={cam}'])
        pictures.append({'file':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    sweep_path=OUT/'frame-sweep.stl'
    sweep_stable=sweep_path.is_file()and hashlib.sha256(sweep_path.read_bytes()).hexdigest()==sweep['sweep_sha256']
    stable=before==sources();passed=stable and sweep_stable and all(r['passed']for r in rows+parts)
    report={'status':'INTEGRATED_NOMINAL_CANDIDATE_PASS'if passed else'FAIL_OR_STALE','sources_stable':stable,
        'source_sha256':before,'frame_sweep':sweep,'frame_sweep_input_stable':sweep_stable,
        'cases':rows,'parts':parts,'pictures':pictures,'case_count':len(rows),
        'pass_count':sum(r['passed']for r in rows),'manufacturing_release':False,
        'limits':['One combined shell includes current seam locators, harness ears and outlet flange.',
            'Nominal motion only; total tolerance, actual clamp closure/contact force, airtightness and structural loads are not validated.',
            'Seam screw access requires frame/harness removal. Fit/tighten outlet tie rods before the harness. Split housing opens only after removing harness/outlet retainer.',
            'Actual blower, angled Y fitting and hose surface are not modeled; no whole launcher physical acceptance.']}
    (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(report['status'],report['pass_count'],'/',len(rows))
    for r in rows:
        if not r['passed']:print('FAIL',r['name'],r['components'])
    return 0 if passed else 1
if __name__=='__main__':raise SystemExit(main())
