#!/usr/bin/env python3
"""Read-only reuse audit of current legacy feeder instances against actual slices.

Run with /Applications/FreeCAD.app/Contents/Resources/bin/python. No slicer,
CAD export, printer connection, old report or old artifact mutation is performed.
All outputs stay beside this script (a dated run plus current report pointers).
"""
from pathlib import Path
import argparse
import collections
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'analysis'))
sys.path.insert(0, str(ROOT/'scripts'))
from cable_slice_artifacts import normalization_review
from review_cable_slice import read_stl

NS = {'m': 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
TOL = 0.00001
REPAIR_KEYS = ['edges_fixed', 'degenerate_facets', 'facets_removed',
               'facets_reversed', 'backwards_edges']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p):
    return str(Path(p).resolve().relative_to(ROOT))


def dump(p, value):
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')


def matrix(text):
    a = np.array(list(map(float, text.split()))) if text else np.array(
        [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0])
    if a.shape != (12,):
        raise ValueError('Unexpected 3MF affine matrix')
    M = np.eye(4)
    M[:3, :3] = a[:9].reshape(3, 3).T
    M[:3, 3] = a[9:]
    return M


def affine(points, M):
    return points @ M[:3, :3].T+M[:3, 3]


def volume(tri):
    return float(np.einsum('ij,ij->i', tri[:, 0],
                 np.cross(tri[:, 1], tri[:, 2])).sum()/6)


def bounds(tri):
    v = tri.reshape(-1, 3)
    return np.array([v.min(0), v.max(0)])


def intended_rotation(command):
    R = np.eye(3)
    for axis in 'xyz':
        flag = '--rotate-'+axis
        if flag not in command:
            continue
        a = math.radians(float(command[command.index(flag)+1]))
        c, s = math.cos(a), math.sin(a)
        part = {'x': [[1, 0, 0], [0, c, -s], [0, s, c]],
                'y': [[c, 0, s], [0, 1, 0], [-s, 0, c]],
                'z': [[c, -s, 0], [s, c, 0], [0, 0, 1]]}[axis]
        R = np.array(part) @ R
    return R


