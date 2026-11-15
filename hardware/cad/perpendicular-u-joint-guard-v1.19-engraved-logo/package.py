"""Single-part X1C PETG project, roof down, editable and unsliced."""
from pathlib import Path
import sys,tempfile,subprocess,json,zipfile
HERE=Path(__file__).resolve().parent;CAD=HERE.parent
sys.path.insert(0,str(CAD))
from build_net_clamp_bambu_package import normalise_stl,copy_template_settings
from build_print_platter import rotation_matrix_xyz
OUT=CAD/'print-packages/barrier-clip-v1.19-engraved-logo'
OUT.mkdir(parents=True,exist_ok=True)
source=CAD/'exports/perpendicular-u-joint-v1.19-engraved-logo/guard-v1.19.stl'
posed=OUT/'guard-v1.19-roof-down.stl'
normalise_stl(source,posed,rotation_matrix_xyz(180,0,0))
template=CAD/'print-packages/barrier-clip-v1.15-6x-black-PETG/barrier-clip-v1.15-6x-upright-black-PETG.3mf'
final=OUT/'guard-v1.19-1x-roof-down-X1C-black-PETG.3mf'
with tempfile.TemporaryDirectory(prefix='guard-v119-') as temp:
    temp=Path(temp);seed=temp/'seed.3mf'
    subprocess.run(['/Applications/BambuStudio.app/Contents/MacOS/BambuStudio','--datadir',str(temp/'config'),'--arrange','1','--orient','0','--export-3mf',str(seed),str(posed)],check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    copy_template_settings(seed,template,final)
with zipfile.ZipFile(final) as z:
    assert not any(n.endswith('.gcode') for n in z.namelist())
    settings=json.loads(z.read('Metadata/project_settings.config'))
    print({k:settings.get(k) for k in ['printer_model','filament_type','wall_loops','sparse_infill_density','enable_support','support_type']})
print(final)
