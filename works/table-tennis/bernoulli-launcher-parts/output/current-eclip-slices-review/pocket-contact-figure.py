#!/usr/bin/env python3
from pathlib import Path
import json,sys,os,numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'analysis'))
import cable_eclip_axis_slice_review as r
F=ROOT/'output/current-eclip-slices/20260927T160923352541Z/cable-input-cover';O=ROOT/'output/current-eclip-slices-review/pocket-contact';O.mkdir(exist_ok=True)
a=json.loads((F/'artifact-review.json').read_text());matrix=np.linalg.inv(a['input_local_to_command']); rows=[]
evidence={**a['evidence_sha256'],r.rel(F/'artifact-review.json'):r.sha(F/'artifact-review.json'),r.rel(__file__):r.sha(__file__),r.rel(r.__file__):r.sha(r.__file__)}
for p,h in evidence.items():assert r.sha(p)==h
for p in r.parser.extrusion_paths((F/'plate_1.gcode').open()):
 if (p.feature.startswith('Support') and abs(p.layer-1.5)<1e-6) or (r.model(p.feature) and min(abs(p.layer-1.7),abs(p.layer-1.8))<1e-6):
  q=r.parser.affine(p.points,matrix);rows.append((p,q))
os.environ.setdefault('MPLCONFIGDIR',str(O/'mpl'));import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Rectangle
fig,axs=plt.subplots(1,2,figsize=(13,6),layout='constrained')
for ax,c in zip(axs,[[-30,20],[74,20]]):
 ax.set_xlim(c[0]-5,c[0]+5);ax.set_ylim(c[1]-5,c[1]+5);ax.set_aspect('equal');ax.grid(alpha=.15);ax.set_title('Square pocket '+str(c));ax.set_xlabel('Input local X / mm');ax.set_ylabel('Input local Y / mm')
fig.canvas.draw()
for ax,c in zip(axs,[[-30,20],[74,20]]):
 scale=(ax.transData.transform([1,0])-ax.transData.transform([0,0]))[0]*72/fig.dpi
 for p,q in sorted(rows,key=lambda x:0 if abs(x[0].layer-1.7)<1e-6 else 1 if x[0].feature.startswith('Support') else 2):
  color='#ccc' if abs(p.layer-1.7)<1e-6 else '#e79b28' if p.feature.startswith('Support') else '#287b9e'
  ax.add_collection(LineCollection([q[:,:2]],colors=color,linewidths=p.width*scale,alpha=.8 if p.feature.startswith('Support') else .65,capstyle='round'))
 ax.add_patch(Rectangle((c[0]-4.2,c[1]-4.2),8.4,8.4,fill=False,color='#9b286c',linestyle=':',linewidth=1))
fig.suptitle('Cover +Z actual pocket layers: grey prior model Z1.7 / orange support Z1.5 / blue roof Z1.8\nSupport has 0.2 mm nominal vertical gap; projections do not prove PETG bonding or removability')
fig.savefig(O/'pocket-layers.png',dpi=160)
result={'status':'ACTUAL_POCKET_LAYER_FIGURE','image':r.rel(O/'pocket-layers.png'),'image_sha256':r.sha(O/'pocket-layers.png'),'source_evidence_sha256':evidence,'sources_stable':all(r.sha(p)==h for p,h in evidence.items()),'physical_acceptance':False}
assert result['sources_stable'];r.dump(O/'report.json',result);print(result['image'])
