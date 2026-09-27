#!/usr/bin/env python3
"""One bounded orientation alternative, unchanged current STL, local profiles only."""
from pathlib import Path
from datetime import datetime,timezone
import importlib.util,json,hashlib
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
S=ROOT/'output/current-manufacturing/feeder-new/runs/20260927T094300899015Z/inlet-rear-anchor-z-down-supported'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def main():
 spec=importlib.util.spec_from_file_location('slice_base',ROOT/'scripts/review_final_feeder_slice.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
 inv=json.loads((S/'invocation.json').read_text());run=OUT/'alternative'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');run.mkdir(parents=True)
 base.OUT=run
 base.PLAN['inlet-rear']=(['--rotate-x','-90'],True,'split-face-down','Original Y=-1.2 split face down; growth -CAD Y; all fastener hole axes vertical; unchanged STL.')
 snapshot={'groups':{'inlet-rear':inv['inputs']},'source_sha256':{**inv['source_sha256_at_start'],str(Path(__file__).relative_to(ROOT)):sha(__file__)},'shared_profile_sha256':inv['shared_profile_sha256']}
 assert all(sha(ROOT/p)==h for p,h in snapshot['source_sha256'].items())
 dump(run/'input-snapshot.json',snapshot)
 folder=base.slice_family('inlet-rear',snapshot)
 dump(OUT/'alternative-latest.json',{'folder':str(folder.relative_to(ROOT)),'source_stl_unchanged':inv['inputs'][0]['sha256'],'status':'NATIVE_GENERATED_REVIEW_REQUIRED'})
 print(folder,flush=True)
if __name__=='__main__':main()
