#!/usr/bin/env python3
"""Offline, isolated Bambu CLI audit. No printer/network operation is invoked."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
CONFIG=ROOT/'output/print-review/config'
STL=ROOT/'output/feeder-support-harness/beam-grip.stl'
CAD=ROOT/'cad/feeder-support-harness.scad'
BAMBU='/Applications/BambuStudio.app/Contents/MacOS/BambuStudio'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('variant',choices=['unsupported','supported'])
    a=p.parse_args();folder=OUT/a.variant;folder.mkdir(exist_ok=True)
    shutil.copy2(CONFIG/'filament.json',folder/'filament.json')
    machine=json.loads((CONFIG/'machine.json').read_text())
    template_root=Path('/Applications/BambuStudio.app/Contents/Resources/profiles/BBL/machine')
    template_sources={}
    for field in ['machine_start_gcode','machine_end_gcode','time_lapse_gcode','change_filament_gcode','layer_change_gcode']:
        path=template_root/f'Bambu Lab X1 Carbon 0.4 nozzle template {field}.json'
        template_sources[str(path)]=sha(path)
        machine[field]=json.loads(path.read_text())[field]
    machine.pop('include',None)
    (folder/'machine.json').write_text(json.dumps(machine,indent=2)+'\n')
    (folder/'template-source-identity.json').write_text(json.dumps(template_sources,indent=2)+'\n')
    process=json.loads((CONFIG/'process.json').read_text())
    process['enable_support']='1'if a.variant=='supported'else'0'
    process['support_type']='tree(auto)'
    process['support_on_build_plate_only']='1'
    (folder/'process.json').write_text(json.dumps(process,indent=2)+'\n')
    cmd=[BAMBU,'--datadir',str(folder/'app-data'),'--load-settings',
         str(folder/'machine.json')+';'+str(folder/'process.json'),
         '--load-filaments',str(folder/'filament.json'),'--orient','0',
         '--rotate-x','90','--arrange','1','--ensure-on-bed','--slice','0',
         '--export-3mf',f'harness-{a.variant}-slice-review.3mf',
         '--outputdir',str(folder),str(STL)]
    record={'variant':a.variant,'command':cmd,'input_stl':str(STL.relative_to(ROOT)),
       'input_stl_sha256':sha(STL),'cad_sha256':sha(CAD),
       'profiles_sha256':{n:sha(folder/f'{n}.json')for n in ['machine','process','filament']},
       'expanded_official_machine_templates_sha256':template_sources,
       'official_profile_origin_record':str((CONFIG/'source-identity.json').relative_to(ROOT)),
       'assumptions':{'printer':'X1C .4 confirmed','filament':'Generic PETG; actual brand not specified',
          'plate':'Textured PEI analysis assumption; user only confirmed PEI',
          'layer_height_mm':.2,'walls':4,'infill_percent':25,'orientation':'rotate X +90; original -Y on bed'},
       'no_print_command':True,'user_profiles_read_or_modified':False,'sent_to_printer':False,
       'physical_acceptance':False}
    (folder/'invocation.json').write_text(json.dumps(record,indent=2)+'\n')
    run=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
    (folder/'bambu-cli.log').write_text(run.stdout+run.stderr)
    record['process_exit_code']=run.returncode
    record['input_unchanged']=record['input_stl_sha256']==sha(STL)and record['cad_sha256']==sha(CAD)
    native=folder/'result.json'
    if native.exists():record['native_result']=json.loads(native.read_text())
    record['artifact_sha256']={f.name:sha(f)for f in folder.iterdir()if f.suffix in ['.3mf','.gcode']}
    (folder/'invocation.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record,indent=2))
    return run.returncode

if __name__=='__main__':raise SystemExit(main())
