#!/usr/bin/env python3
"""Audit current source/artifact identities, without promoting physical status."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ['gate-geometry','guide-openings','airflow-spin','assembly-budget',
           'feeder-body-export-manifest','feeder-body-geometry',
           'feeder-support-check','feeder-integration','spin-head-geometry',
           'feeder-tolerance','service-paths','candidate-inventory']


def referenced_hashes(value):
    if isinstance(value,dict):
        if isinstance(value.get('path'),str) and isinstance(value.get('sha256'),str):
            yield value['path'],value['sha256']
        if isinstance(value.get('artifact'),str) and isinstance(value.get('artifact_sha256'),str):
            yield value['artifact'],value['artifact_sha256']
        for key,item in value.items():
            if key in ('source_sha256','source_and_artifact_sha256') and isinstance(item,dict):
                yield from item.items()
            else: yield from referenced_hashes(item)
    elif isinstance(value,list):
        for item in value: yield from referenced_hashes(item)


def main():
    paths = [ROOT/'output/analysis'/f'{name}.json' for name in REPORTS]
    paths.append(ROOT/'output/guide-revision/check.json')
    paths.append(ROOT/'output/guide-revision/tolerance/report.json')
    paths.append(ROOT/'output/seam-candidate/seam-candidate-report.json')
    paths.append(ROOT/'output/fit-coupons/fit-coupons-report.json')
    paths.append(ROOT/'output/revised-feeder-review/report.json')
    paths.append(ROOT/'output/interface-study/report.json')
    paths.append(ROOT/'output/analysis/guide-witness-decomposition.json')
    paths.append(ROOT/'output/analysis/gate-budget-feasibility.json')
    paths.append(ROOT/'output/preview/render-manifest.json')
    rows = []
    for path in paths:
        if not path.exists():
            rows.append({'report':str(path.relative_to(ROOT)), 'missing':True,'matches_current_files':False})
            continue
        raw = path.read_bytes()
        data = json.loads(raw)
        references = []
        for ref,expected in referenced_hashes(data):
            source = Path(ref)
            if not source.is_absolute(): source = ROOT/source
            actual = hashlib.sha256(source.read_bytes()).hexdigest() if source.exists() else None
            references.append({'path':str(source.relative_to(ROOT)), 'matches':actual==expected})
        rows.append({'report':str(path.relative_to(ROOT)),
                     'report_sha256':hashlib.sha256(raw).hexdigest(),
                     'matches_current_files':bool(references) and all(r['matches'] for r in references),
                     'referenced_files':references,
                     'reported_status':data.get('status',data.get('analysis_status',data.get('static_screen_status',data.get('geometric_status',data.get('physical_validation_status','SEE_REPORT')))))})
    fresh = all(r['matches_current_files'] for r in rows)
    report = {'generated_at_utc':datetime.now(timezone.utc).isoformat(),
              'status':'SNAPSHOT_IDENTITIES_CURRENT' if fresh else 'MISSING_OR_STALE_REPORTS',
              'reports':rows,'manufacturing_release':False,'physical_acceptance':'OPEN',
              'note':'Matching hashes only establishes report identity; it does not turn conditional, partial or open checks into acceptance.'}
    target = ROOT/'output/analysis/current-snapshot.json'
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(report['status'])
    for row in rows:
        if not row['matches_current_files']: print('REFRESH_REQUIRED',row['report'])
    return 0 if fresh else 1


if __name__=='__main__': sys.exit(main())
