#!/usr/bin/env python3
"""Finite connected air corridors against the current complete feeder geometry.

Continuous nominal geometry only: no fan curve, flow rate or seal prediction.
Use the bundled FreeCAD Python runtime for NumPy/Shapely/Matplotlib.
"""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import math
import sys

import numpy as np
from shapely.geometry import Point

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from feeder_body_geometry import read_mesh, Sections, body_parameters
from guide_openings import read_scalar_parameters
from cable_structural_slice_review import inside
from review_integrated_shell_slice import clipped_triangle_in_box

EXPORT = ROOT / 'output/cable-scene-export/20260927T091627124663Z/report.json'
HALF_WIDTH = 1.0
NUMERICAL_GUARD = .00002


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def basis(a, b):
    x = b - a
    length = np.linalg.norm(x)
    x /= length
    hint = np.array([1., 0, 0]) if abs(x[2]) > .9 else np.array([0., 0, 1])
    y = np.cross(hint, x); y /= np.linalg.norm(y)
    z = np.cross(x, y)
    return np.stack([x, y, z], axis=1), length


def corners(lo, hi):
    return np.array([[x, y, z] for x in [lo[0], hi[0]] for y in [lo[1], hi[1]] for z in [lo[2], hi[2]]])


def box_check(t, lo, hi):
    active = t[(t.max(1) >= lo).all(1) & (t.min(1) <= hi).all(1)]
    hits = sum(clipped_triangle_in_box(v, lo, hi) for v in active)
    center_inside = bool(inside((lo + hi) / 2, t))
    return {'triangle_intersections': hits, 'box_center_inside_solid': center_inside,
            'clear': hits == 0 and not center_inside}


def inverse_translation_bounds(motion):
    kind = motion['kind']
    if kind == 'fixed' or kind == 'output-wire':
        return np.zeros((1, 3))
    if kind == 'translate':
        assert motion['input'] == 'stroke' and motion['distance_mm'] == 20
        return np.array([[0, 0, 0], np.array(motion['axis']) * -motion['distance_mm']])
    if kind == 'radial':
        assert motion['open_mm'] >= motion['closed_mm']
        return np.array([np.array(motion['axis']) * (-motion['side'] * (r-motion['initial_radius_mm']))
                         for r in [motion['closed_mm'], motion['open_mm']]])
    if kind == 'spring':
        assert motion['model'] == 'extension-outline' and motion['stroke_mm'] == 20
        # Current tube length increases only along Z. Translating its rest solid
        # through the stroke overbounds this, including both end loops.
        return np.array([[0, y, z] for y in [-.585, .585] for z in [-20., 0.]])
    raise ValueError(f'Unsupported motion for translation bounds: {kind}')


def source_contracts(inv):
    ci = inv['scene_contract']['ci']
    assert ci['motion_law'] == 'fixed-guide-direct-pull-v2'
    assert ci['basis_x'][1] == ci['basis_y'][1] == 0 and ci['basis_z'] == [0, 1, 0]
    inp = (ROOT / 'cad/cable-trigger-input.scad').read_text()
    out = (ROOT / 'cad/cable-output-interface.scad').read_text()
    spring = (ROOT / 'cad/feeder-return-spring.scad').read_text()
    assert 'function ci_B(a)=[ci_ball_arm_R*sin(a),ci_ball_arm_R*cos(a),ci_wire_z];' in inp
    assert 'co_housing_entry()[2]-(a[2]-co_wire_tail),co_wire_d);' in out
    assert 'rs_loop(rs_top(t)-rs_hook_offset);' in spring
    assert 'cylinder(h=rs_top(t)-rs_fixed_z-2*rs_coil_offset' in spring
    return ci


