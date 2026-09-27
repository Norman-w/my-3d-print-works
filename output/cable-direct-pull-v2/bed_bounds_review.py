"""Read-only independent actual 3MF build + emitted-bead bed/exclusion review."""
from pathlib import Path
import json,hashlib,sys,zipfile,xml.etree.ElementTree as ET,collections,itertools,math,datetime
import numpy as np
from shapely.geometry import Polygon,LineString,box,MultiPoint
B=Path(__file__).resolve().parent;ROOT=B.parents[1];sys.path.insert(0,str(ROOT/'analysis'));sys.path.insert(0,str(ROOT/'scripts'))
import cable_input_slice_review as parser
import cable_flat_slice_review as flat
import review_cable_slice as slicer
NS={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
S=B/'slices/20260927T084928459673Z-f76a83eeb9'
def bbox(a):return [a.min(axis=0).tolist(),a.max(axis=0).tolist()]
def affine(t):return parser.three_mf_matrix(t)
def transform(M,a):return a@M[:3,:3].T+M[:3,3]
def polygon(v):return Polygon([list(map(float,x.split('x')))for x in v])
def actual_mesh(z):
 cache={};leaves=[]
 def model(file):
  if file not in cache:cache[file]=ET.fromstring(z.read(file))
  return cache[file]
 def visit(file,oid,M,chain):
  root=model(file);obj=root.find(f'./m:resources/m:object[@id="{oid}"]',NS);assert obj is not None
  mesh=obj.find('./m:mesh',NS)
  if mesh is not None:
   v=np.array([[float(p.attrib[x])for x in 'xyz']for p in mesh.findall('./m:vertices/m:vertex',NS)]);tri=np.array([[int(p.attrib[x])for x in ['v1','v2','v3']]for p in mesh.findall('./m:triangles/m:triangle',NS)])
   lo,hi=v.min(0),v.max(0);corners=np.array(list(itertools.product(*zip(lo,hi))));leaves.append(dict(file=file,object_id=oid,chain=chain,matrix=M,vertices=transform(M,v),triangles=tri,transformed_local_aabb_corners=transform(M,corners)));return
  cs=obj.findall('./m:components/m:component',NS);assert cs
  for c in cs:
   file2=next((x for k,x in c.attrib.items()if k.endswith('}path')),file).lstrip('/');visit(file2,c.attrib['objectid'],M@affine(c.attrib.get('transform')),chain+[c.attrib])
 for item in model('3D/3dmodel.model').findall('./m:build/m:item',NS):visit('3D/3dmodel.model',item.attrib['objectid'],affine(item.attrib.get('transform')),[item.attrib])
 return leaves

def run(part):
 f=S/part;inv=json.loads((f/'invocation.json').read_text());assert inv['status']=='SLICE_GENERATED_REVIEW_REQUIRED'
 for p,h in inv['artifact_sha256'].items():assert sha(f/p)==h
 for p,h in inv['source_sha256_at_start'].items():assert sha(ROOT/p)==h
 for p,h in inv['local_profile_sha256'].items():assert sha(f/(p+'.json'))==h
 machine=json.loads((f/'machine.json').read_text());bed=polygon(machine['printable_area']);ex=polygon(machine['bed_exclude_area']);height=float(machine['printable_height'])
 with zipfile.ZipFile(f/'slice-review.3mf')as z:
  project=json.loads(z.read('Metadata/project_settings.config'));assert project['printable_area']==machine['printable_area']and project['bed_exclude_area']==machine['bed_exclude_area'];leaves=actual_mesh(z)
 a=np.vstack([l['vertices']for l in leaves]);aabb_corners=np.vstack([l['transformed_local_aabb_corners']for l in leaves]);hull=MultiPoint(a[:,:2]).convex_hull
 M,meta=flat.mapping(f,inv);pred=transform(M,slicer.read_stl(ROOT/inv['input']['file']).reshape(-1,3));nozzle=np.array(meta['extruder_offset']);mesh_command=a-nozzle;assert max(np.abs(np.array(bbox(mesh_command))-np.array(bbox(pred))).ravel())<.0001
 # Bed profile is axis-aligned here, explicitly required for interval checks.
 assert bed.equals(box(0,0,256,256));lo=np.array([math.inf]*3);hi=-lo;features=collections.Counter();bykind={};skipped=collections.Counter();violations=[];mindist=math.inf
 for r in parser.extrusion_paths((f/'plate_1.gcode').open()):
  if r.feature in {'Custom','Flush','Undefined',''}:skipped[r.feature]+=1;continue
  # Includes all model, brim, skirt, support and prime-tower paths if present.
  assert r.width>0 and r.height>0
  features[r.feature]+=1;rr=r.width/2+parser.ARC_ERROR+parser.BUFFER_ERROR;q=r.points
  l=q.min(0);h=q.max(0);l[:2]-=rr;h[:2]+=rr;l[2]-=r.height
  lo=np.minimum(lo,l);hi=np.maximum(hi,h)
  if r.feature not in bykind:bykind[r.feature]={'lo':l.copy(),'hi':h.copy()}
  else:bykind[r.feature]['lo']=np.minimum(bykind[r.feature]['lo'],l);bykind[r.feature]['hi']=np.maximum(bykind[r.feature]['hi'],h)
  border=min(l[0],l[1],256-h[0],256-h[1]);ln=LineString(q[:,:2]);exclude_gap=ln.distance(ex)-rr;mindist=min(mindist,exclude_gap)
  if border<0 or exclude_gap<=0 or l[2]<-.00001 or h[2]>height:
   violations.append(dict(line=r.line,feature=r.feature,bead_bounds=[l.tolist(),h.tolist()],bed_border_margin=border,excluded_gap_lower=exclude_gap))
 native=json.loads((f/'result.json').read_text())['sliced_plates'][0]['objects'][0]['bbox'];nlo=np.array([native[k]for k in ['x','y','z']]);nhi=nlo+np.array([native[k]for k in ['width','depth','height']]);aabb_diff=float(np.max(np.abs(np.array(bbox(aabb_corners))-np.array([nlo,nhi]))))
 result=dict(part=part,status='ACTUAL_MESH_AND_MODEL_BRIM_BEADS_WITHIN_PRINTABLE_BED'if not violations and bed.covers(hull)and hull.distance(ex)>0 else'BED_REVIEW_FLAGGED',source_sha256=inv['diagnostic_candidate']['source_sha256'],machine=dict(printable_area=machine['printable_area'],bed_exclude_area=machine['bed_exclude_area'],printable_height=height,resolved_project_matches=True),actual_3mf=dict(build_leaf_instances=len(leaves),total_vertices=len(a),world_vertex_bounds_mm=bbox(a),projected_convex_hull_inside_bed=bed.covers(hull),projected_convex_hull_to_exclude_distance_mm=hull.distance(ex),command_vs_direct_mesh_bbox_max_error_mm=float(np.max(np.abs(np.array(bbox(mesh_command))-np.array(bbox(pred))))),instances=[dict(file=l['file'],object_id=l['object_id'],chain=l['chain'],matrix=l['matrix'].tolist(),transformed_vertex_bbox_mm=bbox(l['vertices']))for l in leaves]),native_bbox_explanation=dict(reported=native,transformed_local_mesh_AABB_corner_bounds_mm=bbox(aabb_corners),maximum_difference_to_native_bbox_mm=aabb_diff,classification='TRANSFORMED_LOCAL_AABB_MATCHES_NATIVE_METADATA'if aabb_diff<.0001 else'NATIVE_BBOX_MISMATCH_REQUIRES_EXPLANATION',note='Actual raw mesh vertices are transformed through every component and build matrix. Separately transforming only the eight corners of the unrotated mesh AABB inflates the bound for nonrectangular parts; equality to reported bbox establishes the metadata explanation, not absence of mesh checks.'),actual_gcode=dict(included_feature_counts=dict(features),separately_excluded_custom_counts=dict(skipped),bead_envelope_bounds_mm=[lo.tolist(),hi.tolist()],minimum_bed_edge_margin_mm=min(lo[0],lo[1],256-hi[0],256-hi[1]),minimum_excluded_polygon_gap_lower_mm=mindist,per_feature_bounds={k:[v['lo'].tolist(),v['hi'].tolist()]for k,v in bykind.items()},violations=violations,arc_and_buffer_extra_mm=parser.ARC_ERROR+parser.BUFFER_ERROR),provenance={p:sha(f/p)for p in ['invocation.json','slice-review.3mf','plate_1.gcode','machine.json','result.json']},parser_sha256=sha(ROOT/'analysis/cable_input_slice_review.py'),script_sha256=sha(__file__),scope='Actual build mesh and positive-extrusion model/brim/other print-feature envelopes. Machine custom start/end purge and travel sequences are excluded explicitly; not a machine collision or material/printing release.',manufacturing_release=False,sent_to_printer=False)
 print(json.dumps({k:result[k]for k in ['part','status']}),flush=True);print(json.dumps({'mesh':bbox(a),'gcode':[lo.tolist(),hi.tolist()],'metadata_diff':aabb_diff,'violations':len(violations)}),flush=True)
 return result
results=[run(p)for p in ['cable-input-body','cable-input-lever']]
report=dict(status='BED_BOUNDS_PASS'if all(r['status']=='ACTUAL_MESH_AND_MODEL_BRIM_BEADS_WITHIN_PRINTABLE_BED'for r in results)else'BED_BOUNDS_FLAGGED',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),parts=results)
out=B/'bed-bounds-review.json';assert not out.exists(),'Never overwrite a prior bed review';out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
