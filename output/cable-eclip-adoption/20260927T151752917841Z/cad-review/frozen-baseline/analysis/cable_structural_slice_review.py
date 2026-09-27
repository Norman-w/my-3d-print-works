#!/usr/bin/env python3
"""Read-only actual slice audit for structural cable parts. Never slices or edits CAD."""
from pathlib import Path
import argparse,collections,hashlib,json,math,os,re,struct,sys,zipfile,xml.etree.ElementTree as ET
import numpy as np
from shapely.geometry import LineString,Polygon,box
from shapely.ops import unary_union
from scipy.spatial import cKDTree
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import review_integrated_shell_slice as helper
helper.np=np;helper.struct=struct
NS={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
P='{http://schemas.microsoft.com/3dmanufacturing/production/2015/06}'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
def bounds(q):return [q.min(0).tolist(),q.max(0).tolist()]if len(q)else None
def matrix(s):
 v=np.array(list(map(float,s.split())))if s else np.array([1,0,0,0,1,0,0,0,1,0,0,0]);m=np.eye(4);m[:3,:3]=v[:9].reshape(3,3).T;m[:3,3]=v[9:];return m

def mapping(folder,inv):
 with zipfile.ZipFile(folder/'slice-review.3mf')as z:
  main=ET.fromstring(z.read('3D/3dmodel.model'));settings=ET.fromstring(z.read('Metadata/model_settings.config'))
  builds=main.findall('./m:build/m:item',NS);assert len(builds)==1
  build=builds[0];oid=build.attrib['objectid'];obj=next(o for o in main.findall('./m:resources/m:object',NS)if o.attrib['id']==oid)
  components=obj.findall('./m:components/m:component',NS);assert len(components)==1
  comp=components[0];parts=settings.find(f"./object[@id='{oid}']").findall('./part');assert len(parts)==1
  part=parts[0];meta={n.attrib.get('key'):n.attrib.get('value')for n in part.findall('./metadata')}
  model=ET.fromstring(z.read(comp.attrib[P+'path'].lstrip('/')));meshobj=next(n for n in model.findall('./m:resources/m:object',NS)if n.attrib['id']==comp.attrib['objectid'])
  vertices=np.array([[float(n.attrib[a])for a in 'xyz']for n in meshobj.findall('./m:mesh/m:vertices/m:vertex',NS)])
  indices=np.array([[int(n.attrib[a])for a in ['v1','v2','v3']]for n in meshobj.findall('./m:mesh/m:triangles/m:triangle',NS)])
  mesh=vertices[indices]
 c,b=matrix(comp.attrib.get('transform')),matrix(build.attrib.get('transform'))
 o=np.array([float(meta['source_offset_'+a])for a in 'xyz']);offset=np.eye(4);offset[:3,3]=-o
 header=(folder/'plate_1.gcode').read_text();raw=re.search(r'^; extruder_offset = ([^\n]+)',header,re.M);assert raw
 nozzle=np.array([*map(float,raw[1].split(',')[0].split('x')),0.]);nm=np.eye(4);nm[:3,3]=-nozzle
 oriented=np.array(inv['cad_to_oriented']);total=nm@b@c@offset@oriented
 source_mesh=helper.read_mesh(Path(inv['oriented']['file']))
 # Directly compare actual archived component triangles in source coordinates.
 archive_source=mesh+o
 # Nearest vertex assignment is bijective; face connectivity and winding must
 # match after face-order/cyclic-vertex normalization. Decimal rounding alone
 # can give a false mismatch when two equal coordinates straddle a bin boundary.
 u,ai=np.unique(source_mesh.reshape(-1,3),axis=0,return_inverse=True)
 d,bi=cKDTree(u).query(archive_source.reshape(-1,3))
 def canonical_faces(ix):
  f=ix.reshape(-1,3);f=np.array([np.roll(row,-int(np.argmin(row)))for row in f]);return f[np.lexsort((f[:,2],f[:,1],f[:,0]))]
 bijective=len(set(bi))==len(u) and len(np.unique(archive_source.reshape(-1,3),axis=0))==len(u)
 connectivity=len(source_mesh)==len(mesh) and np.array_equal(canonical_faces(ai),canonical_faces(bi))
 parity=bijective and connectivity and bool((d<=1e-4).all())

 return total,{'cad_to_oriented':oriented.tolist(),'source_offset':o.tolist(),'component':c.tolist(),'build':b.tolist(),'extruder_offset':nozzle.tolist(),'cad_to_gcode':total.tolist(),'mesh_stat':part.find('./mesh_stat').attrib,'input_triangles':len(source_mesh),'archived_triangles':len(mesh),'archived_triangle_vertex_multiset_matches_at_0_0001_mm':bool(parity),'vertex_matching_bijective':bool(bijective),'oriented_face_connectivity_and_winding_preserved':bool(connectivity),'maximum_vertex_difference_mm':float(d.max()),'archived_zero_area_triangles':int(np.sum(np.linalg.norm(np.cross(mesh[:,1]-mesh[:,0],mesh[:,2]-mesh[:,0]),axis=1)==0))}

def inside(p,t):
 d=np.array([1.,.137123,.213731]);e1=t[:,1]-t[:,0];e2=t[:,2]-t[:,0];h=np.cross(np.broadcast_to(d,e2.shape),e2);a=np.einsum('ij,ij->i',e1,h);ok=abs(a)>1e-10;f=np.zeros(len(t));f[ok]=1/a[ok];s=p-t[:,0];u=f*np.einsum('ij,ij->i',s,h);q=np.cross(s,e1);v=f*(q@d);z=f*np.einsum('ij,ij->i',e2,q);hits=z[ok&(u>=0)&(v>=0)&(u+v<=1)&(z>1e-9)];return len(set(np.round(hits,7)))%2==1

def feature_boxes(part,t):
 rows=[]
 def add(name,lo,hi,access,corridor=False):rows.append({'name':name,'lo':lo,'hi':hi,'access':access,'corridor':corridor})
 if part=='beam-grip':
  for x in [-16,16]:
   for zz in [-60,3]:add(f'M4_mount_{x}_{zz}',[x-1,-60,zz-1],[x+1,-42,zz+1],'Through Y, 2 x 2 mm nominal pick core',True)
  for x in [-10.5,10.5]:add(f'strap_slot_{x}',[x-.8,-67,-151],[x+.8,-43,-133],'Open through Y; clean before feeding strap',True)
  add('M6_bridge_bore',[-59.5,34,76],[-56.5,37,100],'Through Z, 3 x 3 mm nominal pick core',True)
  add('lower_wrench_entry',[-59,34.5,81.5],[-15,36.5,83.5],'Open +X, 2 x 2 mm nominal pick tip; not entire wrench',True)
  add('platform_underside',[-70,-52,84.7],[-46,45,85.05],'Broad underside around M6 seat, accessible before hardware')
  add('strain_relief_channel',[-15,-62,-156],[15,-54,-66],'Open back -Y; remove trees before hose/strap')
 elif part=='frame':
  for x in [-62.5,-51]:add(f'cap_M3_{x}',[x-.8,22,25.2],[x+.8,45,26.8],'Through Y, 1.6 x 1.6 mm nominal pick core',True)
  add('nipple_bore',[-59,31.9,13.7],[-57,43,15.7],'Open +Y before cap/washer; 2 x 2 mm nominal pick core',True)
  add('open_wire_slot',[-58.5,35,5],[-57.5,38.5,31],'Open below lug (-Z) and +Y; 1 x 3.5 mm nominal pick',True)
  add('washer_recess',[-62.9,38.8,9.8],[-53.1,39.22,19.6],'Open +Y before cap, preserve bearing rim')
  # Actual closed cam-slot mouths recovered from the exported planar face.
  face=unary_union([Polygon(v[:,[0,2]])for v in t[(abs(t[:,:,1]-8)<1e-5).all(1)]if Polygon(v[:,[0,2]]).area>1e-10])
  holes=[Polygon(i)for p in ([face]if face.geom_type=='Polygon'else getattr(face,'geoms',[]))for i in p.interiors]
  for j,h in enumerate(holes):
   x0,z0,x1,z1=h.bounds;add(f'cam_slot_{j+1}',[x0,7.8,z0],[x1,13.2,z1],'Through Y; clean both mouths before pins')
   p=h.representative_point();add(f'cam_slot_pick_{j+1}',[p.x-.7,3,p.y-.7],[p.x+.7,18,p.y+.7],'Through Y, 1.4 x 1.4 mm nominal pick core',True)
  for side in [-1,1]:add(f'guide_rail_side{side}',[53.9 if side>0 else -59,19.9,-35],[59 if side>0 else -53.9,24.1,5],'Exposed sliding datum; all support residue must be removed')
 elif part=='cable-route-base':
  for x in [-73,-43]:
   for y in [-12,12]:add(f'clamp_M3_{x}_{y}',[x-.7,y-.7,78],[x+.7,y+.7,106],'Through Z, 1.4 x 1.4 mm nominal pick core',True)
  add('platform_capture',[-70.25,-52.25,84.72],[-45.75,45.25,93.28],'Open -Z before lower托; never scrape hard-stop faces')
  add('long_braces',[-80,50,99],[-35,90,180],'External braces; remove support before placing housing')
 return rows

def run(folder):
 inv=json.loads((folder/'invocation.json').read_text());assert inv['part']in ['beam-grip','frame','cable-route-base'];part=inv['part'];out=folder/'structural-review';out.mkdir(exist_ok=True)
 mat,mp=mapping(folder,inv);R=mat[:3,:3];tr=mat[:3,3];assert np.allclose(R.T@R,np.eye(3),atol=1e-8)
 source=ROOT/inv['input']['file'];t=helper.read_mesh(source);items=feature_boxes(part,t)
 machine=json.loads((folder/'machine.json').read_text());poly=lambda xs:Polygon([list(map(float,x.split('x')))for x in xs]);bed=poly(machine['printable_area']);exclude=poly(machine['bed_exclude_area']);height=float(machine['printable_height'])
 zmax=float((t.reshape(-1,3)@R.T+tr)[:,2].max());selected=np.array(sorted(set([.2]+[round(max(.2,zmax*f)/.2)*.2 for f in [.08,.2,.35,.5,.7,.85,.98]])))
 for v in items:
  lo,hi=np.array(v['lo']),np.array(v['hi']);v['support_envelope_samples']=0;v['support_center_samples']=0;v['support_hit_bounds']=None;v['model_commands_flagged_by_conservative_box']=0
  if v['corridor']:
   cand=t[(t.max(1)>=lo).all(1)&(t.min(1)<=hi).all(1)];v['stl_triangle_intersections']=sum(helper.clipped_triangle_in_box(q,lo,hi)for q in cand);v['center_inside_stl']=bool(inside((lo+hi)/2,t))
 counts=collections.Counter();groups=collections.defaultdict(list);first=[];firstsup=[];firstall=[];sup=[];swidth=[];sheight=[];extrusion_lo=np.array([np.inf]*3);extrusion_hi=-extrusion_lo;violations=[];bridges=[];support_layers=collections.Counter();model_layers=collections.Counter()
 for layer,lh,feature,width,p in helper.paths(folder/'plate_1.gcode'):
  counts[feature]+=1;support=feature.startswith('Support');is_model=not support and feature not in ['Skirt','Brim','Prime tower','Custom']
  # The reused sampler caps arc angle at .1 rad and segment arc length at 1/.1 mm.
  # Worst chord sagitta <= .5*step*tan(.025): .012503 model, .001251 support.
  sag=.001251 if support else .012504;rr=width/2+sag
  lo=p.min(0)-[rr,rr,lh];hi=p.max(0)+[rr,rr,0];extrusion_lo=np.minimum(extrusion_lo,lo);extrusion_hi=np.maximum(extrusion_hi,hi)
  if lo[0]<0 or lo[1]<0 or hi[0]>256 or hi[1]>256 or lo[2]<-1e-6 or hi[2]>height:
   violations.append({'feature':feature,'layer':layer,'kind':'build_bounds','bounds':[lo.tolist(),hi.tolist()]})
  if not exclude.is_empty and box(lo[0],lo[1],hi[0],hi[1]).intersects(exclude):
   if LineString(p[:,:2]).buffer(rr,quad_segs=12).intersects(exclude):violations.append({'feature':feature,'layer':layer,'kind':'bed_exclude'})
  if abs(layer-.2)<1e-6:
   foot=LineString(p[:,:2]).buffer(width/2,quad_segs=12);firstall.append(foot)
   if is_model:first.append(foot)
   if support:firstsup.append(foot)
  if any(abs(layer-z)<1e-6 for z in selected):groups[round(layer,5)].append((feature,p))
  if feature=='Bridge':bridges.append(float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum()))
  if is_model:model_layers[round(layer,5)]+=1
  if support:
   support_layers[round(layer,5)]+=1;center=(p-[0,0,lh/2]-tr)@R;half=np.array([width/2+.051252,width/2+.051252,lh/2])@abs(R)
   sup.append(center);swidth.append(np.full(len(center),width));sheight.append(np.full(len(center),lh))
   for v in items:
    vl,vh=np.array(v['lo']),np.array(v['hi']);mask=((center+half>=vl)&(center-half<=vh)).all(1);v['support_envelope_samples']+=int(mask.sum());v['support_center_samples']+=int(((center>=vl)&(center<=vh)).all(1).sum())
    if mask.any():
     bb=np.array(bounds(center[mask]));old=v['support_hit_bounds'];v['support_hit_bounds']=bb.tolist()if old is None else [np.minimum(old[0],bb[0]).tolist(),np.maximum(old[1],bb[1]).tolist()]
  elif is_model:
   # Inverse mapped bead AABBs: conservative corridor contact flags only.
   a=(p-[0,0,lh/2]-tr)@R;half=np.array([width/2+.512504,width/2+.512504,lh/2])@abs(R)
   for v in items:
    if v['corridor'] and ((a+half>=v['lo'])&(a-half<=v['hi'])).all(1).any():v['model_commands_flagged_by_conservative_box']+=1
 q=np.concatenate(sup)if sup else np.empty((0,3));w=np.concatenate(swidth)if sup else np.empty(0);lh=np.concatenate(sheight)if sup else np.empty(0)
 route_features=None
 if part=='cable-route-base':
  inventory=ROOT/'docs/cable-assembly-inventory.json';ic=json.loads(inventory.read_text())['scene_contract']['cr'];arc=ic['arcs'][2]
  C=np.array(arc[2]);U=np.array(arc[3]);V=np.array(arc[4]);U=U/np.linalg.norm(U);V=V-np.dot(V,U)*U;V=V/np.linalg.norm(V);N=np.cross(U,V);B=np.column_stack([U,V,N]);local=(q-C)@B
  half=np.column_stack([w/2+.0533,w/2+.0533,lh/2])@abs(R@B)
  radius=np.linalg.norm(local[:,:2],axis=1);a=np.degrees(np.arctan2(local[:,1],local[:,0]));radial_half=np.linalg.norm(half[:,:2],axis=1)
  # Rounded echo basis is explicitly padded 0.002 mm; coarse flags only.
  groove=(abs(radius-ic['arc_radius'])<=3.1+radial_half)&(a>=-2)&(a<=arc[5]+2)&(local[:,2]+half[:,2]>=-3.1)&(local[:,2]-half[:,2]<=0)
  center=(abs(radius-ic['arc_radius'])<=3.1)&(a>=0)&(a<=arc[5])&(local[:,2]>=-3.1)&(local[:,2]<=0)
  bolts=[]
  for deg in [10,70,137]:
   for rad in [63,87]:
    pp=np.array([rad*math.cos(math.radians(deg)),rad*math.sin(math.radians(deg))]);d=np.linalg.norm(local[:,:2]-pp,axis=1)
    mask=(d<=1.75+radial_half)&(local[:,2]+half[:,2]>=-7)&(local[:,2]-half[:,2]<=0)
    nut=(d<=3.35+radial_half)&(local[:,2]+half[:,2]>=-7)&(local[:,2]-half[:,2]<=-3.98)
    bolts.append({'angle_deg':deg,'radius_mm':rad,'bore_support_envelope_samples':int(mask.sum()),'nut_entry_support_envelope_samples':int(nut.sum())})
  route_features={'inventory_sha256':sha(inventory),'basis_scope':'rounded SCAD echo, reorthogonalized and extra 0.002 mm envelope margin; diagnostic flags, not clearance proof','groove_arc_support_envelope_samples':int(groove.sum()),'groove_arc_support_center_samples':int(center.sum()),'groove_hit_bounds_CAD':bounds(q[groove]),'bolt_holes_and_open_back_nut_pockets':bolts,'cleaning_direction':'+N open semicircular groove with cap separate; six nut pockets from -N, then through bores; do not trap residue by fitting cap/hose first'}
 fp=unary_union(first);fsp=unary_union(firstsup);fap=unary_union(firstall)
 os.environ.setdefault('MPLCONFIGDIR',str(out/'mpl'));import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
 from matplotlib.collections import LineCollection
 from matplotlib.patches import Rectangle
 fig,axes=plt.subplots(2,4,figsize=(16,8),layout='constrained')
 for ax,z in zip(axes.flat,selected):
  for support,color in [(False,'#24668e'),(True,'#e39626')]:
   seg=[np.stack([p[:-1,:2],p[1:,:2]],1)for f,p in groups[round(z,5)]if f.startswith('Support')==support]
   if seg:ax.add_collection(LineCollection(np.concatenate(seg),colors=color,linewidths=.45))
  ax.set_xlim(extrusion_lo[0]-2,extrusion_hi[0]+2);ax.set_ylim(extrusion_lo[1]-2,extrusion_hi[1]+2);ax.set_aspect('equal');ax.set_title(f'Actual print Z={z:g} mm');ax.grid(alpha=.15)
 fig.suptitle(part+': model/brim (blue), supports (orange)');fig.savefig(out/'layer-paths.png',dpi=140);plt.close(fig)
 fig,axes=plt.subplots(1,3,figsize=(16,6),layout='constrained');edges=np.concatenate([t[:,[0,1]],t[:,[1,2]],t[:,[2,0]]])
 for ax,(a,b)in zip(axes,[(0,2),(1,2),(0,1)]):
  ax.add_collection(LineCollection(edges[:,:,[a,b]],colors='#24668e',linewidths=.15,alpha=.4));n=max(1,len(q)//50000)
  if len(q):ax.scatter(q[::n,a],q[::n,b],s=.3,c='#e39626',alpha=.45)
  for v in items:ax.add_patch(Rectangle((v['lo'][a],v['lo'][b]),v['hi'][a]-v['lo'][a],v['hi'][b]-v['lo'][b],fill=False,color='#944491',lw=.4))
  ax.autoscale();ax.set_aspect('equal');ax.set_xlabel('XYZ'[a]+' CAD mm');ax.set_ylabel('XYZ'[b]+' CAD mm');ax.grid(alpha=.15)
 fig.suptitle(part+': CAD (blue), actual supports (orange), reviewed feature bounds (purple)');fig.savefig(out/'support-access.png',dpi=140);plt.close(fig)
 plate=inv['native_result']['sliced_plates'][0]
 check={'slice_success_no_native_warning':inv['return_code']==0 and inv['native_result']['return_code']==0 and not plate['warning_message'],'input_source_identity_current':sha(source)==inv['input']['sha256'] and all((ROOT/p).is_file()and sha(ROOT/p)==h for p,h in inv['source_sha256_at_start'].items()),'oriented_identity':sha(inv['oriented']['file'])==inv['oriented']['sha256'],'archive_triangle_count_exact':mp['input_triangles']==mp['archived_triangles'],'archive_vertices_match_at_0_0001mm':mp['archived_triangle_vertex_multiset_matches_at_0_0001_mm'],'no_archive_zero_area':mp['archived_zero_area_triangles']==0,'no_reported_mesh_repair':all(int(mp['mesh_stat'].get(k,'0'))==0 for k in ['edges_fixed','degenerate_facets','facets_removed','facets_reversed','backwards_edges']),'all_layer_extrusion_envelopes_inside_build_and_exclusion':not violations,'no_shared_preset_changes':inv['shared_profiles_untouched'],'first_layer_model_present':fp.area>0,'official_bed_is_declared_256_square':bed.equals(box(0,0,256,256))}
 result={'status':'TOOLPATH_REVIEW_REQUIRES_PHYSICAL_FINISH_ACCEPTANCE'if all(check.values())else'DIGITAL_REVIEW_FAILED','part':part,'orientation':inv['orientation'],'checks':check,'mapping':mp,'first_layer':{'model_area_mm2':fp.area,'model_components':len(fp.geoms)if hasattr(fp,'geoms')else 1,'support_area_mm2':fsp.area,'all_features_area_mm2':fap.area},'all_layer_extrusion_bounds_mm':[extrusion_lo.tolist(),extrusion_hi.tolist()],'boundary_violations':violations,'feature_command_counts':dict(counts),'support_sample_count':len(q),'support_bounds_CAD':bounds(q),'support_z_layers':[min(support_layers),max(support_layers)]if support_layers else None,'selected_layers':selected.tolist(),'max_bridge_command_length_mm':max(bridges,default=0),'features':items,'route_features':route_features,'source_sha256_at_start':inv['source_sha256_at_start'],'artifact_sha256':{n:sha(folder/n)for n in ['invocation.json','oriented.stl','plate_1.gcode','slice-review.3mf']},'script_sha256':sha(__file__),'parser_sha256':sha(ROOT/'scripts/review_integrated_shell_slice.py'),'limits':['Positive-E object layers only; pre-object prime/maintenance extrusion belongs to unchanged printer start routines and is not counted here.','Bead width/full layer-height and bounded arc sampling envelopes, not measured PETG dimensions. All model/support/brim/skirt layer paths are included in bed/exclusion checks.','Feature hits are conservative flags for support removal; model-corridor AABBs overestimate actual contact and do not establish blocked holes.','Clear nominal STL corridors are narrow declared pick-tip access, not whole pliers/wrench-body clearance, removal force or complete debris evacuation.','Eight layer views and actual support occupancy locate supports but do not prove every overhang supported, adhesion, load strength, return behavior or an acceptable physical sliding surface.','Generic PETG / Textured PEI remain analysis assumptions; user confirmed PETG and PEI only.'],'sent_to_printer':False,'physical_acceptance':False}
 np.savez_compressed(out/'support-samples.npz',cad_centers=q,width=w,layer_height=lh)
 dump(out/'report.json',result);print(json.dumps({'part':part,'status':result['status'],'checks':check,'first_layer':result['first_layer'],'features':[{k:v[k]for k in ['name','support_envelope_samples','support_center_samples','stl_triangle_intersections','center_inside_stl']if k in v}for v in items]},ensure_ascii=False,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--folder',required=True);a=p.parse_args();run(Path(a.folder).resolve())
