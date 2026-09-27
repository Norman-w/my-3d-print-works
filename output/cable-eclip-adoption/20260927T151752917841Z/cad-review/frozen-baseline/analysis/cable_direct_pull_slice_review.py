#!/usr/bin/env python3
"""Actual-layer review for frozen direct-pull lever/cap; no old wrap-slot ROIs.
Read-only offline inspection. No CAD edits, slicer execution, or print action.
"""
from pathlib import Path
import argparse,collections,hashlib,json,math,os,sys
import numpy as np
from shapely.geometry import LineString,Point,Polygon,box
from shapely.ops import unary_union
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'analysis'))
import cable_flat_slice_review as flat
import cable_input_slice_review as parser
SOURCE=ROOT/'output/cable-input-lip-candidate/candidate.scad'
EXPECTED='491ded77149a2147f010092f7f715f59ef50a2dd714abb56677d596fb6544c9d'
ERROR=parser.ARC_ERROR+parser.BUFFER_ERROR
NONMODEL={'Custom','Brim','Skirt','Prime tower','Prime tower infill','Flush','Undefined',''}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def path(p):p=Path(p);return p if p.is_absolute()else ROOT/p
def dump(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def model(f):return f not in NONMODEL and not f.startswith('Support')
def phi(a):
 x=60*math.sin(a)+28.8;y=60*math.cos(a);return max(0,math.atan2(x,y)-math.acos(60/math.hypot(x,y)))
def takeup(a):
 x=60*math.sin(a)+28.8;y=60*math.cos(a);return .2+60*phi(a)+math.sqrt(x*x+y*y-3600)-29

def angle(u):
 lo,hi=0.,math.radians(30)
 for _ in range(48):
  m=(lo+hi)/2
  if takeup(m)<u:lo=m
  else:hi=m
 return(lo+hi)/2

def wire(u):
 a=angle(u);p=phi(a);T=np.array([-28.8+60*math.sin(p),60*math.cos(p)]);R=np.array([[math.cos(a),-math.sin(a)],[math.sin(a),math.cos(a)]]);end=R@T;start=np.array([0.,60.]);L=float(np.linalg.norm(end-start));near=start+(end-start)*min(12/L,1)
 return {'u_mm':u,'angle_deg':math.degrees(a),'tangent_phi_deg':math.degrees(p),'takeup_residual_mm':takeup(a)-u,'terminal_segment_length_mm':min(12,L),'from_local':[*start,2.],'to_local':[*near,2.],'line':LineString([start,near]),'minimum_bead_clearance_lower_mm':math.inf,'possible_intrusion_commands':0,'examples':[]}

def clear_radius(rows,c):
 d=[r['line'].distance(Point(c))-r['width']/2-ERROR for r in rows if model(r['feature'])];return min(d,default=None)
def foot(rows,extra):return unary_union([r['line'].buffer(max(.00001,r['width']/2+extra),resolution=32)for r in rows if model(r['feature'])])

def run(folder):
 folder=folder.resolve();inv=json.loads((folder/'invocation.json').read_text());part=inv['part'];assert part in ['cable-input-lever','cable-input-terminal-cap'];assert sha(SOURCE)==EXPECTED==inv['diagnostic_candidate']['source_sha256']
 for p,h in inv['source_sha256_at_start'].items():assert path(p).is_file()and sha(path(p))==h,f'Source drift: {p}'
 assert sha(path(inv['input']['file']))==inv['input']['sha256']
 for p,h in inv['artifact_sha256'].items():assert sha(folder/p)==h
 cad_to_command,meta=flat.mapping(folder,inv);s=math.sqrt(.5);L=np.array([[-s,s,0,75],[0,0,1,-82],[s,s,0,5],[0,0,0,1.]])
 local_to_command=cad_to_command@L;inverse=np.linalg.inv(local_to_command);sign=float(local_to_command[2,2]);assert abs(abs(sign)-1)<1e-8 and np.allclose(local_to_command[2,:2],0,atol=1e-8)
 islever=part=='cable-input-lever';assert(sign>0)==islever;assert abs(local_to_command[2,3]-(3.5 if islever else 7.5))<1e-6
 out=folder/'direct-pull-path-review';out.mkdir(exist_ok=True);layers=collections.defaultdict(list);counts=collections.Counter();wires=[wire(u)for u in [0,10,20,22]];ball={'diameter_mm':5,'center_local':[0,60,2],'minimum_bead_clearance_lower_mm':math.inf,'possible_intrusion_commands':0,'examples':[]};terminal_slabs=[]
 with (folder/'plate_1.gcode').open()as f:
  for r in parser.extrusion_paths(f):
   counts[r.feature]+=1
   if not np.allclose(r.points[:,2],r.layer,atol=1e-5):
    if model(r.feature):raise ValueError('Non-planar deposition requires dedicated review')
    continue
   q=parser.affine(r.points,inverse);shift=inverse[:3,:3]@np.array([0,0,-r.height]);z0,z1=sorted([float(q[0,2]),float(q[0,2]+shift[2])]);ln=LineString(q[:,:2]);width=r.width
   if not ln.buffer(width/2+ERROR,resolution=8).intersects(box(-14,46,9,74)):continue
   row={'line':ln,'xy':q[:,:2],'feature':r.feature,'width':width,'height':r.height,'zlo':z0,'zhi':z1,'gcode_line':r.line,'print_top':r.layer};layers[round(r.layer,6)].append(row)
   if not model(r.feature):continue
   if ln.buffer(width/2+ERROR,resolution=8).intersects(box(-5,51,5,69)):terminal_slabs.append([z0,z1])
   dz=max(z0-2,2-z1,0)
   if dz<=2.5:
    br=math.sqrt(max(0,2.5**2-dz**2));gap=ln.distance(Point(0,60))-width/2-ERROR-br;ball['minimum_bead_clearance_lower_mm']=min(ball['minimum_bead_clearance_lower_mm'],gap)
    if gap<0:
     ball['possible_intrusion_commands']+=1
     if len(ball['examples'])<8:ball['examples'].append({'line':r.line,'print_top':r.layer,'local_z_slab':[z0,z1],'feature':r.feature,'clearance_lower_mm':gap})
   if dz<=.75:
    wr=math.sqrt(max(0,.75**2-dz**2))
    for w in wires:
     gap=ln.distance(w['line'])-width/2-ERROR-wr;w['minimum_bead_clearance_lower_mm']=min(w['minimum_bead_clearance_lower_mm'],gap)
     if gap<0:
      w['possible_intrusion_commands']+=1
      if len(w['examples'])<8:w['examples'].append({'line':r.line,'print_top':r.layer,'local_z_slab':[z0,z1],'feature':r.feature,'clearance_lower_mm':gap})
 holes=[]
 for c in [(2,54),(2,66)]:
  rows=[]
  for z,records in sorted(layers.items()):
   localrows=[r for r in records if r['line'].distance(Point(c))<5]
   if not localrows:continue
   radius=clear_radius(localrows,c);heights=sorted(set(r['height']for r in localrows if model(r['feature'])))
   if radius is None:continue
   rows.append({'print_top_mm':z,'bead_heights_mm':heights,'clear_radius_lower_mm':radius,'clear_diameter_lower_mm':2*radius,'local_z_slab_bounds_mm':[min(r['zlo']for r in localrows),max(r['zhi']for r in localrows)],'features':dict(collections.Counter(r['feature']for r in localrows))})
  nominal=2.9 if islever else 3.0;small=[r for r in rows if r['clear_radius_lower_mm']<2.3];assert small;first=small[0]
  # Native layer phase is measured by the preceding actual toolpath layer, not
  # an assumed multiple of the profile height. Transition row heights retained.
  prior=[r for r in rows if r['print_top_mm']<first['print_top_mm']-1e-6];assert prior
  plane=prior[-1]['print_top_mm'];assert prior[-1]['clear_radius_lower_mm']>2.7
  holes.append({'center_local_xy':list(c),'name':'M3/nut pocket'if islever else'M3/socket-head recess','nominal_transition_print_mm':nominal,'actual_transition_print_mm':plane,'transition_error_mm':round(plane-nominal,8),'first_small_hole_layer_top_mm':first['print_top_mm'],'small_hole_min_clear_diameter_lower_mm':min(r['clear_diameter_lower_mm']for r in small),'large_recess_min_inscribed_diameter_lower_mm':min(r['clear_diameter_lower_mm']for r in prior),'layers':rows})
 hardware=[]
 for c in [(2,54),(2,66)]:
  specs=[('M3_rod',-3.5,4.5,1.5,None)]
  if islever:
   rr=5.5/(2*math.cos(math.pi/6));poly=Polygon([(c[0]+rr*math.cos(math.pi/6+k*math.pi/3),c[1]+rr*math.sin(math.pi/6+k*math.pi/3))for k in range(6)])
   specs.append(('M3_nut_SW5_5_rotation30',-3.,-.6,None,poly))
  else:specs.append(('M3_socket_head',4.5,7.5,2.75,None))
  for name,zlo,zhi,rad,poly in specs:
   min_gap=math.inf;hits=0;examples=[];touch=0;min_row=None
   for rows in layers.values():
    for rec in rows:
     if not model(rec['feature']):continue
     overlap=min(zhi,rec['zhi'])-max(zlo,rec['zlo'])
     # Source-declared mating roof at -.6 / head shoulder4.5. Coordinate
     # differences below one G-code Z precision unit are plane contact only;
     # no zero-thickness roof sheet is counted as a solid bead/metal overlap.
     if overlap<=1e-6:
      if abs(overlap)<=1e-6:touch+=1
      continue
     distance=rec['line'].distance(poly)if poly is not None else rec['line'].distance(Point(c))-rad
     gap=distance-rec['width']/2-ERROR
     if gap<min_gap:
      min_gap=gap;min_row={'gcode_line':rec['gcode_line'],'print_top_mm':rec['print_top'],'local_z_slab_mm':[rec['zlo'],rec['zhi']],'feature':rec['feature']}
     if gap<0:
      hits+=1
      if len(examples)<5:examples.append({**min_row,'clearance_lower_mm':gap})
   hardware.append({'name':name,'center_local_xy':list(c),'local_z_interval_mm':[zlo,zhi],'radius_mm':rad,'hex_vertices_local_xy':list(poly.exterior.coords)[:-1]if poly is not None else None,'minimum_bead_clearance_lower_mm':min_gap if math.isfinite(min_gap)else None,'closest_command':min_row,'possible_intrusion_commands':hits,'boundary_plane_contact_commands_excluded':touch,'examples':examples})
 split=max(z[1]for z in terminal_slabs)if islever else min(z[0]for z in terminal_slabs)
 # Plot actual local layer paths at nut/recess transition, sphere, and split.
 desired=([2.9,3.0,4.4,5.5,6.5,6.6]if islever else[.2,2.7,3.0,3.1,4.3,4.4]);chosen=sorted(set(min(layers,key=lambda z:abs(z-v))for v in desired))
 os.environ.setdefault('MPLCONFIGDIR',str(out/'mpl'));import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
 from matplotlib.collections import LineCollection
 from matplotlib.patches import Circle
 fig,axs=plt.subplots(2,3,figsize=(14,10),layout='constrained');colors={'Outer wall':'#155c7a','Inner wall':'#4b98b2','Top surface':'#6c983d','Bottom surface':'#79a043','Bridge':'#dc7722','Overhang wall':'#cf4242','Internal solid infill':'#aac19a'}
 for ax,z in zip(axs.flat,chosen):
  ax.set_xlim(-12,9);ax.set_ylim(47,73);ax.set_aspect('equal');ax.grid(alpha=.15);ax.set_title(f'{part}\nPrint Z {z:g} / local bead {min(r["zlo"]for r in layers[z]):.2f}…{max(r["zhi"]for r in layers[z]):.2f}');ax.set_xlabel('Input lever local X / mm');ax.set_ylabel('Input lever local Y / mm')
 fig.canvas.draw()
 for ax,z in zip(axs.flat,chosen):
  scale=(ax.transData.transform([1,0])-ax.transData.transform([0,0]))[0]*72/fig.dpi
  for r in layers[z]:
   if model(r['feature']):ax.add_collection(LineCollection([r['xy']],colors=colors.get(r['feature'],'#929aa0'),linewidths=r['width']*scale,capstyle='round'))
  for c in [(2,54),(2,66)]:ax.add_patch(Circle(c,1.7,fill=False,color='#ad318a',ls=':',lw=.7))
  ax.add_patch(Circle((0,60),2.5,fill=False,color='#ad318a',ls=':',lw=.7))
  for w in wires:
   xy=np.array(w['line'].coords);ax.plot(xy[:,0],xy[:,1],':',lw=.7,color='#d03896')
 fig.suptitle('Actual bead widths near direct-pull terminal; magenta: nominal holes/ball projection/four cable directions');fig.savefig(out/'terminal-key-layers.png',dpi=160);plt.close(fig)
 for w in wires:
  w.pop('line');
  if not math.isfinite(w['minimum_bead_clearance_lower_mm']):w['minimum_bead_clearance_lower_mm']=None;w['reason']='No printed layer slab intersects wire Z[1.25,2.75]'
 if not math.isfinite(ball['minimum_bead_clearance_lower_mm']):ball['minimum_bead_clearance_lower_mm']=None
 source_stable=all(path(p).is_file()and sha(path(p))==v for p,v in inv['source_sha256_at_start'].items())
 result={'status':'BOUNDED_NEW_TERMINAL_PATH_REVIEW','part':part,'source_snapshot_stable':source_stable,'source_sha256':EXPECTED,'mapping':meta,'local_to_command':local_to_command.tolist(),'local_print_growth_sign':sign,'split_plane':{'nominal_local_z':3.1,'actual_terminal_bead_extreme_local_z':split,'error_mm':round(split-3.1,8),'terminal_xy_witness':[[-5,51],[5,69]]},'fastener_holes':holes,'new_feature_contract':{'ball_pocket_center_local':[0,60,2],'ball_pocket_nominal_diameter_mm':5.6,'split_local_z_mm':3.1,'fan_local_z_mm':[.9,3.2],'fan_offset_mm':1.11,'cap_bolts_local_xy':[[2,54],[2,66]]},'fastener_metal_envelopes':hardware,'ball_envelope':ball,'wire_terminal_envelopes':wires,'wire_scope':'Each source-derived current terminal-to-tangent segment is transformed into rotating lever coordinates; only first 12 mm from ball centre, capsule diameter1.5. No old R60 wrap-slot ROI or u/60 angle assumption.','feature_counts':dict(counts),'support_commands':sum(n for f,n in counts.items()if f.startswith('Support')),'bead_xy_error_bound_mm':ERROR,'sampled_layers':chosen,'artifact_sha256':{n:sha(folder/n)for n in ['invocation.json','plate_1.gcode','slice-review.3mf']},'script_sha256':sha(__file__),'parser_sha256':sha(ROOT/'analysis/cable_input_slice_review.py'),'mapping_helper_sha256':sha(ROOT/'analysis/cable_flat_slice_review.py'),'limits':['All layer slabs use each command declared bead height, including bridge height, and actual local-Z orientation. XY swept disks use declared width with arc/buffer error; not PETG dimensions.','Positive clearance certifies only the stated ideal constant-height wire capsule or nominal sphere against the conservative emitted-bead slab envelope. Four discrete u values are not a continuous motion proof.','Negative lower clearance is possible contact under an over-covering slab projection, not automatically proven physical interference; bridge sag and wire bending are not modeled.','Circular opening measurements are supplemented by exact nominal SW5.5 hex polygon at30 degrees, nominal M3 rod/head cylinders and actual layer-slab overlap. No manufactured tolerance, torque, retention force or loaded-return proof.','Printed local split extremes do not prove flatness, tightening preload or bond strength. Candidate remains isolated.'],'manufacturing_release':False,'physical_acceptance':False,'sent_to_printer':False}
 dump(out/'report.json',result);print(json.dumps({k:result[k]for k in ['part','split_plane','ball_envelope','wire_terminal_envelopes','support_commands']},ensure_ascii=False,indent=2));return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--folder',type=Path,required=True);a=p.parse_args();run(a.folder)
