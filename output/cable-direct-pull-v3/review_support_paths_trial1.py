"""Read-only native manual-support and shoulder/extraction audit, process v3."""
from pathlib import Path
import argparse,json,sys,math,hashlib,collections,zipfile,xml.etree.ElementTree as ET,os,re
import numpy as np
from shapely.geometry import Point,Polygon,LineString,box,MultiPoint
from shapely.ops import unary_union
B=Path(__file__).resolve().parent;ROOT=B.parents[1];sys.path.insert(0,str(ROOT/'analysis'));sys.path.insert(0,str(ROOT/'scripts'))
import cable_input_slice_review as p
import cable_slice_artifacts as artifact
import review_cable_slice as slicer
CORE='http://schemas.microsoft.com/3dmanufacturing/core/2015/02';NS={'m':CORE};ERROR=p.ARC_ERROR+p.BUFFER_ERROR
sha=lambda x:hashlib.sha256(Path(x).read_bytes()).hexdigest()
def dump(f,d):Path(f).write_text(json.dumps(d,ensure_ascii=False,indent=2,default=lambda x:x.item() if isinstance(x,np.generic) else (_ for _ in ()).throw(TypeError(type(x).__name__)))+'\n')
def getmesh(z,file,oid):
 d=ET.fromstring(z.read(file));m=d.find(f'./m:resources/m:object[@id="{oid}"]/m:mesh',NS);assert m is not None
 return np.array([[float(v.attrib[a])for a in 'xyz']for v in m.findall('./m:vertices/m:vertex',NS)]),np.array([[int(v.attrib[a])for a in ['v1','v2','v3']]for v in m.findall('./m:triangles/m:triangle',NS)])
def transforms(folder,inv):
 with zipfile.ZipFile(folder/'slice-review.3mf')as z:
  cfg=ET.fromstring(z.read('Metadata/model_settings.config'));main=ET.fromstring(z.read('3D/3dmodel.model'));parts=cfg.findall('./object/part');normal=[v for v in parts if v.attrib['subtype']=='normal_part'];supports=[v for v in parts if v.attrib['subtype']=='support_enforcer'];assert len(normal)==1 and len(supports)==2 and len(parts)==3
  build=main.findall('./m:build/m:item',NS);assert len(build)==1;BM=p.three_mf_matrix(build[0].attrib.get('transform'));cs=main.findall('./m:resources/m:object/m:components/m:component',NS);assert len(cs)==3
  com=next(c for c in cs if c.attrib['objectid']==normal[0].attrib['id']);CM=p.three_mf_matrix(com.attrib.get('transform'));meta={m.attrib['key']:m.attrib.get('value')for m in normal[0].findall('./metadata')};offset=np.array([float(meta['source_offset_'+x])for x in 'xyz']);U=np.eye(4);U[:3,3]=-offset
  raw=re.search(r'^; extruder_offset = ([^\n]+)',(folder/'plate_1.gcode').read_text(),re.M).group(1).split(',');assert len(raw)==1;nozzle=np.array([*map(float,raw[0].split('x')),0.]);E=np.eye(4);E[:3,3]=-nozzle
  M=E@BM@CM@U@np.array(inv['cad_to_oriented']);s=math.sqrt(.5);L=np.array([[-s,s,0,75],[0,0,1,-82],[s,s,0,5],[0,0,0,1.]])
  local_to_command=M@L;inverse=np.linalg.inv(local_to_command);assert np.allclose(local_to_command[2,:2],0,atol=1e-8);assert abs(abs(local_to_command[2,2])-1)<1e-8
  file=next(v for k,v in com.attrib.items()if k.endswith('}path')).lstrip('/');verts,faces=getmesh(z,file,com.attrib['objectid']);source=slicer.read_stl(inv['input_stl']['file']);oriented=p.affine(source.reshape(-1,3),np.array(inv['cad_to_oriented'])).reshape(-1,3,3)
  ident=artifact.normalization_review(oriented,verts+offset,faces);assert len(source)==len(faces);assert not ident['collapsed_source_triangle_indices'];assert ident['status']=='BOUNDED_VERTEX_CONTRACTION_VERIFIED'
  world=p.affine(verts,E@BM@CM);pred=p.affine(source.reshape(-1,3),M);bboxerr=float(np.max(np.abs(np.array(p.bounds(world))-np.array(p.bounds(pred)))));assert bboxerr<.0001
  enforcers=[]
  for scfg in supports:
   c=next(c for c in cs if c.attrib['objectid']==scfg.attrib['id']);file=next(v for k,v in c.attrib.items()if k.endswith('}path')).lstrip('/');v,t=getmesh(z,file,c.attrib['objectid']);q=p.affine(p.affine(v,E@BM@p.three_mf_matrix(c.attrib.get('transform'))),inverse);bb=p.bounds(q);desired=next(e['local_bounds']for e in inv['enforcers']if e['name']==next(m.attrib['value']for m in scfg.findall('./metadata')if m.attrib['key']=='name'));assert np.max(np.abs(np.array(bb)-np.array(desired)))<.0001;enforcers.append(dict(subtype='support_enforcer',actual_local_bounds=bb,expected_local_bounds=desired))
  project=json.loads(z.read('Metadata/project_settings.config'));rep=normal[0].find('./mesh_stat').attrib;assert all(int(rep.get(k,0))==0 for k in ['edges_fixed','degenerate_facets','facets_removed','facets_reversed','backwards_edges'])
  assert hashlib.sha256(z.read('Metadata/plate_1.gcode')).hexdigest()==sha(folder/'plate_1.gcode')
 return inverse,dict(cad_to_command=M.tolist(),local_to_command=local_to_command.tolist(),build=BM.tolist(),extruder_offset_from_gcode=nozzle.tolist(),normal_component=CM.tolist(),normal_source_offset=offset.tolist(),model_bbox=p.bounds(world),source_vs_actual_bbox_error_mm=bboxerr,normal_part_identity=ident,enforcers=enforcers),project

