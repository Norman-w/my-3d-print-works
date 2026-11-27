"""Validate two-pair contact before publishing its fields to the workbench."""
from pathlib import Path
import json,os
import numpy as np
BASE=Path(__file__).resolve().parent
HERE=Path(os.environ.get('CASE_DIR',BASE/'assembly'))
OUT=Path(os.environ.get('RESULT_DIR',BASE.parent.parent/'preview/guard-assembly-results'))
m=json.loads((OUT/'manifest.json').read_text());c=m['assumptions'];frames=m['frames']
assert c['model_type']=='upper_and_lower_contact' and c['roof_clamped'] is False
assert c['fixed_nodes']==8 and len(c['upper_nodes'])==8
assert m['solver_job_finished'] and m['all_requested_steps_exported']
assert m['mesh_quality']['negative_or_zero_jacobians']==0
assert all(f.get('negative_or_zero_deformed_jacobians_from_frd',0)==0 for f in frames),'Deformed mesh contains inverted elements'
loaded=[f for f in frames if f['torque_Nm']>1]
assert loaded,'No meaningful transmitted load was solved'
assert all(f['upper_positive_pressure_samples']>0 and f['lower_positive_pressure_samples']>0 for f in loaded)
assert all(f['signed_torque_Nm']*f['support_torque_Nm']<0 for f in loaded)
assert all(f['torque_balance_relative']<.02 for f in loaded)
assert all(f['stabilizer_torque_fraction']<.05 for f in loaded),'Numerical springs carry excessive load'
for f in frames:
    values=np.fromfile(OUT/f['file'],dtype='<f4').reshape(-1,5)
    assert len(values)==m['node_count'] and np.isfinite(values).all()
report={'both_contact_pairs_active_under_load':True,'upper_and_lower_torques_opposite':True,
    'roof_xy_not_clamped':True,'solver_job_finished':True,'converged_steps':len(frames),
    'maximum_torque_balance_relative_loaded':max(f['torque_balance_relative'] for f in loaded),
    'maximum_stabilizer_torque_fraction_loaded':max(f['stabilizer_torque_fraction'] for f in loaded),
    'frames':[{'angle_deg':f['angle_deg'],'kg_at_200mm':f['equivalent_kg_at_200mm'],
        'foot_torque_Nm':f['signed_torque_Nm'],'upper_torque_Nm':f['support_torque_Nm'],
        'upper_contacts':f['upper_positive_pressure_samples'],'lower_contacts':f['lower_positive_pressure_samples'],
        'stabilizer_torque_fraction':f['stabilizer_torque_fraction']} for f in frames],
    'numerical_model_is_not_a_calibrated_printed_part':True,'physical_fracture_load_validated':False,
    'mesh_sensitivity_not_repeated_for_two_pair_boundary':True}
report['deformed_jacobians_checked_from_frd']=all('negative_or_zero_deformed_jacobians_from_frd' in f for f in frames)
sensitivity=OUT.parent/f"guard-v{m['version'].replace('.','')}-mesh-sensitivity.json"
if sensitivity.exists():
    study=json.loads(sensitivity.read_text())
    if study.get('same_source_geometry_sha256')==m['mesh_report']['source_sha256']:
        report['mesh_sensitivity_not_repeated_for_two_pair_boundary']=False
        report['formal_mesh_convergence_established']=False
        m['reinforcement_mesh_sensitivity']=study
(HERE/'assembly-validation.json').write_text(json.dumps(report,indent=2)+'\n')
m['assembly_validation']=report
(OUT/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');print(json.dumps(report,indent=2))
