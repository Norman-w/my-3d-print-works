"""Bind four CURRENT input instances to verified frozen slice artifacts.
Read-only with respect to CAD, old reviews and slicer outputs. No reslice/print.
--check validates all live bindings and writes nothing.
"""
from pathlib import Path
import argparse,collections,datetime,hashlib,json,math,re,sys,zipfile,xml.etree.ElementTree as ET
import numpy as np
B=Path(__file__).resolve().parent;ROOT=B.parents[2]
sys.path[:0]=[str(ROOT/'analysis'),str(ROOT/'scripts')]
import cable_slice_artifacts as art
import cable_input_slice_review as paths
import review_cable_slice as slicer
from shapely.geometry import Polygon,LineString
NS={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
EXP=ROOT/'output/cable-scene-export/20260927T091627124663Z/report.json'
INV=ROOT/'docs/cable-assembly-inventory.json'
V3=ROOT/'output/cable-direct-pull-v3'
SELECT={
 'feeder/cable-input-body':V3/'slices/20260927T091647165443Z/cable-input-body',
 'feeder/cable-input-lever':V3/'slices/20260927T092019389929Z/cable-input-lever',
 'feeder/cable-input-terminal-cap':V3/'slices/20260927T092019389929Z/cable-input-terminal-cap',
 'feeder/cable-input-cover':ROOT/'output/print-review/current-cable/20260927T074227302558Z/cable-input-cover'}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text())
path=lambda p:Path(p)if Path(p).is_absolute()else ROOT/p
reference=lambda p:dict(file=str(Path(p).resolve()),sha256=sha(p))
def dump(p,v):Path(p).parent.mkdir(exist_ok=True,parents=True);Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def matrix(t):return paths.three_mf_matrix(t)
def affine(v,m):return paths.affine(v,m)
def oriented_faces(tri):
 # Exact floating coordinate equality, cyclic permutations preserve orientation.
 def canonical(t):
  v=[tuple(float(x)for x in q)for q in t];return min(tuple(v),tuple(v[1:]+v[:1]),tuple(v[2:]+v[:2]))
 return collections.Counter(canonical(t)for t in tri)
def read3mf(p):
 with zipfile.ZipFile(p)as z:
  m=ET.fromstring(z.read('3D/3dmodel.model'));cfg=ET.fromstring(z.read('Metadata/model_settings.config'));build=m.findall('./m:build/m:item',NS);assert len(build)==1 and m.attrib['unit']=='millimeter'
  bm=matrix(build[0].attrib.get('transform'));obj=m.find(f'./m:resources/m:object[@id="{build[0].attrib["objectid"]}"]',NS);cs=obj.findall('./m:components/m:component',NS);parts=cfg.findall('./object/part');assert len(cs)==len(parts)
  result=[]
  for cp in cs:
   config=next(p for p in parts if p.attrib['id']==cp.attrib['objectid']);meta={v.attrib['key']:v.attrib.get('value')for v in config.findall('./metadata')};file=next(v for k,v in cp.attrib.items()if k.endswith('}path')).lstrip('/');src=ET.fromstring(z.read(file));mesh=src.find(f'./m:resources/m:object[@id="{cp.attrib["objectid"]}"]/m:mesh',NS);assert mesh is not None
   v=np.array([[float(n.attrib[a])for a in 'xyz']for n in mesh.findall('./m:vertices/m:vertex',NS)]);t=np.array([[int(n.attrib[a])for a in ['v1','v2','v3']]for n in mesh.findall('./m:triangles/m:triangle',NS)]);cm=matrix(cp.attrib.get('transform'))
   result.append(dict(subtype=config.attrib['subtype'],name=meta.get('name'),meta=meta,vertices=v,triangles=t,component=cm,world_vertices=affine(v,bm@cm),mesh_stat=config.find('./mesh_stat').attrib))
  return dict(parts=result,build=bm,project=load_project(z),archived_gcode_sha=hashlib.sha256(z.read('Metadata/plate_1.gcode')).hexdigest()if'Metadata/plate_1.gcode'in z.namelist()else None)
