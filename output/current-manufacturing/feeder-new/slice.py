#!/usr/bin/env python3
"""Slice only the 13 explicitly unresolved current instances, into isolated output."""
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
import hashlib
import collections

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
spec=importlib.util.spec_from_file_location('legacy_slice_plan',ROOT/'scripts/review_final_feeder_slice.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)

def main():
    reuse_path=ROOT/'output/current-manufacturing/feeder-reuse/report.json'
    export_path=ROOT/'output/cable-scene-export/20260927T091627124663Z/report.json'
    invpath=ROOT/'docs/cable-assembly-inventory.json'
    reuse=json.loads(reuse_path.read_text());ex=json.loads(export_path.read_text())
    assert ex['status']=='CURRENT_SCENE_EXPORT_PASS' and ex['inventory_sha256']==sha(invpath)
    wanted={r['instance_id']for r in reuse['mapping']if r['needs_reslice']}
    assert len(wanted)==13
    rows=[dict(r,id=r['id'].removeprefix('feeder/'),instance_id=r['id'])for r in ex['parts']if r['id']in wanted]
    groups=collections.defaultdict(list)
    for r in rows:
        assert sha(ROOT/r['file'])==r['sha256'];groups[r['family']].append(r)
    assert set(groups)==base.CHANGED_FAMILIES
    before={**ex['source_sha256'],str(Path(__file__).relative_to(ROOT)):sha(__file__),
        'scripts/review_final_feeder_slice.py':sha(ROOT/'scripts/review_final_feeder_slice.py')}
    assert all(sha(ROOT/p)==h for p,h in before.items())
    run=OUT/'runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');run.mkdir(parents=True)
    base.OUT=run
    snapshot={'parts':rows,'groups':dict(groups),'source_sha256':before,
        'shared_profile_sha256':{n:sha(base.CONFIG/(n+'.json'))for n in ['machine','process','filament']},
        'printed_instances':len(rows),'unique_geometry_families':len(groups),
        'current_export_report':str(export_path.relative_to(ROOT)),'current_export_report_sha256':sha(export_path),
        'inventory_sha256':sha(invpath),'reuse_report_sha256':sha(reuse_path),
        'scope':'13 actual unresolved current instances; old folders and shared profiles are read-only.'}
    dump(run/'input-snapshot.json',snapshot)
    dump(OUT/'latest.json',{'run':str(run.relative_to(ROOT)),'status':'SLICING'})
    def job(f):return base.slice_family(f,snapshot)
    with ThreadPoolExecutor(max_workers=2)as pool:folders=list(pool.map(job,list(groups)))
    invocations=[json.loads((f/'invocation.json').read_text())for f in folders]
    okay=all(i['return_code']==0 and i.get('native_result',{}).get('return_code')==0 and i['input_and_cad_stable']for i in invocations)
    report={'status':'NATIVE_SLICES_GENERATED_REVIEW_REQUIRED'if okay else'NATIVE_SLICE_FAILURE_RECORDED',
        'run':str(run.relative_to(ROOT)),'folders':[str(f.relative_to(ROOT))for f in folders],
        'instances':13,'plates':8,'snapshot_sha256':sha(run/'input-snapshot.json'),
        'source_stable':all(sha(ROOT/p)==h for p,h in before.items()),
        'warnings':{i['family']:[p.get('warning_message','')for p in i.get('native_result',{}).get('sliced_plates',[])]for i in invocations},
        'manufacturing_release':False,'sent_to_printer':False}
    dump(run/'slice-report.json',report);dump(OUT/'latest.json',report);print(json.dumps(report,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
