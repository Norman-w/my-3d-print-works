#!/usr/bin/env python3
"""Finite cutter-NOSE space candidates, not a purchased-tool or force proof."""
from pathlib import Path
import importlib.util,json,sys,math
import numpy as np
from shapely.geometry import LineString,MultiPoint
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
s=importlib.util.spec_from_file_location('fr',ROOT/'output/current-manufacturing/feeder-new/review.py');f=importlib.util.module_from_spec(s);s.loader.exec_module(f)
F=ROOT/'output/current-manufacturing/feeder-new/runs/20260927T094300899015Z/inlet-rear-anchor-z-down-supported'
def main():
 old=json.loads((F/'current-review.json').read_text());state=old['instances'][0];tri=f.read_stl(ROOT/state['input']['file']);M=np.array(state['actual_mapping']['current_cad_to_gcode_command']);rows=[]
 for sign in [-1,1]:
  x=sign*43
  if sign<0:lo,hi=[-47,-30,-119],[-41,-12.5,-117]
  else:lo,hi=[39.5,-30,-119],[44.7,-12.5,-117]
  rows.append(dict(id='M4_neck_'+str(sign),lo=lo,hi=hi,approach='-Y',cut_plane_CAD_Z=-118))
  for kind,cx,z,rear_y,width in [('M2_5',sign*10.5,-146,-54.1,3.5),('strap',sign*20.5,-137,-48.3,3)]:
   rows.append(dict(id=kind+'_rear_'+str(sign),lo=[cx-width,-65,z-1],hi=[cx+width,rear_y,z+1],approach='-Y',cut_plane_CAD_Z=z))
   w=3.5 if kind=='M2_5' else 2.4
   rows.append(dict(id=kind+'_front_'+str(sign),lo=[cx-w,-41.7,z-1],hi=[cx+w,-28,z+1],approach='+Y',cut_plane_CAD_Z=z))
 for r in rows:
  lo,hi=np.array(r['lo']),np.array(r['hi']);cand=tri[(tri.max(1)>=lo).all(1)&(tri.min(1)<=hi).all(1)]
  r['source_triangle_intersections']=sum(f.shell.clipped_triangle_in_box(t,lo,hi)for t in cand);r['center_inside']=bool(f.inside((lo+hi)/2,tri));q=f.g.affine(f.corners(lo,hi),M);r['_xy']=MultiPoint(q[:,:2]).convex_hull;r['_z']=[q[:,2].min(),q[:,2].max()];r['model_commands']=0;r['support_commands']=0;r['support_lines']=[]
 for rec in f.g.extrusion_paths((F/'plate_1.gcode').open()):
  if rec.feature in f.NONMODEL:continue
  support=rec.feature.startswith('Support');rad=(rec.width/2+.002)/math.cos(math.pi/128);lo=rec.points.min(0)-[rad,rad,rec.height];hi=rec.points.max(0)+[rad,rad,0];foot=None
  for r in rows:
   z0,z1=r['_z'];b=r['_xy'].bounds
   if hi[2]<z0 or lo[2]>z1 or hi[0]<b[0]or lo[0]>b[2]or hi[1]<b[1]or lo[1]>b[3]:continue
   if foot is None:foot=LineString(rec.points[:,:2]).buffer(rad,quad_segs=32)
   if foot.intersects(r['_xy']):
    r['support_commands'if support else'model_commands']+=1
    if support and len(r['support_lines'])<12:r['support_lines'].append(rec.line)
 for r in rows:
  del r['_xy'];del r['_z'];r['nominal_nose_space_clear']=not r['source_triangle_intersections']and not r['center_inside']and not r['model_commands']
 rep={'status':'ALL_DECLARED_NOSE_WINDOWS_CLEAR_WITH_REAL_SUPPORT_PRESENT'if all(r['nominal_nose_space_clear']and r['support_commands']for r in rows)else'NOSE_WINDOW_REVIEW_FLAGGED','windows':rows,'source_stl_sha256':state['input']['sha256'],'gcode_sha256':f.sha(F/'plate_1.gcode'),'script_sha256':f.sha(__file__),'helper_sha256':f.sha(ROOT/'output/current-manufacturing/feeder-new/review.py'),'interpretation':'Each box includes the complete declared nose entry from the exterior to an actual support neck. It is larger than an infinitesimal probe, but is only a design allowance for a cutter nose: jaws, handle, grasp, closing sweep, exact commercial tool and cut force are unverified. These boxes do not imply the six removal pieces have all been detached or can pass unchanged through each bore.'}
 f.dump(P/'nose-access.json',rep);print(rep['status'],[(r['id'],r['model_commands'],r['support_commands'],r['source_triangle_intersections'])for r in rows],flush=True)
if __name__=='__main__':main()
