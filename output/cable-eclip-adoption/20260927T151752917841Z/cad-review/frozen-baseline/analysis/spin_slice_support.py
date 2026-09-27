#!/usr/bin/env python3
"""Bounded support access review from actual G-code, line widths and STL.

This is an access test for a defined narrow tool, not support break-force or
PETG strength validation. Nothing here submits a print job.
"""
from pathlib import Path
import sys,json,hashlib,collections
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import review_integrated_shell_slice as shell
shell.np=np;shell.collections=collections
from feeder_body_geometry import read_mesh
OUT=ROOT/'output/print-review/spin-head'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def box(label,lo,hi):return {'name':label,'lo':np.array(lo,float),'hi':np.array(hi,float)}
def tools_for(name):
 if name=='body':
  b=[box('central axial access 20x20',[-10,-10,-27],[10,10,77]),box('main radial service access',[33.5,-8,25],[66,8,64])]
  for z in [20,66]:b.append(box(f'opposite nut side blade z{z}',[-24.15,0,z-1],[-22.15,25,z+1]))
  for y in [-18,18]:
   for z in [27,61]:b.append(box(f'cover nut blade y{y} z{z}',[49.35,min(y,y/abs(y)*28),z-1],[51.35,max(y,y/abs(y)*28),z+1]))
  return b
 if name=='cover':return [box('under-cover central approach',[34,-5,36],[51,5,49]),box('M4 side nut blade',[56.35,0,42],[58.35,25,44]),box('latch nut blade',[56,-1,69],[58,1,80])]
 if name=='spring-cage':return [box('axial bore access 6x6',[37,-3,40],[58,3,46])]+[box(f'ear nut blade y{y}',[49.35,min(y,y/abs(y)*20),42],[51.35,max(y,y/abs(y)*20),44])for y in [-11,11]]
 return []
def center_inside_mesh(p,t):
 # Generic oblique ray avoids face/edge alignment. Deduplicate hit distances.
 d=np.array([1.,.137123,.213731]);e1=t[:,1]-t[:,0];e2=t[:,2]-t[:,0];h=np.cross(np.broadcast_to(d,e2.shape),e2);a=np.einsum('ij,ij->i',e1,h);ok=abs(a)>1e-10
 f=np.zeros(len(t));f[ok]=1/a[ok];s=p-t[:,0];u=f*np.einsum('ij,ij->i',s,h);q=np.cross(s,e1);v=f*(q@d);z=f*np.einsum('ij,ij->i',e2,q)
 hits=z[ok&(u>=0)&(v>=0)&(u+v<=1)&(z>1e-9)]
 return len(set(np.round(hits,7)))%2==1
def segment_hits_box(a,b,lo,hi):
 d=b-a;left=0.;right=1.
 for k in range(3):
  if abs(d[k])<1e-12:
   if a[k]<lo[k]or a[k]>hi[k]:return False
  else:
   x,y=(lo[k]-a[k])/d[k],(hi[k]-a[k])/d[k]
   left=max(left,min(x,y));right=min(right,max(x,y))
   if left>right:return False
 return True
