from pathlib import Path
import numpy as np,json,os
HERE=Path(os.environ.get('CASE_DIR',Path(__file__).resolve().parent))
m=np.load(HERE/'volume-mesh.npz');n=m['nodes'];t=m['elements'];p=n[t]
det=np.linalg.det(np.stack((p[:,1]-p[:,0],p[:,2]-p[:,0],p[:,3]-p[:,0]),2))
edges=np.array([np.sum((p[:,i]-p[:,j])**2,axis=1) for i in range(4) for j in range(i)]).T
quality=12*(3*np.abs(det)/6)**(2/3)/edges.sum(axis=1)
report={'nodes':len(n),'elements':len(t),'negative_or_zero_jacobians':int(sum(det<=0)),
        'mean_ratio_min':float(quality.min()),'mean_ratio_quantiles':np.quantile(quality,[.001,.01,.05,.5]).tolist(),
        'elements_below_001':int(sum(quality<.01)),'elements_below_01':int(sum(quality<.1)),
        'min_quality_centroid_mm':p[np.argmin(quality)].mean(axis=0).tolist(),
        'volume_mm3':float(np.sum(det)/6),
        'small_absolute_volume_is_not_alone_a_failure':True,
        'convergence_study_required':True}
(HERE/'quality-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
