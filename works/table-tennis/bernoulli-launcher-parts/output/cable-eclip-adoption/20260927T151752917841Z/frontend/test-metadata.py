from pathlib import Path
import copy, hashlib, importlib.util, json
ROOT=Path(__file__).resolve().parents[4]
def module(name,filename):
 spec=importlib.util.spec_from_file_location(name,ROOT/filename)
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
sync=module('inventory_sync','scripts/sync_cable_inventory.py')
publisher=module('scene_publisher','scripts/publish_cable_scene.py')
source=ROOT/'docs/cable-assembly-inventory.json'
before=source.read_bytes(); inventory=json.loads(before)
rows=copy.deepcopy(inventory['parts'])
original={r['id']:copy.deepcopy(r) for r in rows}
sync.update_axis_scene_rows(rows)
assert len(rows)==86
counts={role:sum(r['role']==role for r in rows) for role in ['printed','purchased','reference']}
assert counts=={'printed':56,'purchased':23,'reference':7},counts
assert len({r['id'] for r in rows})==86
for r in rows:
 if r['id'] in original:
  expected=copy.deepcopy(original[r['id']])
  if r['id'] in ['feeder/cable-input-body','feeder/cable-input-hardware-fixed']:expected['backend']='CGAL'
  assert r==expected,r['id']
first=copy.deepcopy(rows); sync.update_axis_scene_rows(rows); assert rows==first
reference=next(r for r in rows if r['id']=='feeder/cable-input-eclip-space')
assert reference['definitions']=={'cse_part':'input-eclip-space','cse_t':0}
assert reference['motion']=={'kind':'fixed'}
published=[]
for r in rows:
 row=publisher.manifest_part(r,'TEST_FIXTURE_NOT_EXPORTED/'+r['id']+'.stl','0'*64,1)
 assert row['motion']==r['motion']
 assert row['role']==r['role']
 if 'display' in r:
  assert row['display']==r['display'] and row['display'] is not r['display']
  assert row['color']==r['display']['color']
 published.append(row)
assert 'scene-display.mjs' in publisher.WEB
assert len(publisher.WEB)==len(set(publisher.WEB))
bad=copy.deepcopy(first);next(r for r in bad if r['id']==reference['id'])['role']='purchased'
try:sync.update_axis_scene_rows(bad)
except ValueError:pass
else:raise AssertionError('Physical part overwrite accepted')
bad=copy.deepcopy(first)+[copy.deepcopy(reference)]
try:sync.update_axis_scene_rows(bad)
except ValueError:pass
else:raise AssertionError('Duplicate reference accepted')
assert source.read_bytes()==before,'Production inventory was modified'
fixture={'snapshot':'TEST_METADATA_ONLY_NOT_EXPORTED','assembly_catalog':published,'scene_contract':inventory['scene_contract']}
Path(__file__).with_name('metadata-fixture.json').write_text(json.dumps(fixture,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'passed':True,'counts':counts,'idempotent':True,'all_original_rows_preserved_except_CGAL':True,'physical_hardware_groups_unchanged':True,'production_inventory_unchanged':True}))
