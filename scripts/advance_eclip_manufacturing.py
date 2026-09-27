#!/usr/bin/env python3
"""Bind the three re-sliced input instances after an explicit bounded review.

The review index records engineering decisions and named evidence, not physical
release. Keep the 53 unchanged instances and every historical artifact intact.
"""
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone
import argparse, copy, hashlib, json, zipfile

ROOT=Path(__file__).resolve().parents[1]
IDS={'feeder/cable-input-body','feeder/cable-input-lever','feeder/cable-input-cover'}
def path(p):
    p=Path(p);return p if p.is_absolute() else ROOT/p
def rel(p):return str(path(p).resolve().relative_to(ROOT))
def sha(p):return hashlib.sha256(path(p).read_bytes()).hexdigest()
def load(p):return json.loads(path(p).read_text())
def dump(p,v):path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--baseline-manifest',type=Path,required=True)
    ap.add_argument('--review-index',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();base=load(a.baseline_manifest);index=load(a.review_index)
    assert base['counts']['bound_instances']==53 and base['counts']['needs_reslice_instances']==3
    assert {r['instance_id'] for r in index['parts']}==IDS and len(index['parts'])==3
    assert not index['manufacturing_release'] and not index['physical_acceptance']
    out=path(a.output).resolve();out.mkdir(parents=True,exist_ok=False)
    evidence={}
    def bind(p,h=None):
        actual=sha(p)
        if h is not None:assert actual==h,('Stale evidence',p)
        key=rel(p)
        assert key not in evidence or evidence[key]==actual
        evidence[key]=actual
        return actual
    for p in [__file__,a.baseline_manifest,a.review_index]:bind(p)
    for p,h in base['evidence_sha256'].items():bind(p,h)
    reviewed={r['instance_id']:r for r in index['parts']}
    items=copy.deepcopy(base['items'])
    for item in items:
        if item['instance_id'] not in reviewed:continue
        decision=reviewed[item['instance_id']]
        assert decision['bounded_process_review_complete']
        assert decision['remaining_physical_limits']
        assert {'artifact','axis_features','support'}<=decision['reports'].keys()
        if item['instance_id'].endswith('-body'):
            assert {'body_clearances','stop_nut_contact'}<=decision['reports'].keys()
        f=path(decision['slice_folder']);iv=load(f/'invocation.json')
        assert iv['status']=='SLICE_GENERATED_REVIEW_REQUIRED'
        assert iv['input']['sha256']==item['current_stl_sha256']
        assert sha(iv['input']['file'])==item['current_stl_sha256']
        assert not iv['sent_to_printer']
        for name,reference in decision['reports'].items():
            bind(reference['file'],reference['sha256'])
            r=load(reference['file'])
            for p,h in r.get('evidence_sha256',{}).items():bind(p,h)
            if name=='artifact':assert r['status']=='CURRENT_ECLIP_SLICE_ARTIFACT_IDENTITY_PASS'
        for p,h in iv['source_sha256_at_start'].items():bind(p,h)
        for p,h in iv['artifact_sha256'].items():bind(f/p,h)
        for n,h in iv['local_profile_sha256'].items():bind(f/(n+'.json'),h)
        bind(f/'invocation.json')
        plate=f/'slice-review.3mf';gc=f/'plate_1.gcode'
        with zipfile.ZipFile(plate) as z:
            assert hashlib.sha256(z.read('Metadata/plate_1.gcode')).hexdigest()==sha(gc)
        item.update(selected_3mf=rel(plate),selected_3mf_sha256=sha(plate),gcode=rel(gc),gcode_sha256=sha(gc),
            candidate_3mf=None,candidate_3mf_sha256=None,pending_review=False,needs_reslice=False,
            binding_report=rel(out/'report.json'),binding_report_sha256=None,
            identity_status='CURRENT_NATIVE_3MF_ORIENTED_FACE_CORRESPONDENCE_VERIFIED',
            process_status='BOUNDED_CURRENT_SLICE_FEATURE_AND_CLEANUP_REVIEW',
            reason=decision['decision'],review_scope=decision['scope'],
            review_evidence=decision['reports'],remaining_physical_limits=decision['remaining_physical_limits'],
            manufacturing_release=False,physical_acceptance=False)
    groups=defaultdict(list)
    for item in items:groups[item['selected_3mf']].append(item)
    plates=[]
    for file,rows in groups.items():
        assert {r['plate_quantity'] for r in rows}=={len(rows)}
        plates.append({'file':file,'sha256':bind(file,rows[0]['selected_3mf_sha256']),
            'instance_ids':[r['instance_id'] for r in rows],'quantity':len(rows),
            'print_plate_once_for_these_instances':True,'pending_review':False})
    counts={'printed_instances':len(items),'material_instances':dict(Counter(r['material'] for r in items)),
        'bound_instances':len(items),'candidate_instances':0,'pending_instances':0,'needs_reslice_instances':0,
        'selected_plates':len(plates),'candidate_plates':0}
    assert counts['printed_instances']==56 and len(plates)==42
    assert all(sha(p)==h for p,h in evidence.items())
    report={'status':'CURRENT_ECLIP_56_SLICES_BOUND_PHYSICAL_GATES_OPEN',
        'created_utc':datetime.now(timezone.utc).isoformat(),'counts':counts,
        'baseline_manifest':rel(a.baseline_manifest),'review_index':rel(a.review_index),
        'changed_instance_ids':sorted(IDS),'evidence_sha256':evidence,'sources_and_artifacts_stable':True,
        'scope':'Three new native slices replace only the changed input parts. 53 earlier bindings remain unchanged. Selection means the named bounded offline review is complete, not guaranteed printing or assembled function.',
        'manufacturing_release':False,'physical_acceptance':False,'sent_to_printer':False,'goal_complete':False}
    dump(out/'report.json',report)
    for item in items:
        if item['instance_id'] in IDS:item['binding_report_sha256']=sha(out/'report.json')
    manifest={**base,'counts':counts,'items':items,'plates':plates,'candidate_plates':[],
        'evidence_sha256':{**evidence,rel(out/'report.json'):sha(out/'report.json')},'scope':report['scope'],
        'sources_and_artifacts_stable':True,'manufacturing_release':False,'physical_acceptance':False,'sent_to_printer':False}
    dump(out/'manifest.json',manifest)
    print(json.dumps({'status':report['status'],'counts':counts,'manifest':rel(out/'manifest.json')},ensure_ascii=False))

if __name__=='__main__':main()
