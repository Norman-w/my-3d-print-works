#!/usr/bin/env python3
"""Small integration check only; do not rerun or replace historical reviews."""
from pathlib import Path
import concurrent.futures
import hashlib
import json
import subprocess
from feeder_integration import classify

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/revised-feeder-review'
SCAD=ROOT/'cad/revised-feeder-review.scad'
EXE='/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
SOURCES=['cad/parameters.scad','cad/feeder-body.scad','cad/feeder-supports.scad',
         'cad/cam-study.scad','cad/feeder-guide-revision.scad',
         'cad/feeder-seam-candidate.scad','cad/revised-feeder-review.scad',
         'analysis/revised_feeder_review.py','analysis/feeder_integration.py']


def hashes():
    return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES}


def render(name,mode,stroke=.5,fault=0,image=False):
    target=OUT/(name+('.png' if image else '.stl'))
    target.unlink(missing_ok=True)
    cmd=[EXE,'--render','--hardwarnings','--backend','Manifold','-o',str(target)]
    if image:
        eye='-280,-300,180' if mode=='section' else '280,-320,220'
        cmd+=['--imgsize=1500,1500','--viewall','--autocenter','--projection=o',
              f'--camera={eye},0,0,-28']
    else: cmd+=['--export-format','asciistl']
    for k,v in {'revised_mode':mode,'revised_stroke':stroke,'revised_body_fault':fault}.items():
        cmd+=['-D',f'{k}={json.dumps(v)}']
    cmd.append(str(SCAD))
    result=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
    log=result.stdout+result.stderr
    (OUT/(name+'.log')).write_text(log)
    if 'WARNING:' in log or 'ERROR:' in log: raise RuntimeError(log)
    if not target.exists() and 'Current top level object is empty' not in log:
        raise RuntimeError(log)
    return {'name':name,'mode':mode,'stroke':stroke,'body_translation_x_mm':fault,
            'path':str(target.relative_to(ROOT)) if target.exists() else None,
            'returncode':result.returncode}


def probe(job):
    name,t,fault=job
    row=render(name,'probe',t,fault)
    row.update(classify(ROOT/row['path']) if row['path'] else
        {'components':[],'triangle_count':0,'has_solid_or_unclassified_overlap':False})
    row['expected_solid_overlap']=bool(fault)
    row['passed']=row['has_solid_or_unclassified_overlap']==bool(fault)
    return row


def reference(path):
    r=json.loads((ROOT/path).read_text())
    sh=r.get('source_sha256',{})
    current=bool(sh) and all((ROOT/p).exists() and
        hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in sh.items())
    return {'path':path,'report_sha256':hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),
            'source_hashes_current':current,'status':r.get('status'),
            'nominal_samples_passed':r.get('nominal_samples_passed'),
            'scope':'Referenced only; not rerun by this integration script.'}


def main():
    OUT.mkdir(parents=True,exist_ok=True);before=hashes()
    jobs=[(f'body-pose-{i}',t,0) for i,t in enumerate([0,.2,.4,.5,.6,.8,1])]
    jobs.append(('body-offset-positive-control',.5,1))
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        rows=list(pool.map(probe,jobs))
    pictures=[render('review','review',image=True),render('section','section',image=True)]
    refs=[reference(p) for p in ['output/guide-revision/check.json',
                                 'output/analysis/cam-constraint-check.json']]
    stable=before==hashes();passed=stable and all(r['passed'] for r in rows)
    report={'status':'COMBINED_REVIEW_NOMINAL_BODY_CSG_PASS' if passed else 'FAIL_OR_STALE',
            'adopted':False,'manufacturing_release':False,'source_sha256':before,
            'sources_stable_during_checks':stable,'cases':rows,'previews':pictures,
            'scope':'Seam candidate body and BOTH locator pins versus revised supports/gibs, existing modeled hardware, carriage and four finger/pin/nut followers at seven nominal stroke fractions. Explicit planar contacts allowed.',
            'setting':{'gib_advance_mm':.9,'carrier_y_mm':0},
            'included_hardware_modules':['seam_pins','feeder_cap_hardware',
                'feeder_mount_hardware','revision_hardware_local','revision_followers'],
            'excluded_hardware':['Eight seam M3 screws/nuts/head hardware are not modeled.',
                'Body-mount captive nuts are absent from feeder_mount_hardware.',
                'Return spring and actual hose/Y joints are not modeled.'],
            'previous_component_checks':refs,
            'limits':['Seven finite nominal poses; no continuous integration motion proof.',
                'Moving/fixed and cam/four-follower checks are referenced, not rerun here.',
                'Locator free play, guide play and manufacturing distortion are not combined here.',
                'Material, sealing endpoints, strength, real fit, airflow and one-ball operation remain OPEN.',
                'Only CSG overlap remnants are exported to STL; no merged assembly STL or print package is created.']}
    (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    solid_volume=sum(c['volume_mm3'] for c in rows[-1]['components'] if not c['planar_contact_only'])
    note=f'''# 两项候选的整合审阅入口

状态：**{report['status']}**。七个名义行程位置和一个阳性对照共 {sum(r['passed'] for r in rows)}/8 项符合预期。壳体连同两根定位销与新支座、镶条、已建五金、凸轮架及四挡指作实际布尔交集；共面接触单独分类。故意把壳体与其定位销沿 X 平移 1 mm 后检出约 {solid_volume:.6f} mm³ 实体干涉。

入口：`cad/revised-feeder-review.scad` 的 `revised_mode="review"` / `"section"`。镶条推进 0.9 mm，载体 Y=0；预览行程取 0.5。输出 `review.png` 与 `section.png`，没有输出装配合并 STL。各源完整哈希和碰撞分量见同目录 `report.json`。

这把独立分缝候选和可调导向候选放在一起看，并不表示已采用或已生成打印包。移动/固定及凸轮/四指检查仅引用已有报告，同时核对源哈希，没有重跑历史检查。

**未建模/未检查的五金：8 套合壳 M3、侧安装座捕获螺母、回位弹簧、真实软管/Y 接口。**现有 `feeder_mount_hardware()` 只有螺钉和垫片，不能把模块名称解释为包含全部安装五金。四随动肩销及其螺母、两根分缝定位销、盖板五金、调隙/压条五金已包含。

七个离散名义位置不证明全行程或公差包络，导向及分缝自由游隙尚未在本入口叠加。密封端点、材料、切片、真实装配、气路和单球功能仍需独立验收。
'''
    (OUT/'README.md').write_text(note)
    print(report['status'],f'{sum(r["passed"] for r in rows)}/8')
    print('positive-control solid volume',solid_volume)
    print('referenced reports current',[r['source_hashes_current'] for r in refs])
    return 0 if passed else 1


if __name__=='__main__':raise SystemExit(main())
