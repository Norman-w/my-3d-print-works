#!/usr/bin/env python3
"""Process-only second candidate: four blockers plus two rear-key enforcers.

Contract: PETG/X1C/.4; same +CAD Z build and one-piece rear clamp.
Keep collar, rear-key supports and every functional/fastener surface.
Block only plate bores and strap slots; key width 2.6 < bore 2.9 means
blocking the entire rear key would create a fresh unsupported cantilever.
No purchase, printer connection or automatic manufacturing adoption.
"""
from pathlib import Path
from datetime import datetime, timezone
import copy
import hashlib
import json
import shutil
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET
import zipfile

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
OLD = ROOT / 'output/current-manufacturing/feeder-new/runs/20260927T094300899015Z/inlet-rear-anchor-z-down-supported'
sys.path.insert(0, str(ROOT / 'analysis'))
import cable_input_slice_review as geom

CORE = 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
PROD = 'http://schemas.microsoft.com/3dmanufacturing/production/2015/06'
REL = 'http://schemas.openxmlformats.org/package/2006/relationships'
NS = {'m': CORE}
ET.register_namespace('', CORE)
ET.register_namespace('p', PROD)
FACES = [[0,2,1],[1,2,3],[4,5,6],[5,7,6],[0,1,4],[1,5,4],
         [2,6,3],[3,6,7],[0,4,2],[2,4,6],[1,3,5],[3,7,5]]


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v): Path(p).write_text(json.dumps(v, ensure_ascii=False, indent=2)+'\n')
def xml(root):
    ET.register_namespace('', REL if root.tag.startswith('{'+REL+'}') else CORE)
    result=ET.tostring(root,encoding='utf-8',xml_declaration=True)
    ET.register_namespace('',CORE)
    return result


