#!/usr/bin/env python3
"""Nominal outlet packaging, captured-liner stops and mesh review; not release."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib
import json
import math
import re
import subprocess
from feeder_integration import classify

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/interface-study'
CAD=ROOT/'cad/interface-study.scad'
EXE='/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
INSPECT=Path('/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py')
SOURCES=['cad/parameters.scad','cad/feeder-body.scad',
         'cad/feeder-seam-candidate.scad','cad/interface-study.scad',
         'analysis/interface_study.py','analysis/feeder_integration.py']

def hashes():
    return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES}

def run(part,suffix='.stl',name=None,extra=()):
    path=OUT/((name or part)+suffix)
    path.unlink(missing_ok=True)
    cmd=[EXE,'--render','--hardwarnings','--backend','Manifold']
    if suffix=='.stl': cmd+=['--export-format','asciistl']
    cmd+=['-D',f'interface_part={json.dumps(part)}',*extra,'-o',str(path),str(CAD)]
    p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
    log=p.stdout+p.stderr
    (OUT/((name or part)+'.log')).write_text(log)
    if 'WARNING:' in log or 'ERROR:' in log: raise RuntimeError(log)
    if not path.exists() and 'Current top level object is empty' not in log:
        raise RuntimeError(log)
    return path,log

def probe(job):
    part,expected,d=job
    path,_=run(part)
    c=classify(path) if path.exists() else {
        'components':[],'triangle_count':0,'has_solid_or_unclassified_overlap':False}
    # Coincident faceted cylinder skins are not globally planar. Recognize ONLY
    # triangles lying exactly on one existing OD50 polygon face, not arbitrary
    # near-zero volumes. Keep a translated boot control to detect true overlap.
    if part=='boot-body-tube' and path.exists():
        vertices=[tuple(map(float,m.groups())) for m in re.finditer(
            r'^\s*vertex\s+([-+\deE.]+)\s+([-+\deE.]+)\s+([-+\deE.]+)',path.read_text(),re.M)]
        fn=d['polygon_fn']
        planes=[(math.cos((2*k+1)*math.pi/fn),math.sin((2*k+1)*math.pi/fn)) for k in range(fn)]
        apothem=d['tube_od']/2*math.cos(math.pi/fn)
        on_skin=bool(vertices) and all(
            all(d['boot_transition_end']-1e-6<=p[2]<=d['boot_end']+1e-6 for p in vertices[i:i+3]) and
            any(all(abs(nx*p[0]+ny*p[1]-apothem)<1e-6 for p in vertices[i:i+3]) for nx,ny in planes)
            for i in range(0,len(vertices),3))
        c['verified_tube_polygon_boundary_contact_only']=on_skin
        if on_skin: c['has_solid_or_unclassified_overlap']=False
    return {'name':part,'expected_overlap':expected,
            'passed':c['has_solid_or_unclassified_overlap']==expected,**c}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    before=hashes()
    echo,log=run('liner','.echo','dimensions')
    line=next(x for x in echo.read_text().splitlines() if x.startswith('ECHO: "interface_dims", '))
    d=dict(json.loads(line.split(', ',1)[1]))
    body=(ROOT/'cad/feeder-body.scad').read_text()
    # Do not silently inherit copied dimensions from a changed body.
    for key,value in [('body_spigot_bore',d['liner_id']),('body_outlet_stop',2)]:
        m=re.search(rf'^\s*{key}\s*=\s*([\d.]+)\s*;',body,re.M)
        assert m and float(m.group(1))==value, f'Changed source contract: {key}'
    jobs=[('liner-body',False),('liner-tube',False),('boot-body-tube',False),
          ('tube-assembly-sweep',False),('ballway',False),
          ('liner-upstream-stop',True),('liner-downstream-stop',True),
          ('boot-offset-control',True)]
    with ThreadPoolExecutor(max_workers=3) as pool:
        checks=list(pool.map(probe,[(part,expected,d) for part,expected in jobs]))
    meshes=[]
    for part in ['liner','boot-envelope']:
        path,_=run(part)
        p=subprocess.run(['python3',str(INSPECT),str(path),'--require-watertight','--json'],
                         text=True,capture_output=True)
        if p.returncode: raise RuntimeError(p.stdout+p.stderr)
        raw=json.loads(p.stdout)
        meshes.append({'part':part,'path':str(path.relative_to(ROOT)),
                       'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                       'inspection':raw,'component_count':len(classify(path)['components'])})
    renders=[]
    for name,part,camera in [
        ('section-isometric','section','-180,-180,120,0,0,82'),
        ('section-front','section','-180,0,82,0,0,82'),
        ('assembly-top','assembly','0,0,280,0,0,82')]:
        path,_=run(part,'.png',name,['--imgsize','1200,950','--camera',camera,
            '--projection','o','--viewall','--colorscheme','Tomorrow'])
        renders.append({'path':str(path.relative_to(ROOT)),
                        'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    stable=before==hashes()
    passed=stable and all(r['passed'] for r in checks) and all(m['component_count']==1 for m in meshes)
    report={'status':'NOMINAL_INTERFACE_PACKAGING_ONLY' if passed else 'FAIL_OR_STALE',
        'units':'mm','source_sha256':before,'sources_stable':stable,'dimensions':d,
        'calculated':{
            'effective_tube_engagement':d['socket_end']-d['tube_start'],
            'liner_nominal_wall':(d['liner_od']-d['liner_id'])/2,
            'liner_polygon_face_wall':(d['liner_od']-d['liner_id'])/2*math.cos(math.pi/d['polygon_fn']),
            'liner_after_band_reserve':d['liner_end']-d['band_z'][1]-d['band_width']/2,
            'liner_shoulder_capture_radial_overlap_with_tube':(d['shoulder_od']-d['tube_id'])/2},
        'checks':checks,'meshes':meshes,'renders':renders,
        'scope':'Nominal rigid geometry. Liner stops work only while the hard tube remains seated. Tube retention is NOT established. Boot is an uncompressed reference envelope, not selected elastomer geometry. 41.5 mm coaxial probe is not all eccentric ball trajectories.',
        'omitted':['clamp screw housings and tool access','elastomer installation deformation and squeeze','real tube material/tolerance','support bracket and anchor','thin liner/tube strength','air resistance and ball dynamics'],
        'manufacturing_release':False,'physical_acceptance':'OPEN'}
    (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(report['status'], f'{sum(r["passed"] for r in checks)}/{len(checks)} checks')
    return 0 if passed else 1

if __name__=='__main__': raise SystemExit(main())
