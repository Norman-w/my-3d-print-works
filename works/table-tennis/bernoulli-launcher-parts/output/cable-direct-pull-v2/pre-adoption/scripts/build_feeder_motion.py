#!/usr/bin/env python3
"""Publish a frontend-only motion lesson from the preserved exported STL pose.

Never invokes CAD, slicing, or manufacturing verification. The frozen mesh
snapshot remains explicit; this cannot promote pending mechanical revisions.
"""
from pathlib import Path
import hashlib
import json
import shutil
from build_motion_hardware import main as build_hardware

ROOT=Path(__file__).resolve().parents[1]
PUBLIC=ROOT/'output/revision-review'
BASE=ROOT/'output/launcher-final-history/before-frame-y-guide'
WEB_FILES=['feeder-motion.html','feeder-motion.mjs','feeder-motion-kinematics.mjs','feeder-overview.mjs','trigger-concept-kinematics.mjs','trigger-overlay.mjs','scene-assets.mjs']

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    report_path=BASE/'output/launcher-final/report.json'
    report=json.loads(report_path.read_text())
    motion_sources=['cad/cam-study.scad','cad/parameters.scad','cad/feeder-supports.scad','cad/feeder-pin-seat-revision.scad','cad/feeder-return-spring.scad']
    for path in motion_sources:
        assert sha(ROOT/path)==report['source_sha256'][path],f'Motion basis changed since snapshot: {path}'
    selected=[r for r in report['parts'] if r['role']=='printed' or r['id']=='pc-reference']
    assert len(selected)==34 and sum(r['role']=='printed' for r in selected)==33
    assets=[];parts=[]
    def copy(src,dest):
        target=PUBLIC/dest;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(src,target)
        assert sha(target)==sha(src)
        assets.append({'source':str(src.relative_to(ROOT)),'file':dest,'sha256':sha(target)})
    for row in selected:
        src=BASE/row['file'];assert sha(src)==row['sha256'],row['id']
        dest=f'motion-models/{row["id"]}.stl';copy(src,dest)
        parts.append({'id':row['id'],'name':row['name'],'file':dest,'sha256':row['sha256'],'role':row['role']})
    for name in WEB_FILES:
        copy(ROOT/'web'/name,name)
    build_hardware()
    hardware=json.loads((PUBLIC/'motion-hardware/hardware-manifest.json').read_text())
    viewer=json.loads((PUBLIC/'manifest.json').read_text())
    frozen={f'feeder/{r["id"]}':r for r in parts}
    catalog=[]
    for original in viewer['parts']:
        row=dict(original)
        if row['id'] in frozen:
            baseline=frozen[row['id']]
            assert sha(PUBLIC/row['file'])==baseline['sha256'],f'Viewer differs from frozen motion source: {row["id"]}'
            row['file']=baseline['file']
        row['sha256']=sha(PUBLIC/row['file'])
        if row['id']=='feeder/hardware':row['subparts']=hardware['parts']
        catalog.append(row)
    assert len(catalog)==48 and len({r['id']for r in catalog})==48
    for row in hardware['parts']:
        assert sha(PUBLIC/row['file'])==row['sha256']
        assets.append({'source':'partition of preserved hardware triangles','file':row['file'],'sha256':row['sha256']})
    assets.append({'source':'preserved hardware partition proof','file':'motion-hardware/hardware-manifest.json','sha256':sha(PUBLIC/'motion-hardware/hardware-manifest.json')})
    manifest={'snapshot':'preserved-baseline33-la_t0','parts':parts,
        'source_report':str(report_path.relative_to(ROOT)),'source_report_sha256':sha(report_path),
        'web_sources':{str((ROOT/'web'/n).relative_to(ROOT)):sha(ROOT/'web'/n)
            for n in WEB_FILES},
        'motion_source_sha256':{p:sha(ROOT/p)for p in motion_sources},
        'motion_units':'millimetres; offsets relative to exported la_t=0 assembly vertices',
        'assembly_catalog':catalog,'catalogue_count':len(catalog),
        'hardware_partition':hardware,
        'scene_contract':'One persistent assembly graph. Camera presets never replace models, hide parts or reset the motion cycle. Each catalogue entry is loaded once and visibility is independent.',
        'moving_STL_instances':10,'omitted':'No catalogue assets omitted. Optional hold fork is parked beside spin head, not overlaid on work mode.',
        'spring_animation':'Original spring-reference STL; lower eye fixed, upper eye translated, central envelope stretched between source coil endpoints. No replacement procedural spring.',
        'procedural_references':['three illustrative 41mm balls','external system context','trigger grip and cable installation proposal overlay'],
        'ball_timing':'Illustrative; move balls only while gates are fully open. Not a pneumatic/dynamic result.',
        'system_layout':'Connection illustration only. External Y-fitting angle, blower/hopper shape and hose/tube lengths are unmeasured illustrative references.',
        'trigger':'Integral finger ring, axial +Z translation 20 mm toward the Y fitting; no pivot or reversing linkage.',
        'proposed_trigger':'Conventional rearward-pull trigger before vertical grip. Clockwise rotation moves lower contact rearward; top pin drives horizontal carriage through vertical slot; pull-only cable transfers 20mm to diagonal feeder. Whole layout schematic only: CAD/STL not modified; mounts, cable, hand clearance and forces unvalidated.',
        'lubrication_markers':'External carriage rails, external finger sliders, shoulder followers against cam slot walls; no lubricant in ball path.',
        'manufacturing_release':False,'physical_acceptance':False}
    out=PUBLIC/'motion-manifest.json';out.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    assets.append({'source':'web motion snapshot manifest','file':out.name,'sha256':sha(out)})
    entry='feeder-motion.html?view=system'
    index=PUBLIC/'index.html';s=index.read_text().replace('href="feeder-motion.html"',f'href="{entry}"').replace('href="feeder-motion.html?view=trigger"',f'href="{entry}"')
    if f'href="{entry}"' not in s:
        s=s.replace('<a class="button" href="models.html?group=feeder">',f'<a class="button" href="{entry}">三维工作循环 ▶</a><a class="button" href="models.html?group=feeder">')
    index.write_text(s)
    model_page=PUBLIC/'models.html';s=model_page.read_text().replace('href="feeder-motion.html"',f'href="{entry}"').replace('href="feeder-motion.html?view=trigger"',f'href="{entry}"')
    if f'href="{entry}"' not in s:
        s=s.replace('<h1 id="title">STL 预览</h1>',f'<h1 id="title">STL 预览</h1><a href="{entry}" style="color:#98d9ef;padding:8px 0">▶ 三维工作循环</a>')
    model_page.write_text(s)
    evidence_file=PUBLIC/'evidence.json';e=json.loads(evidence_file.read_text())
    names={a['file']for a in assets};e['assets']=[a for a in e['assets']if a['file']not in names]+assets
    e['motion_page']={'manifest':'motion-manifest.json','snapshot':manifest['snapshot'],'physical_acceptance':False}
    evidence_file.write_text(json.dumps(e,ensure_ascii=False,indent=2)+'\n')
    print(f'Published unified scene: {len(catalog)} original catalogue entries; no CAD executed.')

if __name__=='__main__':main()
