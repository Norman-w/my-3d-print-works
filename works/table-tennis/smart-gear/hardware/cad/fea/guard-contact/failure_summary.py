from pathlib import Path
import json
HERE=Path(__file__).resolve().parent
paths={'base':HERE.parent.parent/'preview/guard-fea-results/manifest.json','refined':HERE/'refined/results/manifest.json'}
def crossing(frames,key,threshold):
    for a,b in zip(frames,frames[1:]):
        if a[key]<threshold<=b[key]:
            t=(threshold-a[key])/(b[key]-a[key]);return a['equivalent_kg_at_200mm']+t*(b['equivalent_kg_at_200mm']-a['equivalent_kg_at_200mm'])
    return None
results={}
for name,path in paths.items():
    m=json.loads(path.read_text());f=sorted(m['frames'],key=lambda x:x['equivalent_kg_at_200mm'])
    if f[0]['equivalent_kg_at_200mm']>.001:f=[{'equivalent_kg_at_200mm':0,'max_vm_body_MPa':0,'max_layer_tension_body_MPa':0}]+f
    layer={str(v):crossing(f,'max_layer_tension_body_MPa',v) for v in (14,18,22)}
    xy={str(v):crossing(f,'max_vm_body_MPa',v) for v in (45,47,49)}
    first=[min(layer[str(z)],xy[str(x)]) for z in (14,18,22) for x in (45,47,49) if layer[str(z)] is not None and xy[str(x)] is not None]
    results[name]={'layer_criterion_kg_at_200mm':layer,'von_mises_yield_criterion_kg_at_200mm':xy,'first_reference_criterion_range_kg':[min(first),max(first)] if first else None,'finished':m['solver_job_finished']}
report={'material_brand':'彩格','material_parameters_are_other_brand_reference':True,'actual_fracture_load_determined':False,
        'withdrawn_for_actual_assembly':True,'reason':'Legacy roof-clamp boundary bypasses upper-beam contact; retain only as a mathematical boundary-condition comparison.',
        'interpretation':'First attainment of a reference stress criterion in an idealized solid elastic FE model, not physical breakage.',
        'methods':'Piecewise interpolation of converged contact equilibria; no extrapolation past available results','cases':results}
(HERE/'failure-summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
