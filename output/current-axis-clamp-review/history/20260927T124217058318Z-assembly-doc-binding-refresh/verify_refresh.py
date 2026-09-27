#!/usr/bin/env python3
"""Verify the bounded doc-binding refresh; no CAD or package regeneration."""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import hashlib
import json
import re

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
OLD=ROOT/'output/current-assembly-package/runs/20260927T122149439656Z'
NEW=ROOT/'output/current-assembly-package/runs/20260927T124252819653Z'
CH='output/current-assembly-package/cable-hardware'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text())
def save(p,d): p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
checks=[]
def check(name,ok,detail=None):
    checks.append({'id':name,'passed':bool(ok),'detail':detail})
    assert ok, (name,detail)

a,b=read(OLD/'manifest.json'),read(NEW/'manifest.json')
ha,hb=read(HERE/CH/'hardware.json'),read(ROOT/CH/'hardware.json')
changed={k for k in a.keys()|b.keys() if a.get(k)!=b.get(k)}
check('only_assembly_time_and_source_bindings_changed',changed=={'created_utc','source_sha256'},sorted(changed))
hchanged={k for k in ha.keys()|hb.keys() if ha.get(k)!=hb.get(k)}
check('only_cable_time_and_source_bindings_changed',hchanged=={'created_utc','source_sha256'},sorted(hchanged))
for name,count in [('bom',44),('installed_occurrences',301),('printed_picklist',56)]:
    check(name+'_exact_structural_equality',a[name]==b[name] and len(b[name])==count,count)
for name in ['nonadditive_cable_children','removed_baseline_instances','retained_shared_nut_instances',
             'ignored_duplicate_retained_cable_records','cable_procurement_options_not_additive',
             'design_selections','counts','open_items','manufacturing_release','physical_acceptance']:
    check(name+'_unchanged',a[name]==b[name])
for name in ['hardware.csv','print-picklist.csv','README.md']:
    check(name+'_byte_identical',(OLD/name).read_bytes()==(NEW/name).read_bytes())
for name in ['items','installation_sites','installed_occurrences','procurement_roots_not_additive_with_members','replacement_delta']:
    check('cable_'+name+'_unchanged',ha[name]==hb[name])

changes={k:{'old':a['source_sha256'].get(k),'new':b['source_sha256'].get(k)}
    for k in a['source_sha256'].keys()|b['source_sha256'].keys()
    if a['source_sha256'].get(k)!=b['source_sha256'].get(k)}
check('exactly_expected_two_assembly_binding_changes',set(changes)=={'docs/cable-trigger-input.md',CH+'/hardware.json'},changes)
hc={k:{'old':ha['source_sha256'].get(k),'new':hb['source_sha256'].get(k)}
    for k in ha['source_sha256'].keys()|hb['source_sha256'].keys()
    if ha['source_sha256'].get(k)!=hb['source_sha256'].get(k)}
check('exactly_input_document_cable_binding_change',set(hc)=={'docs/cable-trigger-input.md'},hc)
check('108_current_package_sources_match',len(b['source_sha256'])==108 and all(sha(ROOT/p)==v for p,v in b['source_sha256'].items()))
check('20_current_cable_sources_match',len(hb['source_sha256'])==20 and all(sha(ROOT/p)==v for p,v in hb['source_sha256'].items()))
check('all_extractor_checks_true',all(hb['checks'].values()),hb['checks'])
check('24_cable_types_28_sites_87_records',len(hb['items'])==24 and len(hb['installation_sites'])==28 and len(hb['installed_occurrences'])==87)
occ=hb['installed_occurrences']
actual=Counter(o['item_id'] for o in occ if o['change']!='retained_from_baseline')
check('item_quantity_matches_occurrence_sum',all(actual[it['item_id']]==it['assembly_required_new_quantity'] for it in hb['items']))
check('four_retained_m4_nuts',Counter(o['item_id'] for o in occ if o['change']=='retained_from_baseline')=={'m4-nut':4})
check('nonadditive_children_refer_to_existing_parent',all(o['parent_occurrence_id'] in {p['occurrence_id'] for p in occ} for o in occ if o['parent_occurrence_id']))
check('original_extractor_unchanged',sha(ROOT/CH/'extract.py')==sha(HERE/CH/'extract.py'))
latest=read(ROOT/'output/current-assembly-package/latest.json')
check('latest_binds_new_manifest',latest['directory']==str(NEW.relative_to(ROOT)) and latest['manifest_sha256']==sha(NEW/'manifest.json'))
links=[]
for target in re.findall(r'\]\(([^)]+)\)',(NEW/'README.md').read_text()):
    if not target.startswith('http'):
        links.append(target)
        check('local_link_'+target,(NEW/target).resolve().is_file())
