"""V2 actual emitted bead envelope at fixed guide; contact evidence, not measured fit."""
from pathlib import Path
import sys,json,math,collections,os,argparse
import numpy as np
from shapely.geometry import LineString,Point,box
B=Path(__file__).resolve().parent;ROOT=B.parents[1];sys.path.insert(0,str(ROOT/'analysis'))
import cable_input_slice_review as p
import cable_flat_slice_review as flat
import path_review as v2

def run(folder):
 folder=folder.resolve();inv=json.loads((folder/'invocation.json').read_text());assert inv['selector']=='cdp_body' and inv['diagnostic_candidate']['source_sha256']==v2.EXPECTED==v2.sha(v2.SOURCE)
 for f,h in inv['source_sha256_at_start'].items():assert v2.sha(v2.path(f))==h
 for f,h in inv['artifact_sha256'].items():assert v2.sha(folder/f)==h
 M,meta=flat.mapping(folder,inv);s=math.sqrt(.5);L=np.array([[-s,s,0,75],[0,0,1,-82],[s,s,0,5],[0,0,0,1.]])
 inverse=np.linalg.inv(M@L);assert np.allclose(inverse[:3,:3]@np.array([0,0,1]),[0,0,1],atol=1e-6)
 rows=[];counts=collections.Counter();R=v2.RG;CX=v2.CX;err=p.ARC_ERROR+p.BUFFER_ERROR
 # Wire centre contact region at u22. Piecewise approximation shrunk by its
 # own sagitta, so lower clearances remain conservative.
 ph=v2.phi(v2.angle(22));aa=np.linspace(0,ph,math.ceil(math.degrees(ph)/.01)+1);wire=LineString(np.column_stack([CX+R*np.sin(aa),R*np.cos(aa)]));wire_error=R*(1-math.cos((aa[1]-aa[0])/2))
 focus=box(CX-1,57,CX+9.5,61)
 with (folder/'plate_1.gcode').open()as g:
  for rec in p.extrusion_paths(g):
   if not v2.model(rec.feature):continue
   q=p.affine(rec.points,inverse);z=float(q[0,2]);z0=z-rec.height
   if z<1.25 or z0>2.75:continue
   ln=LineString(q[:,:2]);
   if ln.distance(focus)>rec.width/2+err:continue
   dz=max(z0-2,2-z,0);rad=math.sqrt(max(0,.75**2-dz**2));gap=ln.distance(wire)-rec.width/2-err-wire_error-rad
   rows.append(dict(line=rec.line,feature=rec.feature,width=rec.width,local_z_slab=[z0,z],print_top=rec.layer,clearance_lower_mm=gap,xy=q[:,:2],geometry=ln));counts[rec.feature]+=1
 out=B/'path-review'/folder.parent.name/'cable-input-body-guide';out.mkdir(parents=True,exist_ok=True)
 os.environ.setdefault('MPLCONFIGDIR',str(out/'mpl'));import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
 from matplotlib.collections import LineCollection
 selected=min(set(round(r['local_z_slab'][1],6)for r in rows),key=lambda z:abs(z-2));fig,ax=plt.subplots(figsize=(10,5),layout='constrained');ax.set_xlim(CX-1,CX+9.5);ax.set_ylim(57.5,61);ax.set_aspect('equal');ax.grid(alpha=.2);ax.set_xlabel('Input fixed local X / mm');ax.set_ylabel('Input fixed local Y / mm');ax.set_title(f'V2 fixed guide actual beads, layer top local Z={selected:g} mm');fig.canvas.draw();scale=(ax.transData.transform([1,0])-ax.transData.transform([0,0]))[0]*72/fig.dpi
 for row in rows:
  if abs(row['local_z_slab'][1]-selected)<1e-5:ax.add_collection(LineCollection([row['xy']],colors='#287996',linewidths=row['width']*scale))
 arc=np.array(wire.coords);ax.plot(arc[:,0],arc[:,1],':',color='#c72b89',label='Core centre / u22 contact arc')
 surface=np.column_stack([CX+(R-.75)*np.sin(aa),(R-.75)*np.cos(aa)]);ax.plot(surface[:,0],surface[:,1],'--',lw=.8,color='#d77916',label='Ideal guide wall R59.25');ax.legend();fig.savefig(out/'guide-key-layer.png',dpi=170);plt.close(fig)
 result=dict(status='BOUNDED_GUIDE_BEAD_CONTACT_REVIEW',source_sha256=v2.EXPECTED,guide_contract=v2.CONTRACT,part=inv['part'],folder=str(folder),mapping=meta,rows_in_wire_height=len(rows),feature_counts=dict(counts),wire_contact_arc_phi_deg=[0,math.degrees(ph)],wire_polyline_sagitta_bound_mm=wire_error,bead_error_bound_mm=err,minimum_clearance_lower_mm=min(r['clearance_lower_mm']for r in rows),possible_contact_commands=sum(r['clearance_lower_mm']<0 for r in rows),closest_commands=[{k:v for k,v in r.items()if k not in ['xy','geometry']}for r in sorted(rows,key=lambda r:r['clearance_lower_mm'])[:15]],interpretation='The guide is intended to touch the wire. Negative conservative bead clearance is a flagged numerical/material-fit margin, not a newly proven jam or an unsupported span. This checks all emitted layers overlapping the core diameter at localZ2 against a conservative contact arc through u22.',limits=['Declared bead width/height is an envelope model, not measured PETG. Wire follows a positive-tension ideal tangent path; no arbitrary-slack guarantee.','Actual guide radius/friction/wear/preload and full loaded return remain unverified.','Whole-STL underside and previous-layer overlap are reported separately by body_path_review.py.'],artifact_sha256={f:v2.sha(folder/f)for f in ['invocation.json','plate_1.gcode','slice-review.3mf']},script_sha256=v2.sha(__file__),image=str(out/'guide-key-layer.png'),manufacturing_release=False,physical_acceptance=False)
 v2.dump(out/'report.json',result);print(json.dumps({k:result[k]for k in ['status','minimum_clearance_lower_mm','possible_contact_commands']}));return result
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--folder',required=True,type=Path);run(ap.parse_args().folder)
