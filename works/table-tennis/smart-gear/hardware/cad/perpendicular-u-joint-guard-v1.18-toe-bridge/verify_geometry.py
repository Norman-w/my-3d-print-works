"""Verify fixed fit envelopes and unchanged roof/lip against actual exports."""
from pathlib import Path
import json
import manifold3d as m
from build import load,OUT,CAD

old=load(CAD/'exports/perpendicular-u-joint-v1.16-root-radius/guard-v1.16-body.stl')
new=load(OUT/'guard-v1.18-body.stl')
full=load(OUT/'guard-v1.18.stl')
box=lambda size,position:m.Manifold.cube(size).translate(position)
changed=(old-new)+(new-old)
report={
    'body_components':len(new.decompose()),'full_components':len(full.decompose()),
    'body_volume_mm3':new.volume(),'old_volume_mm3':old.volume(),
    'body_volume_increase_percent':(new.volume()/old.volume()-1)*100,
    'upper_roof_difference_mm3':(changed^box([120,120,40],[-60,-60,20])).volume(),
    'bottom_1_5_mm_band_difference_mm3':(changed^box([120,120,1.5],[-60,-60,-23.5])).volume(),
    'upper_tube_entry_intrusion_mm3':(new^box([120,21,83],[-60,-10.5,-60])).volume(),
    'lower_foot_cavity_intrusion_mm3':(new^box([21.8,120,22],[-10.9,-60,-22])).volume(),
    'screw_D16_intrusion_mm3':(new^m.Manifold.cylinder(100,7.98,7.98,64).translate([0,0,-50])).volume(),
    'old_material_removed_mm3':(old-new).volume(),
    'body_bounds_mm':new.bounding_box(),'full_bounds_mm':full.bounding_box(),
    'numerical_boolean_volume_tolerance_mm3':.01,
}
assert report['body_components']==report['full_components']==1
for name in ['upper_roof_difference_mm3','bottom_1_5_mm_band_difference_mm3','upper_tube_entry_intrusion_mm3','lower_foot_cavity_intrusion_mm3','screw_D16_intrusion_mm3']:
    assert abs(report[name])<.01,(name,report[name])
review=CAD/'review/perpendicular-u-joint-v1.18-toe-bridge';review.mkdir(parents=True,exist_ok=True)
(review/'geometry-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
