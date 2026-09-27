#!/usr/bin/env python3
"""Rebind unchanged printed meshes to frozen slice evidence; never slice/print.

Run with FreeCAD Python. Historical source hashes remain historical; only the
new export is checked against live CAD. A changed part loses its selected plate.
"""
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import argparse, copy, hashlib, json, sys, zipfile
import xml.etree.ElementTree as ET
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'analysis')]
from review_cable_slice import read_stl
from cable_slice_artifacts import normalization_review

CHANGED={'feeder/cable-input-body','feeder/cable-input-lever','feeder/cable-input-cover'}
CAP='feeder/cable-input-terminal-cap'
NS={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}

def path(p):
    p=Path(p);return p if p.is_absolute() else ROOT/p
def sha(p):return hashlib.sha256(path(p).read_bytes()).hexdigest()
def rel(p):
    p=path(p).resolve();return str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)
def load(p):return json.loads(path(p).read_text())
def dump(p,v):path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def faces(tri):
    def key(t):
        v=[tuple(float(x) for x in q) for q in t]
        return min(tuple(v),tuple(v[1:]+v[:1]),tuple(v[2:]+v[:2]))
    return Counter(key(t) for t in tri)
def transform(tri,m):return tri@m[:3,:3].T+m[:3,3]

def cap_archive_check(current, old_item, binding, current_to_old, ci):
    # Recheck the actual normal mesh rather than relying on equal bounding boxes.
    item=next(r for r in binding['items'] if r['instance_id']==CAP)
    placement=item['placement'];pre=np.array(placement['cad_to_oriented'])
    with zipfile.ZipFile(path(old_item['selected_3mf'])) as z:
        main=ET.fromstring(z.read('3D/3dmodel.model'))
        settings=ET.fromstring(z.read('Metadata/model_settings.config'))
        builds=main.findall('./m:build/m:item',NS);assert len(builds)==1
        resource=main.find('./m:resources/m:object[@id="'+builds[0].attrib['objectid']+'"]',NS)
        normal=settings.findall('./object/part[@subtype="normal_part"]');assert len(normal)==1
        cp=next(c for c in resource.findall('./m:components/m:component',NS) if c.attrib['objectid']==normal[0].attrib['id'])
        name=next(v for k,v in cp.attrib.items() if k.endswith('}path')).lstrip('/')
        model=ET.fromstring(z.read(name));mesh=model.find('./m:resources/m:object[@id="'+cp.attrib['objectid']+'"]/m:mesh',NS)
        vertices=np.array([[float(v.attrib[a]) for a in 'xyz'] for v in mesh.findall('./m:vertices/m:vertex',NS)])
        triangles=np.array([[int(v.attrib[a]) for a in ['v1','v2','v3']] for v in mesh.findall('./m:triangles/m:triangle',NS)])
        md={m.attrib['key']:m.attrib.get('value') for m in normal[0].findall('./metadata')}
        offset=np.array([float(md['source_offset_'+a]) for a in 'xyz'])
    proof=normalization_review(transform(current,pre@current_to_old),vertices+offset,triangles)
    assert proof['status']=='BOUNDED_VERTEX_CONTRACTION_VERIFIED'
    assert not proof['collapsed_source_triangle_indices'] and len(current)==len(triangles)
    local=np.eye(4);local[:3,:3]=np.array([ci['basis_x'],ci['basis_y'],ci['basis_z']]).T;local[:3,3]=ci['origin']
    command=np.array(placement['cad_to_command'])@current_to_old
    err=float(np.max(np.abs(command@local-np.array(placement['input_local_to_command']))))
    assert err<1e-8,'Local feature/toolpath alignment changed'
    return {'actual_3mf_normal_mesh':proof,'current_cad_to_oriented':(pre@current_to_old).tolist(),
            'current_cad_to_command':command.tolist(),'current_input_local_to_command':(command@local).tolist(),
            'local_mapping_max_difference_mm':err,
            'support_scope':'Unchanged local normal mesh, existing enforcers and exact same 3MF/Gcode; inherit the prior bounded cleanup findings, including recorded strict failures.'}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--export-report',type=Path,required=True)
    ap.add_argument('--baseline-export',type=Path,default=ROOT/'output/cable-scene-export/20260927T091627124663Z/report.json')
    ap.add_argument('--baseline-manifest',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    evidence={}
    def verify(p,h=None):
        actual=sha(p)
        if h is not None:assert actual==h,'Changed evidence: '+str(p)
        key=rel(p);assert key not in evidence or evidence[key]==actual
        evidence[key]=actual;return actual
    for p in [__file__,ROOT/'analysis/cable_slice_artifacts.py',ROOT/'scripts/review_cable_slice.py',
              args.export_report,args.baseline_export,args.baseline_manifest]:verify(p)
    new=load(args.export_report);old=load(args.baseline_export);base=load(args.baseline_manifest)
    assert new['status']=='CURRENT_SCENE_EXPORT_PASS' and new['sources_stable']
    assert old['status']=='CURRENT_SCENE_EXPORT_PASS' and base['counts']['bound_instances']==56
    for p,h in new['source_sha256'].items():verify(p,h)
    inv_path=args.export_report.parent/'inventory.json';verify(inv_path,new['inventory_sha256']);inv=load(inv_path)
    current={r['id']:r for r in new['parts'] if r['role']=='printed'}
    previous={r['id']:r for r in old['parts'] if r['role']=='printed'}
    bound={r['instance_id']:r for r in base['items']}
    assert set(current)==set(previous)==set(bound) and len(current)==56
    mapping=[];items=[];selected=defaultdict(list)
    for ident,row in current.items():
        prior=previous[ident];b=bound[ident]
        assert row['passed'] and prior['passed']
        verify(row['file'],row['sha256']);verify(prior['file'],prior['sha256'])
        assert b['current_stl_sha256']==prior['sha256']
        verify(b['binding_report'],b['binding_report_sha256'])
        verify(b['selected_3mf'],b['selected_3mf_sha256']);verify(b['gcode'],b['gcode_sha256'])
        with zipfile.ZipFile(path(b['selected_3mf'])) as z:
            assert hashlib.sha256(z.read('Metadata/plate_1.gcode')).hexdigest()==b['gcode_sha256']
            project=json.loads(z.read('Metadata/project_settings.config'))
            assert project['printer_model']=='Bambu Lab X1 Carbon' and project['nozzle_diameter']==['0.4']
            assert project['filament_type']==(['TPU'] if b['material']=='Bambu TPU 95A HF' else ['PETG'])
        a=read_stl(path(row['file']));p=read_stl(path(prior['file']))
        matrix=np.eye(4)
        if ident==CAP:matrix[:3,3]=[0,3,0]
        equivalent=len(a)==len(p) and faces(transform(a,matrix))==faces(p)
        changed=ident in CHANGED
        assert equivalent!=changed,(ident,'Unexpected geometry relation; do not silently expand reuse')
        proof={'instance_id':ident,'current_stl':row['file'],'current_stl_sha256':row['sha256'],
               'historical_stl':prior['file'],'historical_stl_sha256':prior['sha256'],
               'byte_identical':row['sha256']==prior['sha256'],'current_triangle_count':len(a),
               'historical_triangle_count':len(p),'current_to_historical_cad':matrix.tolist(),
               'exact_oriented_triangle_multiset_equal':equivalent,'needs_reslice':changed,
               'historical_binding_report':b['binding_report'],'historical_binding_report_sha256':b['binding_report_sha256'],
               'historical_identity_status':b['identity_status'],'historical_process_status':b['process_status']}
        if ident==CAP:
            proof['translated_cap']=cap_archive_check(a,b,load(b['binding_report']),matrix,inv['scene_contract']['ci'])
        item=copy.deepcopy(b);item.update(current_stl=row['file'],current_stl_sha256=row['sha256'],
            needs_reslice=changed,pending_review=changed,
            binding_report=rel(out/'report.json'),binding_report_sha256=None,
            historical_binding_report=b['binding_report'],historical_binding_report_sha256=b['binding_report_sha256'],
            inherited_identity_status=b['identity_status'],inherited_process_status=b['process_status'],
            identity_status='GEOMETRY_CHANGED_NEEDS_RESLICE' if changed else 'EXACT_ORIENTED_MESH_REBIND'+('_CAD_TRANSLATION' if ident==CAP else ''),
            reason='New shaft bore/socket/relief geometry requires a new slice and feature review.' if changed else
                   'Every oriented source triangle matches frozen baseline under the stated rigid transform; original slice artifacts and bounded process findings retained.',
            manufacturing_release=False,physical_acceptance=False)
        if changed:
            item.update(historical_selected_3mf=b['selected_3mf'],historical_selected_3mf_sha256=b['selected_3mf_sha256'],
                historical_gcode=b['gcode'],historical_gcode_sha256=b['gcode_sha256'],selected_3mf=None,
                selected_3mf_sha256=None,candidate_3mf=None,candidate_3mf_sha256=None,gcode=None,gcode_sha256=None,
                process_status='NEEDS_NEW_SLICE_AND_FEATURE_REVIEW')
        else:selected[item['selected_3mf']].append(ident)
        items.append(item);mapping.append(proof)
    plates=[]
    by_id={r['instance_id']:r for r in items}
    for plate,ids in selected.items():
        assert {by_id[i]['plate_quantity'] for i in ids}=={len(ids)},'Cannot partially reuse a multi-instance plate'
        plates.append({'file':plate,'sha256':sha(plate),'instance_ids':ids,'quantity':len(ids),
                       'print_plate_once_for_these_instances':True,'pending_review':False})
    counts={'printed_instances':56,'material_instances':dict(Counter(r['material'] for r in items)),
            'bound_instances':53,'candidate_instances':0,'pending_instances':3,'needs_reslice_instances':3,
            'selected_plates':len(plates),'candidate_plates':0}
    assert sum(not r['needs_reslice'] for r in items)==53
    assert all(sha(p)==h for p,h in evidence.items()),'Evidence changed during rebind'
    report={'status':'CURRENT_ECLIP_53_SLICES_REBOUND_3_REQUIRE_RESLICE','created_utc':datetime.now(timezone.utc).isoformat(),
            'current_export':{'file':rel(args.export_report),'sha256':sha(args.export_report)},
            'historical_export':{'file':rel(args.baseline_export),'sha256':sha(args.baseline_export)},
            'historical_manifest':{'file':rel(args.baseline_manifest),'sha256':sha(args.baseline_manifest)},
            'counts':counts,'mapping':mapping,'evidence_sha256':evidence,'sources_and_artifacts_stable':True,
            'scope':'52 unchanged meshes and one exactly translated terminal cap reuse frozen selected artifacts. Three changed models are unselected. Historical whole-source hashes are not relabelled current; their process/physical limitations remain inherited.',
            'manufacturing_release':False,'physical_acceptance':False,'sent_to_printer':False}
    dump(out/'report.json',report);report_sha=sha(out/'report.json')
    for item in items:item['binding_report_sha256']=report_sha
    manifest={'schema_version':1,'status':'CURRENT_MANUFACTURING_INDEX_WITH_OPEN_GATES','counts':counts,'items':items,'plates':plates,
              'candidate_plates':[],'evidence_sha256':{**evidence,rel(out/'report.json'):report_sha},
              'sources_and_artifacts_stable':True,'manufacturing_release':False,'physical_acceptance':False,'sent_to_printer':False,
              'scope':report['scope'],'assumptions':base['assumptions']}
    dump(out/'manifest.json',manifest)
    print(json.dumps({'status':report['status'],'counts':counts,'manifest':rel(out/'manifest.json'),'report_sha256':report_sha},indent=2))

if __name__=='__main__':main()
