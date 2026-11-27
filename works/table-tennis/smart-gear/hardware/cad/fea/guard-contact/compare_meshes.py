"""Compare fields at equal reaction torque, not equal imposed rotation."""
from pathlib import Path
import json
import numpy as np
HERE=Path(__file__).resolve().parent
base=json.loads((HERE.parent.parent/'preview/guard-fea-results/manifest.json').read_text())
fine=json.loads((HERE/'refined/results/manifest.json').read_text())
def interpolate(m,key,kg):
    f=sorted(m['frames'],key=lambda f:f['equivalent_kg_at_200mm'])
    return float(np.interp(kg,[v['equivalent_kg_at_200mm'] for v in f],[v[key] for v in f]))
limit=min(max(f['equivalent_kg_at_200mm'] for f in m['frames']) for m in (base,fine))
rows=[]
for kg in (1,3,5,8,10):
    if kg>limit:continue
    metrics={}
    for key in ('max_vm_body_MPa','p99_vm_body_MPa','max_layer_tension_body_MPa','max_displacement_mm'):
        a,b=[interpolate(m,key,kg) for m in (base,fine)]
        metrics[key]={'base':a,'refined':b,'relative_change':abs(b-a)/max(abs(a),1e-9)}
    rows.append({'kg_at_200mm':kg,'metrics':metrics})
report={'base_tetrahedra':base['mesh_report']['tetrahedra'],'refined_tetrahedra':fine['mesh_report']['tetrahedra'],
    'comparison':'equal reaction load; piecewise interpolation between converged states','rows':rows,
    'peak_stress_10percent_check':bool(rows) and all(r['metrics'][k]['relative_change']<.1 for r in rows for k in ('max_vm_body_MPa','max_layer_tension_body_MPa')),
    'pre_failure_3_to_5kg_peak_stress_10percent_check':len([r for r in rows if 3<=r['kg_at_200mm']<=5])>=2 and all(r['metrics'][k]['relative_change']<.1 for r in rows if 3<=r['kg_at_200mm']<=5 for k in ('max_vm_body_MPa','max_layer_tension_body_MPa')),
    'not_a_rigorous_asymptotic_convergence_proof':True}
(HERE/'mesh-comparison.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
