#!/usr/bin/env python3
"""Geometric first-article gates; no claim of physical fit or seal performance."""
import json
import math
import os
import re
import shutil
import subprocess
from pathlib import Path
import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
SCAD = ROOT / 'orthokeratology_lens_cleaning_kit_box.scad'
OUT = ROOT / 'output' / '3d-print'
QA = ROOT / 'output' / 'validation'
QA.mkdir(parents=True, exist_ok=True)
BIN = os.environ.get('OPENSCAD_BIN') or shutil.which('openscad') or '/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
PREFIX = 'orthokeratology_lens_cleaning_kit_box_'

def mesh(name):
    return trimesh.load_mesh(OUT / (PREFIX + name + '.stl'))

def intersection_volume(a, b):
    result = trimesh.boolean.intersection([a, b], engine='manifold')
    return float(result.volume) if not result.is_empty else 0.0

def export_check(name, body):
    path = QA / (name + '.stl')
    # `use` does not inherit the caller's special $fn variable. Match the main
    # export's curve tessellation, particularly for rounded glyph outlines.
    fn = re.search(r'\$fn\s*=\s*([0-9.]+)', SCAD.read_text())[1]
    result = subprocess.run([BIN, '--backend=CGAL', '-D', 'model_mode="qa"', '-o', str(path),
                             '-'], input=f'use <{SCAD}>\n$fn={fn};\n{body}',
                            text=True, capture_output=True, cwd=ROOT)
    if result.returncode:
        raise RuntimeError(result.stderr)
    return trimesh.load_mesh(path)

source_text=SCAD.read_text()
def parameter(name):
    return float(re.search(rf'^{name}\s*=\s*([0-9.]+);',source_text,re.M)[1])
wall=parameter('wall'); floor=parameter('base_floor')
L=parameter('inner_length')+2*wall
W=parameter('inner_width')+2*wall+parameter('front_service')+parameter('rear_service')
H=parameter('inner_height_total')/2+floor
inner_y=wall+parameter('front_service')
center=[L/2,inner_y+50,H]
pivot=np.array([0,W-parameter('axis_inset'),H])
report = {'revision': 'H', 'units': 'mm', 'meshes': {}}
for name in ['print_in_place_open','closed_preview','base','lid','open90','section','hinge_coupon']:
    m=mesh(name)
    components=m.split(only_watertight=False,repair=False)
    edge_counts=np.bincount(m.edges_unique_inverse)
    repeated=int(np.count_nonzero((m.faces[:,0]==m.faces[:,1]) | (m.faces[:,1]==m.faces[:,2]) | (m.faces[:,0]==m.faces[:,2])))
    zero_area=int(np.count_nonzero(m.area_faces<=1e-12))
    assert np.isfinite(m.vertices).all() and len(m.faces)>0, name
    assert repeated==0 and np.all(edge_counts==2), ('Invalid face or edge topology',name)
    # CGAL can triangulate collinear points on coplanar catch surfaces in
    # auxiliary views. Report them explicitly; enforce zero on printable files.
    if name in ['print_in_place_open','hinge_coupon']:
        assert zero_area==0, ('Zero-area face in printable artifact',name)
    report['meshes'][name] = dict(bounds=m.bounds.tolist(), size=m.extents.tolist(),
        volume=float(m.volume), watertight=bool(m.is_watertight),
        components=len(components), faces=len(m.faces),
        repeated_vertex_faces=repeated, zero_area_faces=zero_area,
        boundary_edges=int(np.count_nonzero(edge_counts==1)),
        non_manifold_edges=int(np.count_nonzero(edge_counts>2)),
        winding_consistent=bool(m.is_winding_consistent))
    assert m.is_watertight and m.is_winding_consistent and m.volume>0, name
    (OUT/(name+'.report.json')).write_text(json.dumps({
        'path':str((OUT/(PREFIX+name+'.stl')).relative_to(ROOT)),
        'units':'mm (CAD convention; STL has no embedded units)',
        **report['meshes'][name]},indent=2)+'\n')
    if name in ['base','lid']: assert len(components)==1, (name,len(components))
assert report['meshes']['print_in_place_open']['components']==2, 'Captive pair must NOT be fused or have loose parts'
assert all(v<256 for v in report['meshes']['print_in_place_open']['size'])
assert abs(report['meshes']['print_in_place_open']['bounds'][0][2])<.001, 'Print pose must touch bed'
assert np.allclose(report['meshes']['closed_preview']['bounds'][0],[0,0,0],atol=1e-5)
assert np.allclose(report['meshes']['closed_preview']['bounds'][1],[L,W,2*H],atol=1e-5), 'Mechanism protrudes outside closed silhouette'

