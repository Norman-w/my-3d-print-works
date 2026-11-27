#!/usr/bin/env python3
"""Extract native zero-setting contracts from a completed, hash-matched review."""
from pathlib import Path
import hashlib,json
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
latest=json.loads((OUT/'latest.json').read_text());run=ROOT/latest['directory']
assert sha(run/'report.json')==latest['report_sha256']
r=json.loads((run/'report.json').read_text())
assert r['sources_stable'] and all(c['passed'] for c in r['checks'])
assert all(sha(ROOT/p)==h for p,h in r['source_sha256'].items())
files={}
for mode in ['original','candidate']:
    rows=[x for x in r['native_runs'] if x['mode']==mode and x['delta']==0]
    assert len(rows)==1 and rows[0]['valid']
    p=run/(mode+'-contract.json');p.write_text(json.dumps(rows[0]['contract'],ensure_ascii=False,indent=2)+'\n')
    files[str(p.relative_to(ROOT))]=sha(p)
v={'report':str((run/'report.json').relative_to(ROOT)),'report_sha256':sha(run/'report.json'),
   'source_identities_current':True,'extracted_contracts':files,'script_sha256':sha(Path(__file__)),
   'readme_sha256':sha(OUT/'README.md')}
(OUT/'contract-extraction.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(v,indent=2))
