#!/usr/bin/env python3
"""Whole-support downward swept-prism audit of an existing actual G-code.
No slicing, source editing, physics or plastic separation claim.
"""
from pathlib import Path
import argparse,collections,hashlib,importlib.util,json,math,os,sys,time
import numpy as np
from shapely.geometry import LineString,Polygon,MultiPoint,GeometryCollection
from shapely.ops import unary_union
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'analysis'),str(ROOT/'scripts')]
import cable_input_slice_review as g
from review_cable_slice import read_stl
spec=importlib.util.spec_from_file_location('reuse',ROOT/'output/current-manufacturing/feeder-reuse/review.py');reuse=importlib.util.module_from_spec(spec);spec.loader.exec_module(reuse)
ERR=.002
SKIP={'Custom','Flush','Prime tower','Prime tower infill','Undefined',''}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def rel(p):return str(Path(p).resolve().relative_to(ROOT))
def clip_below(t,z):
 out=[]
 for a,b in zip(t,np.roll(t,-1,axis=0)):
  ina=a[2]<=z;inb=b[2]<=z
  if ina:out.append(a)
  if ina!=inb:out.append(a+(b-a)*((z-a[2])/(b[2]-a[2])))
 return np.array(out)
def surfaces_below(tri,z):
 # Project actual mesh surface pieces below z. This covers every downward
 # ray that could meet the closed solid; degenerate vertical projections
 # are retained as lines/points by convex_hull, never discarded.
 pieces=[]
 for t in tri[tri[:,:,2].min(1)<=z+1e-10]:
  p=clip_below(t,z)
  if len(p):pieces.append(MultiPoint(p[:,:2]).convex_hull)
 return unary_union(pieces)