def main():
    old=json.loads((OLD/'invocation.json').read_text())
    source=ROOT/old['inputs'][0]['file']
    assert sha(source)==old['inputs'][0]['sha256']
    assert sha(source)=='146bcf746c8f1a52825c68675ad1844d8ed4de079c75c3885504240121e3069a'
    identities={**old['source_sha256_at_start'],str(Path(__file__).relative_to(ROOT)):sha(__file__)}
    assert all(sha(ROOT/p)==h for p,h in identities.items())
    f=OUT/'runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    f.mkdir(parents=True)
    with zipfile.ZipFile(OLD/'slice-review.3mf') as z: data={n:z.read(n) for n in z.namelist()}
    main=ET.fromstring(data['3D/3dmodel.model'])
    settings=ET.fromstring(data['Metadata/model_settings.config'])
    rels=ET.fromstring(data['3D/_rels/3dmodel.model.rels'])
    cs=main.find('./m:resources/m:object/m:components',NS)
    basec=cs.find('./m:component',NS)
    config=settings.find('./object')
    assert len(cs)==1 and len(config.findall('./part'))==1
    C=geom.three_mf_matrix(basec.attrib['transform'])
    meta={m.attrib['key']:m.attrib.get('value') for m in config.find('./part').findall('./metadata')}
    offset=np.array([float(meta['source_offset_'+a]) for a in 'xyz'])
    # Original STL is stored translated by -source_offset in its raw mesh.
    # Reusing the same component transform preserves CAD coordinates exactly.
    assert np.allclose(C[:3,:3],np.eye(3)) and np.allclose(C[:3,3],offset)
    normal_file=next(v.lstrip('/') for k,v in basec.attrib.items() if k.endswith('}path'))
    normal_digest=hashlib.sha256(data[normal_file]).hexdigest()
    boxes=[]
    for x in [-10.5,10.5]:
        boxes.append(dict(name='plate_bore_'+str(x),bounds=[[x-1.85,-48.4,-143.85],[x+1.85,-40.8,-140.05]],reason='Plate only; retain projecting rear-key support behind Y=-48.4.'))
    for x in [-20.5,20.5]:
        boxes.append(dict(name='strap_slot_'+str(x),bounds=[[x-1.9,-48.4,-153.4],[x+1.9,-41.6,-130.6]],reason='Open 3 mm slot; actual bridge anchorage must be reviewed.'))
    for x in [-10.5,10.5]:
        boxes.append(dict(name='rear_key_upper_enforcer_'+str(x),bounds=[[x-1.4,-53.95,-141.5],[x+1.4,-48.5,-140.4]],subtype='support_enforcer',reason='Force support under first rear-key upper wall while staying outside plate-bore blocker.'))
    for i,b in enumerate(boxes):
        oid=str(20+i);lo,hi=np.array(b['bounds'])
        vertices=np.array([[x,y,z] for z in [lo[2],hi[2]] for y in [lo[1],hi[1]] for x in [lo[0],hi[0]]])-offset
        model=ET.Element('{'+CORE+'}model',unit='millimeter')
        res=ET.SubElement(model,'{'+CORE+'}resources')
        obj=ET.SubElement(res,'{'+CORE+'}object',id=oid,type='model')
        mesh=ET.SubElement(obj,'{'+CORE+'}mesh')
        vs=ET.SubElement(mesh,'{'+CORE+'}vertices'); ts=ET.SubElement(mesh,'{'+CORE+'}triangles')
        for v in vertices: ET.SubElement(vs,'{'+CORE+'}vertex',**{a:format(n,'.17g') for a,n in zip('xyz',v)})
        for t in FACES: ET.SubElement(ts,'{'+CORE+'}triangle',**{a:str(n) for a,n in zip(['v1','v2','v3'],t)})
        file='3D/Objects/blocker_'+oid+'.model';data[file]=xml(model)
        cp=copy.deepcopy(basec);cp.set('objectid',oid);cp.set('{'+PROD+'}path','/'+file);cp.set('{'+PROD+'}UUID',str(uuid.uuid4()));cs.append(cp)
        part=ET.SubElement(config,'part',id=oid,subtype=b.get('subtype','support_blocker'),uuid=str(uuid.uuid4()))
        for k,v in {'name':b['name'],'matrix':' '.join(format(v,'.17g') for v in C.reshape(-1)),
                    'source_file':'process-only-blocker','source_object_id':'0','source_volume_id':str(i+1)}.items():
            ET.SubElement(part,'metadata',key=k,value=v)
        ET.SubElement(part,'mesh_stat',face_count='12',edges_fixed='0',degenerate_facets='0',facets_removed='0',facets_reversed='0',backwards_edges='0')
        ET.SubElement(rels,'{'+REL+'}Relationship',Target='/'+file,Id='blocker-'+oid,Type='http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel')
        b.update(object_id=oid,subtype=b.get('subtype','support_blocker'),raw_mesh_sha256=hashlib.sha256(data[file]).hexdigest())
    data['3D/3dmodel.model']=xml(main);data['Metadata/model_settings.config']=xml(settings);data['3D/_rels/3dmodel.model.rels']=xml(rels)
    assert hashlib.sha256(data[normal_file]).hexdigest()==normal_digest
    for name in list(data):
        if '.gcode' in name or name in ['Metadata/slice_info.config','Metadata/plate_1.json']:del data[name]
    inp=f/'modifiers-input.3mf'
    with zipfile.ZipFile(inp,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for n,v in data.items():z.writestr(n,v)
    for n in ['machine','filament']:shutil.copy2(OLD/(n+'.json'),f/(n+'.json'))
    process=json.loads((OLD/'process.json').read_text())
    process.update(layer_height='0.1',initial_layer_print_height='0.1')
    dump(f/'process.json',process)
    cmd=['/Applications/BambuStudio.app/Contents/MacOS/BambuStudio','--datadir',str(f/'app-data'),
         '--load-settings',str(f/'machine.json')+';'+str(f/'process.json'),'--load-filaments',str(f/'filament.json'),
         '--orient','0','--arrange','0','--ensure-on-bed','--slice','0','--export-3mf','slice-review.3mf','--outputdir',str(f),str(inp)]
    inv=dict(family='inlet-rear',inputs=old['inputs'],source_sha256_at_start=identities,modifiers=boxes,
             inherited_invocation=str((OLD/'invocation.json').relative_to(ROOT)),inherited_invocation_sha256=sha(OLD/'invocation.json'),
             inherited_3mf_sha256=sha(OLD/'slice-review.3mf'),input3mf_sha256=sha(inp),input_normal_mesh_xml_sha256=normal_digest,
             command=cmd,local_profile_sha256={n:sha(f/(n+'.json')) for n in ['machine','process','filament']},
             mechanical_geometry_changed=False,sent_to_printer=False,manufacturing_release=False,physical_acceptance=False)
    dump(f/'invocation.json',inv);dump(OUT/'latest.json',{'folder':str(f.relative_to(ROOT)),'status':'NATIVE_SLICING'})
    print(str(f),flush=True)
    r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
    (f/'bambu-cli.log').write_text(r.stdout+r.stderr)
    inv.update(return_code=r.returncode,input_and_cad_stable=all(sha(ROOT/p)==h for p,h in identities.items()))
    if (f/'result.json').exists():inv['native_result']=json.loads((f/'result.json').read_text())
    inv['artifact_sha256']={n:sha(f/n) for n in ['slice-review.3mf','plate_1.gcode'] if (f/n).exists()}
    dump(f/'invocation.json',inv)
    status='NATIVE_CANDIDATE_REVIEW_REQUIRED' if r.returncode==0 and len(inv['artifact_sha256'])==2 else 'NATIVE_SLICE_FAILED'
    dump(OUT/'latest.json',dict(folder=str(f.relative_to(ROOT)),status=status))
    print(json.dumps(dict(status=status,return_code=r.returncode,warnings=[x.get('warning_message') for x in inv.get('native_result',{}).get('sliced_plates',[])]),ensure_ascii=False),flush=True)


if __name__=='__main__':main()