def load_project(z):return json.loads(z.read('Metadata/project_settings.config'))
def normalization(source,v,t):
 r=art.normalization_review(source,v,t)
 assert r['status']=='BOUNDED_VERTEX_CONTRACTION_VERIFIED'and not r['collapsed_source_triangle_indices']and len(source)==len(t)
 r['scope']='Exact oriented-face correspondence after bounded native vertex precision conversion; no faces lost and no physical material/process guarantee.'
 return r
def bed_and_counts(f,project):
 bed=Polygon([list(map(float,s.split('x')))for s in project['printable_area']]);ex=Polygon([list(map(float,s.split('x')))for s in project['bed_exclude_area']]);assert list(bed.bounds)==[0.,0.,256.,256.]
 counts=collections.Counter();lo=np.full(2,np.inf);hi=-lo;edge=np.inf;exgap=np.inf;bad=[]
 for q in paths.extrusion_paths((f/'plate_1.gcode').open()):
  counts[q.feature]+=1
  if q.feature in {'Custom','Flush','Undefined',''}:continue
  r=q.width/2+paths.ARC_ERROR+paths.BUFFER_ERROR;l=q.points[:,:2].min(0)-r;h=q.points[:,:2].max(0)+r;lo=np.minimum(lo,l);hi=np.maximum(hi,h)
  a=min(l.min(),(256-h).min());b=LineString(q.points[:,:2]).distance(ex)-r;edge=min(edge,a);exgap=min(exgap,b)
  if a<0 or b<=0:bad.append(dict(line=q.line,feature=q.feature,bed_edge_gap_mm=a,excluded_area_gap_mm=b))
 assert not bad
 return dict(passed=True,nominal_model_brim_support_bead_bounds_xy=[lo.tolist(),hi.tolist()],minimum_bed_edge_gap_mm=edge,minimum_excluded_area_gap_mm=exgap,path_counts=dict(counts),support_path_count=sum(v for k,v in counts.items()if k.startswith('Support')),skipped_startup_features=['Custom','Flush','Undefined',''],bead_error_budget_mm=paths.ARC_ERROR+paths.BUFFER_ERROR,violations=bad)