def main():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out = ROOT / 'output/current-airway-review' / stamp
    out.mkdir(parents=True)
    export = json.loads(EXPORT.read_text())
    inv = json.loads((ROOT / 'docs/cable-assembly-inventory.json').read_text())
    assert export['status'] == 'CURRENT_SCENE_EXPORT_PASS'
    evidence = {str(EXPORT.relative_to(ROOT)): sha(EXPORT), **export['source_sha256']}
    for p, h in evidence.items():
        assert sha(ROOT / p) == h, p
    ci = source_contracts(inv)
    parts = []
    for row in export['parts']:
        if not row['id'].startswith('feeder/'):
            continue
        assert sha(ROOT / row['file']) == row['sha256']
        evidence[row['file']] = row['sha256']
        t, _ = read_mesh(ROOT / row['file'])
        parts.append((row, t))
    base, _ = read_scalar_parameters(ROOT / 'cad/parameters.scad')
    p, _ = body_parameters(ROOT / 'cad/feeder-body.scad', base)
    z0 = p['body_inlet_shoulder'] + p['transition_length']/2
    z1 = p['body_guide_end'] + p['transition_length']/2
    route_r = ((p['body_spigot_bore']+4+p['guide_od'])/4 + (p['body_spigot_bore']+p['body_id'])/4)/2
    pc = next(t for r,t in parts if r['id'] == 'feeder/pc-reference')
    start = p['body_inlet_start'] + 2
    end = float(pc[:,:,2].max()) - 2
    paths = []
    for angle in [45, 135, 225, 315]:
        a = math.radians(angle)
        xy = np.array([math.cos(a), math.sin(a)]) * route_r
        vertices = np.array([[0,0,start], [0,0,z0], [*xy,z0], [*xy,z1], [0,0,z1], [0,0,end]])
        results = []
        for index, (a,b) in enumerate(zip(vertices[:-1],vertices[1:])):
            matrix, length = basis(a,b)
            h = HALF_WIDTH + NUMERICAL_GUARD
            # Adjacent perpendicular boxes already overlap around their joint.
            # Do not extend a bypass segment 1 mm past its window centre into
            # the taper. Only a numerical outward guard pads its axial ends.
            lo = np.array([-NUMERICAL_GUARD,-h,-h]); hi = np.array([length+NUMERICAL_GUARD,h,h])
            world = corners(lo,hi) @ matrix.T + a
            row_results = []
            for row,t in parts:
                m = row['motion']; kind = m['kind']
                if kind in ['trigger-rotate','input-wire']:
                    # Rotation about the global Y axis keeps Y exactly fixed.
                    # The wire centerline is always in its fixed local Z plane.
                    if kind == 'trigger-rotate':
                        assert m['axis'] == [0,1,0]
                        ymin,ymax = t[:,:,1].min(),t[:,:,1].max()
                    else:
                        yc = ci['origin'][1] + ci['wire_z']
                        ymin,ymax = yc-ci['wire_d']/2, yc+ci['wire_d']/2
                        assert t[:,:,1].min() >= ymin-1e-6 and t[:,:,1].max() <= ymax+1e-6
                    clear = world[:,1].max() < ymin or world[:,1].min() > ymax
                    row_results.append({'id':row['id'], 'method':'continuous fixed-Y slab', 'clear':bool(clear)})
                    continue
                offsets = inverse_translation_bounds(m) @ matrix
                lower,upper = lo+offsets.min(0),hi+offsets.max(0)
                local = (t-a) @ matrix
                if (local.max((0,1)) < lower).any() or (local.min((0,1)) > upper).any():
                    check = {'triangle_intersections':0, 'box_center_inside_solid':False, 'clear':True}
                else:
                    check = box_check(local,lower,upper)
                row_results.append({'id':row['id'], 'method':'static mesh' if kind in ['fixed','output-wire'] else 'inverse swept-box overbound', **check})
            results.append({'segment':index,'basis_columns':matrix.tolist(),'local_box_mm':[lo.tolist(),hi.tolist()],
                            'clear':all(r['clear'] for r in row_results),'parts':row_results})
        overlaps=[]
        for j in range(1,len(vertices)-1):
            incoming=(vertices[j]-vertices[j-1]);incoming/=np.linalg.norm(incoming)
            outgoing=(vertices[j+1]-vertices[j]);outgoing/=np.linalg.norm(outgoing)
            witness=vertices[j]+.25*(outgoing-incoming)
            margin=[]
            for k in [j-1,j]:
                matrix=np.array(results[k]['basis_columns'])
                local=(witness-vertices[k])@matrix
                lower,upper=np.array(results[k]['local_box_mm'])
                margin.append(float(min(np.min(local-lower),np.min(upper-local))))
            assert min(margin)>.1, 'Consecutive corridor boxes do not have the required positive overlap'
            overlaps.append({'joint':j,'interior_point_mm':witness.tolist(),'inscribed_overlap_ball_radius_mm':.1,'minimum_box_boundary_distance_mm':min(margin)})
        paths.append({'angle_deg':angle,'vertices_mm':vertices.tolist(),'square_width_mm':2*HALF_WIDTH,
                      'clear':all(r['clear'] for r in results),'segments':results,'positive_volume_joint_overlaps':overlaps})
    shells = np.concatenate([t for r,t in parts if r['id'] in ['feeder/positive-half','feeder/negative-half']])
    control = box_check(shells,np.array([33.5,-.5,-51.]),np.array([34.5,.5,-49.]))
    assert not control['clear'], 'Wall-penetrating control was not detected'
    for f in [Path(__file__),ROOT/'analysis/feeder_body_geometry.py',ROOT/'analysis/cable_structural_slice_review.py',ROOT/'scripts/review_integrated_shell_slice.py']:
        evidence[str(f.relative_to(ROOT))] = sha(f)
    stable = all(sha(ROOT/f) == h for f,h in evidence.items())
    d = {'status':'FOUR_CONTINUOUS_FINITE_CORRIDORS_CLEAR_IN_CURRENT_FEEDER' if stable and all(x['clear'] for x in paths) else 'CURRENT_AIRWAY_REVIEW_FLAGGED',
         'created_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':evidence,'sources_stable':stable,
         'feeder_instances_checked':len(parts),'trigger_stroke_mm':[0,20], 'square_width_mm':2*HALF_WIDTH,
         'numerical_guard_mm':NUMERICAL_GUARD,'paths':paths,'wall_positive_control':control,
         'interpretation':'Each overlapping sequence of guarded 2x2 mm boxes is a positive-volume air connection from the existing inlet to the nominal outlet PC, through a diagonal bypass branch. Common inlet/outlet segments overlap; branch areas must not be summed as a whole-route minimum. This proves only nominal geometric connectivity.',
         'method':'All current feeder STL instances, with static triangles clipped against each corridor box and interior-center checks. Translating motions use inverse swept boxes containing every continuous pose; trigger parts use fixed-Y slabs, output wire is a shrinking subset of its rest solid, and spring extension uses a conservative translation/eye-float envelope. No finite pose sampling is used to infer full stroke.',
         'limits':['Reference PC/hose/pads are nominal user/design envelopes, not measured external shapes.',
                   'Balls are not solids in this connectivity proof; arriving balls can cover common inlet sections.',
                   'No total/minimum useful section area, hydraulic diameter, leakage, pressure loss, flow rate, Y suction or blower capability is inferred.',
                   'Spin head is on a separate discharge axis after the unmeasured Y fitting and is not part of this feeder corridor proof.',
                   'Print tolerance, deflection, residue, seam seal quality and loaded flow remain open.'],
         'manufacturing_release':False,'physical_acceptance':False}
    (out/'report.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
    # Source-mesh axial cut: r at the 45-degree branch versus original Z.
    import os
    os.environ['MPLCONFIGDIR']=str(out/'matplotlib-config')
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(8,11))
    radial=np.array([1,1,0])/math.sqrt(2); side=np.array([-1,1,0])/math.sqrt(2)
    for row,t in parts:
        if row['id'] not in ['feeder/positive-half','feeder/negative-half','feeder/liner','feeder/pc-reference']:
            continue
        transformed=np.stack([t@radial,t[:,:,2],t@side],axis=-1)
        _,section=Sections(transformed).at(0)
        for poly in section.geoms if hasattr(section,'geoms') else [section]:
            if poly.is_empty or poly.geom_type!='Polygon':continue
            x,y=poly.exterior.xy;ax.fill(x,y,color='#b6c9d2')
            for ring in poly.interiors:
                x,y=ring.xy;ax.fill(x,y,color='white')
    v=np.array(paths[0]['vertices_mm']);q=np.column_stack([v@radial,v[:,2]])
    ax.plot(q[:,0],q[:,1],color='#e27822',linewidth=3,label='2 x 2 mm connected witness (45 deg)')
    ax.set(xlabel='Diagonal radial coordinate / mm',ylabel='Feeder Z / mm',title='Current feeder: nominal connected bypass witness')
    ax.set_aspect('equal');ax.legend(loc='upper left',fontsize=8);ax.grid(alpha=.2)
    fig.tight_layout();fig.savefig(out/'corridor-section.png',dpi=170);plt.close(fig)
    print(json.dumps({'report':str(out/'report.json'),'status':d['status'],'instances':len(parts),
                      'failures':[{'angle':x['angle_deg'],'segment':s['segment'],'part':r['id'],'method':r['method']} for x in paths for s in x['segments'] for r in s['parts'] if not r['clear']]},indent=2))
    return 0 if d['status'].startswith('FOUR_CONTINUOUS') else 1


if __name__=='__main__':
    raise SystemExit(main())