baseline=read(HERE/'backup-manifest.json')
check('all_six_backup_files_preserved',len(baseline['files_sha256'])==6 and all(sha(HERE/p)==v for p,v in baseline['files_sha256'].items()))

verification={
 'status':'SOURCE_COUNT_AND_HIERARCHY_CHECKS_PASS',
 'verified_utc':datetime.now(timezone.utc).isoformat(),
 'source_count':len(hb['source_sha256']),
 'installation_site_count':len(hb['installation_sites']),
 'item_type_count':len(hb['items']),
 'installed_occurrence_count_including_nonadditive_and_retained':len(occ),
 'scope':'Current actual source/count/hierarchy and doc-only refresh checks. No manufacturing/purchase/strength acceptance.',
 'hashes':{f:sha(ROOT/CH/f) for f in ['extract.py','hardware.json','README.md','extract.log']},
 'source_sha256':hb['source_sha256'],
 'all_sources_current':True,
 'doc_binding_only_refresh':True,
 'previous_evidence_backup':str(HERE.relative_to(ROOT)),
 'comparison_record':str((HERE/'comparison.json').relative_to(ROOT)),
 'assembly_run':str(NEW.relative_to(ROOT)),
 'CAD_changed':False,
 'specifications_changed':False,
}
save(ROOT/CH/'verification.json',verification)
report={
 'status':'PASS_DOCUMENT_BINDING_REFRESH_ONLY',
 'created_utc':datetime.now(timezone.utc).isoformat(),
 'old_run':str(OLD.relative_to(ROOT)),'new_run':str(NEW.relative_to(ROOT)),
 'old_manifest_sha256':sha(OLD/'manifest.json'),'new_manifest_sha256':sha(NEW/'manifest.json'),
 'changed_source_sha256':changes,'checks':checks,
 'counts':{'checks':len(checks),'passed':sum(c['passed'] for c in checks),'BOM_rows':44,'installed_occurrences':301,'printed_picklist':56,'source_bindings':108},
 'changed_production_files':[CH+'/hardware.json',CH+'/extract.log',CH+'/verification.json','output/current-assembly-package/latest.json'],
 'regenerated_byte_identical_files':[CH+'/README.md'],
 'commands_run':['python3 output/current-assembly-package/cable-hardware/extract.py > output/current-assembly-package/cable-hardware/extract.log','python3 scripts/build_current_assembly_package.py'],
 'no_CAD_export_slicing_purchase_or_print':True,
 'new_verification_sha256':sha(ROOT/CH/'verification.json'),
 'backup_manifest_sha256':sha(HERE/'backup-manifest.json'),
 'review_script_sha256':sha(Path(__file__)),
 'manufacturing_release':False,'physical_acceptance':False,
}
save(HERE/'comparison.json',report)
print(json.dumps({'status':report['status'],'new_run':report['new_run'],'counts':report['counts'],'manifest_sha256':report['new_manifest_sha256'],'comparison_sha256':sha(HERE/'comparison.json')},ensure_ascii=False,indent=2))
