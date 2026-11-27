"""Compare actual nodal fields at the same transmitted load, not angle."""
from pathlib import Path
import json,os
import numpy as np
CAD=Path(__file__).resolve().parents[2]
PREVIEW=CAD/'preview'

def sample(directory,kg):
    m=json.loads((directory/'manifest.json').read_text())
    assert m['solver_job_finished'] and m['all_requested_steps_exported']
    assert m['assembly_validation']['both_contact_pairs_active_under_load']
    frames=sorted([f for f in m['frames'] if f['torque_Nm']>.1 and f['upper_positive_pressure_samples']>0 and f['lower_positive_pressure_samples']>0],key=lambda f:f['equivalent_kg_at_200mm'])
    assert frames[0]['equivalent_kg_at_200mm']<=kg<=frames[-1]['equivalent_kg_at_200mm']
    hi=next(i for i,f in enumerate(frames) if f['equivalent_kg_at_200mm']>=kg)
    a=frames[max(0,hi-1)];b=frames[hi]
    t=(kg-a['equivalent_kg_at_200mm'])/max(1e-12,b['equivalent_kg_at_200mm']-a['equivalent_kg_at_200mm'])
    field=(1-t)*np.fromfile(directory/a['file'],dtype='<f4').reshape(-1,5)+t*np.fromfile(directory/b['file'],dtype='<f4').reshape(-1,5)
    p=np.fromfile(directory/m['positions'],dtype='<f4').reshape(-1,3)
    body=p[:,2]<22;idx=np.argmax(np.where(body,field[:,0],-1))
    return {'kg_at_200mm':kg,'torque_Nm':kg*1.96133,'angle_deg':(1-t)*a['angle_deg']+t*b['angle_deg'],
        'max_vm_surface_body_MPa':float(field[body,0].max()),'max_layer_tension_surface_body_MPa':float(field[body,1].max()),
        'max_displacement_surface_mm':float(np.linalg.norm(field[:,2:],axis=1).max()),'peak_xyz_mm':p[idx].tolist(),
        'interpolated_between_solved_loads_kg':[a['equivalent_kg_at_200mm'],b['equivalent_kg_at_200mm']]}

def main():
    rows=[]
    for kg in [3,4.9,6,8]:
        try:a=sample(PREVIEW/'guard-assembly-results',kg);b=sample(PREVIEW/os.environ.get('NEW_RESULTS','guard-v117-results'),kg)
        except AssertionError:continue
        rows.append({'old':a,'new':b,'vm_reduction_percent':100*(1-b['max_vm_surface_body_MPa']/a['max_vm_surface_body_MPa']),
            'layer_tension_reduction_percent':100*(1-b['max_layer_tension_surface_body_MPa']/a['max_layer_tension_surface_body_MPa'])})
    assert rows,'No shared bearing load range'
    report={'comparison':'same load / same material and contact assumptions; interpolate real solved surface nodal fields',
        'mesh_convergence_established_for_comparison':False,'physical_fracture_load_validated':False,'rows':rows}
    (PREVIEW/os.environ.get('COMPARISON_FILE','guard-v117-comparison.json')).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=="__main__":main()