def archive_models(archive):
    """Recover exact archived normal meshes and the full command-space mapping."""
    result = {}
    with zipfile.ZipFile(archive) as z:
        main = ET.fromstring(z.read('3D/3dmodel.model'))
        config = ET.fromstring(z.read('Metadata/model_settings.config'))
        objects = {n.attrib['id']: n for n in main.findall('./m:resources/m:object', NS)}
        settings = {n.attrib['id']: n for n in config.findall('./object')}
        gcode = z.read('Metadata/plate_1.gcode')
        header = gcode.decode(errors='strict')
        raw = re.search(r'^; extruder_offset = ([^\n]+)', header, re.M).group(1).split(',')[0]
        nozzle = np.array([*map(float, raw.split('x')), 0.])
        for build in main.findall('./m:build/m:item', NS):
            oid = build.attrib['objectid']
            parts = settings[oid].findall('./part')
            components = objects[oid].findall('./m:components/m:component', NS)
            if len(parts) != 1 or len(components) != 1 or parts[0].attrib.get('subtype') != 'normal_part':
                raise ValueError('Expected one normal part per selected legacy build instance')
            part, component = parts[0], components[0]
            metadata = {m.attrib['key']: m.attrib['value'] for m in part.findall('./metadata')}
            member = next(v for k, v in component.attrib.items() if k.endswith('}path')).lstrip('/')
            model = ET.fromstring(z.read(member))
            resource = next(n for n in model.findall('./m:resources/m:object', NS)
                            if n.attrib['id'] == component.attrib['objectid'])
            vertices = np.array([[float(v.attrib[a]) for a in 'xyz']
                                 for v in resource.findall('./m:mesh/m:vertices/m:vertex', NS)])
            faces = np.array([[int(v.attrib[a]) for a in ['v1', 'v2', 'v3']]
                              for v in resource.findall('./m:mesh/m:triangles/m:triangle', NS)])
            offset = np.array([float(metadata['source_offset_'+a]) for a in 'xyz'])
            C, B = matrix(component.attrib.get('transform')), matrix(build.attrib.get('transform'))
            source_to_command = B @ C
            source_to_command[:3, 3] -= source_to_command[:3, :3] @ offset+nozzle
            name = Path(metadata['source_file']).stem
            if name in result:
                raise ValueError('Duplicated archived source instance')
            result[name] = dict(vertices=vertices+offset, faces=faces,
                metadata=metadata, repair_stats=part.find('./mesh_stat').attrib,
                mapping={'source_file': metadata['source_file'], 'archive_member': member,
                    'archive_object_id': component.attrib['objectid'], 'build_id': oid,
                    'source_offset': offset.tolist(), 'component_matrix': C.tolist(),
                    'build_matrix': B.tolist(), 'extruder_offset_from_gcode': nozzle.tolist(),
                    'current_cad_to_gcode_command': source_to_command.tolist(),
                    'current_cad_to_archived_source': np.eye(4).tolist()})
        project = json.loads(z.read('Metadata/project_settings.config'))
        return result, project, hashlib.sha256(gcode).hexdigest(), main.attrib.get('unit')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--inventory', type=Path, default=ROOT/'docs/cable-assembly-inventory.json')
    ap.add_argument('--export', type=Path, default=ROOT/'output/cable-scene-export/20260927T091627124663Z/report.json')
    ap.add_argument('--baseline', type=Path, default=ROOT/'output/print-review/final-feeder/baseline33/report.json')
    args = ap.parse_args()
    output = Path(__file__).resolve().parent
    run_dir = output/'runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    run_dir.mkdir(parents=True)
    I, E, O = [json.loads(p.read_text()) for p in [args.inventory, args.export, args.baseline]]
    record_path = args.baseline.parent/'record.json'
    record = json.loads(record_path.read_text())
    baseline_plate = {p['family']: p for p in O['plates']}
    current = {p['id']: p for p in E['parts']}
    eligible = [p for p in I['parts'] if p['role'] == 'printed' and p['group'] == 'feeder'
                and not p['id'].startswith('feeder/cable-') and p['id'] not in ['feeder/beam-grip', 'feeder/frame']]
    evidence = {}
    def watch(p):
        p = Path(p).resolve()
        evidence[rel(p)] = sha(p)
        return evidence[rel(p)]
    for p in [args.inventory, args.export, args.baseline, record_path, Path(__file__),
              ROOT/'analysis/cable_slice_artifacts.py', ROOT/'scripts/review_cable_slice.py']:
        watch(p)
    if E['status'] != 'CURRENT_SCENE_EXPORT_PASS' or sha(args.inventory) != E['inventory_sha256']:
        raise ValueError('Current inventory/export identity is not the specified authority')
    if watch(args.baseline) != record['baseline_report_sha256']:
        raise ValueError('Archived baseline report changed')
    for path, expected in E['source_sha256'].items():
        if watch(ROOT/path) != expected:
            raise ValueError('Current export source changed: '+path)
    for filename, key in [('support-access.json', 'support_access_report_sha256'),
                          ('shell-critical-features.json', 'shell_feature_report_sha256')]:
        if watch(args.baseline.parent/filename) != O[key]:
            raise ValueError('Original bounded process review evidence changed')
    plates, candidates = {}, {}
    for old in O['selected_plates']:
        if old['id'] in ['beam-grip', 'frame']:
            continue
        folder, archive = ROOT/old['slice_folder'], ROOT/old['gcode_3mf_path']
        invocation = folder/'invocation.json'
        inv = json.loads(invocation.read_text())
        objects, config, archived_gcode_sha, units = archive_models(archive)
        gcode, review = ROOT/old['gcode_path'], folder/'plate-review.json'
        invocation_sha = watch(invocation)
        archive_sha, gcode_sha = watch(archive), watch(gcode)
        review_sha = watch(review)
        original_archive = next(folder/n for n in inv['artifact_sha256'] if n.endswith('.3mf'))
        local_profiles = {name: watch(folder/(name+'.json')) for name in ['machine', 'process', 'filament']}
        original_files = [invocation, gcode, review, original_archive]+[folder/(n+'.json') for n in local_profiles]
        if old['id'] in ['positive-half', 'negative-half']:
            original_files.append(folder/'toolpath-review.json')
        preserved = all(watch(p) == record['evidence_sha256'].get(rel(p)) for p in original_files)
        native = inv['native_result']
        expected_ids = {r['id'] for r in old['source_stls']}
        named_inputs = {r['id']: r['sha256'] for r in inv['inputs']}
        old_hashes = {r['id']: r['sha256'] for r in old['source_stls']}
        R0 = intended_rotation(inv['command'])
        orientations = []
        repairs = []
        for obj in objects.values():
            R = np.array(obj['mapping']['current_cad_to_gcode_command'])[:3, :3]
            orientations.append(bool(np.max(np.abs(R.T@R-np.eye(3))) < 1e-7
                and abs(np.linalg.det(R)-1) < 1e-7
                and np.max(np.abs(R.T@np.array([0, 0, 1])-R0.T@np.array([0, 0, 1]))) < 1e-7))
            repairs.append(all(int(obj['repair_stats'].get(k, 0)) == 0 for k in REPAIR_KEYS))
        bounded = baseline_plate[old['id']]
        checks = {'original_evidence_bytes_preserved': preserved,
            'selected_3mf_sha_matches_baseline': archive_sha == old['gcode_3mf_sha256'],
            'selected_3mf_equals_original_slice_3mf': archive_sha == watch(original_archive),
            'external_gcode_sha_matches_baseline': gcode_sha == old['gcode_sha256'],
            'gcode_in_archive_exactly_matches_external': archived_gcode_sha == gcode_sha,
            'invocation_artifacts_match': all(watch(folder/n) == h for n, h in inv['artifact_sha256'].items()),
            'local_profiles_match_invocation': local_profiles == inv['local_profile_sha256'],
            'recorded_original_input_hashes_agree': named_inputs == old_hashes,
            'quantity_and_unique_archived_instances': old['quantity'] == len(objects) == len(expected_ids) and set(objects) == expected_ids,
            'native_success_no_warning': inv['return_code'] == native['return_code'] == 0 and
                all(not p.get('warning_message') for p in native['sliced_plates']),
            'original_plate_bounded_checks_recorded_pass': all(bounded['checks'].values()),
            'proper_rigid_rotation_and_intended_bed_normal': all(orientations),
            'no_slicer_reported_mesh_repairs': all(repairs),
            'mm_units': units == 'millimeter',
            'X1C_04': config.get('printer_model') == 'Bambu Lab X1 Carbon' and config.get('nozzle_diameter') == ['0.4'],
            'PETG': config.get('filament_type') == ['PETG'],
            'Textured_PEI_analysis_assumption_retained': config.get('curr_bed_type') == 'Textured PEI Plate',
            'layer_02_walls4_infill25': config.get('layer_height') == '0.2' and config.get('wall_loops') == '4'
                 and config.get('sparse_infill_density') == '25%'}
        plate_record = {'family': old['id'], 'slice_folder': old['slice_folder'],
            'quantity': old['quantity'], 'instance_ids': ['feeder/'+n for n in sorted(objects)],
            'old_report': rel(args.baseline), 'old_report_sha256': sha(args.baseline),
            'selected_3mf': rel(archive), 'selected_3mf_sha256': archive_sha,
            'original_3mf': rel(original_archive), 'gcode': rel(gcode), 'gcode_sha256': gcode_sha,
            'invocation_sha256': invocation_sha, 'plate_review_sha256': review_sha,
            'orientation_description': old['orientation'], 'actual_transforms': {n:o['mapping'] for n,o in objects.items()},
            'checks': checks, 'process_status': 'HISTORICAL_BOUNDED_OFFLINE_REVIEW_INTACT' if all(checks.values()) else 'HISTORICAL_EVIDENCE_FLAGGED',
            'resolved_process': {k:config.get(k) for k in ['printer_model', 'nozzle_diameter', 'filament_type', 'filament_settings_id',
                'curr_bed_type', 'layer_height', 'wall_loops', 'sparse_infill_density', 'enable_support', 'support_type',
                'support_object_xy_distance', 'support_top_z_distance', 'nozzle_temperature', 'nozzle_temperature_initial_layer']}}
        plates[old['id']] = plate_record
        for original in old['source_stls']:
            candidates['feeder/'+original['id']] = (old, original, objects[original['id']], plate_record)
    rows = []
    for item in eligible:
        model = current[item['id']]
        stl = ROOT/model['file']
        if watch(stl) != model['sha256']:
            raise ValueError('Current STL changed: '+item['id'])
        row = {'instance_id': item['id'], 'family': item['family'], 'name': item['name'],
            'current_stl': model['file'], 'current_stl_sha256': model['sha256'],
            'current_quantity': 1, 'slice_folder': None, 'old_report': rel(args.baseline),
            'identity_status': 'NO_HISTORICAL_SLICE_INSTANCE', 'process_status': 'NO_CURRENT_SLICE_EVIDENCE',
            'needs_reslice': True, 'reason': 'Current instance has no baseline33 selected plate; planned orientations are not sliced artifacts.'}
        if item['id'] in candidates:
            old, original, obj, plate = candidates[item['id']]
            tri = read_stl(stl)
            identity = normalization_review(tri, obj['vertices'], obj['faces'])
            oldtri = obj['vertices'][obj['faces']]
            # Exact oriented face multiset correspondence, no collapsed or extra
            # faces, and every corner bounded after the explicit identity map.
            correspondence = (identity['status'] == 'BOUNDED_VERTEX_CONTRACTION_VERIFIED'
                and not identity['collapsed_source_triangle_indices']
                and len(tri) == len(obj['faces'])
                and identity['maximum_corner_displacement_mm'] < TOL)
            byte_equal = model['sha256'] == original['sha256']
            identity.update(current_to_archived_source_transform=np.eye(4).tolist(),
                tolerance_mm=TOL, byte_identity=byte_equal,
                triangle_count_preserved=len(tri) == len(obj['faces']),
                current_bounds=bounds(tri).tolist(), archived_bounds=bounds(oldtri).tolist(),
                signed_volume_difference_mm3=volume(tri)-volume(oldtri),
                interpretation='An identity rigid transform, actual archive vertices plus documented source_offset, and an oriented face bijection. No fitted scale, reflection, name-only or bbox-only acceptance. Corner displacement bounds every corresponding triangle point by barycentric interpolation; this is precision-bounded mesh correspondence, not byte identity.')
            process_ok = all(plate['checks'].values())
            row.update(slice_folder=old['slice_folder'], selected_3mf=plate['selected_3mf'], gcode=plate['gcode'],
                old_stl_sha256=original['sha256'], plate_family=old['id'], plate_quantity=old['quantity'],
                old_orientation=old['orientation'], actual_mapping=obj['mapping'],
                identity_status=('BYTE_IDENTICAL_AND_ARCHIVE_FACE_BIJECTION' if byte_equal else 'ARCHIVE_FACE_BIJECTION_WITH_BOUNDED_CONVERSION')
                    if correspondence else 'CURRENT_GEOMETRY_DIFFERS_FROM_ARCHIVED_MESH',
                process_status='BOUNDED_OFFLINE_EVIDENCE_REUSABLE' if correspondence and process_ok else
                    ('HISTORICAL_PROCESS_ONLY_GEOMETRY_CHANGED' if not correspondence else 'HISTORICAL_PROCESS_EVIDENCE_FLAGGED'),
                needs_reslice=not(correspondence and process_ok), mesh_correspondence=identity,
                reason=('Complete current STL bytes match old input, and actual selected 3MF triangles, archived G-code, quantity and orientation are verified.' if byte_equal else
                    'STL bytes differ, but every actual selected 3MF oriented face corresponds one-to-one to current CAD under identity transform within the recorded conversion error; all native slice/process evidence is intact.')
                    if correspondence and process_ok else 'Archived mesh differs in face topology/geometry; same bounding box or family name is insufficient. The old G-code cannot manufacture the current part.' if not correspondence else 'Geometry correspondence passed but historical artifact/process checks failed.')
        rows.append(row)
    if not all(sha(ROOT/p) == h for p,h in evidence.items()):
        raise ValueError('An audited source or artifact changed while reading')
    reusable = [r for r in rows if not r['needs_reslice']]
    report = {'status': 'LEGACY_FEEDER_REUSE_AUDIT_COMPLETE_WITH_RESLICING_GAPS',
        'created_utc': datetime.now(timezone.utc).isoformat(), 'scope': 'Only feeder printed instances excluding cable-* and replaced beam-grip/frame.',
        'inventory': rel(args.inventory), 'current_export_report': rel(args.export), 'baseline_report': rel(args.baseline),
        'counts': {'in_scope_instances': len(rows), 'reusable_instances': len(reusable),
            'reusable_plates': len({r['plate_family'] for r in reusable}),
            'byte_identical_instances': sum(r['identity_status']=='BYTE_IDENTICAL_AND_ARCHIVE_FACE_BIJECTION' for r in rows),
            'nonbyte_but_face_bijection_instances': sum(r['identity_status']=='ARCHIVE_FACE_BIJECTION_WITH_BOUNDED_CONVERSION' for r in rows),
            'needs_reslice_instances': sum(r['needs_reslice'] for r in rows),
            'changed_geometry_instances': sum(r['identity_status']=='CURRENT_GEOMETRY_DIFFERS_FROM_ARCHIVED_MESH' for r in rows),
            'no_old_slice_instances': sum(r['identity_status']=='NO_HISTORICAL_SLICE_INSTANCE' for r in rows)},
        'mapping': rows, 'plates': list(plates.values()), 'source_and_artifact_sha256': evidence,
        'sources_and_artifacts_stable': True, 'rigid_identity_tolerance_mm': TOL,
        'reused_plate_quantities_verified': all(sum(r.get('plate_family')==f and not r['needs_reslice'] for r in rows)==plates[f]['quantity'] for f in {r['plate_family'] for r in reusable}),
        'notes': ['Historical source hashes are not required to equal current CAD: whole current STL/actual archive mesh correspondence is the geometry gate. Old invocations are not rewritten.',
            'A successful slice process is necessary but not the geometric or manufacturing acceptance test. Existing bounded path/support reviews are retained only for proven matching meshes.',
            'Only PEI was confirmed by the user; Textured PEI and Generic PETG remain the archived process assumptions, not confirmed plate texture or filament brand.',
            'No cutting, printing, printer submission or new slicing occurred. Strength, PETG release, tolerance, wear and physical mechanism acceptance remain open.'],
        'manufacturing_release': False, 'physical_acceptance': False, 'sent_to_printer': False}
    columns = ['instance_id', 'current_stl_sha256', 'slice_folder', 'old_report', 'identity_status', 'process_status', 'needs_reslice', 'reason']
    buf = io.StringIO(); writer = csv.DictWriter(buf, fieldnames=columns, extrasaction='ignore'); writer.writeheader(); writer.writerows(rows)
    for directory in [run_dir, output]:
        dump(directory/'report.json', report); dump(directory/'mapping.json', rows)
        (directory/'mapping.csv').write_text(buf.getvalue())
    dump(output/'latest.json', {'run':rel(run_dir), 'report_sha256':sha(run_dir/'report.json'), 'script_sha256':sha(__file__)})
    print(json.dumps({'output':rel(run_dir), **report['counts'], 'report_sha256':sha(output/'report.json')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