def main(write=True):
 exp=load(EXP);inventory=load(INV);assert exp['status']=='CURRENT_SCENE_EXPORT_PASS'and exp['sources_stable'];assert sha(INV)==exp['inventory_sha256']
 checked_sources={n:sha(path(n))==h for n,h in exp['source_sha256'].items()};assert all(checked_sources.values()),[n for n,v in checked_sources.items()if not v]
 exported={p['id']:p for p in exp['parts']};invs={p['id']:p for p in inventory['parts']};summary=load(V3/'local-review-summary.json');v3parts={p['part']:p for p in summary['parts']};island=load(V3/'first-layer-island-review/report.json');islands={p['part']:p for p in island['parts']};records=[]
 for instance_id,f in SELECT.items():
  slug=instance_id.split('/')[-1];current=exported[instance_id];assert current['role']=='printed'and current['passed']and current['definitions']==invs[instance_id]['definitions']
  stl=path(current['file']);assert sha(stl)==current['sha256'];tri=slicer.read_stl(stl);inv=load(f/'invocation.json');supported=slug!='cable-input-cover';oldinput=inv['input_stl']if supported else inv['input'];oldstl=path(oldinput['file']);assert sha(oldstl)==oldinput['sha256'];oldtri=slicer.read_stl(oldstl);same=oriented_faces(tri)==oriented_faces(oldtri);assert same and len(tri)==len(oldtri)
  artifacts=inv['artifacts']if supported else inv['artifact_sha256'];assert all(sha(f/n)==h for n,h in artifacts.items());profiles=inv['profile_sha256']if supported else inv['local_profile_sha256'];assert all(sha(f/(n+'.json'))==h for n,h in profiles.items())
  native=inv['native_result'];assert native['return_code']==0;assert inv['returncode'if supported else'return_code']==0
  archive=read3mf(f/'slice-review.3mf');normal=[p for p in archive['parts']if p['subtype']=='normal_part'];enforcers=[p for p in archive['parts']if p['subtype']=='support_enforcer'];assert len(normal)==1 and len(enforcers)==(2 if supported else 0);assert len(archive['parts'])==1+len(enforcers)
  n=normal[0];pre=np.array(inv['cad_to_oriented']);assert np.allclose(pre[3],[0,0,0,1])and np.allclose(pre[:3,:3].T@pre[:3,:3],np.eye(3),atol=1e-10)and abs(np.linalg.det(pre[:3,:3])-1)<1e-10
  offset=np.array([float(n['meta']['source_offset_'+k])for k in 'xyz']);oriented=affine(tri.reshape(-1,3),pre).reshape(-1,3,3);proof=normalization(oriented,n['vertices']+offset,n['triangles']);assert all(int(n['mesh_stat'].get(k,0))==0 for k in ['edges_fixed','degenerate_facets','facets_removed','facets_reversed','backwards_edges'])
  assert archive['archived_gcode_sha']==sha(f/'plate_1.gcode')
  gc=(f/'plate_1.gcode').read_text();raw=re.search(r'^; extruder_offset = ([^\n]+)',gc,re.M).group(1).split(',');assert len(raw)==1;nozzle=np.array([*map(float,raw[0].split('x')),0.]);E=np.eye(4);E[:3,3]=-nozzle;U=np.eye(4);U[:3,3]=-offset;command=E@archive['build']@n['component']@U@pre
  ci=inventory['scene_contract']['ci'];L=np.eye(4);L[:3,:3]=np.array([ci['basis_x'],ci['basis_y'],ci['basis_z']]).T;L[:3,3]=ci['origin'];local_command=command@L;expected_growth=1 if slug in ['cable-input-body','cable-input-lever']else-1;assert abs(local_command[2,2]-expected_growth)<1e-8 and np.allclose(local_command[2,:2],0,atol=1e-8)
  expected_world=affine(tri.reshape(-1,3),command);native_command=affine(n['world_vertices'],E);bounds_error=float(np.max(np.abs(np.array(paths.bounds(expected_world))-np.array(paths.bounds(native_command)))));assert bounds_error<.0001
  project=archive['project'];assert project['printer_model']=='Bambu Lab X1 Carbon'and project['nozzle_diameter']==['0.4']and project['filament_type']==['PETG'];assert project['layer_height']=='0.1'and project['wall_loops']=='4'and project['sparse_infill_density']=='25%';assert project['enable_support']==('1'if supported else'0')
  exact_project_parameters=['layer_height','initial_layer_print_height','wall_loops','sparse_infill_density','enable_support','support_type','support_on_build_plate_only','support_top_z_distance','support_bottom_z_distance','support_object_xy_distance','support_interface_top_layers','support_interface_spacing','raft_first_layer_expansion','brim_type','brim_width','curr_bed_type','filament_type','printer_model','nozzle_diameter']
  eproof=[]
  if supported:
   assert project['support_type']=='normal(manual)'and project['support_on_build_plate_only']=='1';assert float(project['support_top_z_distance'])==.2 and float(project['support_bottom_z_distance'])==.2 and float(project['support_object_xy_distance'])==.35;assert project['support_interface_top_layers']=='2'and project['support_interface_spacing']=='0'and project['raft_first_layer_expansion']=='0'
   assert sha(f/'support-input.3mf')==inv['input3mf_sha256'];inputarchive=read3mf(f/'support-input.3mf');assert len(inputarchive['parts'])==3
   for ep in enforcers:
    original=next(p for p in inputarchive['parts']if p['name']==ep['name']and p['subtype']=='support_enforcer');norm=normalization(original['world_vertices'][original['triangles']],ep['world_vertices'],ep['triangles']);local_v=affine(affine(ep['world_vertices'],E),np.linalg.inv(local_command));actualbounds=paths.bounds(local_v);spec=next(q for q in inv['enforcers']if q['name']==ep['name']);assert np.max(np.abs(np.array(actualbounds)-np.array(spec['local_bounds'])))<.0001
    eproof.append(dict(name=ep['name'],subtype=ep['subtype'],triangle_count=len(ep['triangles']),local_bounds=actualbounds,expected_local_bounds=spec['local_bounds'],source_to_native_enforcer_mesh=norm,role='slicer-only modifier; excluded from physical normal-part mesh'))
   rp=f/'support-path-review/report.json';rr=load(rp);assert sha(rp)==v3parts[slug]['review_sha256'];assert rr['artifact_sha256']['plate_1.gcode']==sha(f/'plate_1.gcode');assert rr['artifact_sha256']['slice-review.3mf']==sha(f/'slice-review.3mf')
   cleanup=dict(interior=inv['pocket_contract'],direction_local=[0,0,-expected_growth],stage='After removal from PEI and before hardware/assembly; pull through original shallow nut/head opening, never through D3.4 bore.',strict_original_pocket_only_pass=rr['all_support_localized'],exterior_bed_island_count=v3parts[slug]['exterior_bed_island_count'],classification=v3parts[slug]['support_cleanup_classification'],remaining_interior_support_contained=True,exterior_route='Remove exterior support islands with Brim/bed cleanup; they are outside entire model projection and disconnected from interior supports.'if slug in islands else None)
   refs=[reference(rp),reference(V3/'local-review-summary.json')]
   if slug in islands:
    assert islands[slug]['all_remaining_support_contained'];assert islands[slug]['native_source']['artifacts']['plate_1.gcode']==sha(f/'plate_1.gcode');refs.append(reference(V3/'first-layer-island-review/report.json'))
   limits=rr['limits']+['Original strict pocket-only failure is preserved for lever/cap; its exterior-bed-island alternative cleanup classification is separate.']if slug in islands else rr['limits'];critical=dict(pockets=v3parts[slug]['pockets'])
  else:
   assert sha(path(inv['oriented']['file']))==inv['oriented']['sha256'];assert np.max(np.abs(slicer.read_stl(path(inv['oriented']['file']))-oriented))<.00002
   rp=f/'flat-path-review/report.json';rr=load(rp);assert rr['status']=='BOUNDED_TOOLPATH_REVIEW_NO_NEW_FLAGS'and not rr['flags'];assert rr['gcode_sha256']==sha(f/'plate_1.gcode')and rr['3mf_sha256']==sha(f/'slice-review.3mf');assert np.max(np.abs(np.array(rr['mapping']['cad_to_command'])-command))<1e-8
   ar=load(f/'artifact-review.json');assert ar['status']=='SLICE_ARTIFACT_IDENTITY_PASS'and ar['slice_invocation_sha256']==sha(f/'invocation.json');refs=[reference(rp),reference(f/'artifact-review.json')];cleanup=dict(classification='NO_GENERATED_SUPPORT',interior=None,exterior_bed_island_count=0,stage='Remove the normal Brim/bed residues; no support-body extraction is requested.');critical=dict(planes=rr['critical_planes'],openings=[{k:q[k]for k in ['name','inset_through_core_clear_all_layers','actual_toolpath_seat_height_mm','seat_height_delta_mm','final_recess_inset_0p2_model_bead_overlap_mm2']}for q in rr['openings']]);limits=rr['limits']
  bed=bed_and_counts(f,project);assert bed['support_path_count']==(rr['actual_support_path_count']if supported else 0)
  r=dict(instance_id=instance_id,name=invs[instance_id]['name'],quantity=1,status='CURRENT_INSTANCE_FROZEN_SLICE_REUSE_VERIFIED',current_stl=str(stl),current_stl_sha256=sha(stl),current_export_definition=current['definitions'],current_backend=current['backend'],source_binding=dict(current_export_report=reference(EXP),current_inventory=reference(INV),source_hashes_verified=checked_sources,current_input_scad_sha256=sha(ROOT/'cad/cable-trigger-input.scad')),selected_slice=str(f),historical_slice_input=reference(oldstl),historical_input_is_current_stl_byte_identical=sha(stl)==sha(oldstl),exact_oriented_triangle_multiset_identical=True,current_triangle_count=len(tri),actual_3mf_normal_mesh=proof,placement=dict(cad_to_oriented=pre.tolist(),source_offset=offset.tolist(),component=n['component'].tolist(),build=archive['build'].tolist(),extruder_offset=nozzle.tolist(),cad_to_command=command.tolist(),input_local_to_command=local_command.tolist(),normal_actual_3mf_build_bounds=paths.bounds(n['world_vertices']),normal_command_bounds=paths.bounds(native_command),current_predicted_vs_native_command_bbox_error_mm=bounds_error,build_direction_input_local=[0,0,expected_growth]),process={k:project.get(k)for k in exact_project_parameters},profiles={k:reference(f/(k+'.json'))for k in ['machine','filament','process']},support_enforcers=eproof,support_cleanup=cleanup,critical_path_evidence=critical,bed_and_path_counts=bed,review_evidence=refs,artifacts={k:reference(f/k)for k in ['invocation.json','result.json','slice-review.3mf','plate_1.gcode']+(['support-input.3mf']if supported else['oriented.stl'])},resolved_project_settings_sha256=hashlib.sha256(json.dumps(project,sort_keys=True,separators=(',',':')).encode()).hexdigest(),profile_assumptions=['X1C / 0.4 mm and PETG confirmed by user; Generic PETG temperatures/profile remain a material assumption.','Actual slice selects Textured PEI; user specified PEI without confirming texture.'],remaining_physical_limits=limits,operation='reuse_exact_selected_artifacts_only',resliced=False,mechanical_geometry_changed=False,manufacturing_release=False,physical_acceptance=False,sent_to_printer=False)
  if write:dump(B/'parts'/slug/'binding.json',r);dump(B/'parts'/slug/'resolved-project-settings.json',project)
  records.append(r)
 manifest=dict(schema_version=1,status='FOUR_CURRENT_INPUT_INSTANCES_BOUND_TO_FROZEN_PROCESS',generated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='Four current input manufacturing items; reuse verified existing native 3MF/G-code, no slicing or printer action.',current_export_report=reference(EXP),current_inventory=reference(INV),items=records,configuration_adapter=dict(operation='reuse_exact_selected_artifacts_only',expected_instance_ids=list(SELECT),verify_command=['/Applications/FreeCAD.app/Contents/Resources/bin/python',str(Path(__file__).resolve()),'--check'],build_command_does_not_slice=True,forbid_reuse_after_mesh_or_profile_hash_change=True),script_sha256=sha(__file__),manufacturing_release=False,physical_acceptance=False,sent_to_printer=False)
 assert all(sha(path(n))==h for n,h in exp['source_sha256'].items()),'Current source changed during binding'
 if write:dump(B/'manifest.json',manifest)
 else:
  old=load(B/'manifest.json');assert old['script_sha256']==sha(__file__);assert old['current_export_report']==manifest['current_export_report'];assert old['current_inventory']==manifest['current_inventory'];assert old['items']==records
 print(json.dumps({'status':manifest['status'],'write':write,'manifest':str(B/'manifest.json'),'items':[{'id':r['instance_id'],'triangles':r['current_triangle_count'],'same_stl_bytes':r['historical_input_is_current_stl_byte_identical'],'support_enforcers':len(r['support_enforcers']),'bed_pass':r['bed_and_path_counts']['passed']}for r in records]},ensure_ascii=False,indent=2))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--check',action='store_true');args=ap.parse_args();main(write=not args.check)