# Orientation-only proxy, NOT slicer support volume: downward surfaces steeper
# than 50 degrees from vertical, excluding the first .3 mm above the bed.
steep_area={}
for pose in ['open90','print_in_place_open']:
    m=mesh(pose)
    mask=(m.face_normals[:,2]<-math.sin(math.radians(50))) & (m.triangles_center[:,2]>.3)
    steep_area[pose]=float(m.area_faces[mask].sum())
report['printability']={'steep_downward_area_mm2':steep_area,
    'threshold_deg_from_vertical':50,'excluded_bed_height':.3,
    'pusher_extension':2.5,'catch_side_arm_length':6.1,'finger_root_bridge':3,
    'spring_free_length':H+4.3+parameter('latch_depth_shift')-parameter('finger_root_height')-2,'pin_bridge_length':6.7,
    'actual_slicing_and_support_removal':'pending'}
assert steep_area['print_in_place_open']<steep_area['open90']

# Short mechanisms now fit wholly within the front service band.
gauge=trimesh.creation.box(extents=[130,100,50])
gauge.apply_translation(center)
base, lid = mesh('base'), mesh('lid')
def rotated(angle, source=lid):
    m=source.copy()
    m.apply_transform(trimesh.transformations.rotation_matrix(math.radians(-angle),[1,0,0],point=pivot))
    return m
closed_lid=rotated(0)
nominal_gauge=trimesh.creation.box(extents=[130,100,50])
nominal_gauge.apply_translation(center)
report['rectangular_clearance']={'nominal':[130,100,50],'guaranteed_clear':[130,100,50],
    'nominal_cavity_intrusion_mm3':intersection_volume(base,nominal_gauge)+intersection_volume(closed_lid,nominal_gauge),
    'base_intrusion_mm3':intersection_volume(base,gauge),
    'lid_intrusion_mm3':intersection_volume(closed_lid,gauge)}
assert max(report['rectangular_clearance'][k] for k in ['base_intrusion_mm3','lid_intrusion_mm3'])<0.01
report['closed_overlap_mm3']=intersection_volume(base,closed_lid)
assert report['closed_overlap_mm3']<0.01, report['closed_overlap_mm3']

# Finger access must open at the actual seam, not on the cheek of either half.
mouth_gauge=trimesh.creation.box(extents=[16,1.6,2])
mouth_gauge.apply_translation([L/2,1,H])
report['mouth_grip']={'center':[L/2,0,H], 'max_depth':4,
    'local_backing_y':5.2,
    'finger_space_intrusion_mm3':intersection_volume(base,mouth_gauge)+intersection_volume(closed_lid,mouth_gauge)}
assert report['mouth_grip']['finger_space_intrusion_mm3']<.01
# Former side pockets must now contain solid wall, on BOTH halves and sides.
for x in [wall/2,L-wall/2]:
    for z,part in [(H-9,base),(H+9,closed_lid)]:
        wall_gauge=trimesh.creation.box(extents=[wall-.2,24,4])
        wall_gauge.apply_translation([x,center[1],z])
        assert abs(intersection_volume(part,wall_gauge)-wall_gauge.volume)<.01

# Verify real floor material, thin side rims, and open interior service pockets.
remaining_roof=floor-parameter('label_depth')
for z,thickness,part in [(floor/2,floor,base),(2*H-floor+remaining_roof/2,remaining_roof,closed_lid)]:
    plate=trimesh.creation.box(extents=[110,80,thickness])
    plate.apply_translation([L/2,center[1],z])
    # Boolean backend uses float32: at Z=53.6 a ~1.5e-6 mm rounding offset
    # over the full 8800 mm2 panel exceeds the old fixed .01 mm3 threshold.
    assert abs(intersection_volume(part,plate)-plate.volume)<max(.01,plate.area*2e-6)
letter_cut=export_check('lid_letter_cut','lid_label_cut_closed();')
full_roof=trimesh.creation.box(extents=[110,80,floor])
full_roof.apply_translation([L/2,center[1],2*H-floor/2])
removed=intersection_volume(letter_cut,full_roof)
assert removed>10, 'Lid label is empty or missing'
assert intersection_volume(closed_lid,letter_cut)<.01, 'Engraving was not cut from the lid'
assert abs(intersection_volume(closed_lid,full_roof)-(full_roof.volume-removed))<.01
report['lid_engraving']={'lines':['ORTHO-K','LENS CARE KIT','Candy'],
    'depth':parameter('label_depth'),'remaining_roof':remaining_roof,
    'removed_volume_mm3':removed,'cut_bounds':letter_cut.bounds.tolist()}