def shape(c,kind):
 if kind.startswith('hex'):
  r=5.8/(2*math.cos(math.pi/6));return Polygon([(c[0]+r*math.cos(math.pi/6+i*math.pi/3),c[1]+r*math.sin(math.pi/6+i*math.pi/3))for i in range(6)])
 return Point(c).buffer(3.1,quad_segs=180)
def model(feature):return feature not in {'Custom','Flush','Brim','Skirt','Undefined',''}and not feature.startswith('Support')
def footprint(rows):return unary_union([r['path'].buffer(r['width']/2+ERROR,quad_segs=32)for r in rows])
def chunks(g):
 if g.is_empty:return[]
 if g.geom_type=='LineString':return[g]
 return [s for child in getattr(g,'geoms',[])for s in chunks(child)]
def gapstats(rows,shoulder,under):
 entries=[]
 for r in rows:
  clipped=r['path'].intersection(shoulder);gaps=chunks(clipped.difference(under.buffer(r['width']/2,quad_segs=32)))
  for g in gaps:
   if g.length>.005:entries.append(dict(line=r['line'],feature=r['feature'],length_mm=g.length,end_chord_mm=float(np.linalg.norm(np.array(g.coords[0])-np.array(g.coords[-1]))),bounds=list(g.bounds)))
 return dict(count=len(entries),max_continuous_path_length_mm=max([e['length_mm']for e in entries],default=0),max_endpoint_chord_mm=max([e['end_chord_mm']for e in entries],default=0),entries=entries)
