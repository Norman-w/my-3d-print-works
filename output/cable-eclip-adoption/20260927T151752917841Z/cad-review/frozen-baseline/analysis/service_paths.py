#!/usr/bin/env python3
"""Check complete straight nut-sweep CSG and explicit obstruction controls."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
from feeder_integration import classify

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/analysis/service-paths'
SCAD = '/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
SOURCES = ['cad/parameters.scad','cad/cam-study.scad','cad/feeder-supports.scad',
           'cad/spin-head.scad','cad/spin-parameters.scad','cad/assembly-service-checks.scad',
           'analysis/service_paths.py','analysis/feeder_integration.py']

def hashes():
    return {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in SOURCES}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    before=hashes()
    rows=[]
    for case,expect_overlap in [('feeder_nut',False),('feeder_nut_old_rib',True),
                                ('spin_nut_first',False),('spin_nut_wrong_order',True)]:
        path=OUT/f'{case}.stl'
        path.unlink(missing_ok=True)
        command=[SCAD,'--hardwarnings','--backend','Manifold','--export-format','asciistl',
                 '-D',f'service_case="{case}"','-o',str(path),str(ROOT/'cad/assembly-service-checks.scad')]
        result=subprocess.run(command,cwd=ROOT,text=True,capture_output=True)
        log=result.stdout+result.stderr
        (OUT/f'{case}.log').write_text(log)
        if 'WARNING:' in log or 'ERROR:' in log: raise RuntimeError(log)
        if path.exists(): info=classify(path)
        elif 'Current top level object is empty' in log:
            info={'has_solid_or_unclassified_overlap':False,'triangle_count':0,'components':[]}
        else: raise RuntimeError(log)
        rows.append({'case':case,'expected_solid_overlap':expect_overlap,
                     'passes':info['has_solid_or_unclassified_overlap']==expect_overlap,**info})
    stable=before==hashes()
    success=stable and all(r['passes'] for r in rows)
    report={'status':'NOMINAL_NUT_SWEEPS_AND_CONTROLS_PASS' if success else 'FAIL_OR_STALE',
            'source_sha256':before,'sources_stable':stable,'cases':rows,
            'scope':'Convex envelopes enclose continuous straight translation of stated nominal nuts. Correct sequence must be used.',
            'limits':['No printed deviation, nut finish, friction, hand/tool access or force proof.',
                      'No full mechanism tolerance or physical-assembly acceptance.'],
            'physical_acceptance':'OPEN'}
    (OUT.parent/'service-paths.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(report['status'])
    for row in rows: print(row['case'],row['passes'])
    return 0 if success else 1

if __name__=='__main__': sys.exit(main())
