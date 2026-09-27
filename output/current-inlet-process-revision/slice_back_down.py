#!/usr/bin/env python3
"""Third process hypothesis: rear-key ends down, all fastening axes vertical.
Same STL and original .2 mm profiles; opposite growth to the prior split-face
orientation. No CAD, shared profile or printer action.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, importlib.util, json

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
OLD=ROOT/'output/current-manufacturing/feeder-new/runs/20260927T094300899015Z/inlet-rear-anchor-z-down-supported'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
dump=lambda p,d:Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')


def main():
    spec=importlib.util.spec_from_file_location('base',ROOT/'scripts/review_final_feeder_slice.py')
    base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
    old=json.loads((OLD/'invocation.json').read_text())
    source=ROOT/old['inputs'][0]['file'];assert sha(source)=='146bcf746c8f1a52825c68675ad1844d8ed4de079c75c3885504240121e3069a'
    run=OUT/'runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');run.mkdir(parents=True)
    base.OUT=run
    base.PLAN['inlet-rear']=(['--rotate-x','90'],True,'rear-key-ends-down','CAD Y=-53.8 rear-key ends face bed; growth +CAD Y. M2.5 bores/strap slots vertical; unchanged solid and original .2 mm profile.')
    snapshot={'groups':{'inlet-rear':old['inputs']},'source_sha256':{**old['source_sha256_at_start'],str(Path(__file__).relative_to(ROOT)):sha(__file__)},'shared_profile_sha256':old['shared_profile_sha256']}
    assert all(sha(ROOT/p)==h for p,h in snapshot['source_sha256'].items())
    assert all(sha(base.CONFIG/(n+'.json'))==h for n,h in snapshot['shared_profile_sha256'].items())
    dump(run/'input-snapshot.json',snapshot)
    print(str(run),flush=True)
    folder=base.slice_family('inlet-rear',snapshot)
    inv=json.loads((folder/'invocation.json').read_text())
    status='NATIVE_ORIENTATION_CANDIDATE_REVIEW_REQUIRED' if inv['return_code']==inv.get('native_result',{}).get('return_code')==0 else 'NATIVE_SLICE_FAILED'
    dump(OUT/'back-down-latest.json',dict(folder=str(folder.relative_to(ROOT)),status=status,mechanical_geometry_changed=False))
    print(json.dumps(dict(folder=str(folder.relative_to(ROOT)),status=status),ensure_ascii=False),flush=True)


if __name__=='__main__':main()
