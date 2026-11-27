#!/usr/bin/env python3
"""Expand official X1C G-code templates and re-slice ONE hold fork offline.

No CAD change, printer discovery or print submission. Old evidence is archived
once before changing shared configuration or replacing slice artifacts.
"""
from pathlib import Path
import hashlib
import json
import re
import shutil
import struct
import subprocess
import xml.etree.ElementTree as ET
import zipfile

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/'output/print-review/config'
OUT=ROOT/'output/print-review/hold-fork'
STL=ROOT/'output/spin-head/spin-hold-fork.stl'
PROFILE_ROOT=Path('/Applications/BambuStudio.app/Contents/Resources/profiles/BBL/machine')
BAMBU='/Applications/BambuStudio.app/Contents/MacOS/BambuStudio'
FIELDS=('machine_start_gcode','machine_end_gcode','time_lapse_gcode',
        'change_filament_gcode','layer_change_gcode')
NS={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,data):p.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')

def archive_once(folder,names):
    archive=folder/'before-template-expansion'
    manifest=archive/'manifest.json'
    if manifest.exists():
        for item in json.loads(manifest.read_text())['files']:
            if sha(archive/item['name'])!=item['sha256']:
                raise RuntimeError(f'Archived evidence changed: {item["name"]}')
        return archive
    archive.mkdir(parents=True,exist_ok=True);files=[]
    for name in names:
        p=folder/name
        if p.exists():
            shutil.copy2(p,archive/name)
            files.append({'name':name,'sha256':sha(p)})
    dump(manifest,{'purpose':'Original pre-expansion evidence; never overwritten on rerun',
         'files':files})
    return archive

def canonical_mesh(faces):
    rounded=sorted(tuple(sorted(tuple(round(v,5)for v in p)for p in face))for face in faces)
    return hashlib.sha256(json.dumps(rounded,separators=(',',':')).encode()).hexdigest()

def stl_faces(path):
    b=path.read_bytes()
    if len(b)>=84 and 84+50*struct.unpack_from('<I',b,80)[0]==len(b):
        rows=[struct.unpack_from('<12f',b,84+50*i)for i in range(struct.unpack_from('<I',b,80)[0])]
        return [tuple(tuple(row[j:j+3])for j in (3,6,9))for row in rows]
    vertices=[tuple(map(float,m))for m in re.findall(r'^\s*vertex\s+(\S+)\s+(\S+)\s+(\S+)',b.decode(),re.M)]
    return [vertices[i:i+3]for i in range(0,len(vertices),3)]

def project_facts(path):
    with zipfile.ZipFile(path)as z:
        settings=ET.fromstring(z.read('Metadata/model_settings.config'))
        part=settings.find('./object/part')
        md={m.attrib['key']:m.attrib.get('value')for m in part.findall('metadata')if'key'in m.attrib}
        offset=[float(md['source_offset_'+a])for a in 'xyz']
        main=ET.fromstring(z.read('3D/3dmodel.model'))
        component=main.find('./m:resources/m:object/m:components/m:component',NS)
        item=main.find('./m:build/m:item',NS)
        objpath=next(v.lstrip('/')for k,v in component.attrib.items()if k.endswith('}path'))
        obj=ET.fromstring(z.read(objpath))
        vertices=[tuple(float(v.attrib[a])+offset[i]for i,a in enumerate('xyz'))for v in obj.findall('.//m:vertex',NS)]
        faces=[tuple(vertices[int(t.attrib[a])]for a in ['v1','v2','v3'])for t in obj.findall('.//m:triangle',NS)]
        return {'source_file':md['source_file'],'source_offset':offset,
            'component_transform':[float(v)for v in component.attrib['transform'].split()],
            'build_transform':[float(v)for v in item.attrib['transform'].split()],
            'face_count':len(faces),'canonical_source_mesh_sha256_5dp':canonical_mesh(faces)}

