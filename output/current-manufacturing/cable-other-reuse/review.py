"""Transfer six unchanged cable-part slices to the current explicit inventory.

Read-only against every old artifact: no slicing, mesh repair or printer access.
Strict identity and bounded numeric contraction remain different conclusions.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import struct
import sys
import xml.etree.ElementTree as ET
import zipfile
import numpy as np

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
sys.path.insert(0,str(ROOT/'analysis'))
sys.path.insert(0,str(ROOT/'scripts'))
from cable_structural_slice_review import mapping, NS, P
from cable_slice_artifacts import normalization_review
from review_cable_slice import read_stl

CURRENT=ROOT/'output/cable-scene-export/20260927T091627124663Z/report.json'
PARTS={
 'cable-output-cap':('20260927T073454146325Z','flat-path-review'),
 'cable-route-cap':('20260927T073454146325Z','flat-path-review'),
 'cable-route-lower':('20260927T073454146325Z','flat-path-review'),
 'beam-grip':('20260927T073454146325Z','structural-review'),
 'frame':('20260927T073454146325Z','structural-review'),
 'cable-route-base':('20260927T073651395924Z','structural-review'),
}
EVIDENCE={}
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def record(path):
 path=Path(path);EVIDENCE[str(path.relative_to(ROOT))]=sha(path);return path
def read(path):return json.loads(record(path).read_text())
def same(path,expected):record(path);return sha(path)==expected
def current_sources(report):return all(same(ROOT/p,h) for p,h in report['source_sha256'].items())

def review(part,stamp,kind,export):
 folder=ROOT/'output/print-review/current-cable'/stamp/part
 inv=read(folder/'invocation.json');old=read(folder/kind/'report.json')
 row=next(x for x in export['parts'] if x['id']=='feeder/'+part)
 source=ROOT/row['file'];oriented=folder/'oriented.stl'
 checks={
  'current_stl_verified':same(source,row['sha256']),
  'current_stl_byte_identical_to_slice_input':sha(source)==inv['input']['sha256'],
  'old_input_stl_unchanged':same(ROOT/inv['input']['file'],inv['input']['sha256']),
  'oriented_stl_unchanged':same(oriented,inv['oriented']['sha256']),
  'local_profiles_match_slice_start':all(same(folder/(n+'.json'),h) for n,h in inv['local_profile_sha256'].items()),
  'slice_artifacts_match_invocation':all(same(folder/n,h) for n,h in inv['artifact_sha256'].items()),
  'native_success_and_empty_warnings':inv['return_code']==0 and inv['native_result']['return_code']==0 and not any(x.get('warning_message') for x in inv['native_result']['sliced_plates']),
 }
 matrix=np.array(inv['cad_to_oriented']);source_mesh=read_stl(source);oriented_mesh=read_stl(oriented)
 predicted=source_mesh@matrix[:3,:3].T+matrix[:3,3]
 reorientation_error=float(np.max(abs(predicted-oriented_mesh))) if predicted.shape==oriented_mesh.shape else None
 checks['rigid_no_scale_or_reflection']=bool(np.allclose(matrix[:3,:3].T@matrix[:3,:3],np.eye(3),atol=1e-10) and abs(np.linalg.det(matrix[:3,:3])-1)<1e-10)
 oriented_bytes=oriented.read_bytes()
 binary_stl=len(oriented_bytes)>=84 and len(oriented_bytes)==84+50*struct.unpack_from('<I',oriented_bytes,80)[0]
 # Historical binary STL stores each transformed coordinate as IEEE Float32.
 # Verify that precise serialization step instead of widening a tolerance.
 if binary_stl:
  transport_match=predicted.shape==oriented_mesh.shape and np.array_equal(predicted.astype(np.float32).astype(float),oriented_mesh)
 else:
  transport_match=reorientation_error is not None and reorientation_error<1e-12
 checks['current_to_oriented_one_to_one']=bool(transport_match)
 _,parity=mapping(folder,inv)
 with zipfile.ZipFile(folder/'slice-review.3mf') as z:
  project=json.loads(z.read('Metadata/project_settings.config'))
  checks['archive_gcode_equals_external']=hashlib.sha256(z.read('Metadata/plate_1.gcode')).hexdigest()==sha(folder/'plate_1.gcode')
  main=ET.fromstring(z.read('3D/3dmodel.model'));checks['units_mm']=main.attrib.get('unit')=='millimeter'
  component=main.find('./m:resources/m:object/m:components/m:component',NS)
  model=ET.fromstring(z.read(component.attrib[P+'path'].lstrip('/')))
  obj=next(x for x in model.findall('./m:resources/m:object',NS) if x.attrib['id']==component.attrib['objectid'])
  vertices=np.array([[float(x.attrib[a]) for a in 'xyz'] for x in obj.findall('./m:mesh/m:vertices/m:vertex',NS)])
  faces=np.array([[int(x.attrib[a]) for a in ['v1','v2','v3']] for x in obj.findall('./m:mesh/m:triangles/m:triangle',NS)])
 checks['normal_mesh_no_zero_area']=parity['archived_zero_area_triangles']==0
 checks['no_reported_repairs']=all(int(parity['mesh_stat'].get(k,0))==0 for k in ['edges_fixed','degenerate_facets','facets_removed','facets_reversed','backwards_edges'])
 strict=parity['input_triangles']==parity['archived_triangles'] and parity['archived_triangle_vertex_multiset_matches_at_0_0001_mm']
 normalization=None
 if not strict:
  normalization=normalization_review(oriented_mesh,vertices+np.array(parity['source_offset']),faces)
  prior=read(folder/'float-normalization-review.json')
  checks['bounded_normalization_reproduced']=normalization['status']==prior['status']=='BOUNDED_VERTEX_CONTRACTION_VERIFIED' and normalization['collapsed_source_triangle_indices']==prior['collapsed_source_triangle_indices'] and abs(normalization['maximum_corner_displacement_mm']-prior['maximum_corner_displacement_mm'])<1e-12
 else:checks['strict_normal_mesh_identity']=True
 if kind=='structural-review':
  checks['reviewed_artifacts_unchanged']=all(same(folder/n,h) for n,h in old['artifact_sha256'].items())
  # Do not relabel the old strict triangle failure or stale whole-source claim.
  inherited={k:v for k,v in old['checks'].items() if k not in ['input_source_identity_current','archive_triangle_count_exact','archive_vertices_match_at_0_0001mm']}
  checks['existing_bounded_path_checks']=all(inherited.values())
 else:
  checks['reviewed_artifacts_unchanged']=all(same(folder/n,old[k]) for n,k in [('invocation.json','invocation_sha256'),('oriented.stl','oriented_sha256'),('plate_1.gcode','gcode_sha256'),('slice-review.3mf','3mf_sha256')])
  checks['existing_bounded_path_checks']=old['status']=='BOUNDED_TOOLPATH_REVIEW_NO_NEW_FLAGS' and old['flags']==[]
 process={k:project.get(k) for k in ['printer_model','printer_variant','nozzle_diameter','filament_type','filament_settings_id','curr_bed_type','layer_height','initial_layer_print_height','wall_loops','sparse_infill_density','enable_support','support_type','support_on_build_plate_only','brim_type','brim_width']}
 checks['layer_and_wall_and_infill_match']=str(process['layer_height'])==str(inv['assumptions']['layer_height_mm']) and str(process['wall_loops'])=='4' and process['sparse_infill_density']=='25%'
 checks['material_PETG']=project.get('filament_type')==['PETG']
 status='STRICT_NORMAL_MESH_IDENTITY' if strict else 'BOUNDED_NUMERIC_NORMALIZATION_WITH_STRICT_FACE_FAILURE_RETAINED'
 return {'instance_id':row['id'],'current_stl':row['file'],'current_stl_sha256':row['sha256'],'quantity':1,
   'slice_folder':str(folder.relative_to(ROOT)),'old_report':str((folder/kind/'report.json').relative_to(ROOT)),
   'identity_status':status,'process_status':'EXISTING_BOUNDED_TOOLPATH_REVIEW_TRANSFERRED_PHYSICAL_FINISH_OPEN' if all(checks.values()) else 'TRANSFER_FAILED',
   'needs_reslice':not all(checks.values()),'reason':'Current mesh equals original slice input; original actual artifacts and process identities rechecked. Finite feature/support-cleaning scope is preserved.',
   'checks':checks,'cad_to_oriented':matrix.tolist(),'reorientation_max_error_mm':reorientation_error,
   'oriented_transport':{'encoding':'binary_float32' if binary_stl else 'ascii',
     'criterion':'Exact array equality after declared IEEE Float32 serialization' if binary_stl else 'Cornerwise residual below 1e-12 mm',
     'triangle_order_preserved':True,'all_coordinates_match_declared_transport':bool(transport_match)},
   'normal_mesh_mapping':parity,'normalization':normalization,'process':process,
   'artifact_sha256':{n:sha(folder/n) for n in ['slice-review.3mf','plate_1.gcode','oriented.stl','invocation.json','machine.json','filament.json','process.json']},
   'bounded_feature_review_status':old['status'],'remaining_limits':old['limits'],
   'manufacturing_release':False,'physical_acceptance':False}

def main():
 export=read(CURRENT);assert export['status']=='CURRENT_SCENE_EXPORT_PASS' and current_sources(export)
 for p in [Path(__file__),ROOT/'analysis/cable_structural_slice_review.py',ROOT/'analysis/cable_slice_artifacts.py',ROOT/'scripts/review_cable_slice.py',ROOT/'scripts/review_integrated_shell_slice.py']:record(p)
 rows=[review(p,*v,export) for p,v in PARTS.items()]
 stable=all(sha(ROOT/p)==h for p,h in EVIDENCE.items()) and current_sources(export)
 d={'status':'CURRENT_SIX_SLICES_TRANSFERRED_WITH_EXPLICIT_LIMITS' if stable and not any(v['needs_reslice'] for v in rows) else 'REUSE_REQUIRES_REVIEW',
    'created_utc':datetime.now(timezone.utc).isoformat(),'sources_stable':stable,'parts':rows,'evidence_sha256':EVIDENCE,
    'manufacturing_release':False,'physical_acceptance':False,'sent_to_printer':False,
    'scope':'Six actual unchanged geometry slices. Byte identity from current STL to original input, explicit rigid reorientation and actual 3MF normal meshes/configuration/Gcode checked. Old whole-source reports are not rewritten; their bounded path evidence is transferred only for unchanged artifacts. No new physical finish/load claim.'}
 (OUT/'report.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
 print(d['status']);print(json.dumps([{k:x[k] for k in ['instance_id','identity_status','needs_reslice','checks']} for x in rows],ensure_ascii=False,indent=2))
 return 0 if d['status'].startswith('CURRENT_SIX') else 1

if __name__=='__main__':raise SystemExit(main())
