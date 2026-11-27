#!/usr/bin/env python3
"""Read actual new-axis 3MF meshes, transforms, profiles and G-code identities.

This checks offline manufacturing evidence only. It neither slices nor prints.
"""
from pathlib import Path
import argparse, datetime, hashlib, importlib.util, json, re, sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'analysis'), str(ROOT / 'scripts')]
import cable_slice_artifacts as artifacts
import cable_input_slice_review as parser
import review_cable_slice as slicer
from cable_slice_contract import frozen_scene, input_matrix

# Frozen, general archive reader already used to bind the historical plates.
READER = ROOT / 'output/current-manufacturing/input-process/bind_current_input_process.py'
spec = importlib.util.spec_from_file_location('frozen_archive_reader', READER)
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)

def path(p):
    p = Path(p)
    return p if p.is_absolute() else ROOT / p
def sha(p): return hashlib.sha256(path(p).read_bytes()).hexdigest()
def load(p): return json.loads(path(p).read_text())
def rel(p): return str(path(p).resolve().relative_to(ROOT))

def review(folder):
    folder = path(folder).resolve()
    inv = load(folder / 'invocation.json')
    assert inv['part'] in {'cable-input-body', 'cable-input-lever', 'cable-input-cover'}
    evidence = {}
    def verify(p, expected=None):
        h = sha(p)
        if expected is not None: assert h == expected, 'Identity changed: ' + str(p)
        evidence[rel(p)] = h
        return h
    for p in [__file__, READER, ROOT/'analysis/cable_slice_artifacts.py',
              ROOT/'analysis/cable_input_slice_review.py', ROOT/'analysis/cable_slice_contract.py',
              ROOT/'scripts/review_cable_slice.py', folder/'invocation.json']:
        verify(p)
    for p,h in inv['source_sha256_at_start'].items(): verify(p,h)
    for key in ['input', 'oriented']: verify(inv[key]['file'], inv[key]['sha256'])
    verify(inv['export_report'], inv['export_report_sha256'])
    for name,h in inv['artifact_sha256'].items(): verify(folder/name,h)
    for name,h in inv['local_profile_sha256'].items(): verify(folder/(name+'.json'),h)
    scene, contract = frozen_scene(inv)
    verify(contract['frozen_inventory'],contract['frozen_inventory_sha256'])
    source = slicer.read_stl(path(inv['input']['file']))
    oriented = slicer.read_stl(path(inv['oriented']['file']))
    pre = np.array(inv['cad_to_oriented'])
    assert np.allclose(pre[3],[0,0,0,1])
    assert np.allclose(pre[:3,:3].T@pre[:3,:3],np.eye(3),atol=1e-10)
    assert abs(np.linalg.det(pre[:3,:3])-1)<1e-10
    expected = parser.affine(source,pre)
    assert expected.shape == oriented.shape
    rigid_error = float(np.max(np.abs(expected-oriented)))
    assert rigid_error < 1e-10
    archive = reader.read3mf(folder/'slice-review.3mf')
    normal = [p for p in archive['parts'] if p['subtype']=='normal_part']
    support = [p for p in archive['parts'] if p['subtype']=='support_enforcer']
    assert len(normal)==1 and len(archive['parts'])==1+len(support)
    n = normal[0]
    offset = np.array([float(n['meta']['source_offset_'+a]) for a in 'xyz'])
    # Authored 3MF is not a native STL-import record. Bambu re-centres its raw
    # mesh but preserves source_offset=0, so that metadata cannot undo centring.
    # Prove both full meshes in the input assembly frame using explicit 3MF
    # component/build transforms; no bounding-box alignment is inferred.
    input_file=inv['input3mf']['file']
    verify(input_file,inv['input3mf']['sha256'])
    input_archive=reader.read3mf(path(input_file))
    input_normal=[p for p in input_archive['parts'] if p['subtype']=='normal_part']
    assert len(input_normal)==1
    ni=input_normal[0]
    assert np.allclose(ni['component'],np.eye(4),atol=1e-12)
    input_proof=artifacts.normalization_review(oriented,ni['vertices'],ni['triangles'])
    assert input_proof['status']=='BOUNDED_VERTEX_CONTRACTION_VERIFIED'
    assert not input_proof['collapsed_source_triangle_indices']
    native_in_input=parser.affine(n['world_vertices'],np.linalg.inv(input_archive['build']))
    proof = artifacts.normalization_review(oriented,native_in_input,n['triangles'])
    assert proof['status']=='BOUNDED_VERTEX_CONTRACTION_VERIFIED', proof
    assert not proof['collapsed_source_triangle_indices'], proof
    assert len(source)==len(n['triangles'])
    assert int(n['mesh_stat']['face_count'])==len(n['triangles'])
    assert not any(int(n['mesh_stat'].get(k,0)) for k in
        ['edges_fixed','degenerate_facets','facets_removed','facets_reversed','backwards_edges'])
    assert archive['archived_gcode_sha']==sha(folder/'plate_1.gcode')
    gcode=(folder/'plate_1.gcode').read_text()
    raw=re.search(r'^; extruder_offset = ([^\n]+)',gcode,re.M).group(1).split(',')
    assert len(raw)==1
    nozzle=np.array([*map(float,raw[0].split('x')),0.])
    E=np.eye(4);E[:3,3]=-nozzle
    command=E@input_archive['build']@pre
    local_command=command@input_matrix(scene)
    growth=1 if inv['part'] in ['cable-input-body','cable-input-lever'] else -1
    assert np.allclose(local_command[2,:3],[0,0,growth],atol=1e-8)
    bounds_error=float(np.max(np.abs(np.array(parser.bounds(parser.affine(source.reshape(-1,3),command)))-
        np.array(parser.bounds(parser.affine(n['world_vertices'],E))))))
    assert bounds_error<1e-5
    project=archive['project']
    assert project['printer_model']=='Bambu Lab X1 Carbon' and project['nozzle_diameter']==['0.4']
    assert project['filament_type']==['PETG']
    assert all(str(project[k])==v for k,v in {'layer_height':'0.1','initial_layer_print_height':'0.1',
        'wall_loops':'4','sparse_infill_density':'25%'}.items())
    assert project['enable_support']==('1' if support else '0')
    if support:
        assert len(support)==len(inv['enforcers'])
        assert project['support_type']=='normal(manual)' and project['support_on_build_plate_only']=='1'
    enforcers=[]
    for s in support:
        v=parser.affine(parser.affine(s['world_vertices'],E),np.linalg.inv(local_command))
        expected_support=next(x for x in inv['enforcers'] if x['name']==s['name'])
        assert np.max(np.abs(np.array(parser.bounds(v))-np.array(expected_support['local_bounds'])))<1e-4
        support_proof=artifacts.normalization_review(
            np.array(expected_support['local_vertices'])[np.array(expected_support['faces'])],v,s['triangles'])
        assert support_proof['status']=='BOUNDED_VERTEX_CONTRACTION_VERIFIED',support_proof
        assert not support_proof['collapsed_source_triangle_indices']
        enforcers.append({'name':s['name'],'subtype':s['subtype'],'local_bounds':parser.bounds(v),
                         'triangle_count':len(s['triangles']),'complete_enforcer_face_proof':support_proof})
    native=inv['native_result']
    assert native['return_code']==0 and inv['return_code']==0
    warnings=[p.get('warning_message','') for p in native.get('sliced_plates',[])]
    bed=reader.bed_and_counts(folder,project)
    first=gcode.index('; CHANGE_LAYER')
    temperatures=re.findall(r'^M10[49]\b[^\n;]*?\bS([-+\d.]+)',gcode[:first],re.M)
    assert temperatures and float(temperatures[-1])==255
    fields=['printer_model','nozzle_diameter','filament_type','curr_bed_type','layer_height',
        'initial_layer_print_height','wall_loops','sparse_infill_density','enable_support','support_type',
        'support_on_build_plate_only','support_top_z_distance','support_bottom_z_distance',
        'support_object_xy_distance','support_interface_top_layers','support_interface_spacing']
    result={'status':'CURRENT_ECLIP_SLICE_ARTIFACT_IDENTITY_PASS','part':inv['part'],
        'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_rigid_transform_max_error_mm':rigid_error,'normal_mesh':proof,
        'input_3mf_normal_mesh':input_proof,
        'mesh_stat':n['mesh_stat'],'frozen_scene_contract':contract,
        'placement':{'cad_to_oriented':pre.tolist(),'source_offset':offset.tolist(),
            'component':n['component'].tolist(),'build':archive['build'].tolist(),
            'input_build':input_archive['build'].tolist(),
            'mapping_method':'Full input/output oriented mesh correspondence in input assembly coordinates; authored-3MF source_offset is recorded but not treated as STL centring metadata.',
            'extruder_offset':nozzle.tolist(),'cad_to_command':command.tolist(),
            'input_local_to_command':local_command.tolist(),'build_growth_local_z':growth,
            'predicted_vs_native_bounds_error_mm':bounds_error},
        'input_local_to_command':local_command.tolist(),
        'support_enforcers':enforcers,'bed_and_paths':bed,'native_warnings':warnings,
        'resolved_process':{k:project.get(k) for k in fields},
        'last_nozzle_temperature_before_first_layer_c':float(temperatures[-1]),
        'evidence_sha256':evidence,'sources_and_artifacts_stable':all(sha(p)==h for p,h in evidence.items()),
        'limits':['Identity, placement, declared configuration and bed bounds only; feature paths and cleanup need separate review.',
            'Generic PETG and Textured PEI remain process assumptions; no physical dimensional, strength or return-force acceptance.'],
        'manufacturing_release':False,'physical_acceptance':False,'sent_to_printer':False}
    assert result['sources_and_artifacts_stable']
    output=folder/'artifact-review.json'
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'part':inv['part'],'status':result['status'],'triangles':len(source),
        'maximum_corner_displacement_mm':proof['maximum_corner_displacement_mm'],
        'warnings':warnings,'report':rel(output)},ensure_ascii=False),flush=True)
    return result

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--folder',type=Path,required=True)
    review(ap.parse_args().folder)
