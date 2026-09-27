#!/usr/bin/env python3
from pathlib import Path
import collections,json,sys,math,hashlib,time
import numpy as np
from shapely.geometry import LineString,Polygon,box,MultiPoint
from shapely.ops import unary_union
from shapely.affinity import translate
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'analysis'))
import cable_input_slice_review as parser
SOURCE=ROOT/'output/current-manufacturing/feeder-new/runs/20260927T094300899015Z/inlet-rear-anchor-z-down-supported'
OUT=Path(__file__).resolve().parent
MODEL_SKIP={'Custom','Flush','Prime tower','Prime tower infill','Undefined','','Brim','Skirt'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def polys(g):return []if g.is_empty else[g]if g.geom_type=='Polygon'else[p for p in g.geoms if p.geom_type=='Polygon']
def main():
 started=time.time();groups=collections.defaultdict(lambda:collections.defaultdict(list));records=collections.Counter()
 for r in parser.extrusion_paths((SOURCE/'plate_1.gcode').open()):
  k='support'if r.feature.startswith('Support')else'brim'if r.feature in ['Brim','Skirt']else'model'if r.feature not in MODEL_SKIP else None
  if k is None:continue
  rad=(r.width/2+.002)/math.cos(math.pi/128)
  groups[round(r.layer,6)][k].append(LineString(r.points[:,:2]).buffer(rad,quad_segs=16));records[k]+=1
 for z in groups:
  for k in list(groups[z]):groups[z][k]=unary_union(groups[z][k])
 print('unioned',len(groups),records,round(time.time()-started,2),flush=True)
 # Fixed .2 mm layers verified separately below; gcode support heights may differ,
 # so retain exact top/bottom metadata in next version for final evidence.
 oldmodel=Polygon();rows=[];bad_down=[];bad_back=[];bad_fwd=[]
 for z in sorted(groups):
  d=groups[z];m=d.get('model',Polygon());s=d.get('support',Polygon());oldmodel=unary_union([oldmodel,m])
  if s.is_empty:continue
  down=s.intersection(oldmodel);back=[];fwd=[]
  for c in polys(s):
   bs=unary_union([c,translate(c,yoff=-100)]).convex_hull;fs=unary_union([c,translate(c,yoff=100)]).convex_hull
   if bs.intersects(m):back.append(c)
   if fs.intersects(m):fwd.append(c)
  b=unary_union(back);f=unary_union(fwd)
  rows.append({'top_print_z':z,'support_components':len(polys(s)),'support_area':s.area,'down_collision_area':down.area,'down_collision_bounds':list(down.bounds)if not down.is_empty else None,'back_nonclear_components':len(back),'fwd_nonclear_components':len(fwd)})
  if not down.is_empty:bad_down.append(down)
  if not b.is_empty:bad_back.append(b)
  if not f.is_empty:bad_fwd.append(f)
 rep={'gcode_sha256':sha(SOURCE/'plate_1.gcode'),'rows':rows,'path_records':dict(records),'down_bad_projection_bounds':list(unary_union(bad_down).bounds),'elapsed_s':time.time()-started,'scope':'diagnostic only; not full rigid connected support extraction proof'}
 dump(OUT/'direction-diagnostic.json',rep)
 import pickle
 with(OUT/'layer-polygons.pickle').open('wb')as f:pickle.dump(dict(groups),f)
 print('done',len(rows),'downclear',sum(r['down_collision_area']<1e-8 for r in rows),'elapsed',rep['elapsed_s'],flush=True)
if __name__=='__main__':main()
