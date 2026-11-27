#!/usr/bin/env python3
"""Refresh current scene metadata from the native precise CAD contract.

Preserves explicit part identities and spin/reference metadata. This updates
the review inventory only, never exports or publishes an asset implicitly.
"""
from datetime import datetime, timezone
from pathlib import Path
import copy
import hashlib
import json
import math
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT/'docs/cable-assembly-inventory.json'
CAD = ROOT/'cad/cable-scene-export.scad'
EXE = '/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes():
    paths = {Path(__file__).resolve()}
    pending = [CAD]
    while pending:
        path = pending.pop().resolve()
        if path in paths:
            continue
        paths.add(path)
        pending.extend(path.parent/dep for dep in re.findall(
            r'\b(?:use|include)\s*<([^>]+)>', path.read_text()))
    return {str(p.relative_to(ROOT)):sha(p) for p in sorted(paths)}


def unpack(value):
    if not isinstance(value, list):
        return value
    if value and value[0] == '__f12__':
        if len(value) != 4 or any(type(n) is not int for n in value[1:]):
            raise ValueError('Invalid precise number')
        _, integer, middle, fraction = value
        if abs(integer) >= 1000000 or not (0 <= middle < 1000000 and 0 <= fraction < 1000000):
            raise ValueError('Precise number transport out of range')
        result = integer + middle/1e6 + fraction/1e12
        if not math.isfinite(result):
            raise ValueError('Nonfinite precise number')
        return result
    return [unpack(v) for v in value]


def pairs(rows):
    if any(not isinstance(r,list) or len(r)!=2 or not isinstance(r[0],str) for r in rows):
        raise ValueError('Malformed source contract')
    data = dict(rows)
    if len(data)!=len(rows):
        raise ValueError('Duplicate contract keys')
    return data


def main():
    out = ROOT/'output/cable-direct-adoption/inventory'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out.mkdir(parents=True)
    before = source_hashes()
    echo = out/'scene-contract.echo'
    command = [EXE,'--hardwarnings','-D','cse_part="contract-precise"','-o',str(echo),str(CAD)]
    run = subprocess.run(command,cwd=ROOT,text=True,capture_output=True)
    emitted = echo.read_text() if echo.exists() else ''
    (out/'native.log').write_text(run.stdout+run.stderr)
    if run.returncode or any(s in run.stdout+run.stderr+emitted for s in ['ERROR:','WARNING:']):
        raise RuntimeError('Native contract failed')
    prefix = 'ECHO: "CABLE_SCENE_CONTRACT_PRECISE", '
    lines = [s[len(prefix):] for s in emitted.splitlines() if s.startswith(prefix)]
    if len(lines)!=1:
        raise ValueError('Expected one native scene contract')
    decoded = pairs(unpack(json.loads(re.sub(r'\bundef\b','null',lines[0]))))
    inventory = json.loads(INVENTORY.read_text())
    (out/'inventory-before.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
    scene = inventory['scene_contract']
    for key in ['ci','co','cr','retention']:
        scene[key] = pairs(decoded[key])
    scene['cad_motion_checks'] = {k:v for k,v in decoded.items() if k not in ['ci','co','cr','retention']}
    ci = scene['ci']
    if ci['motion_law']!='fixed-guide-direct-pull-v2' or ci['stroke']!=scene['co']['stroke'] or ci['stroke']!=20:
        raise ValueError('Unexpected input/output law or travel')
    if scene['cr']['route_law']!='fixed-third-arc-equal-length-v1':
        raise ValueError('Unexpected housing installation family')
    rows = inventory['parts']
    by_id = {r['id']:r for r in rows}
    cap_id = 'feeder/cable-input-terminal-cap'
    if cap_id not in by_id:
        cap = copy.deepcopy(by_id['feeder/cable-input-lever'])
        cap.update(id=cap_id,name='芯线端球捕获盖',family='input-terminal-cap',
                   definitions={'cse_part':'input-terminal-cap','cse_t':0})
        rows.insert(rows.index(by_id['feeder/cable-input-lever'])+1,cap)
        by_id[cap_id]=cap
    for key in ['feeder/cable-input-lever',cap_id,'feeder/cable-input-hardware-moving']:
        by_id[key]['motion'] = {'kind':'trigger-rotate','input':'stroke',
            'origin':ci['origin'],'axis':ci['basis_z'],'stroke_mm':ci['stroke'],
            'motion_law':ci['motion_law'],'t_range':[0,1]}
    by_id['feeder/cable-input-body']['backend']='CGAL'
    by_id['feeder/cable-input-hardware-moving']['name']='旋转POM衬套、端球及捕获盖M3螺钉螺母'
    by_id['feeder/cable-input-hardware-moving']['terminal_cap_hardware'] = ci['cap_fasteners']
    core = by_id['feeder/cable-core-input']
    core['name']='固定导向与移动端球之间的钢芯'
    for key in ['arc_rest_angle_deg','arc_end_angle_deg']:
        core['motion'].pop(key,None)
    core['motion']['motion_law']=ci['motion_law']
    inventory['baseline']['added_printed_instances']=8
    inventory['motion_schema']['input_motion_law']=ci['motion_law']
    inventory['counts']={
        **{role:sum(r['role']==role for r in rows) for role in ['printed','purchased','reference']},
        'feeder_printed':sum(r['role']=='printed' and r['group']=='feeder' for r in rows),
        'spin_printed_including_hold':sum(r['role']=='printed' and r['group'] in ['spin','hold'] for r in rows),
        'total_instances':len(rows)}
    if inventory['counts']!={'printed':56,'purchased':23,'reference':6,'feeder_printed':46,'spin_printed_including_hold':10,'total_instances':85}:
        raise ValueError('Inventory instance composition changed unexpectedly')
    if len({r['id'] for r in rows})!=len(rows):
        raise ValueError('Duplicate part id')
    if before!=source_hashes():
        raise RuntimeError('CAD changed during native metadata extraction')
    inventory['source_sha256']=before
    inventory['contract_evidence']={'echo':str(echo.relative_to(ROOT)),'sha256':sha(echo),
        'numeric_encoding':'native cc_pack fixed-decimal 12 places',
        'script':str(Path(__file__).resolve().relative_to(ROOT))}
    INVENTORY.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
    report={'status':'CURRENT_INVENTORY_NATIVE_CONTRACT_PASS_NOT_PUBLISHED',
        'command':command,'source_sha256':before,'sources_stable':True,
        'inventory_sha256':sha(INVENTORY),'counts':inventory['counts'],
        'manufacturing_release':False,'physical_acceptance':False}
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
