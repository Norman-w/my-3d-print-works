#!/usr/bin/env python3
"""Bound lateral underlay distance at the existing cover ring; no slicing."""
from pathlib import Path
import sys,json,math,hashlib,os
import numpy as np
from shapely.geometry import LineString,Point
from shapely.ops import unary_union
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'analysis'))
import cable_eclip_axis_slice_review as rev
F=ROOT/'output/current-eclip-slices/20260927T155733716437Z/cable-input-cover'
O=ROOT/'output/current-eclip-slices-review/cover-step';O.mkdir(exist_ok=True)
a=json.loads((F/'artifact-review.json').read_text());inv=np.linalg.inv(a['input_local_to_command'])
evidence={**a['evidence_sha256'],rev.rel(F/'artifact-review.json'):rev.sha(F/'artifact-review.json'),rev.rel(__file__):rev.sha(__file__),rev.rel(rev.__file__):rev.sha(rev.__file__)}
for p,h in evidence.items():assert rev.sha(p)==h
rows={2.7:[],2.8:[]}
for r in rev.parser.extrusion_paths((F/'plate_1.gcode').open()):
 if not rev.model(r.feature) or round(r.layer,6) not in rows:continue
 q=rev.parser.affine(r.points,inv); ln=LineString(q[:,:2])
 if ln.distance(Point(0,0))>6:continue
 rows[round(r.layer,6)].append({'line':ln,'width':r.width,'feature':r.feature,'gcode_line':r.line})
prior=rev.footprint(rows[2.7]); ring=Point(0,0).buffer(4.6,resolution=180).difference(Point(0,0).buffer(4.15,resolution=180))
step=.02;details=[]
for r in rows[2.8]:
 ln=r['line'];clipped=ln.intersection(ring)
 if clipped.is_empty:continue
 pieces=list(rev.parser.lines_of(clipped));max_distance=0.;max_halfwidth_excess=-float('inf')
 for p in pieces:
  n=max(1,math.ceil(p.length/step)); ds=[prior.distance(p.interpolate(float(t)))for t in np.linspace(0,p.length,n+1)]
  max_distance=max(max_distance,max(ds))
  max_halfwidth_excess=max(max_halfwidth_excess,max(ds)-r['width']/2)
 details.append({'line':r['gcode_line'],'feature':r['feature'],'width_mm':r['width'],'circle_segment_length_mm':clipped.length,
  'max_centerline_distance_to_previous_bead_footprint_lower_mm':max_distance,
  'max_centerline_distance_upper_mm':max_distance+step/2+rev.parser.ARC_ERROR,
  'max_distance_beyond_current_halfwidth_lower_mm':max_halfwidth_excess})
os.environ.setdefault('MPLCONFIGDIR',str(O/'mpl'));import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
fig,ax=plt.subplots(figsize=(8,8));ax.set_xlim(-5.2,5.2);ax.set_ylim(-5.2,5.2);ax.set_aspect('equal');ax.grid(alpha=.2);fig.canvas.draw();scale=(ax.transData.transform([1,0])-ax.transData.transform([0,0]))[0]*72/fig.dpi
for z,color in [(2.7,'#a8a8a8'),(2.8,'#247fa7')]:
 for r in rows[z]:ax.add_collection(LineCollection([list(r['line'].coords)],colors=color,linewidths=r['width']*scale,alpha=.65,capstyle='round'))
for r in [4.15,4.6]:ax.add_patch(plt.Circle((0,0),r,fill=False,lw=.8,color='#aa357c',linestyle=':'))
ax.set_title('Cover step: grey prior Z2.7 / blue first step Z2.8\nMagenta: nominal R4.15 / R4.60');ax.set_xlabel('Local X / mm');ax.set_ylabel('Local Y / mm');fig.savefig(O/'ring-step.png',dpi=160)
report={'status':'LATERAL_UNDERLAY_DISTANCE_BOUND','slice_folder':rev.rel(F),'source_nominal_radial_step_mm':.45,'sampling_step_max_mm':step,'details':details,'maximum_distance_upper_mm':max(r['max_centerline_distance_upper_mm']for r in details),'interpretation':'Distance is lateral to prior-layer bead projection. Circumferential path length is not free bridge span. Bound concerns sampled discretized commanded path, with sample Lipschitz and arc errors added; it does not prove actual PETG bonding or sag. Previous footprint is conservatively expanded, so these distances are a descriptive nominal underlay measure, not a guaranteed minimum physical contact.','evidence_sha256':evidence,'sources_stable':all(rev.sha(p)==h for p,h in evidence.items()),'manufacturing_release':False,'physical_acceptance':False,'image_sha256':rev.sha(O/'ring-step.png')}
assert report['sources_stable'];rev.dump(O/'report.json',report);print(json.dumps(report,ensure_ascii=False,indent=2))
