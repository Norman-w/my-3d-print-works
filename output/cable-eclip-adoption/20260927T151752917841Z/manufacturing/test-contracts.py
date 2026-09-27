from pathlib import Path
import sys,json,copy,hashlib,numpy as np
ROOT=Path(__file__).resolve().parents[4];sys.path[:0]=[str(ROOT/'analysis'),str(ROOT/'scripts')]
from cable_slice_contract import frozen_scene,input_matrix,route_frame,legacy_scene
from cable_input_slice_review import slice_mapping
from cable_flat_slice_review import specifications,ci
from rebind_eclip_manufacturing import faces,transform
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
oldfolder=ROOT/'output/print-review/current-cable/20260927T073454146325Z/cable-input-body'
inv=json.loads((oldfolder/'invocation.json').read_text());old,e=frozen_scene(inv)
assert old['ci']['origin']==[75,-82,5]
assert not e['current_whole_source_matches_historical']
mapping,e2=slice_mapping(oldfolder,inv)
assert e2['frozen_scene_contract']['frozen_inventory_sha256']==e['frozen_inventory_sha256']
newpath=ROOT/'output/cable-scene-export/20260927T153058669616Z/report.json';r=json.loads(newpath.read_text());part=next(x for x in r['parts']if x['id']=='feeder/cable-input-cover')
newinv={'export_report':str(newpath),'export_report_sha256':sha(newpath),'part':'cable-input-cover','input':part,'source_sha256_at_start':r['source_sha256']}
new,ne=frozen_scene(newinv)
assert np.allclose(input_matrix(new)[:3,3]-input_matrix(old)[:3,3],[0,-3,0],rtol=0,atol=1e-12)
assert np.array_equal(input_matrix(new)[:3,:3],input_matrix(old)[:3,:3])
for a,b in zip(route_frame(old),route_frame(new)):assert np.allclose(a,b,rtol=0,atol=1e-10)
assert np.allclose(ci([0,0,14],old),[75,-68,5],rtol=0,atol=1e-12)
assert np.allclose(ci([0,0,14],new),[75,-71,5],rtol=0,atol=1e-12)
assert specifications('cable-input-cover',old)[0][0]['plane']==4.5
for bad in [dict(inv,export_report_sha256='0'*64),dict(inv,input=part)]:
 try:frozen_scene(bad)
 except ValueError:pass
 else:raise AssertionError('Unbound report/input accepted')
bad=copy.deepcopy(old);bad['_slice_source_sha256']['cad/cable-housing-route.scad']='unknown'
try:route_frame(bad)
except ValueError:pass
else:raise AssertionError('Legacy route constants used for unknown source')
tri=np.array([[[0.,0,0],[1,0,0],[0,1,0]],[[0,0,1],[0,1,1],[1,0,1]]])
assert faces(tri)==faces(np.roll(tri[::-1],1,axis=1))
assert faces(tri)!=faces(tri[:,::-1,:])
changed=tri.copy();changed[0,0,0]+=.000000001;assert faces(tri)!=faces(changed)
m=np.eye(4);m[:3,3]=[0,3,0];assert faces(tri)==faces(transform(tri-[0,3,0],m))
print(json.dumps({'status':'FROZEN_COORDINATES_AND_EXACT_FACE_IDENTITY_TESTS_PASS','old_origin':old['ci']['origin'],'new_origin':new['ci']['origin'],'third_arc_unchanged':True,'historical_actual_3mf_mapping_recovered':True,'negative_report_sha_input_mesh_unknown_route_reversed_face_and_1nm_change_rejected':True,'source_sha256':{str(p.relative_to(ROOT)):sha(p)for p in [ROOT/'analysis/cable_slice_contract.py',ROOT/'analysis/cable_input_slice_review.py',ROOT/'analysis/cable_flat_slice_review.py',ROOT/'analysis/cable_direct_pull_slice_review.py',ROOT/'scripts/rebind_eclip_manufacturing.py',Path(__file__)]}},indent=2))