def main():
 reports=[]
 for name in ['body','cover','spring-cage']:
  folder=OUT/name;t,_=read_mesh(ROOT/f'output/spin-head/spin-{name}.stl');sd=np.load(folder/'support-paths.npz');R=sd['rotation'];tr=sd['translation'];q=sd['points'];w=sd['width'];h=sd['height'];boxes=tools_for(name)
  for b in boxes:
   cand=t[(t.max(1)>=b['lo']).all(1)&(t.min(1)<=b['hi']).all(1)]
   b['stl_surface_hits']=sum(shell.clipped_triangle_in_box(v,b['lo'],b['hi'])for v in cand)
   b['center_inside_mesh']=center_inside_mesh((b['lo']+b['hi'])/2,t)
   corners=np.array([[x,y,z]for x in [b['lo'][0],b['hi'][0]]for y in [b['lo'][1],b['hi'][1]]for z in [b['lo'][2],b['hi'][2]]]);cmd=corners@R.T+tr;b['cmd_lo']=cmd.min(0);b['cmd_hi']=cmd.max(0);b['model_envelope_hits']=0
   # Actual support footprint expanded by line width / 2 and full layer height.
   ext=np.abs(R.T)@np.vstack([w/2,w/2,h]);b['support_samples_in_or_touching_access']=int(((q+ext.T>=b['lo']).all(1)&(q-ext.T<=b['hi']).all(1)).sum())
  for z,lh,feature,width,pts in shell.paths(folder/'plate_1.gcode'):
   if feature.startswith('Support')or feature in ['Brim','Skirt','Custom']:continue
   for b in boxes:
    # Conservative square XY bead envelope, down through the full actual
    # layer, around each sampled arc chord. Arc sagitta <= .00125 mm.
    lo=b['cmd_lo']-np.array([width/2+.00125,width/2+.00125,0]);hi=b['cmd_hi']+np.array([width/2+.00125,width/2+.00125,lh])
    if (pts.max(0)<lo).any()or(pts.min(0)>hi).any():continue
    if any(segment_hits_box(a,c,lo,hi)for a,c in zip(pts[:-1],pts[1:])):b['model_envelope_hits']+=1
  fig,axes=plt.subplots(1,3,figsize=(15,6));colors=['#127283','#de6e32']
  for ax,(a,b)in zip(axes,[(0,2),(1,2),(0,1)]):
   # Exact mesh triangle edges and sampled actual support centrelines are
   # illustrative; numeric bead-envelope checks above retain widths/heights.
   edges=np.concatenate([t[:,[0,1]],t[:,[1,2]],t[:,[2,0]]]);ax.add_collection(LineCollection(edges[:,:,[a,b]],colors=colors[0],linewidths=.12,alpha=.35))
   n=max(1,len(q)//30000);ax.scatter(q[::n,a],q[::n,b],s=.22,c=colors[1],alpha=.4)
   for tool in boxes:
    from matplotlib.patches import Rectangle
    ax.add_patch(Rectangle((tool['lo'][a],tool['lo'][b]),tool['hi'][a]-tool['lo'][a],tool['hi'][b]-tool['lo'][b],fill=False,color='#803fab',lw=.5))
   ax.autoscale();ax.set_aspect('equal');ax.set_xlabel('XYZ'[a]+' / mm');ax.set_ylabel('XYZ'[b]+' / mm');ax.grid(alpha=.15)
  fig.suptitle(name+': STL (blue), actual support paths (orange), reviewed tool corridors (purple)');fig.tight_layout();fig.savefig(folder/'support-access.png',dpi=160);plt.close(fig)
  rows=[]
  for b in boxes:
   rows.append({k:(v.tolist()if isinstance(v,np.ndarray)else bool(v)if isinstance(v,np.bool_)else v)for k,v in b.items()})
  reports.append({'part':name,'input_stl_sha256':sha(ROOT/f'output/spin-head/spin-{name}.stl'),'gcode_sha256':sha(folder/'plate_1.gcode'),'support_path_sha256':sha(folder/'support-paths.npz'),'corridors':rows,'all_corridors_clear_in_stl':all(b['stl_surface_hits']==0 and not b['center_inside_mesh']for b in boxes),'all_corridors_clear_of_declared_model_beads':all(b['model_envelope_hits']==0 for b in boxes),'image':str((folder/'support-access.png').relative_to(ROOT))})
 report={'status':'BOUNDED_TOOL_ACCESS_REVIEW','parts':reports,'script_sha256':sha(Path(__file__)),'limits':['Tools are explicit nominal rectangular access envelopes, including narrow2mm blades; not a claim for arbitrary pliers or wrench bodies.','Actual support paths present within a corridor must be removed from outside inward before the tool advances.','The model bead is a conservative square line-width envelope through its entire layer height, not a physical PETG surface measurement.','Reviewed access does not prove break force, every fragmented support extraction, printed strength or no residual particles.','No enclosed cavity is created by assembly while cleaning: clean each part separately before inserting nuts, spring or carriage.'],'sent_to_printer':False}
 dump(OUT/'support-access-review.json',report)
 print(json.dumps([{k:v for k,v in p.items()if k in ['part','all_corridors_clear_in_stl','all_corridors_clear_of_declared_model_beads']}for p in reports],indent=2))
if __name__=='__main__':main()
