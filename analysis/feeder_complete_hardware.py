#!/usr/bin/env python3
"""Add the previously omitted seam fasteners and mounting nuts to nominal checks."""
from pathlib import Path
import concurrent.futures
import hashlib
import json
import re
import subprocess
from feeder_integration import classify

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/complete-hardware'
CAD=ROOT/'cad/feeder-complete-hardware.scad'
EXE='/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'

def sources():
    paths={Path(__file__).resolve(),ROOT/'analysis/feeder_integration.py'}
    pending=[CAD]
    while pending:
        p=pending.pop().resolve()
        if p in paths:continue
        paths.add(p)
        for dep in re.findall(r'\b(?:use|include)\s*<([^>]+)>',p.read_text()):pending.append(p.parent/dep)
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths}

def contract():
    text=(ROOT/'cad/feeder-body.scad').read_text()
    expected={'body_split_boss_x':'7','body_split_boss_y':'40',
        'body_split_bolt_z':'[-72,-46,-10,16]','body_side_mount_x':'35.5',
        'body_side_mount_y':'-14','body_side_mount_z':'[-45,16]'}
    for key,value in expected.items():
        m=re.search(r'^'+key+r'\s*=\s*([^;]+)',text,re.M)
        assert m and re.sub(r'\s+','',m.group(1))==value,(key,'Hardware placement contract changed')
    return expected

def probe(job):
    name,defs,want=job;path=OUT/(name+'.stl');path.unlink(missing_ok=True)
    cmd=[EXE,'--hardwarnings','--backend','Manifold','--export-format','asciistl']
    for key,value in defs.items():cmd+=['-D',f'{key}={json.dumps(value)}']
    cmd+=['-o',str(path),str(CAD)]
    p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
    log=p.stdout+p.stderr;(OUT/(name+'.log')).write_text(log)
    if 'WARNING:'in log or 'ERROR:'in log:raise RuntimeError(log)
    if path.exists():r=classify(path)
    elif 'Current top level object is empty'in log:r={'components':[],'has_solid_or_unclassified_overlap':False}
    else:raise RuntimeError(log)
    return {'name':name,'definitions':defs,'expected_solid_overlap':want,
        'passed':r['has_solid_or_unclassified_overlap']==want,**r}

def main():
    OUT.mkdir(parents=True,exist_ok=True);before=sources();c=contract()
    jobs=[(f'fit-{t}',{'fh_part':'fit','fh_t':t},False)for t in [0,.2,.4,.5,.6,.8,1]]
    jobs += [(name,{'fh_part':name},False)for name in ['hardware-fit','mount-feed','seam-feed']]
    jobs += [('seam-tools-before-frame',{'fh_part':'seam-tools','fh_frame_installed':False},False),
             ('seam-tools-midstroke',{'fh_part':'seam-tools','fh_t':.5},False),
             ('seam-tools-frame-rest-obstruction',{'fh_part':'seam-tools','fh_t':0},True)]
    jobs += [('wrong-mount-sequence',{'fh_part':'wrong-mount-sequence'},True),
             ('misalignment-control',{'fh_part':'fit','fh_fault':.6},True)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3)as pool:cases=list(pool.map(probe,jobs))
    stable=before==sources();ok=stable and all(r['passed']for r in cases)
    result={'status':'NOMINAL_COMPLETE_FASTENER_CHECK_PASS'if ok else'FAIL_OR_STALE',
        'source_sha256':before,'sources_stable':stable,'placement_contract':c,'cases':cases,
        'modeled_additions':{'M3x12_seam_bolts':8,'M3_seam_nuts':8,'M3_body_mount_nuts':4},
        'limits':['Nominal envelopes without thread/socket geometry or actual purchased tolerances.',
            'Mount nuts enter before supports. Seam screws are fitted before the frame; the rest-state frame obstructs straight seam tools. Midstroke is a checked pose, not an automatically retained service state.',
            'This check does not include the new harness/outlet until integrated.',
            'Assembly sequence, torque, printed fit and physical function remain unverified.']}
    (OUT/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(result['status'],len(cases),'checks')
    for r in cases:
        if not r['passed']:print('FAIL',r['name'],r['components'])
    return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