def repair_shared_machine():
    archive=archive_once(CONFIG,['machine.json','process.json','filament.json','source-identity.json'])
    machine_path=CONFIG/'machine.json';before=json.loads(machine_path.read_text());machine=dict(before)
    preset_path=PROFILE_ROOT/'Bambu Lab X1 Carbon 0.4 nozzle.json'
    preset=json.loads(preset_path.read_text());records=[]
    for name in preset['include']:
        p=PROFILE_ROOT/(name+'.json');fragment=json.loads(p.read_text())
        fields=[f for f in FIELDS if f in fragment]
        if len(fields)!=1:raise RuntimeError(f'Unexpected official fragment fields: {p}')
        field=fields[0];machine[field]=fragment[field]
        records.append({'field':field,'source':str(p),'source_sha256':sha(p),
            'was_already_equal':before.get(field)==fragment[field]})
    if {r['field']for r in records}!=set(FIELDS):raise RuntimeError('Incomplete machine G-code template set')
    machine.pop('include',None)
    # Preserve every other current shared field, including the explicit PEI
    # analysis assumption. Do not import template name/instantiation metadata.
    changed=[k for k in set(before)|set(machine)if before.get(k)!=machine.get(k)]
    if set(changed)-set(FIELDS)-{'include'}:raise RuntimeError('Unexpected shared config mutation')
    dump(machine_path,machine)
    identity_path=CONFIG/'source-identity.json';identity=json.loads(identity_path.read_text())
    for r in records:identity.setdefault('source_sha256',{})[r['source']]=r['source_sha256']
    identity['template_expansion']={'strategy':'Official child include fields override inherited common G-code; template metadata is not merged.',
        'archived_original_config':str(archive.relative_to(ROOT)),
        'official_machine_preset':str(preset_path),'official_machine_preset_sha256':sha(preset_path),
        'templates':records,'resolved_machine_sha256':sha(machine_path),
        'process_and_filament_unchanged':True,'script':str(Path(__file__).relative_to(ROOT))}
    dump(identity_path,identity)
    return {'changed_fields_this_run':changed,'templates':records,'machine_sha256':sha(machine_path),
        'original_config_archive':str(archive.relative_to(ROOT))}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    old=archive_once(OUT,['hold-fork-slice-review.3mf','plate_1.gcode','result.json'])
    original=project_facts(old/'hold-fork-slice-review.3mf')
    source_faces=stl_faces(STL);current=canonical_mesh(source_faces)
    if current!=original['canonical_source_mesh_sha256_5dp']:
        raise RuntimeError('Current STL differs from original sliced hold fork; stop instead of silently substituting a part')
    initial_stl_sha=sha(STL)
    cad_paths=[ROOT/'cad/spin-head.scad',ROOT/'cad/spin-parameters.scad',ROOT/'cad/parameters.scad']
    cad_sha={str(p.relative_to(ROOT)):sha(p)for p in cad_paths}
    fix=repair_shared_machine()
    config_sha={n:sha(CONFIG/(n+'.json'))for n in ['machine','process','filament']}
    command=[BAMBU,'--datadir',str(OUT/'app-data'),'--load-settings',
        str(CONFIG/'machine.json')+';'+str(CONFIG/'process.json'),
        '--load-filaments',str(CONFIG/'filament.json'),'--orient','0','--rotate-y','-90',
        '--arrange','1','--ensure-on-bed','--slice','0','--export-3mf','hold-fork-slice-review.3mf',
        '--outputdir',str(OUT),str(STL)]
    # Remove stale output markers so a failed export cannot inherit an old pass.
    for n in ['result.json','hold-fork-slice-review.3mf','plate_1.gcode']:(OUT/n).unlink(missing_ok=True)
    dump(OUT/'invocation.json',{'command':command,'input_stl_sha256':initial_stl_sha,'config_sha256':config_sha,
        'offline_only':True,'sent_to_printer':False})
    run=subprocess.run(command,cwd=ROOT,text=True,capture_output=True)
    (OUT/'bambu-cli.log').write_text(run.stdout+run.stderr)
    if run.returncode or not all((OUT/n).exists()for n in ['result.json','plate_1.gcode','hold-fork-slice-review.3mf']):
        dump(OUT/'review-report.json',{'status':'SLICE_EXECUTION_FAILED','return_code':run.returncode,
            'command':command,'shared_config_fix':fix,'no_print_sent':True})
        return 1
    native=json.loads((OUT/'result.json').read_text());gcode=(OUT/'plate_1.gcode').read_text()
    first_layer=gcode.index('; CHANGE_LAYER')
    heaters=[{'offset':m.start(),'command':m[0].strip(),'temperature_c':float(m[1])}
        for m in re.finditer(r'^M10[49]\b[^\n;]*?\bS([-+\d.]+)[^\n]*',gcode,re.M)]
    before_layer=[h for h in heaters if h['offset']<first_layer]
    first_temp=before_layer[-1]['temperature_c']if before_layer else None
    filament=json.loads((CONFIG/'filament.json').read_text());target=float(filament['nozzle_temperature_initial_layer'][0])
    machine=json.loads((CONFIG/'machine.json').read_text())
    template_matches={r['field']:machine[r['field']]==json.loads(Path(r['source']).read_text())[r['field']]for r in fix['templates']}
    new=project_facts(OUT/'hold-fork-slice-review.3mf')
    original_gcode=(old/'plate_1.gcode').read_text()
    old_heaters=re.findall(r'^M10[49]\b.*$',original_gcode,re.M)
    warnings=[p.get('warning_message','')for p in native.get('sliced_plates',[])if p.get('warning_message')]
    checks={'process_and_native_return_zero':run.returncode==0 and native.get('return_code')==0,
        'no_native_warning':not warnings,'five_official_templates_exact':all(template_matches.values()),
        'initial_nozzle_target_is_255':target==255,'last_setpoint_before_first_layer_matches':first_temp==target,
        'same_mesh_as_original_slice':new['canonical_source_mesh_sha256_5dp']==current,
        'same_component_orientation':all(abs(a-b)<1e-9 for a,b in zip(original['component_transform'],new['component_transform'])),
        'same_build_placement':all(abs(a-b)<1e-9 for a,b in zip(original['build_transform'],new['build_transform'])),
        'input_stl_unchanged':sha(STL)==initial_stl_sha,
        'cad_unchanged':all(sha(ROOT/p)==h for p,h in cad_sha.items()),
        'configs_stable_during_slice':all(sha(CONFIG/(n+'.json'))==h for n,h in config_sha.items())}
    plate=native['sliced_plates'][0]
    report={'status':'OFFLINE_HOLD_FORK_SLICE_AUDITED_PHYSICAL_OPEN'if all(checks.values())else'REVIEW_FLAGGED',
        'checks':checks,'command':command,'script_sha256':sha(Path(__file__)),
        'input_stl':str(STL.relative_to(ROOT)),'input_stl_sha256':initial_stl_sha,'cad_sha256':cad_sha,
        'shared_config_fix':fix,'config_sha256':config_sha,'template_matches':template_matches,
        'original_slice_archive':str(old.relative_to(ROOT)),'original_heater_commands':old_heaters,
        'original_3mf':original,'new_3mf':new,'filament_initial_target_c':target,
        'last_nozzle_setpoint_before_first_layer_c':first_temp,'actual_heater_commands':heaters,
        'native_result':native,'warnings':warnings,
        'estimates':{'seconds':plate['total_predication'],'filament_g':plate['filaments'][0]['total_used_g']},
        'artifact_sha256':{n:sha(OUT/n)for n in ['hold-fork-slice-review.3mf','plate_1.gcode','result.json','bambu-cli.log']},
        'assumptions':{'machine':'X1C .4','material':'Generic PETG; brand unconfirmed',
          'plate':'Textured PEI analysis assumption; user confirmed PEI, not texture',
          'layer_height_mm':.2,'wall_loops':4,'infill_percent':25,'supports_enabled':False,
          'orientation':'Original -90 degree Y rotation; original +X becomes print +Z'},
        'limits':['One hold fork only; no inference for other parts or the complete assembly.',
          'Official start/end/filament/time-lapse/layer templates and generated first-layer setpoint checked; no physical printer execution.',
          'Fit, PETG strength, layer adhesion, wear, bed-specific adhesion and actual temperature remain untested.'],
        'sent_to_printer':False,'print_ready':False}
    dump(OUT/'review-report.json',report)
    with zipfile.ZipFile(OUT/'hold-fork-slice-review.3mf')as z:
        (OUT/'plate-preview.png').write_bytes(z.read('Metadata/plate_1.png'))
    print(json.dumps({k:report[k]for k in ['status','checks','estimates','last_nozzle_setpoint_before_first_layer_c']},indent=2))
    return 0 if all(checks.values())else 1

if __name__=='__main__':raise SystemExit(main())
