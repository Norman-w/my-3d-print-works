"""Aggregate bounded v2 evidence without changing any component's verdict."""
from pathlib import Path
import json, hashlib
from datetime import datetime, timezone

B=Path(__file__).resolve().parent;ROOT=B.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    formal=ROOT/'output/cable-scene-export/20260927T071458613482Z/report.json'
    old=json.loads(formal.read_text())
    formal_drift=[p for p,h in old['source_sha256'].items() if sha(ROOT/p)!=h]
    assert not formal_drift,formal_drift
    paths=[B/'local-review-summary.json',B/'source-identity.json',B/'slice-reuse-proof.json',
     B/'independent/adjuster-review.json',B/'independent/native-verification.json',
     B/'independent/tool-review-upper-sector/report.json',B/'independent/route-and-tool-review.md',
     B/'independent/route-and-tool-review.json',
     B/'housing-route/numeric/report.json',B/'housing-route/numeric/native-report.json',
     B/'housing-route/service/20260927T084938984042Z/report.json',
     B/'host-review/20260927T084810774074Z/report.json',B/'actuation/report.json',
     B/'render/report.json',B/'integration-plan.json',B/'README.md']
    bed=B/'bed-bounds-review.json'
    if bed.exists():paths.append(bed)
    rows=[]
    for p in paths:
        row=dict(file=str(p.relative_to(ROOT)),sha256=sha(p))
        if p.suffix=='.json':row['recorded_status']=json.loads(p.read_text()).get('status','See report scope and component verdicts')
        rows.append(row)
    result=dict(status='V2_DIGITAL_REVIEW_PROGRESS_NOT_RELEASED',created_utc=datetime.now(timezone.utc).isoformat(),
      candidate_sha256=sha(B/'candidate.scad'),route_sha256=sha(B/'housing-route/equal-length-route.scad'),
      formal_scene=dict(report=str(formal.relative_to(ROOT)),source_count=len(old['source_sha256']),all_current_sources_unchanged=True,
       printed_instances=55,scene_entries=84,candidate_integrated=False),
      evidence=rows,
      preserved_failures=[
       'output/cable-input-slack-review/report.json',
       'output/cable-input-lip-candidate/adjuster-travel/20260927T083207056075Z/report.json',
       'output/cable-direct-pull-v2/independent/tool-review/report.json'],
      interpretation='Each evidence file retains its own scope and verdict. Do not add counts into a single universal acceptance claim. The new trigger and route are isolated candidates; existing formal source and LAN scene remain unchanged.',
      remaining=['FDM overhang/bridge manufacturing treatment and actual material/profile agreement',
       'Adopt all affected CAD contracts, scene motion, cap inventory, service checks and print plan consistently',
       'Supplier fitting seats/thread runout/tool dimensions and clamping/torque evidence',
       'Actual friction, preload, loaded return, material strength and original-device outer geometry',
       'First-machine one-ball/airflow/spin operation; not replaced by images or sampled CAD checks'],
      manufacturing_release=False,physical_acceptance=False,sent_to_printer=False)
    (B/'phase-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],evidence_files=len(rows),formal_source_count=len(old['source_sha256']),candidate_sha256=result['candidate_sha256']),indent=2))

if __name__=='__main__':main()