def run(folder):
 folder=folder.resolve();inv=json.loads((folder/'invocation.json').read_text());assert inv['status']=='SLICED_REVIEW_REQUIRED' and inv['source_stable'];assert sha(inv['candidate_source'])==inv['source_sha256'];assert sha(inv['input_stl']['file'])==inv['input_stl']['sha256'];assert all(sha(folder/n)==h for n,h in inv['artifacts'].items());assert all(sha(folder/(n+'.json'))==h for n,h in inv['profile_sha256'].items())
 inverse,mapping,project=transforms(folder,inv);assert project['enable_support']=='1'and project['support_type']=='normal(manual)'and project['support_on_build_plate_only']=='1';assert project['layer_height']=='0.1'
 cfg=inv['pocket_contract'];growth=cfg['growth'];assert abs(np.linalg.inv(inverse)[2,2]-growth)<1e-7
 centres=cfg['centres'];opens=[shape(c,cfg['opening'])for c in centres];shoulders=[o.difference(Point(c).buffer(1.7,quad_segs=180))for o,c in zip(opens,centres)]
 roof=float((np.linalg.inv(inverse)@np.array([centres[0][0],centres[0][1],cfg['contact'],1]))[2]);entry=min(cfg['z'])if growth>0 else max(cfg['z']);layers=collections.defaultdict(list);support=[];counts=collections.Counter();bed=Polygon([list(map(float,x.split('x')))for x in project['printable_area']]);exclude=Polygon([list(map(float,x.split('x')))for x in project['bed_exclude_area']]);assert bed.equals(box(0,0,256,256));bedbad=[];bedlo=np.array([math.inf,math.inf]);bedhi=-bedlo;extractbad=[]
 for rec in p.extrusion_paths((folder/'plate_1.gcode').open()):
  counts[rec.feature]+=1
  if rec.feature in {'Custom','Flush','Undefined',''}:continue
  rr=rec.width/2+ERROR;lo=rec.points[:,:2].min(0)-rr;hi=rec.points[:,:2].max(0)+rr;bedlo=np.minimum(bedlo,lo);bedhi=np.maximum(bedhi,hi)
  ln=LineString(rec.points[:,:2]);border=min(lo.min(),(256-hi).min());exgap=ln.distance(exclude)-rr
  if border<0 or exgap<=0:bedbad.append(dict(line=rec.line,feature=rec.feature,border=border,exclusion_gap=exgap))
  if not(rec.feature.startswith('Support')or(model(rec.feature)and roof-.41<=rec.layer<=roof+.41)):continue
  q=p.affine(rec.points,inverse);localtop=q[0,2];za,zb=sorted([localtop,localtop-growth*rec.height]);row=dict(line=rec.line,feature=rec.feature,print_top=rec.layer,height=rec.height,width=rec.width,path=LineString(q[:,:2]),xy=q[:,:2],local_z=[za,zb]);layers[round(rec.layer,6)].append(row)
  if rec.feature.startswith('Support'):
   ds=[row['path'].distance(Point(c))for c in centres];idx=int(np.argmin(ds));row['pocket']=idx;support.append(row);fp=row['path'].buffer(rr,quad_segs=32);outside=fp.difference(opens[idx]).area
   zlow,zhigh=sorted([entry,cfg['contact']]);valid_z=za>=zlow-1e-5 and zb<=zhigh+1e-5
   if outside>1e-8 or not valid_z:extractbad.append(dict(line=rec.line,feature=rec.feature,pocket=idx,outside_opening_area_mm2=outside,local_z=[za,zb],within_axial_shallow_cavity=valid_z))
 out=folder/'support-path-review';out.mkdir(exist_ok=True);findings=[];plot_data=[]
 for idx,(c,opening,shoulder)in enumerate(zip(centres,opens,shoulders)):
  sr=[r for r in support if r['pocket']==idx];inter=[r for r in sr if r['feature']=='Support interface'];assert inter,'Native enforcer produced no top interface'
  supportlast=max(r['print_top']for r in inter);lastrows=[r for r in inter if abs(r['print_top']-supportlast)<1e-6];under=footprint(lastrows)
  modeltops=sorted(z for z,rs in layers.items()if any(model(r['feature'])and r['path'].distance(opening)<1 for r in rs));first=min(z for z in modeltops if z>roof+1e-5);prior=max(z for z in modeltops if z<=roof+1e-5)
  roofrows=[r for r in layers[first]if model(r['feature'])and r['path'].distance(opening)<1];priorrows=[r for r in layers[prior]if model(r['feature'])and r['path'].distance(opening)<1];oldfoot=footprint(priorrows)
  allproj=footprint(sr);before=gapstats(roofrows,shoulder,oldfoot);after=gapstats(roofrows,shoulder,oldfoot.union(under));shoulderarea=shoulder.area
  metal=Point(c).buffer(2.75,quad_segs=180)if cfg['opening'].startswith('circle')else Polygon([(c[0]+5.5/math.sqrt(3)*math.cos(math.pi/6+k*math.pi/3),c[1]+5.5/math.sqrt(3)*math.sin(math.pi/6+k*math.pi/3))for k in range(6)]);bearing=metal.difference(Point(c).buffer(1.7,quad_segs=180))
  findings.append(dict(centre_local_xy=c,contact_plane_local_z=cfg['contact'],contact_plane_print_z=roof,first_shoulder_model_layer_print_z=first,previous_model_layer_print_z=prior,last_support_interface_layer_print_z=supportlast,nominal_vertical_gap_mm=roof-supportlast,support_count=len(sr),support_interface_count=len(inter),support_projection_outside_original_opening_mm2=allproj.difference(opening).area,opening_contains_complete_support_projection=opening.covers(allproj),support_to_opening_boundary_min_gap_mm=allproj.distance(opening.boundary),shoulder_area_mm2=shoulderarea,top_interface_projected_area_under_shoulder_mm2=under.intersection(shoulder).area,metal_bearing_area_preserved_mm2=bearing.area,metal_bearing_loss_mm2=0,shoulder_paths_without_previous_model_overlap=before,shoulder_paths_without_previous_model_or_top_interface_overlap=after,removal_direction_local=[0,0,-growth],removal_contract='Rigid axial extraction through this original constant-section shallow opening, before hardware/assembly. Projection containment proves nominal room only, not adhesion release or grasp force.'))
  plot_data.append((c,opening,priorrows,lastrows,roofrows,oldfoot,under))
 os.environ.setdefault('MPLCONFIGDIR',str(out/'mpl'));import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
 from matplotlib.collections import LineCollection
 fig,axs=plt.subplots(2,3,figsize=(13,9),layout='constrained')
 for idx,(c,o,prev,interface,roofrows,pf,sf)in enumerate(plot_data):
  for j,rs in enumerate([prev,interface,roofrows]):
   ax=axs[idx,j];ax.set_xlim(c[0]-4,c[0]+4);ax.set_ylim(c[1]-4,c[1]+4);ax.set_aspect('equal');ax.grid(alpha=.15);ax.set_title(['Previous model layer','Last support interface','First shoulder model layer'][j]+f'\npocket {idx+1}');ax.set_xlabel('Input local X / mm');ax.set_ylabel('Input local Y / mm')
 fig.canvas.draw()
 for idx,(c,o,prev,interface,roofrows,pf,sf)in enumerate(plot_data):
  for j,rs in enumerate([prev,interface,roofrows]):
   ax=axs[idx,j];scale=(ax.transData.transform([1,0])-ax.transData.transform([0,0]))[0]*72/fig.dpi
   if j==2:
    for g in getattr(sf,'geoms',[sf]):
     if g.geom_type=='Polygon':ax.fill(*g.exterior.xy,color='#edb679',alpha=.4)
   for r in rs:ax.add_collection(LineCollection([r['xy']],colors='#ce7324'if r['feature'].startswith('Support')else'#176886',linewidths=r['width']*scale,capstyle='round'))
   ax.plot(*o.exterior.xy,':',color='#a92170',lw=.7)
 fig.suptitle(inv['part']+' — unchanged bearing geometry, actual manual-support paths\nOrange: support footprint; blue: model; magenta: original extraction opening');fig.savefig(out/'shoulder-support-layers.png',dpi=170);plt.close(fig)
 result=dict(status='LOCAL_MANUAL_SUPPORT_PATH_REVIEW',part=inv['part'],geometry_changed=False,normal_part_identity=mapping['normal_part_identity'],mapping=mapping,process={k:project[k]for k in ['enable_support','support_type','support_on_build_plate_only','support_top_z_distance','support_object_xy_distance','support_interface_top_layers','support_interface_spacing','layer_height']},enforcer_roles_roundtrip_verified=True,actual_support_path_count=len(support),support_features={k:v for k,v in counts.items()if k.startswith('Support')},support_outside_selected_extraction_cavities=extractbad,all_support_localized=not extractbad,bed=dict(model_brim_support_bead_bounds_xy=[bedlo.tolist(),bedhi.tolist()],violations=bedbad,passed=not bedbad),pockets=findings,artifact_sha256={n:sha(folder/n)for n in ['invocation.json','slice-review.3mf','plate_1.gcode']},script_sha256=sha(__file__),parser_sha256=sha(ROOT/'analysis/cable_input_slice_review.py'),limits=['Support is separated by the recorded air gap; projected underlay is not a physical guarantee of no sag or reliable PETG separation.','Remaining unsupported-path lengths are curved centerline fragments relative to nominal bead footprints, not mechanical free spans.','No reduction in nominal metal bearing area; support scars, dimensions, torque and layer adhesion remain physical unknowns.','No support was requested for the transverse stop bore/nut chamber or M6 round roof. Those previously documented short bridges remain.','Removal envelope excludes unknown extraction-tool dimensions and glue-like support fusion. This is normal part manufacturing support, not a coupon.'],manufacturing_release=False,sent_to_printer=False)
 dump(out/'report.json',result);print(json.dumps({'part':inv['part'],'localized':not extractbad,'outside':len(extractbad),'support_count':len(support),'gaps':[(r['shoulder_paths_without_previous_model_overlap']['max_continuous_path_length_mm'],r['shoulder_paths_without_previous_model_or_top_interface_overlap']['max_continuous_path_length_mm'])for r in findings],'bed_pass':not bedbad}),flush=True);return result
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--folder',required=True,type=Path);run(ap.parse_args().folder)
