from pathlib import Path
import hashlib,json
p=Path(__file__).resolve().parent;r=json.loads((p/'report.json').read_text());root=p.parents[2]
fail=[n for n,h in r['evidence_sha256'].items()if not(root/n).is_file()or hashlib.sha256((root/n).read_bytes()).hexdigest()!=h]
assert not fail,fail
print(json.dumps({'status':'EVIDENCE_HASHES_PASS','count':len(r['evidence_sha256']),'report_sha256':hashlib.sha256((p/'report.json').read_bytes()).hexdigest()}))
