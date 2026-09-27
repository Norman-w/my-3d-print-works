#!/usr/bin/env python3
"""Finite six-region disassembly audit of the ORIGINAL slice only.
Regions are required removed pieces, not an assertion that a cutter can create them.
"""
from pathlib import Path
import importlib.util,collections,json,math,time,sys,os
import numpy as np
from shapely.geometry import LineString,Polygon,box
from shapely.ops import unary_union
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
s=importlib.util.spec_from_file_location('sweep',P/'sweep_review.py');a=importlib.util.module_from_spec(s);s.loader.exec_module(a)
F=ROOT/'output/current-manufacturing/feeder-new/runs/20260927T094300899015Z/inlet-rear-anchor-z-down-supported';OUT=P/'original-partition';OUT.mkdir(exist_ok=True)
REGIONS=[]
for sign in [-1,1]:
 for name,x,width,z0,z1,y0,y1 in [('M4',43,8,-118.1,-107,-25,0),('M2_5',10.5,3,-146.1,-140,-61,-40),('strap',20.5,3.5,-137.1,-130.5,-58,-40)]:
  REGIONS.append({'id':name+('_left'if sign<0 else'_right'),'lo':[sign*x-width,y0,z0],'hi':[sign*x+width,y1,z1]})
def main():
 t0=time.time();old=json.loads((F/'current-review.json').read_text());state=old['instances'][0];M=np.array(state['actual_mapping']['current_cad_to_gcode_command']);tri=a.g.affine(a.read_stl(ROOT/state['input']['file']).reshape(-1,3),M).reshape(-1,3,3)
 groups=collections.defaultdict(lambda:collections.defaultdict(list));met=collections.defaultdict(lambda:collections.defaultdict(list));actual=[]
 for r in a.g.extrusion_paths((F/'plate_1.gcode').open()):
  k='support'if r.feature.startswith('Support')else'model'if r.feature not in a.SKIP|{'Brim','Skirt'}else None
  if k is None:continue
  rad=(r.width/2+.002)/math.cos(math.pi/128);p=LineString(r.points[:,:2]).buffer(rad,quad_segs=32);z=round(r.layer,6)
  groups[z][k].append(p);met[z][k].append((float(r.points[:,2].min()-r.height),float(r.points[:,2].max()),r.line))
  if k=='support':actual.append(r)
 for z in groups:
  for k in groups[z]:groups[z][k]=unary_union(groups[z][k])
 models=[(min(x[0]for x in met[z]['model']),groups[z]['model'])for z in sorted(groups)if'model'in groups[z]]
 cumulative=Polygon();j=0;rows=[];piece_stats={r['id']:{'swept_projection_area_sum_mm2':0.,'layer_slabs':0,'path_lines':[],'path_bounds_cad':None}for r in REGIONS}
 # Clip each true-height grouped slab at every ROI Z plane, so no whole
 # layer is silently removed merely because it touches a proposed cut box.
 for z in sorted(groups):
  if'support'not in groups[z]:continue
  sup=groups[z]['support'];lo=min(x[0]for x in met[z]['support']);hi=max(x[1]for x in met[z]['support'])
  while j<len(models)and models[j][0]<=hi+1e-10:cumulative=unary_union([cumulative,models[j][1]]);j+=1
  cuts=sorted(set([lo,hi]+[zz+156 for r in REGIONS for zz in [r['lo'][2],r['hi'][2]]if lo<zz+156<hi]))
  for bottom,top in zip(cuts,cuts[1:]):
   remaining=sup;mid=(bottom+top)/2
   for r in REGIONS:
    if r['lo'][2]+156<=mid<=r['hi'][2]+156:
     q=box(r['lo'][0]+M[0,3],r['lo'][1]+M[1,3],r['hi'][0]+M[0,3],r['hi'][1]+M[1,3]);removed=remaining.intersection(q);remaining=remaining.difference(q)
     if not removed.is_empty:piece_stats[r['id']]['swept_projection_area_sum_mm2']+=removed.area;piece_stats[r['id']]['layer_slabs']+=1
   if remaining.is_empty:continue
   hs=remaining.intersection(a.surfaces_below(tri,top));hm=remaining.intersection(cumulative)
   rows.append({'bottom':bottom,'top':top,'clear_stl':hs.is_empty,'clear_actual_model':hm.is_empty,'stl_hit_area':hs.area,'model_hit_area':hm.area,'hit_bounds':list(unary_union([hs,hm]).bounds)if not hs.is_empty or not hm.is_empty else None})
 for r in REGIONS:
  allp=[];st=piece_stats[r['id']]
  for rec in actual:
   q=a.g.affine(rec.points,np.linalg.inv(M));rad=(rec.width/2+.002)/math.cos(math.pi/128);ql=q.min(0)-[rad,rad,rec.height];qh=q.max(0)+[rad,rad,0]
   if (qh>=r['lo']).all()and(ql<=r['hi']).all():
    st['path_lines'].append(rec.line);allp.append(q)
  if allp:st['path_bounds_cad']=[np.concatenate(allp).min(0).tolist(),np.concatenate(allp).max(0).tolist()]
  st['path_line_count']=len(st['path_lines']);st['path_lines']=st['path_lines'][:20]
 # Actual neck sections at the proposed first cut heights, NOT guessed trees.
 necks=[]
 for name,z,ymax,xs in [('M4',38,-12.6,[-43,43]),('M2_5_rear',10,-54.2,[-10.5,10.5]),('strap_rear',19,-48.5,[-20.5,20.5])]:
  for x in xs:
   w=8 if name=='M4' else 4
   q=groups[z]['support'].intersection(box(x+128-w,90,x+128+w,ymax+153.49999002316284))
   # This is the full actual section in the stated rear window.
   necks.append({'name':name,'side_x':x,'cad_z':z-156,'rear_y_limit':ymax,'support_section_area_mm2':q.area,'support_section_xy_bounds_cad':[q.bounds[0]-127.99999,q.bounds[1]-153.49999002316284,q.bounds[2]-127.99999,q.bounds[3]-153.49999002316284]if not q.is_empty else None})
 rep={'status':'REMAINING_EXTERNAL_TREE_SWEEP_CLEAR_AFTER_SIX_REGIONS_REMOVED'if all(r['clear_stl']and r['clear_actual_model']for r in rows)else'REMAINING_TREE_STILL_BLOCKED','regions':REGIONS,'region_actual_support':piece_stats,'neck_sections':necks,'remaining_slabs':len(rows),'blocked_slabs':[r for r in rows if not r['clear_stl']or not r['clear_actual_model']],'rows':rows,'original_slice_report':a.rel(F/'current-review.json'),'original_slice_report_sha256':a.sha(F/'current-review.json'),'current_stl_sha256':state['input']['sha256'],'gcode_sha256':a.sha(F/'plate_1.gcode'),'selected_3mf_sha256':a.sha(F/'slice-review.3mf'),'source_sha256':a.sha(__file__),'sweep_helper_sha256':a.sha(P/'sweep_review.py'),'elapsed_s':time.time()-t0,'interpretation':'The six rectangles define all material that must be separated first. A clear remaining sweep certifies no OTHER under-collar/brace/key branch is geometrically locked in -CAD Z. It does not certify a physical cutting sequence can create those exact six pieces, nor that each piece fits through a hole without trimming. No tool or detachment force claim.'}
 a.dump(OUT/'report.json',rep);print(rep['status'],len(rep['blocked_slabs']),flush=True)
 # CAD front/rear section map, actual support paths and transparent source mesh.
 os.environ['MPLCONFIGDIR']=str(P/'matplotlib-config');import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
 from matplotlib.collections import PolyCollection,LineCollection
 fig,ax=plt.subplots(figsize=(11,7),layout='constrained');cad=a.read_stl(ROOT/state['input']['file']);ax.add_collection(PolyCollection(cad[:,:,[0,2]],facecolors='#7199ad',edgecolors='#335d71',alpha=.22,linewidths=.2))
 paths=[a.g.affine(r.points,np.linalg.inv(M))for r in actual];segs=np.concatenate([np.stack([q[:-1,[0,2]],q[1:,[0,2]]],axis=1)for q in paths]);ax.add_collection(LineCollection(segs,colors='#dd8b28',linewidths=.3,alpha=.55))
 colors=['#b92a36','#b05b00','#873fa8']*2
 for i,r in enumerate(REGIONS):
  x,y,z0=r['lo'];xh,yh,z1=r['hi'];ax.add_patch(plt.Rectangle((x,z0),xh-x,z1-z0,fill=False,color=colors[i],lw=1.5));ax.text((x+xh)/2,z1+.7,r['id'],ha='center',fontsize=8,color=colors[i])
 ax.annotate('Remaining external tree: -CAD Z after 6 regions removed',xy=(0,-168),xytext=(0,-160),ha='center',arrowprops={'arrowstyle':'->'},fontsize=10)
 ax.set_xlim(-55,55);ax.set_ylim(-170,-99);ax.set_aspect('equal');ax.set_xlabel('CAD X / mm');ax.set_ylabel('CAD Z / mm');ax.set_title('Original slice: actual support paths, finite branch-removal regions')
 fig.savefig(OUT/'branch-map.png',dpi=160);plt.close(fig)
if __name__=='__main__':main()
