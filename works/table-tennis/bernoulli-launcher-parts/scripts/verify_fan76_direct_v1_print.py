#!/usr/bin/env python3
"""Audit the native five-piece Ø76 slice, without contacting a printer.

This variant has recessed bayonet roofs at Z21.5, not Ø41 radial lugs.
Reuse only mesh/transform/G-code parsers from the other package's auditor.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from verify_fan_tee_v5_print import (
    extrusion_paths, geometry, nozzle_xy_offset, sha, support_paths, thread_wall_screen,
)


def audit(package, project, layout_path, *, expected_parts=5, mother_z_interval=(76, 176)):
    layout = json.loads(layout_path.read_text())
    baseline = json.loads((layout_path.parent / 'config/native-baseline.json').read_text())
    records = geometry(project, layout, expected_parts=expected_parts)
    with ZipFile(package) as archive:
        settings = json.loads(archive.read('Metadata/project_settings.config'))
        gcode_files = [n for n in archive.namelist() if n.endswith('.gcode')]
        assert len(gcode_files) == 1
        gcode = archive.read(gcode_files[0]).decode()
        slice_info = ET.fromstring(archive.read('Metadata/slice_info.config'))
        assert len(slice_info.findall('plate')) == 1
        plate = {m.get('key'): m.get('value') for m in slice_info.find('plate').findall('metadata')}
        sliced_objects = list(slice_info.iter('object'))
    with ZipFile(project) as archive:
        project_settings = json.loads(archive.read('Metadata/project_settings.config'))
    segments, counts = support_paths(gcode)
    xy_offset = nozzle_xy_offset(settings)
    wall_screen = thread_wall_screen(gcode, records, mother_z_interval, xy_offset)
    body = next(r for r in records if r['role'] == 'connector')
    tf, offset = body['transform'], body['source_offset']

    def local(point):
        x, y = point[0] + xy_offset[0] - tf[9], point[1] + xy_offset[1] - tf[10]
        return (tf[0]*x + tf[1]*y + offset[0],
                tf[3]*x + tf[4]*y + offset[1], point[2] - tf[11] + offset[2])

    local_segments = [dict(s, start=local(s['start']), end=local(s['end'])) for s in segments]
    outside = [s for s in local_segments if any(
        p[2] > 21.400001 or math.hypot(*p[:2]) > 45 for p in (s['start'], s['end']))]
    roof_layers = {1: [], -1: []}
    for segment in extrusion_paths(gcode):
        if segment['z'] > 23:
            break
        if segment['z'] < 21.5 or segment['role'] not in {'Bridge', 'Overhang wall'}:
            continue
        for point in (segment['start'], segment['end']):
            p = local(point)
            for side in (1, -1):
                angle = math.degrees(math.atan2(p[1]*side, p[0]*side)) % 360
                if 38.3 <= math.hypot(*p[:2]) <= 41.1 and 83.7 <= angle <= 114.3:
                    roof_layers[side].append(segment['z'])
    # Tooth contact is excluded separately by Z. This roof audit only applies
    # to shells preserving the original Z21.5 bayonet collar geometry.
    contacts = []
    for side in (1, -1):
        near_roof = []
        for s in local_segments:
            for p in (s['start'], s['end']):
                angle = math.degrees(math.atan2(p[1]*side, p[0]*side)) % 360
                if 38.3 <= math.hypot(*p[:2]) <= 41.1 and 83.7 <= angle <= 114.3 and p[2] >= 20.8:
                    near_roof.append((p, angle, s['role']))
        gaps = [21.5 - p[2] for p, _, _ in near_roof]
        angles = [a for _, a, _ in near_roof]
        # Compare deposited surfaces, not the CAD roof's mid-layer location:
        # the Z21.5 roof is first extruded at Z21.8; .2-mm layer bottom Z21.6
        # above support top Z21.4 gives the configured .2-mm physical gap.
        first_roof_z = min(roof_layers[side]) if roof_layers[side] else None
        support_top = max(p[2] for p, _, _ in near_roof) if near_roof else None
        layer_height = float(settings['layer_height'])
        deposited_gap = first_roof_z - layer_height - support_top if first_roof_z and support_top else None
        contacts.append({
            'side_y': side, 'roof_z_mm': 21.5, 'contact_endpoints': len(gaps),
            'feature_counts': dict(Counter(role for _, _, role in near_roof)),
            'gap_to_cad_roof_mm': [min(gaps), max(gaps)] if gaps else None,
            'first_deposited_roof_z_mm': first_roof_z,
            'support_top_z_mm': support_top, 'deposited_surface_gap_mm': deposited_gap,
            'angular_span_degrees': [min(angles), max(angles)] if angles else None,
            'pass': len(gaps) >= 10 and deposited_gap is not None and .15 <= deposited_gap <= .3
                    and max(angles) - min(angles) >= 10,
        })
    prep = gcode.split('; Z_HEIGHT:', 1)[0]
    markers = {name: bool(re.search(pattern, prep, re.M)) for name, pattern in {
        'home': r'^\s*G28(?:\s|$)', 'level': r'^\s*G29(?:\s|$)',
        'bed_wait': r'^\s*M190(?:\s|$)', 'nozzle_wait': r'^\s*M109(?:\s|$)',
        'ams': r'^\s*M620(?:\s|$)',
    }.items()}
    checks = {
        'exact_source_meshes': len(records) == expected_parts and all(r['all_triangles_match_at_0_001_mm'] for r in records),
        'exact_sliced_object_count': len(sliced_objects) == expected_parts
            and all(o.get('skipped', 'false') == 'false' for o in sliced_objects)
            and Counter(o.get('name') for o in sliced_objects) == Counter(r['source'] for r in records),
        'native_geometry_slice_settings_match': project_settings == settings,
        'x1c_04': settings.get('printer_settings_id') == 'Bambu Lab X1 Carbon 0.4 nozzle'
            and settings.get('nozzle_diameter') == ['0.4'] and plate.get('printer_model_id') == 'BL-P001',
        'petg': settings.get('filament_type') == ['PETG'],
        'startup_preserved': hashlib.sha256(settings['machine_start_gcode'].encode()).hexdigest() == baseline['startup_sha256'],
        'end_preserved': hashlib.sha256(settings['machine_end_gcode'].encode()).hexdigest() == baseline['end_sha256'],
        'prep_commands_exist': all(markers.values()),
        'linear_extrusion_paths': settings.get('enable_arc_fitting') == '0',
        'tree_support_enabled': settings.get('enable_support') == '1' and settings.get('support_type') == 'tree(auto)',
        'both_bayonet_roofs_have_contacts': all(c['pass'] for c in contacts),
        'support_only_in_bayonet_collar': bool(segments) and not outside,
        'thread_root_and_crest_survive_native_slicing': wall_screen['pass'],
    }
    return {
        'status': ('DIGITAL_FIVE_PART_SLICE_PASS' if expected_parts == 5 else 'DIGITAL_SINGLE_BODY_SLICE_PASS') if all(checks.values()) else 'SLICE_REVIEW_REQUIRED',
        'expected_part_count': expected_parts, 'mother_thread_screen_z_mm': mother_z_interval,
        'checks': checks, 'package': str(package), 'package_sha256': sha(package),
        'native_project': str(project), 'project_sha256': sha(project), 'parts': records,
        'layers': gcode.count('; Z_HEIGHT:'), 'plate_info': plate,
        'support_counts': dict(counts),
        'support_z_range_mm': [min(s['z'] for s in segments), max(s['z'] for s in segments)] if segments else None,
        'support_outside_bayonet_collar': len(outside), 'bayonet_roof_contacts': contacts,
        'thread_wall_screen': wall_screen, 'gcode_to_bed_xy_offset_mm': xy_offset,
        'preparation_markers': markers, 'commands_do_not_prove_machine_execution': True,
        'physical_acceptance': False,
        'scope': 'Digital source/slice and collar-support screen; removal access and actual print/fit still require observation.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--layout', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    result = audit(args.package.resolve(), args.project.resolve(), args.layout.resolve())
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        args.report.write_text(text + '\n')
    print(text)
    return int(not all(result['checks'].values()))


if __name__ == '__main__':
    raise SystemExit(main())