for x in [wall/2,L-wall/2]:
    rim=trimesh.creation.box(extents=[wall-.8,60,.4])
    rim.apply_translation([x,center[1],H-.8])
    assert abs(intersection_volume(base,rim)-rim.volume)<.01, 'Side rim has a leftover groove'
for x in [10,L/2,L-10]:
    for y in [wall+1, W-wall-1]:
        pocket=trimesh.creation.box(extents=[4,1,8])
        pocket.apply_translation([x,y,10])
        assert intersection_volume(base,pocket)<.01, 'Service band was not hollowed'
report['thin_shell']={'ordinary_wall':wall,'floor_and_roof':floor,'side_rim_groove':'absent',
    'front_local_housing_depth':inner_y,'rear_local_pad_depth':W-inner_y-100}

# OpenSCAD `use` retains default module scope parameters from the source.
rigid_base=export_check('rigid_base','base_half();')
rigid_lid=export_check('rigid_lid','lid_half_closed(false);')
angles=list(range(0,101,2))
volumes=[intersection_volume(rigid_base,rotated(a,rigid_lid)) for a in angles]
report['rigid_sweep']={'range_deg':[0,100],'angle_step_deg':2,'samples':len(angles),
    'max_overlap_mm3':max(volumes), 'failed_angles':[a for a,v in zip(angles,volumes) if v>0.01]}
assert max(volumes)<0.01, report['rigid_sweep']

# Flush button skins and the rear axle cover must actually remain solid.
for cx in [30,L-30]:
    # Probe below the external seam bevel, not in the intentionally removed bevel.
    cover=trimesh.creation.box(extents=[12,.2,6])
    cover.apply_translation([cx,W-.55,H])
    assert abs(intersection_volume(closed_lid,cover)-cover.volume)<.01
for cx in [35,L-35]:
    skin=trimesh.creation.box(extents=[22,.6,20])
    skin.apply_translation([cx,.4,13.5])
    assert abs(intersection_volume(base,skin)-skin.volume)<.01
pushers=export_check('pushers','release_pushers();')
no_pushers=export_check('base_without_pushers','base_half(true,false);')
root=trimesh.boolean.intersection([pushers,no_pushers],engine='manifold')
assert not root.is_empty and root.bounds[1][1]<.801, 'Pusher is joined to a rigid part beyond the skin'
catches=export_check('internal_catches','union() { front_positions() catch(); internal_catch_bridges(); }')
stroke_checks=[]
for stroke in [0,.5,1,1.5]:
    p=pushers.copy(); p.apply_translation([0,stroke,0])
    v=intersection_volume(p,catches)
    assert v<.01, ('Pusher hits catch frame',stroke,v)
    stroke_checks.append({'stroke_mm':stroke,'catch_frame_overlap_mm3':v})
report['concealed_release']={'membrane_thickness':.8,'stroke_checks':stroke_checks,
    'pusher_root_max_y':float(root.bounds[1][1]),'physical_elasticity_test':'pending'}
# Flexible contacts during closing are expected, but report the entire sweep.
report['unflexed_latch_contacts']=[{'angle':a,'overlap_mm3':intersection_volume(base,rotated(a))}
    for a in [0,1,2,3,4,5,10,20,45,90,100]]
report['seal']={'type':'none','gasket_required':False,'watertight_requirement':False}
report['hinge']={'radial_gap':.35,'axial_gap':.35,'pin_bridge_length':6.7,
    'bore_bias':.15,'minimum_radial_gap':.2,'closed_lift_max':.2,
    'physical_release_test':'pending'}
report['hinge']['pivot']=pivot.tolist()
previous=json.loads((ROOT/'archive/rev-f-sealed/mechanics.json').read_text())
old_volume=previous['meshes']['print_in_place_open']['volume']
new_volume=report['meshes']['print_in_place_open']['volume']
report['material_comparison']={'rev_f_solid_mm3':old_volume,'rev_h_solid_mm3':new_volume,
    'solid_reduction_percent':100*(1-new_volume/old_volume),'sliced_filament_mass':'not_measured'}
(QA/'mechanics.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
