#!/usr/bin/env python3
"""Read an existing cable-input slice; never slice, change CAD, or send a print.

Run with FreeCAD's Python (numpy/shapely/matplotlib), --folder SLICE_DIRECTORY.
The ROI dimensions are locked to a known input CAD identity. Toolpaths are
mapped back through the actual 3MF placement and invocation pre-orientation.
Bead/ROI intersection is a conservative layer-slab projection, not measured
plastic. Bridge command lengths are never called unsupported spans.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import struct
import sys
import xml.etree.ElementTree as ET
import zipfile

import numpy as np
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
INPUT_SOURCE = ROOT / 'cad/cable-trigger-input.scad'
ROI_SOURCE_SHA = '01d2b74807dd584a6dfe855fa36b9ef11929df49453812943dfd080756f98e84'
ARC_ERROR = .00125
BUFFER_ERROR = .002
NS = {'m': 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
IGNORED = {'Custom', 'Brim', 'Skirt', 'Prime tower', 'Prime tower infill'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def path_from(value, base=ROOT):
    p = Path(value)
    return p if p.is_absolute() else base / p


def affine(points, matrix):
    return np.asarray(points) @ matrix[:3, :3].T + matrix[:3, 3]


def mesh_vertices(path):
    data = Path(path).read_bytes()
    if len(data) >= 84:
        n = struct.unpack_from('<I', data, 80)[0]
        if len(data) == 84 + 50 * n:
            dtype = np.dtype([('normal', '<f4', 3), ('vertices', '<f4', (3, 3)), ('attr', '<u2')])
            return np.frombuffer(data, dtype=dtype, offset=84)['vertices'].reshape(-1, 3).astype(float)
    values = re.findall(rb'vertex\s+([-+eE.0-9]+)\s+([-+eE.0-9]+)\s+([-+eE.0-9]+)', data)
    if not values:
        raise ValueError(f'No STL vertices: {path}')
    return np.asarray(values, dtype=float)


def bounds(points):
    return [np.min(points, axis=0).tolist(), np.max(points, axis=0).tolist()]


def three_mf_matrix(text):
    v = np.array(list(map(float, text.split()))) if text else np.r_[np.eye(3).T.flatten(), [0, 0, 0]]
    if len(v) != 12:
        raise ValueError('Expected 3MF 12-entry transform')
    a = np.eye(4)
    a[:3, :3] = v[:9].reshape(3, 3).T
    a[:3, 3] = v[9:]
    return a


def slice_mapping(folder, invocation):
    """Recover the source-oriented-STL -> commanded-nozzle mapping explicitly."""
    source = path_from(invocation['input']['file'])
    oriented = path_from(invocation['oriented']['file'])
    for path, expected in [(source, invocation['input']['sha256']), (oriented, invocation['oriented']['sha256'])]:
        if sha(path) != expected:
            raise ValueError(f'Identity mismatch: {path}')
    for name, expected in invocation['source_sha256_at_start'].items():
        if sha(path_from(name)) != expected:
            raise ValueError(f'CAD/dependency identity changed: {name}')
    for name, expected in invocation.get('artifact_sha256', {}).items():
        if (folder / name).is_file() and sha(folder / name) != expected:
            raise ValueError(f'Slice artifact identity changed: {name}')
    if sha(INPUT_SOURCE) != ROI_SOURCE_SHA:
        raise ValueError('ROI source changed; dimensions and axes require a fresh review')
    pre = np.array(invocation['cad_to_oriented'], dtype=float)
    if pre.shape != (4, 4) or not np.allclose(pre[3], [0, 0, 0, 1]):
        raise ValueError('cad_to_oriented must be a 4x4 column-vector affine matrix')
    expected_vertices = affine(mesh_vertices(source), pre)
    oriented_vertices = mesh_vertices(oriented)
    pre_error = float(np.max(np.abs(np.asarray(bounds(expected_vertices)) - np.asarray(bounds(oriented_vertices)))))
    if pre_error > .002:
        raise ValueError(f'Pre-orientation STL bounds do not match stated matrix: {pre_error}')

    project = folder / 'slice-review.3mf'
    with zipfile.ZipFile(project) as archive:
        main = ET.fromstring(archive.read('3D/3dmodel.model'))
        settings = ET.fromstring(archive.read('Metadata/model_settings.config'))
        items = main.findall('./m:build/m:item', NS)
        if len(items) != 1:
            raise ValueError('Review requires exactly one build object')
        build = items[0]
        obj = main.find(f'./m:resources/m:object[@id="{build.attrib["objectid"]}"]', NS)
        components = obj.findall('./m:components/m:component', NS)
        if len(components) != 1:
            raise ValueError('Review requires exactly one component')
        component = components[0]
        parts = settings.findall('./object/part')
        if len(parts) != 1:
            raise ValueError('Ambiguous part metadata')
        meta = {x.attrib.get('key'): x.attrib.get('value') for x in parts[0].findall('metadata')}
        offset = np.array([float(meta['source_offset_' + a]) for a in 'xyz'])
        part_path = next((v for k, v in component.attrib.items() if k.endswith('}path')), None)
        part_root = ET.fromstring(archive.read(part_path.lstrip('/'))) if part_path else main
        target = part_root.find(f'./m:resources/m:object[@id="{component.attrib["objectid"]}"]', NS)
        vertices = target.findall('./m:mesh/m:vertices/m:vertex', NS)
        if not vertices:
            raise ValueError('Cannot verify source_offset against project mesh vertices')
        verts = np.array([[float(v.attrib[a]) for a in 'xyz'] for v in vertices])
        centered_error = float(np.max(np.abs(np.asarray(bounds(verts + offset)) - np.asarray(bounds(oriented_vertices)))))
        if centered_error > .002:
            raise ValueError(f'Project mesh/source_offset differs from oriented STL bounds: {centered_error}')
        component_matrix = three_mf_matrix(component.attrib.get('transform'))
        build_matrix = three_mf_matrix(build.attrib.get('transform'))
    header = (folder / 'plate_1.gcode').read_text()
    match = re.search(r'^; extruder_offset = ([^\n]+)', header, re.M)
    if not match:
        raise ValueError('Missing extruder_offset; refusing implicit zero')
    raw_offsets = match.group(1).strip().split(',')
    if len(raw_offsets) != 1:
        raise ValueError('Multiple nozzle offsets need tool-change-aware review')
    extruder = np.array([*map(float, raw_offsets[0].split('x')), 0.])
    uncenter = np.eye(4)
    uncenter[:3, 3] = -offset
    nozzle = np.eye(4)
    nozzle[:3, 3] = -extruder
    cad_to_command = nozzle @ build_matrix @ component_matrix @ uncenter @ pre
    s = math.sqrt(.5)
    local_to_cad = np.array([[-s, s, 0, 75], [0, 0, 1, -82], [s, s, 0, 5], [0, 0, 0, 1.]])
    local_to_command = cad_to_command @ local_to_cad
    R = local_to_command[:3, :3]
    if not np.allclose(R.T @ R, np.eye(3), atol=1e-5) or not np.isclose(np.linalg.det(R), 1, atol=1e-5):
        raise ValueError('Review only supports rigid, unscaled, non-mirrored placement')
    if not np.allclose(R[:, 2], [0, 0, 1], atol=1e-5):
        raise ValueError('ROIs assume selected body/lever local +Z layer growth')
    return np.linalg.inv(local_to_command), {
        'cad_to_oriented': pre.tolist(), 'component': component_matrix.tolist(),
        'build': build_matrix.tolist(), 'source_offset': offset.tolist(),
        'extruder_offset': extruder.tolist(), 'cad_to_command': cad_to_command.tolist(),
        'local_to_command': local_to_command.tolist(), 'command_to_local': np.linalg.inv(local_to_command).tolist(),
        'pre_orientation_bounds_error_mm': pre_error, 'project_source_bounds_error_mm': centered_error,
        'input_stl_sha256': sha(source), 'oriented_stl_sha256': sha(oriented),
        'gcode_sha256': sha(folder / 'plate_1.gcode'), 'project_sha256': sha(project),
    }


@dataclass
class PathRecord:
    line: int
    stroke: int
    layer: float
    height: float
    feature: str
    width: float
    points: np.ndarray


def extrusion_paths(lines):
    """G0/1/2/3 + M82/83 + G90/91 + G92, including same-XY full circles.

    Straight moves keep exact endpoints. Arc chord sagitta <= ARC_ERROR.
    Metadata is taken from emitted G-code, not guessed from a process preset.
    """
    pos = np.zeros(3)
    absolute_xyz = True
    relative_e = True
    last_e = 0.
    layer = None
    height = None
    width = None
    feature = ''
    stroke = 0
    prior_extruded = False
    for line_no, line in enumerate(lines, 1):
        for prefix, key in [('; Z_HEIGHT:', 'layer'), ('; LAYER_HEIGHT:', 'height'), ('; LINE_WIDTH:', 'width')]:
            if line.startswith(prefix):
                value = float(line.split(':', 1)[1])
                if key == 'layer':
                    layer = value
                elif key == 'height':
                    height = value
                else:
                    width = value
        if line.startswith('; FEATURE:'):
            new_feature = line.split(':', 1)[1].strip()
            if new_feature != feature:
                prior_extruded = False
            feature = new_feature
        code = line.split(';', 1)[0].strip()
        if not code:
            continue
        token = code.split()[0]
        if token == 'G90': absolute_xyz = True
        if token == 'G91': absolute_xyz = False
        if token == 'M83': relative_e = True
        if token == 'M82': relative_e = False
        if token in {'G20', 'G18', 'G19'}:
            raise ValueError(f'Unsupported units/arc plane at line {line_no}: {code}')
        values = {k: float(v) for k, v in re.findall(r'([XYZEFIJKR])\s*([-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?)', code)}
        if token == 'G92':
            for k, a in enumerate('XYZ'):
                if a in values: pos[k] = values[a]
            if 'E' in values: last_e = values['E']
            continue
        if token not in {'G0', 'G1', 'G2', 'G3'}:
            continue
        target = pos.copy()
        for k, a in enumerate('XYZ'):
            if a in values: target[k] = values[a] + (0 if absolute_xyz else pos[k])
        e = values.get('E', 0) if relative_e else values.get('E', last_e) - last_e
        if 'E' in values: last_e = last_e + values['E'] if relative_e else values['E']
        moving = np.linalg.norm(target - pos) > 1e-12 or token in {'G2', 'G3'}
        emitted = layer is not None and e > 0 and moving
        if emitted:
            if height is None or width is None or not feature:
                raise ValueError(f'Missing layer/line metadata before extrusion line {line_no}')
            if not prior_extruded:
                stroke += 1
            if token in {'G2', 'G3'}:
                if 'R' in values or ('I' not in values and 'J' not in values):
                    raise ValueError(f'Arc needs explicit relative I/J at line {line_no}')
                center = pos[:2] + [values.get('I', 0), values.get('J', 0)]
                radius = np.linalg.norm(pos[:2] - center)
                if radius <= 0:
                    raise ValueError(f'Zero-radius arc at line {line_no}')
                if abs(np.linalg.norm(target[:2] - center) - radius) > .02:
                    raise ValueError(f'Arc radii disagree at line {line_no}')
                a0 = math.atan2(pos[1] - center[1], pos[0] - center[0])
                a1 = math.atan2(target[1] - center[1], target[0] - center[0])
                da = (a1 - a0) % (2 * math.pi) if token == 'G3' else -((a0 - a1) % (2 * math.pi))
                if abs(da) < 1e-10: da = 2 * math.pi if token == 'G3' else -2 * math.pi
                max_angle = min(.1, 2 * math.acos(max(-1, 1 - ARC_ERROR / radius)))
                n = max(2, math.ceil(abs(da) / max_angle))
                angles = np.linspace(a0, a0 + da, n + 1)
                points = np.column_stack([center[0] + radius * np.cos(angles), center[1] + radius * np.sin(angles), np.linspace(pos[2], target[2], n + 1)])
                points[-1] = target
            else:
                points = np.array([pos.copy(), target.copy()])
            yield PathRecord(line_no, stroke, layer, height, feature, width, points)
        if moving or e < 0:
            prior_extruded = emitted
        pos = target


def sector(r0, r1, a0, a1):
    n = max(2, math.ceil((a1 - a0) / 2))
    angles = np.radians(np.linspace(a0, a1, n + 1))
    outer = np.column_stack([r1 * np.cos(angles), r1 * np.sin(angles)])
    inner = np.column_stack([r0 * np.cos(angles[::-1]), r0 * np.sin(angles[::-1])])
    return Polygon(np.vstack([outer, inner]))


def roi_specs(selector):
    if selector == 'ci_body':
        return [
            {'name': 'stop_long_tunnel_interior', 'kind': 'xcylinder', 'x': [-64, -42], 'y': -24, 'z': 2, 'radius': 3.6, 'zrange': [-1.6, 5.6], 'roof': 5.6, 'access': 'Local -X via Ø7.2; bounded interior window, not the entire external entry.'},
            {'name': 'stop_nut_chamber', 'kind': 'xhex', 'x': [-38.3, -32.6], 'y': -24, 'z': 2, 'af': 5.8, 'zrange': [-.9, 4.9], 'roof': 4.9, 'access': 'Local -X through long Ø7.2 service bore; not open at +Z.'},
            {'name': 'stop_M3_exit', 'kind': 'xcylinder', 'x': [-32.6, -29], 'y': -24, 'z': 2, 'radius': 1.7, 'zrange': [.3, 3.7], 'roof': 3.7, 'access': 'Local +X through Ø3.4 exit before stop screw installation.'},
            {'name': 'M6_adjuster_through_seat', 'kind': 'xcylinder', 'x': [-45, -37], 'y': 60, 'z': 2, 'radius': 3.2, 'zrange': [-1.2, 5.2], 'roof': 5.2, 'access': 'Both local X ends, nominal seat length8 mm.'},
        ]
    if selector == 'ci_lever':
        return [
            {'name': 'R60_face_open_core_groove', 'kind': 'sector', 'r': [58.9, 61.1], 'angles': [44, 116], 'zrange': [.9, 7.5], 'roof': None, 'access': 'Open +local Z before fixed cover assembly.'},
            {'name': 'ball_terminal_pocket', 'kind': 'ball_entry', 'center': [60 / math.sqrt(2), 60 / math.sqrt(2), 2], 'radius': 2.8, 'zrange': [-.8, 7.5], 'roof': None, 'access': 'Open +local Z via Ø5.6 entry, lower hemisphere floor.'},
            {'name': 'tangent_2p2mm_window', 'kind': 'sector', 'r': [60.8, 64], 'angles': [89, 115], 'zrange': [.9, 3.1], 'roof': 3.1, 'access': 'Radially outward, nominal2.2 mm height. PETG removal force not certified.'},
        ]
    raise ValueError(f'Unsupported selector {selector}')


def roi_projection(spec, bottom, top):
    """Void projected over the entire actual deposited-layer slab (conservative)."""
    lo, hi = max(bottom, spec['zrange'][0]), min(top, spec['zrange'][1])
    if hi <= lo + 1e-9:
        return Polygon()
    kind = spec['kind']
    if kind == 'sector':
        return sector(*spec['r'], *spec['angles'])
    if kind == 'ball_entry':
        c = spec['center']
        z = max(lo, min(c[2], hi))
        radius = spec['radius'] if hi >= c[2] else math.sqrt(max(0, spec['radius'] ** 2 - (z - c[2]) ** 2))
        return Point(c[:2]).buffer(radius, quad_segs=72)
    if kind == 'xcylinder':
        closest = max(lo, min(spec['z'], hi))
        radius = math.sqrt(max(0, spec['radius'] ** 2 - (closest - spec['z']) ** 2))
        return box(spec['x'][0], spec['y'] - radius, spec['x'][1], spec['y'] + radius)
    if kind == 'xhex':
        r = spec['af'] / math.sqrt(3)
        angles = np.radians(np.arange(30, 390, 60))
        yz = Polygon(np.column_stack([spec['y'] + r * np.sin(angles), spec['z'] - r * np.cos(angles)]))
        slab = yz.intersection(box(-1000, lo, 1000, hi))
        return box(spec['x'][0], slab.bounds[0], spec['x'][1], slab.bounds[2]) if not slab.is_empty else Polygon()
    raise ValueError(kind)


def full_projection(spec):
    return roi_projection(spec, *spec['zrange'])


def lines_of(geometry):
    if geometry.is_empty:
        return []
    if geometry.geom_type in {'LineString', 'LinearRing'}:
        return [geometry]
    return [line for child in getattr(geometry, 'geoms', []) for line in lines_of(child)]


def bead(line, width, extra=BUFFER_ERROR):
    # Circumscribe the round end caps: numerical polygon approximation must
    # not reduce the declared half-width footprint used for absence checks.
    return line.buffer((width / 2 + extra) / math.cos(math.pi / 96), quad_segs=24)


def classify(feature):
    return 'Support' if feature.startswith('Support') else 'Bridge' if 'Bridge' in feature else 'Overhang' if 'Overhang' in feature else 'Model'


def downward_planar_faces(source, cad_to_local):
    """Whole-input-STL planar undersides, independent of hand-picked hole ROIs."""
    triangles = affine(mesh_vertices(source), cad_to_local).reshape(-1, 3, 3)
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    bed = float(triangles[:, :, 2].min())
    selected = (np.ptp(triangles[:, :, 2], axis=1) < 1e-5) & (normals[:, 2] < -1e-7)
    grouped = defaultdict(list)
    for triangle in triangles[selected]:
        z = round(float(triangle[:, 2].mean()), 5)
        if z <= bed + .001: continue
        grouped[z].append(Polygon(triangle[:, :2]))
    result = []
    for z, polygons in sorted(grouped.items()):
        merged = unary_union(polygons)
        components = [merged] if merged.geom_type == 'Polygon' else list(merged.geoms)
        for index, polygon in enumerate(components):
            if polygon.area > .01:
                result.append({'name': f'downface_z{z:g}_{index}', 'source_z': z, 'area_mm2': polygon.area, 'polygon': polygon})
    return result


def underlay_runs(line, prior_model):
    """Continuous path fragments lacking previous-model centerline underlay.

    These are geometric candidate gaps, not mechanical unsupported-span or
    successful-bridge claims. End contacts may be too short for real anchorage.
    """
    return [{'length_mm': float(g.length), 'bounds_xy': list(g.bounds),
             'both_ends_touch_previous_model_footprint': all(prior_model.distance(Point(p)) < .005 for p in [g.coords[0], g.coords[-1]]),
             'geometry': g}
            for g in lines_of(line.difference(prior_model)) if g.length > .005]


def review(folder):
    folder = Path(folder).resolve()
    output = folder / 'input-feature-review'
    output.mkdir(parents=True, exist_ok=True)
    inv = json.loads((folder / 'invocation.json').read_text())
    selector = inv.get('selector') or {'cable-input-body': 'ci_body', 'cable-input-lever': 'ci_lever'}[inv['part']]
    specs = roi_specs(selector)
    inverse, mapping = slice_mapping(folder, inv)
    cad_to_local = inverse @ np.array(mapping['cad_to_command'])
    downfaces = downward_planar_faces(path_from(inv['input']['file']), cad_to_local)
    records = []
    counts = Counter()
    layer_tops = set()
    model_tops = set()
    footprints = defaultdict(list)
    z_bounds = {}
    focus = unary_union([full_projection(s).buffer(8) for s in specs] + [d['polygon'].buffer(4) for d in downfaces])
    focus_bounds = focus.bounds
    for record in extrusion_paths((folder / 'plate_1.gcode').open()):
        counts[record.feature] += 1
        if record.feature in IGNORED:
            continue
        q = affine(record.points, inverse)
        if np.ptp(q[:, 2]) > 1e-5:
            raise ValueError(f'Nonplanar model extrusion at G-code line{record.line}; needs separate review')
        z = float(q[0, 2])
        layer_tops.add(round(z, 7))
        if not record.feature.startswith('Support'):
            model_tops.add(round(z, 7))
        # These two candidates have local+Z print growth; width remains in XY.
        record.points = q
        record.layer = z
        p = LineString(q[:, :2])
        if p.bounds[2] < focus_bounds[0] or p.bounds[0] > focus_bounds[2] or p.bounds[3] < focus_bounds[1] or p.bounds[1] > focus_bounds[3]:
            continue
        if p.distance(focus) > record.width / 2 + BUFFER_ERROR:
            continue
        records.append((record, p))
        key = round(z, 7)
        z_bounds[key] = [z - record.height, z]
        if not record.feature.startswith('Support'):
            footprints[key].append((p, record.width))

    ordered_tops = sorted(model_tops)
    footprint_cache = {}
    def prior_footprint(z):
        below = [v for v in ordered_tops if v < z - 1e-6]
        if not below:
            return None, Polygon()
        prior = below[-1]
        if prior not in footprint_cache:
            footprint_cache[prior] = unary_union([bead(p, w, 0) for p, w in footprints.get(prior, [])])
        return prior, footprint_cache[prior]

    summaries = []
    plot_data = {}
    for spec in specs:
        occupied = []
        classes = Counter()
        z_layers = defaultdict(lambda: {'Support': 0, 'Model': 0, 'Bridge': 0, 'Overhang': 0})
        outline = full_projection(spec)
        selected = []
        for r, p in records:
            shape = roi_projection(spec, r.layer - r.height, r.layer)
            if shape.is_empty or p.distance(shape) > r.width / 2 + BUFFER_ERROR:
                continue
            footprint = bead(p, r.width)
            intersection = footprint.intersection(shape)
            if intersection.area < 1e-8:
                continue
            cls = classify(r.feature)
            classes[cls] += 1
            z_layers[round(r.layer, 7)][cls] += 1
            selected.append((r, p))
            if cls == 'Support':
                occupied.append({'gcode_line': r.line, 'stroke': r.stroke, 'feature': r.feature,
                                 'layer_slab_local_z': [r.layer - r.height, r.layer], 'declared_width_mm': r.width,
                                 'bead_projection_intersection_area_mm2': intersection.area,
                                 'intersection_bounds_local_xy': list(intersection.bounds),
                                 'centerline_length_in_projected_void_mm': p.intersection(shape).length})
        roof = spec.get('roof')
        bridge_review = []
        if roof is not None:
            # The first two emitted model layers crossing/above the nominal
            # roof expose layer quantization and any bridged lip initiation.
            target_layers = sorted({round(r.layer, 7) for r, p in records
                                    if r.layer >= roof - 1e-6 and r.layer - r.height < roof + .41 and p.distance(outline) < 2})[:3]
            for z in target_layers:
                prior_z, prior = prior_footprint(z)
                strokes = defaultdict(list)
                for r, p in records:
                    if abs(r.layer - z) < 1e-6 and not r.feature.startswith('Support') and p.distance(outline) < 3:
                        strokes[(r.stroke, r.feature, r.width)].append((r, p))
                paths = []
                for (stroke, feature, width), segments in strokes.items():
                    # A stroke may have skipped out-of-focus commands. Merge
                    # only genuinely connected endpoints; never bridge gaps.
                    chunks = []
                    for r, p in segments:
                        if chunks and np.linalg.norm(np.array(chunks[-1][-1]) - np.array(p.coords[0])) < 1e-5:
                            chunks[-1].extend(list(p.coords)[1:])
                        else:
                            chunks.append(list(p.coords))
                    for coords in chunks:
                        path = LineString(coords)
                        if path.distance(outline) > width / 2 + BUFFER_ERROR:
                            continue
                        gaps = underlay_runs(path, prior)
                        relevant = [g for g in gaps if g['geometry'].distance(outline) <= width / 2 + BUFFER_ERROR]
                        if not relevant:
                            continue
                        # A long centerline can lie beyond the previous layer
                        # while its bead still overlaps sideways. Report the
                        # stronger no-overlap condition separately, not as a
                        # bridge span. The printed bead shape is still nominal.
                        overlap_region = prior.buffer(width / 2, quad_segs=24)
                        no_overlap = [g for g in underlay_runs(path, overlap_region)
                                      if g['geometry'].distance(outline) <= width / 2 + BUFFER_ERROR]
                        def serialize_gap(g):
                            result = {k: v for k, v in g.items() if k != 'geometry'}
                            result['length_within_source_roi_projection_mm'] = g['geometry'].intersection(outline).length
                            return result
                        paths.append({'stroke': stroke, 'feature': feature, 'gcode_lines': [v[0].line for v in segments],
                                      'continuous_path_length_mm': path.length,
                                      'centerline_without_previous_model_footprint': [serialize_gap(g) for g in relevant],
                                      'path_without_any_declared_bead_overlap_with_previous_model': [serialize_gap(g) for g in no_overlap]})
                bridge_review.append({'local_z_top': z, 'nominal_roof_z': roof, 'previous_emitted_layer_z': prior_z,
                                      'model_paths_with_geometric_underlay_gaps': paths,
                                      'max_geometric_centerline_gap_touching_roi_mm': max([g['length_mm'] for p in paths for g in p['centerline_without_previous_model_footprint']], default=0),
                                      'max_continuous_no_bead_overlap_path_touching_roi_mm': max([g['length_mm'] for p in paths for g in p['path_without_any_declared_bead_overlap_with_previous_model']], default=0),
                                      'interpretation': 'Curved path length relative to previous actual model-bead footprints only; not a free span. Centerline underlay and any sideways bead overlap are separate. Support is not counted as a model anchor.'})
        plot_data[spec['name']] = (spec, selected, bridge_review)
        summaries.append({'roi': spec, 'support_path_hits': len(occupied), 'support_paths': occupied,
                          'support_centerline_hits_in_projected_void': sum(v['centerline_length_in_projected_void_mm'] > 1e-6 for v in occupied),
                          'bead_projection_hit_counts': dict(classes), 'layer_hit_counts': [{'local_z_top': z, **v} for z, v in sorted(z_layers.items())],
                          'roof_model_path_review': bridge_review,
                          'support_absence_in_reviewed_void': not occupied,
                          'cleanup_access_assessed_from_actual_support': False,
                          'interpretation': 'Conservative projected bead/slab intersections; model edge hits alone are not a CAD collision or blockage claim.'})
    downface_review = review_downfaces(downfaces, records, prior_footprint)
    images = make_plots(output, selector, specs, records, plot_data)
    images += make_roof_plots(output, selector, specs, records, plot_data, prior_footprint)
    images += make_downface_plot(output, selector, downfaces, downface_review, records, prior_footprint)
    no_support = all(v['support_absence_in_reviewed_void'] for v in summaries)
    report = {
        'status': 'CRITICAL_VOID_SUPPORT_FOUND_REVIEW_REQUIRED' if not no_support else 'CRITICAL_VOID_SUPPORT_FREE_BRIDGING_REVIEW_REQUIRED',
        'part': inv['part'], 'selector': selector, 'folder': str(folder),
        'mapping': mapping, 'source_sha256_at_start': inv['source_sha256_at_start'],
        'roi_source_sha256': ROI_SOURCE_SHA, 'review_script_sha256': sha(Path(__file__)),
        'feature_path_counts': dict(counts), 'critical_roi_results': summaries, 'images': images,
        'whole_STL_downward_planar_face_review': downface_review,
        'identity_checks': {'preorientation_stl_bounds_match': True, 'project_source_offset_bounds_match': True, 'current_source_hashes_match': True},
        'numerical_contract': {'arc_chord_sagitta_max_mm': ARC_ERROR, 'bead_projection_extra_mm': BUFFER_ERROR,
                               'width_source': 'emitted LINE_WIDTH', 'height_source': 'emitted LAYER_HEIGHT',
                               'support_projection': 'whole actual local-Z bead slab against union of source void cross sections over that slab'},
        'limits': ['This is an offline path inspection, not a sliced-part manufacturing release.',
                   'A raw Bridge command length is not an unsupported span. Geometric underlay gaps are explicitly computed against the previous actual model layer.',
                   'A footprint touching both ends does not certify anchorage length, adhesion, sag or PETG bridge strength.',
                   'Curved-void slab projection over-covers a bead/void overlap and can flag wall-adjacent support conservatively.',
                   'The long stop-bore interior ROI is a named internal window; it does not prove the complete external entry free.',
                   'Support adhesion, fragment extraction, tool approach, residual debris, shrinkage and actual hole fit remain open.',
                   'No print, coupon, source modification, scaling or G-code upload is performed.'],
        'sent_to_printer': False, 'physical_acceptance': False, 'manufacturing_release': False,
    }
    write_json(output / 'report.json', report)
    print(json.dumps({'part': inv['part'], 'status': report['status'], 'support_hits': {v['roi']['name']: v['support_path_hits'] for v in summaries}, 'report': str(output / 'report.json')}, ensure_ascii=False))
    return report


def review_downfaces(downfaces, records, prior_footprint):
    results = []
    for face in downfaces:
        shape, source_z = face['polygon'], face['source_z']
        layers = sorted({round(r.layer, 7) for r, p in records if not r.feature.startswith('Support')
                         and r.layer > source_z + 1e-5 and r.layer - r.height <= source_z + .21
                         and p.distance(shape) < r.width / 2 + BUFFER_ERROR})
        if not layers:
            results.append({'name': face['name'], 'source_z': source_z, 'area_mm2': shape.area,
                            'bounds_local_xy': list(shape.bounds), 'actual_first_model_layer': None})
            continue
        z = layers[0]
        prior_z, prior = prior_footprint(z)
        actual = []
        supports = []
        paths = []
        for r, p in records:
            if p.distance(shape) > r.width / 2 + BUFFER_ERROR: continue
            if r.feature.startswith('Support') and source_z - .61 <= r.layer <= source_z + 1e-5:
                supports.append((r, p))
            elif not r.feature.startswith('Support') and abs(r.layer - z) < 1e-6:
                actual.append(bead(p, r.width, 0))
                # Restrict current centerline to the actual underside's area.
                region = prior.buffer(r.width / 2, quad_segs=24)
                pieces = lines_of(p.intersection(shape).difference(region))
                lengths = [g.length for g in pieces if g.length > .01]
                if lengths:
                    paths.append({'line': r.line, 'feature': r.feature, 'no_previous_layer_bead_overlap_path_pieces_mm': lengths})
        model_first = unary_union(actual)
        support_footprint = unary_union([bead(p, r.width) for r, p in supports])
        results.append({'name': face['name'], 'source_z': source_z, 'area_mm2': shape.area,
                        'bounds_local_xy': list(shape.bounds), 'actual_first_model_layer': z,
                        'previous_model_layer': prior_z,
                        'source_face_area_not_over_previous_model_footprint_mm2': shape.difference(prior).area,
                        'first_model_bead_area_over_face_mm2': model_first.intersection(shape).area,
                        'support_paths_within_0p61_below_face': len(supports),
                        'support_projection_area_over_face_mm2': support_footprint.intersection(shape).area,
                        'nearest_support_top_local_z': max((r.layer for r, _ in supports), default=None),
                        'first_model_paths_without_previous_model_bead_overlap': paths,
                        'interpretation': 'Whole-STL horizontal underside candidate, not an attribution of the slicer warning. Nearby support is projected through up to0.61 mm and may have a deliberate separation gap.'})
    return results


def make_downface_plot(output, selector, downfaces, results, records, prior_footprint):
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    selected = [(f, r) for f, r in zip(downfaces, results) if r.get('actual_first_model_layer') is not None and f['area_mm2'] > 1]
    if not selected: return []
    figure, axes = plt.subplots(math.ceil(len(selected) / 2), 2, figsize=(14, 4 * math.ceil(len(selected) / 2)), squeeze=False, layout='constrained')
    for ax, (face, info) in zip(axes.flat, selected):
        shape = face['polygon']; b = shape.bounds; z = info['actual_first_model_layer']
        x, y = shape.exterior.xy; ax.fill(x, y, color='#edb8b6', alpha=.55)
        groups = defaultdict(list)
        for r, p in records:
            if p.distance(shape) > 2: continue
            if r.feature.startswith('Support') and face['source_z'] - .61 <= r.layer <= face['source_z'] + 1e-5:
                key = 'Support below face'
            elif not r.feature.startswith('Support') and abs(r.layer - z) < 1e-6:
                key = 'First model layer'
            else: continue
            q = r.points
            groups[key].append(np.stack([q[:-1, :2], q[1:, :2]], axis=1))
        for name, color in [('First model layer', '#24627a'), ('Support below face', '#ec772c')]:
            if groups[name]: ax.add_collection(LineCollection(np.concatenate(groups[name]), colors=color, linewidths=.7, label=name))
        ax.set_xlim(b[0] - 3, b[2] + 3); ax.set_ylim(b[1] - 3, b[3] + 3)
        ax.set_aspect('equal'); ax.grid(alpha=.15)
        ax.set_title(f"{face['name']}: source underside area {shape.area:.2f} mm²\nfirst model Z{z:g}; {info['support_paths_within_0p61_below_face']} nearby support paths")
        ax.set_xlabel('Input local X / mm'); ax.set_ylabel('Input local Y / mm'); ax.legend(fontsize=8)
    for ax in list(axes.flat)[len(selected):]: ax.axis('off')
    figure.suptitle(selector + ': whole-STL planar underside survey; pink source underside, blue model, orange support')
    target = output / 'downward-faces.png'; figure.savefig(target, dpi=160); plt.close(figure)
    return [str(target)]


def make_plots(output, selector, specs, records, plot_data):
    os.environ.setdefault('MPLCONFIGDIR', str(output / 'matplotlib-config'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    colors = {'Model': '#24627a', 'Support': '#ec772c', 'Bridge': '#923bc0', 'Overhang': '#398d52'}
    figure, axes = plt.subplots(len(specs), 2, figsize=(15, 4.1 * len(specs)), squeeze=False, layout='constrained')
    for row, spec in enumerate(specs):
        _, selected, roof_rows = plot_data[spec['name']]
        outline = full_projection(spec)
        b = outline.bounds
        ax = axes[row, 0]
        by = defaultdict(list)
        # Side view uses all ROI-touching paths; displayed line thickness is
        # illustrative. JSON keeps declared widths and real deposited slabs.
        for r, p in selected:
            q = r.points
            by[classify(r.feature)].append(np.stack([q[:-1, [0, 2]], q[1:, [0, 2]]], axis=1))
        for key in ['Model', 'Overhang', 'Bridge', 'Support']:
            if by[key]: ax.add_collection(LineCollection(np.concatenate(by[key]), colors=colors[key], linewidths=.6 if key != 'Support' else 1.0, alpha=.65))
        ax.set_xlim(b[0] - 1, b[2] + 1)
        ax.set_ylim(spec['zrange'][0] - .5, spec['zrange'][1] + .8)
        ax.set_xlabel('Input local X / mm'); ax.set_ylabel('Input local Z / mm')
        ax.set_title(spec['name'] + ': projected actual paths touching void')
        ax.grid(alpha=.18)
        ax.set_aspect('auto')
        ax.set_title(spec['name'] + ': path side projection (Z scale enlarged)')
        ax = axes[row, 1]
        if roof_rows:
            target = max(roof_rows, key=lambda v: v['max_continuous_no_bead_overlap_path_touching_roi_mm'])['local_z_top']
        elif spec['kind'] == 'ball_entry':
            target = min((r.layer for r, _ in selected if r.layer >= spec['center'][2]), default=spec['center'][2])
        else:
            target = min((r.layer for r, _ in selected), default=spec['zrange'][0] + .2)
        by = defaultdict(list)
        for r, p in records:
            if abs(r.layer - target) < 1e-5 and p.distance(outline) < 3:
                q = r.points
                by[classify(r.feature)].append(np.stack([q[:-1, :2], q[1:, :2]], axis=1))
        for key in ['Model', 'Overhang', 'Bridge', 'Support']:
            if by[key]: ax.add_collection(LineCollection(np.concatenate(by[key]), colors=colors[key], linewidths=.7, label=key))
        for ring in [outline.exterior, *outline.interiors] if outline.geom_type == 'Polygon' else []:
            x, y = ring.xy; ax.plot(x, y, '--', color='#555555', linewidth=.7)
        ax.set_xlim(b[0] - 3, b[2] + 3); ax.set_ylim(b[1] - 3, b[3] + 3)
        ax.set_aspect('equal'); ax.grid(alpha=.18)
        ax.set_title(f'Actual layer local Z top {target:.3f}; dashed = source void projection')
        ax.set_xlabel('Input local X / mm'); ax.set_ylabel('Input local Y / mm')
        if by: ax.legend(loc='best', fontsize=8)
    figure.suptitle(selector + ': source-mapped toolpath inspection; blue model, orange support, purple bridge, green overhang', fontsize=12)
    target = output / 'critical-paths.png'
    figure.savefig(target, dpi=160)
    plt.close(figure)
    return [str(target)]


def make_roof_plots(output, selector, specs, records, plot_data, prior_footprint):
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    from matplotlib.path import Path as MplPath
    from matplotlib.patches import PathPatch
    from shapely.geometry.polygon import orient
    colors = {'Model': '#24627a', 'Support': '#ec772c', 'Bridge': '#923bc0', 'Overhang': '#398d52'}
    rows = [s for s in specs if s['roof'] is not None]
    fig, axes = plt.subplots(len(rows), 3, figsize=(17, max(5, 4 * len(rows))), squeeze=False, layout='constrained')
    def plot_footprint(ax, geometry):
        polygons = [geometry] if geometry.geom_type == 'Polygon' else list(getattr(geometry, 'geoms', []))
        for polygon in polygons:
            if polygon.geom_type != 'Polygon': continue
            polygon = orient(polygon, sign=1)
            vertices, codes = [], []
            for ring in [polygon.exterior, *polygon.interiors]:
                coordinates = list(ring.coords)
                vertices.extend(coordinates)
                codes.extend([MplPath.MOVETO] + [MplPath.LINETO] * (len(coordinates) - 2) + [MplPath.CLOSEPOLY])
            ax.add_patch(PathPatch(MplPath(vertices, codes), facecolor='#b7bec5', edgecolor='none', alpha=.65))
    for i, spec in enumerate(rows):
        _, _, checked = plot_data[spec['name']]
        selected = max(checked, key=lambda v: v['max_continuous_no_bead_overlap_path_touching_roi_mm'])
        z = selected['local_z_top']
        all_z = sorted({round(r.layer, 7) for r, _ in records if not r.feature.startswith('Support')})
        below = [v for v in all_z if v < z - 1e-6]
        above = [v for v in all_z if v > z + 1e-6]
        layers = [below[-1] if below else z, z, above[0] if above else z]
        outline = full_projection(spec)
        b = outline.bounds
        window = box(b[0] - 2, b[1] - 2, b[2] + 2, b[3] + 2)
        for j, layer in enumerate(layers):
            ax = axes[i, j]
            previous_z, previous = prior_footprint(layer)
            plot_footprint(ax, previous.intersection(window))
            by = defaultdict(list)
            for r, p in records:
                if abs(r.layer - layer) < 1e-6 and p.distance(window) < r.width / 2:
                    q = r.points
                    by[classify(r.feature)].append(np.stack([q[:-1, :2], q[1:, :2]], axis=1))
            for key in ['Model', 'Overhang', 'Bridge', 'Support']:
                if by[key]: ax.add_collection(LineCollection(np.concatenate(by[key]), colors=colors[key], linewidths=.9, label=key))
            for ring in [outline.exterior, *outline.interiors]:
                xx, yy = ring.xy; ax.plot(xx, yy, '--', color='#444444', linewidth=.7)
            ax.set_xlim(b[0] - 2, b[2] + 2); ax.set_ylim(b[1] - 2, b[3] + 2)
            ax.set_aspect('equal'); ax.grid(alpha=.12)
            ax.set_xlabel('Input local X / mm'); ax.set_ylabel('Input local Y / mm')
            ax.set_title(f'{spec["name"]}\nZ top {layer:g}; grey = model footprint at {previous_z:g}' if previous_z is not None else f'Z top {layer:g}; no previous model')
            if by: ax.legend(fontsize=7)
    fig.suptitle(selector + ': actual critical roof paths versus preceding printed model footprint; no bridge-strength claim')
    target = output / 'roof-paths.png'
    fig.savefig(target, dpi=170); plt.close(fig)
    return [str(target)]


def self_test():
    import io
    sample = '''G90\nM83\nG1 X0 Y0 Z.2\n; Z_HEIGHT: .2\n; LAYER_HEIGHT: .2\n; LINE_WIDTH: .4\n; FEATURE: Bridge\nG1 X4 E.5\nG1 X10 E.5\nG1 X20\n; FEATURE: Support interface\nG3 X20 Y0 I-2 J0 E1\nM82\nG92 E10\nG1 X21 E10.1\nG1 E9\nG1 X22 E9.2\nG91\nG1 X1 E9.3\n'''
    paths = list(extrusion_paths(io.StringIO(sample)))
    assert len(paths) == 6
    assert paths[0].stroke == paths[1].stroke
    assert paths[2].stroke != paths[1].stroke and len(paths[2].points) > 10
    assert np.allclose(paths[-1].points[-1], [23, 0, .2])
    prior = unary_union([box(-1, -1, 2, 1), box(8, -1, 11, 1)])
    spans = underlay_runs(LineString([(0, 0), (4, 0), (10, 0)]), prior)
    assert len(spans) == 1 and abs(spans[0]['length_mm'] - 6) < 1e-9
    assert spans[0]['both_ends_touch_previous_model_footprint']
    assert sum(p.length for p in [LineString([(0, 0), (4, 0)]), LineString([(4, 0), (10, 0)])]) == 10
    for selector in ['ci_body', 'ci_lever']:
        for roi in roi_specs(selector):
            shape = full_projection(roi)
            assert shape.is_valid and shape.area > 0
            assert roi_projection(roi, roi['zrange'][1] + 1, roi['zrange'][1] + 2).is_empty
    cylinder = roi_specs('ci_body')[0]
    assert abs(full_projection(cylinder).bounds[3] - (-24 + 3.6)) < 1e-9
    matrix = three_mf_matrix('0 1 0 -1 0 0 0 0 1 10 20 30')
    assert np.allclose(affine([[2, 3, 4]], matrix), [[7, 22, 34]])
    print(json.dumps({'self_test': 'PASS', 'tests': ['relative/absolute extrusion and coordinates', 'same-XY full circle', 'continuous strokes across commands', '6mm geometric gap vs 10mm commands', 'ROI slab bounds', '3MF transform convention']}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', type=Path)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test()
    if args.folder:
        review(args.folder)
    if not args.self_test and not args.folder:
        parser.error('Specify --folder or --self-test')


if __name__ == '__main__':
    main()
