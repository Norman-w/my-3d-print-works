"""Rebuild native v1.18 structure and subtract the parametric recessed label."""
from pathlib import Path
import importlib.util,json,subprocess,hashlib,shutil
HERE=Path(__file__).resolve().parent
CAD=HERE.parent
spec=importlib.util.spec_from_file_location('finish',CAD/'perpendicular-u-joint-guard-v1.17-load-path/build.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
OUT=CAD/'exports/perpendicular-u-joint-v1.19-engraved-logo'
OUT.mkdir(exist_ok=True,parents=True)
def main():
    for feature,name in [('raw','raw-solid.stl'),('cutter','logo-cutter.stl')]:
        subprocess.run([shutil.which('openscad') or '/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD','--backend=Manifold','--export-format=binstl','-D',f'FEATURE="{feature}"','-o',str(OUT/name),str(HERE/'engraved_guard.scad')],check=True)
    raw=b.load(OUT/'raw-solid.stl')
    bottom=b.m.Manifold.cube([120,120,1.5]).translate([-60,-60,-23.5])
    body=b.export_precision((b.finish(raw,.6)+(raw^bottom)).set_tolerance(.0001).simplify(.0001))
    final=b.export_precision(body-b.load(OUT/'logo-cutter.stl'))
    assert len(final.decompose())==1
    assert (final-body).volume()<.001
    removed=body-final
    assert removed.volume()>1
    assert removed.bounding_box()[2]>=30.399
    b.write(final,OUT/'guard-v1.19.stl')
    report={'engraving_depth_mm':.6,'removed_volume_mm3':removed.volume(),'removed_bounds_mm':removed.bounding_box(),'bounds_mm':final.bounding_box(),'single_solid':True,'sha256':hashlib.sha256((OUT/'guard-v1.19.stl').read_bytes()).hexdigest()}
    (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
