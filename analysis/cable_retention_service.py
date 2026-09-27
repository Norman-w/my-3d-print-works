#!/usr/bin/env python3
"""Review a removable route guide as an added obstacle to service envelopes."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import ast
import hashlib
import json
import re
import subprocess
from feeder_integration import classify

ROOT=Path(__file__).resolve().parents[1]
SERVICE=ROOT/'cad/cable-service-review.scad'
RETAINER=ROOT/'cad/cable-route-retention.scad'
EXE='/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'

def hashes():
    paths={Path(__file__).resolve(),ROOT/'analysis/feeder_integration.py'}
    todo=[SERVICE,RETAINER]
    while todo:
        p=todo.pop().resolve()
        if p in paths:continue
        paths.add(p)
        todo.extend(p.parent/name for name in re.findall(r'\b(?:use|include)\s*<([^>]+)>',p.read_text()))
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}

def run(out,name,source,defs,extension='stl'):
    target=out/(name+'.'+extension)
    cmd=[EXE,'--hardwarnings','--backend','Manifold']
    if extension=='stl':cmd+=['--export-format','asciistl']
    for key,value in defs.items():cmd+=['-D',key+'='+json.dumps(value)]
    cmd+=['-o',str(target),str(source)]
    r=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
    log=r.stdout+r.stderr;(out/(name+'.log')).write_text(log)
    empty='Current top level object is empty' in log and not target.exists()
    ok=not ('ERROR:' in log or 'WARNING:' in log) and (r.returncode==0 or empty) and (target.exists() or empty)
    return {'name':name,'command':cmd,'returncode':r.returncode,'execution_ok':ok,
            'empty':empty,'file':str(target.relative_to(ROOT)) if target.exists() else None}

def main():
    out=ROOT/'output/cable-retention-service'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out.mkdir(parents=True)
    before=hashes()
    contract_result=run(out,'contract',SERVICE,{'csr_part':'contract'},'echo')
    if not contract_result['execution_ok'] or not contract_result['file']:
        raise RuntimeError('Missing service contract; see '+str(out))
    raw=(ROOT/contract_result['file']).read_text()
    value=next(x for x in raw.splitlines() if x.startswith('ECHO: "CSR_CONTRACT", ')).split('ECHO: "CSR_CONTRACT", ',1)[1]
    for a,b in [('undef','None'),('true','True'),('false','False')]:value=re.sub(r'\b'+a+r'\b',b,value)
    contract=dict(ast.literal_eval(value))
    wrapper=out/'probe.scad'
    wrapper.write_text(f'use <{SERVICE}>\nuse <{RETAINER}>\nkind="input-mount-tools";fault=false;\n'
        'intersection(){crr_all();union(){csr_service_envelope(kind);if(fault)crr_base();}}\n')
    def check(job):
        kind,fault=job;name=kind+('-positive-control' if fault else '')
        row=run(out,name,wrapper,{'kind':kind,'fault':fault})
        info=classify(ROOT/row['file']) if row['file'] else {'components':[],'has_solid_or_unclassified_overlap':False}
        row.update(classification=info,expected_overlap=fault,
                   passed=row['execution_ok'] and info['has_solid_or_unclassified_overlap']==fault)
        print(name,row['passed'],flush=True);return row
    jobs=[(k,False) for k in contract['kinds']]+[(contract['kinds'][0],True)]
    with ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(check,jobs))
    stable=before==hashes();passed=stable and all(row['passed'] for row in rows)
    report={'status':'RETAINER_SERVICE_ENVELOPES_PASS' if passed else 'FAIL_OR_STALE',
        'sources_stable':stable,'source_sha256':before,'service_contract':contract,'results':rows,
        'scope':'New guide printed parts and hardware against declared existing service envelopes. '
                'Continuous/sampled limits and cable disconnection prerequisites are inherited from service contract.',
        'unverified':['new guide own installation and service (separate review)',
            'tool choice/hand clearance/torque','arbitrary free cable deformation','load and print strength'],
        'manufacturing_release':False,'physical_acceptance':False}
    p=out/'report.json';p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(report['status'],p,flush=True);return 0 if passed else 1
if __name__=='__main__':raise SystemExit(main())
