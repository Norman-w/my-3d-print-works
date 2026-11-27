"""Resolution sensitivity for the same reinforced geometry and contact model."""
import json
from compare_reinforcement import PREVIEW,sample

coarse=PREVIEW/'guard-v118-results'
fine=PREVIEW/'guard-v118-refined-results'
cm=json.loads((coarse/'manifest.json').read_text())
fm=json.loads((fine/'manifest.json').read_text())
assert cm['mesh_report']['source_sha256']==fm['mesh_report']['source_sha256']
rows=[]
for kg in [4.9,8]:
    a=sample(coarse,kg);b=sample(fine,kg)
    metrics=['max_vm_surface_body_MPa','max_layer_tension_surface_body_MPa','max_displacement_surface_mm']
    rows.append({'kg_at_200mm':kg,'coarse':a,'refined':b,
        'relative_difference_to_refined_percent':{k:100*abs(a[k]-b[k])/max(abs(b[k]),1e-12) for k in metrics}})
report={'same_source_geometry_sha256':fm['mesh_report']['source_sha256'],
    'coarse_elements':cm['mesh_report']['tetrahedra'],'refined_elements':fm['mesh_report']['tetrahedra'],
    'two_resolutions_are_not_a_formal_convergence_proof':True,'rows':rows}
(PREVIEW/'guard-v118-mesh-sensitivity.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