def main():
 a=argparse.ArgumentParser();a.add_argument('--folder',type=Path,required=True);a.add_argument('--label',required=True);args=a.parse_args();folder=args.folder.resolve();dest=OUT/args.label;dest.mkdir(exist_ok=True)
 inv=json.loads((folder/'invocation.json').read_text());source=ROOT/inv['inputs'][0]['file'];archive=folder/'slice-review.3mf';code=folder/'plate_1.gcode'
 before={rel(p):sha(p)for p in [source,archive,code,folder/'invocation.json',ROOT/'cad/inlet-retention-final.scad']}
 objs,_,arch_sha,_=reuse.archive_models(archive);obj=objs[source.stem];M=np.array(obj['mapping']['current_cad_to_gcode_command']);tri=g.affine(read_stl(source).reshape(-1,3),M).reshape(-1,3,3)
 assert len(inv['inputs'])==1 and arch_sha==sha(code) and abs(np.linalg.det(M[:3,:3])-1)<1e-7
 groups=collections.defaultdict(lambda:collections.defaultdict(list));meta=collections.defaultdict(lambda:collections.defaultdict(list));paths=collections.defaultdict(list);counts=collections.Counter();heights=collections.Counter();t0=time.time()
 for r in g.extrusion_paths(code.open()):
  k='support'if r.feature.startswith('Support')else'brim'if r.feature in ['Brim','Skirt']else'model'if r.feature not in SKIP else None
  if k is None:continue
  # Positive extrusion arcs chord error <= .00125; .002 covers it.
  # quad_segs32 => 128-gon, circumscribe by dividing by cos(pi/128).
  rad=(r.width/2+ERR)/math.cos(math.pi/128)
  top=float(r.points[:,2].max());bottom=float(r.points[:,2].min()-r.height)
  z=round(r.layer,6);groups[z][k].append(LineString(r.points[:,:2]).buffer(rad,quad_segs=32))
  meta[z][k].append((bottom,top,r.line));counts[k]+=1;heights[(k,r.height)]+=1
  if k=='support' or (k=='model'and len(paths[k])%7==0):paths[k].append(r.points)
 for z in groups:
  for k in groups[z]:groups[z][k]=unary_union(groups[z][k])
 print(args.label,'layers',len(groups),'records',dict(counts),flush=True)
 models=[(min(x[0]for x in meta[z]['model']),max(x[1]for x in meta[z]['model']),groups[z]['model'])for z in sorted(groups)if'model'in groups[z]]
 cumulative=Polygon();j=0;rows=[];hits=[]
 for z in sorted(groups):
  if'support'not in groups[z]:continue
  s=groups[z]['support'];bottom=min(x[0]for x in meta[z]['support']);top=max(x[1]for x in meta[z]['support'])
  while j<len(models)and models[j][0]<=top+1e-10:
   cumulative=unary_union([cumulative,models[j][2]]);j+=1
  model_hit=s.intersection(cumulative)
  projection=surfaces_below(tri,top)
  stl_hit=s.intersection(projection)
  row={'print_top_z':top,'print_bottom_z':bottom,'support_area_mm2':s.area,'model_sweep_hit_area_mm2':model_hit.area,'model_sweep_hit_length_mm':model_hit.length if model_hit.area==0 else None,'stl_sweep_hit_area_mm2':stl_hit.area,'stl_sweep_hit_length_mm':stl_hit.length if stl_hit.area==0 else None,'clear_model':model_hit.is_empty,'clear_current_stl':stl_hit.is_empty,'support_line_range':[min(x[2]for x in meta[z]['support']),max(x[2]for x in meta[z]['support'])]}
  if not model_hit.is_empty or not stl_hit.is_empty:
   row['hit_bounds_print_xy']=list(unary_union([model_hit,stl_hit]).bounds);hits.append((z,unary_union([model_hit,stl_hit])))
  rows.append(row)
 print(args.label,'failed slabs',len(hits),flush=True)
 # Actual side/end projections; polygon triangles are source STL, orange
 # polylines are every emitted support path, not an idealized scaffold.
 os.environ['MPLCONFIGDIR']=str(OUT/'matplotlib-config')
 import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
 from matplotlib.collections import PolyCollection,LineCollection
 fig,axs=plt.subplots(1,2,figsize=(13,6),layout='constrained')
 for ax,axes,title in zip(axs,[(0,2),(1,2)],['Front: print X / Z','Side: print Y / Z']):
  ax.add_collection(PolyCollection(tri[:,:,axes],facecolors='#77a5b5',edgecolors='#346477',linewidths=.25,alpha=.38))
  seg=np.concatenate([np.stack([p[:-1,axes],p[1:,axes]],axis=1)for p in paths['support']])
  ax.add_collection(LineCollection(seg,colors='#da8524',linewidths=.25,alpha=.8))
  lo=tri.reshape(-1,3).min(0);hi=tri.reshape(-1,3).max(0)
  allp=np.concatenate(paths['support']);xl=min(lo[axes[0]],allp[:,axes[0]].min());xh=max(hi[axes[0]],allp[:,axes[0]].max())
  ax.set_xlim(xl-8,xh+8);ax.set_ylim(-12,hi[2]+5);ax.set_aspect('equal');ax.set_title(title);ax.set_xlabel('mm');ax.set_ylabel('print Z / mm')
  ax.annotate('Extraction candidate: -print Z',xy=((xl+xh)/2,-9),xytext=((xl+xh)/2,3),ha='center',fontsize=9,arrowprops={'arrowstyle':'->','color':'#a94b13'})
 fig.suptitle(args.label+': current STL (blue), every actual support path (orange)')
 fig.savefig(dest/'actual-support-projections.png',dpi=160);plt.close(fig)
 # Cross-sections where support is largest and where counterexample exists.
 selected=sorted(set([max(rows,key=lambda r:r['support_area_mm2'])['print_top_z']]+[x[0]for x in hits[:3]]+[rows[-1]['print_top_z']]))
 fig,axs=plt.subplots(1,len(selected),figsize=(5*len(selected),5),layout='constrained');axs=np.atleast_1d(axs)
 for ax,z in zip(axs,selected):
  for k,color in [('model','#3c7891'),('support','#da8524')]:
   geom=groups[round(z,6)].get(k,Polygon());parts=[geom]if geom.geom_type=='Polygon'else list(geom.geoms)if hasattr(geom,'geoms')else[]
   for p in parts:
    if p.geom_type=='Polygon':ax.fill(*p.exterior.xy,color=color,alpha=.65)
  for hz,h in hits:
   if abs(hz-z)<1e-7:
    parts=[h]if h.geom_type=='Polygon'else list(h.geoms)if hasattr(h,'geoms')else[]
    for p in parts:
     if p.geom_type=='Polygon':ax.fill(*p.exterior.xy,color='#c82333')
  ax.set_aspect('equal');ax.set_title(f'print Z={z:g} mm');ax.set_xlabel('print X/mm');ax.set_ylabel('print Y/mm')
 fig.suptitle('Actual sections; red is obstruction to entire downward translation')
 fig.savefig(dest/'critical-sections.png',dpi=150);plt.close(fig)
 fullclear=not hits
 rep={'status':'WHOLE_SUPPORT_DOWNWARD_SWEEP_CLEAR_NOMINAL'if fullclear else'WHOLE_SUPPORT_DOWNWARD_SWEEP_BLOCKED','instance_id':'feeder/inlet-rear','source_stl':rel(source),'source_stl_sha256':sha(source),'slice_folder':rel(folder),'selected_3mf':rel(archive),'selected_3mf_sha256':sha(archive),'gcode':rel(code),'gcode_sha256':sha(code),'cad_to_gcode':M.tolist(),'extraction_cad_unit_vector':(-M[:3,:3].T@np.array([0,0,1])).tolist(),'support_record_count':counts['support'],'brim_record_count':counts['brim'],'path_records':dict(counts),'height_values':[{ 'kind':k,'height':h,'count':c}for(k,h),c in heights.items()],'support_slabs':len(rows),'blocked_slabs':len(hits),'all_slabs_clear_of_current_STL_and_actual_model':fullclear,'rows':rows,'source_and_artifact_hashes_before':before,'identities_stable':all(sha(ROOT/p)==h for p,h in before.items()),'algorithm_sha256':sha(__file__),'parser_sha256':sha(ROOT/'analysis/cable_input_slice_review.py'),'elapsed_seconds':time.time()-t0,'method':'Every support extrusion is a circumscribed width+0.002 mm footprint and full recorded height slab. For every slab, intersect its XY footprint with both (a) all model bead footprints whose recorded bottom is below its top, and (b) projections of every current STL surface clipped below that top. Empty intersections prove that the entire support prism union can translate continuously in -printZ until below the part, without assuming branch separation, flexibility, or a thin probe. Slab height simplification is conservative: each same-layer footprint uses the maximum top/minimum bottom of its actual records. Surface line/point projections retained.','limits':['Nominal bead envelope only, not measured PETG.','Contact separation/adhesion force, grip, surface damage and debris are not proven.','Print-bed removal precedes support extraction; no adhesion model.','Clearance does not establish print strength or physical dimensional acceptance.'],'physical_acceptance':False,'sent_to_printer':False}
 dump(dest/'report.json',rep);print(json.dumps({k:rep[k]for k in ['status','blocked_slabs','support_record_count','elapsed_seconds']}),flush=True)
if __name__=='__main__':main()
