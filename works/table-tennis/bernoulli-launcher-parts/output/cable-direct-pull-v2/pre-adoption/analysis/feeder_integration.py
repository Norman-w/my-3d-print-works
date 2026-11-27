#!/usr/bin/env python3
"""Check actual feeder-body/support CSG, preserving zero-thickness contacts.

Finite nominal poses and removal samples only; no dynamics, tolerance or strength
proof. Exact coplanar mounting contacts are recorded, not called solid overlap.
"""
from pathlib import Path
import hashlib
import json
import math
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/analysis'
SCAD = '/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
SOURCES = ['parameters.scad','cam-study.scad','feeder-supports.scad',
           'feeder-body.scad','feeder-assembly.scad']


def hashes():
    return {f'cad/{p}': hashlib.sha256((ROOT/'cad'/p).read_bytes()).hexdigest()
            for p in SOURCES}


def subtract(a,b): return tuple(x-y for x,y in zip(a,b))
def dot(a,b): return sum(x*y for x,y in zip(a,b))
def cross(a,b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def classify(path):
    vertices = [tuple(map(float,m.groups())) for m in re.finditer(
        r'^\s*vertex\s+([-+\deE.]+)\s+([-+\deE.]+)\s+([-+\deE.]+)',
        path.read_text(), re.M)]
    if len(vertices)%3: raise ValueError('Malformed ASCII STL')
    triangles = [vertices[i:i+3] for i in range(0,len(vertices),3)]
    keys = [tuple(round(x,7) for x in v) for v in vertices]
    parents = list(range(len(triangles)))
    def find(x):
        while parents[x]!=x:
            parents[x] = parents[parents[x]]
            x = parents[x]
        return x
    owners = {}
    for i in range(len(triangles)):
        for k in keys[i*3:i*3+3]:
            if k in owners: parents[find(i)] = find(owners[k])
            else: owners[k] = i
    groups = {}
    for i,t in enumerate(triangles): groups.setdefault(find(i),[]).append(t)
    results = []
    for group in groups.values():
        points = [v for t in group for v in t]
        volume = abs(sum(dot(a,cross(b,c))/6 for a,b,c in group))
        normals = [cross(subtract(b,a),subtract(c,a)) for a,b,c in group]
        n = max(normals,key=lambda v:dot(v,v))
        length = math.sqrt(dot(n,n))
        planar_error = max(abs(dot(n,subtract(p,points[0])))/length for p in points) if length else 0
        planar = planar_error < 1e-6 and volume < 1e-5
        results.append({'triangles':len(group),'volume_mm3':volume,
                        'planar_error_mm':planar_error,'planar_contact_only':planar,
                        'bounds':[[min(p[a] for p in points),max(p[a] for p in points)] for a in range(3)]})
    return {'triangle_count':len(triangles),'components':results,
            'has_solid_or_unclassified_overlap':any(not x['planar_contact_only'] for x in results)}


def probe(name,definitions):
    path = OUT/f'feeder-integrated-{name}.stl'
    path.unlink(missing_ok=True)
    cmd = [SCAD,'--hardwarnings','--backend','Manifold','--export-format','asciistl']
    for key,value in definitions.items(): cmd += ['-D',f'{key}={json.dumps(value)}']
    cmd += ['-o',str(path),str(ROOT/'cad/feeder-assembly.scad')]
    result = subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
    log = result.stdout+result.stderr
    (OUT/f'feeder-integrated-{name}.log').write_text(log)
    if 'WARNING:' in log or 'ERROR:' in log: raise RuntimeError(log)
    if path.exists(): classified = classify(path)
    elif 'Current top level object is empty' in log:
        classified = {'triangle_count':0,'components':[], 'has_solid_or_unclassified_overlap':False}
    else: raise RuntimeError(f'Unclassified OpenSCAD failure: {log}')
    return {'name':name,'definitions':definitions,'returncode':result.returncode,**classified}


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    before = hashes()
    poses = [0,.2,.4,.5,.6,.8,1]
    rows = [probe(f'motion-{i}',{'assembly_part':'body_interference','assembly_stroke':t})
            for i,t in enumerate(poses)]
    # Removing pins/caps first is a prerequisite; finger extraction and frame
    # lifting are sampled against body only. Support-own probes run separately.
    for i,t in enumerate([0,.1,.25,.5,.75,1]):
        rows.append(probe(f'removal-{i}',{'assembly_part':'removal_probe','assembly_removal':t}))
    fault = probe('fault-positive',{'assembly_part':'body_interference','assembly_body_fault':1})
    stable = before == hashes()
    passed = stable and not any(r['has_solid_or_unclassified_overlap'] for r in rows) and fault['has_solid_or_unclassified_overlap']
    report = {'status':'NOMINAL_SAMPLED_CSG_PASS' if passed else 'FAIL_OR_STALE',
              'source_sha256':before,'sources_stable_during_check':stable,
              'nominal_samples':rows,'positive_control':fault,
              'limits':['Finite nominal poses; unsampled positions are not proven.',
                        'Planar mounting contacts are explicitly separated from solid overlaps.',
                        'Manufacturing clearances, guide error budget, seals, strength and physical function remain OPEN.',
                        'The source-sized whole body is used; interface fit is still unmeasured.'],
              'physical_acceptance':'OPEN'}
    target = OUT/'feeder-integration.json'
    target.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(report['status'],target)
    for row in rows:
        if row['has_solid_or_unclassified_overlap']: print('OVERLAP',row['name'],row['components'])
    return 0 if passed else 1


if __name__=='__main__': sys.exit(main())
