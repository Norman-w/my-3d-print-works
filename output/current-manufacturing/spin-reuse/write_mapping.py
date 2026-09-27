#!/usr/bin/env python3
"""Derive the concise mapping from this directory's completed audit report."""
from pathlib import Path
import hashlib, json
out=Path(__file__).resolve().parent
root=out.parents[2]
p=out/'report.json'
r=json.loads(p.read_text())
keys=['instance_id','current_stl_sha256','slice_folder','old_report',
      'identity_status','process_status','needs_reslice','reason',
      'quantity_required','quantity_in_selected_3mf','material','selected_3mf',
      'selected_3mf_sha256','gcode_sha256']
m={'status':r['status'],'source_report':str(p.relative_to(root)),
   'source_report_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
   'rows':[{k:x[k]for k in keys}for x in r['rows']],
   'manufacturing_release':False,'physical_acceptance':False}
(out/'mapping.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
print(m['status'],m['source_report_sha256'])
