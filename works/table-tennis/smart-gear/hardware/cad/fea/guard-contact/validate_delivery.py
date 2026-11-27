"""Independent consistency gates on the delivered FE data and raw solver jobs."""
from pathlib import Path
import json,hashlib
import numpy as np
HERE=Path(__file__).resolve().parent
OUT=HERE.parent.parent/'preview/guard-fea-results'
m=json.loads((OUT/'manifest.json').read_text());fine=json.loads((HERE/'refined/results/manifest.json').read_text())
comparison=json.loads((HERE/'mesh-comparison.json').read_text());failure=json.loads((HERE/'failure-summary.json').read_text())
assert m['solver_job_finished'] and fine['solver_job_finished']
assert m['all_requested_steps_exported'] and fine['all_requested_steps_exported']
assert len(m['frames'])==8 and len(fine['frames'])==3
assert m['frd_sha256']==hashlib.sha256((HERE/'contact.frd').read_bytes()).hexdigest()
assert m['mesh_quality']['negative_or_zero_jacobians']==0
assert fine['mesh_quality']['negative_or_zero_jacobians']==0
coords=np.fromfile(OUT/m['positions'],dtype='<f4').reshape(-1,3)
indices=np.fromfile(OUT/m['triangles'],dtype='<u4')
assert len(coords)==m['node_count'] and len(indices)==3*m['triangle_count'] and indices.max()<len(coords)
assert np.all(np.isfinite(coords))
for f in m['frames']:
    a=np.fromfile(OUT/f['file'],dtype='<f4').reshape(-1,5)
    assert len(a)==m['node_count'] and np.all(np.isfinite(a))
    assert np.min(a[:,:2])>=0
    if f['angle_deg']<=1:
        assert f['torque_Nm']<1e-6 and f['max_vm_body_MPa']==0 and f['contact_sample_count']==0
    else:
        assert f['contact_sample_count']>0 and f['torque_balance_relative']<.01
    # FRD has five-digit printed stresses/forces; use a force-scaled gate
    # rather than a fixed .01 N limit at multi-kN reactions.
    assert np.max(np.abs(f['net_force_N']))<max(.01,f['torque_Nm']*1000/38.5*.0001)
    assert abs(f['equivalent_kg_at_200mm']*9.80665*.2-f['torque_Nm'])<1e-9
assert comparison['pre_failure_3_to_5kg_peak_stress_10percent_check']
f5=m['frames'][3]
assert f5['max_penetration_mm']<.01
report={'both_solver_jobs_finished':True,'base_steps':8,'refined_steps':3,
    'no_nonpositive_reference_jacobians':True,
    'unloaded_contact_gap_verified':True,'binary_fields_finite_and_correct_shape':True,
    'max_torque_balance_relative':max(f['torque_balance_relative'] for f in m['frames'] if f['torque_Nm']>.01),
    'max_force_balance_relative_to_contact_couple':max(float(np.linalg.norm(f['net_force_N']))/max(1,f['torque_Nm']*1000/38.5) for f in m['frames']),
    'max_penetration_mm_all_elastic_steps':max(f['max_penetration_mm'] for f in m['frames']),
    'near_5kg_penetration_mm':f5['max_penetration_mm'],
    'mesh_sensitivity':comparison,'reference_failure_screening':failure,
    'physical_fracture_validated':False,
    'remaining_mesh_limit':'Ten very-low-mean-ratio boundary tetrahedra remain near the bottom lip; no inverted elements. Near-failure load sensitivity is bounded by the two-mesh comparison, not a proof of asymptotic convergence.'}
(HERE/'delivery-validation.json').write_text(json.dumps(report,indent=2)+'\n')
m['validation']=report
(OUT/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('mesh_sensitivity','reference_failure_screening')},indent=2))
