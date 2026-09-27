#!/usr/bin/env python3
"""Publish identity-checked design files into the existing dedicated LAN root."""
from pathlib import Path
import csv
import hashlib
import html
import json
import shutil
import tempfile
import time
import zipfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/revision-review'
VIEWER=Path('/Users/norman/.codex/skills/stl-http-preview/preview')

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def verify(path,expected):
    if sha(ROOT/path)!=expected:raise RuntimeError('Stale evidence: '+path)
def report(name):
    r=json.loads((ROOT/name).read_text())
    for path,value in r['source_sha256'].items():verify(path,value)
    if r.get('sources_stable') is False:raise RuntimeError('Unstable source: '+name)
    return r

def main():
    feeder=report('output/launcher-final/report.json')
    if feeder['status']!='INTEGRATED_FEEDER_DIGITAL_CHECKS_PASS':raise RuntimeError('Feeder checks incomplete')
    if not {'frame-y-gib-right','frame-y-gib-left'}.issubset({p['id'] for p in feeder['parts']}):
        raise RuntimeError('The revised public-frame Y guides have not been integrated yet')
    spin=report('output/analysis/spin-head-geometry.json')
    if not all(spin[k] for k in ['all_expected_intersections_match','all_part_meshes_watertight','all_parts_single_component']):
        raise RuntimeError('Spin geometry checks incomplete')
    if not all(spin['independent_geometry_from_exported_meshes']['section_checks'].values()):
        raise RuntimeError('Spin section checks incomplete')
    exact=json.loads((ROOT/'output/spin-head/exact-area-review-final.json').read_text())
    verify('output/analysis/spin-head-geometry.json',exact['source_report_sha256'])
    verify('analysis/exact_mesh.py',exact['checker_sha256'])
    if not exact['all_passed']:raise RuntimeError('Spin exact mesh checks incomplete')
    for row in exact['parts']:verify(row['file'],row['sha256'])
    metal=report('output/spin-complete-hardware/report.json')
    if metal.get('open_case_names') or not all(x['passed'] for x in metal['cases']):
        raise RuntimeError('Spin hardware checks incomplete')
    guide=report('output/feeder-frame-y-guide/report.json')
    inlet=report('output/inlet-retention-final/report.json')
    if not all(x['passed'] for r in [guide,inlet] for x in r['cases']):
        raise RuntimeError('New interface checks incomplete')
    pair=json.loads((ROOT/'output/printed-pair-fit/report.json').read_text())
    verify('output/launcher-final/report.json',pair['source_report_sha256'])
    verify('analysis/printed_pair_fit.py',pair['script_sha256'])
    if pair['status']!='PRINTED_PAIR_POSE_PASS':raise RuntimeError('Printed pair check failed')
    package=json.loads((ROOT/'output/manufacturing/launcher-candidate-package-report.json').read_text())
    verify(package['path'],package['sha256'])
    for path,value in package['frozen_slice_reports'].items():verify(path,value)
    feeder_slice=report('output/print-review/final-feeder/report.json')
    verify('output/launcher-final/report.json',feeder_slice['final_geometry_report_sha256'])
    if package['printed_instances']!=48 or feeder_slice['printed_instances']!=38:
        raise RuntimeError('Package is not the current 48-part candidate')
    bom=report('output/manufacturing/feeder-hardware-bom.json')
    if bom['printed_instances']!=38 or bom['hardware_units_total']!=195:
        raise RuntimeError('Unexpected current feeder hardware contract')
    with zipfile.ZipFile(ROOT/package['path']) as archive:
        if archive.testzip() is not None:raise RuntimeError('Corrupt candidate ZIP')
        zip_manifest=json.loads(archive.read('manifest.json'))
        packaged={r['path']:r['sha256'] for r in zip_manifest['files']}
        for path,expected in packaged.items():
            if path.startswith(('docs/','output/manufacturing/')):verify(path,expected)
        if zip_manifest['frozen_slice_reports']!=package['frozen_slice_reports']:
            raise RuntimeError('Candidate ZIP and receipt select different reports')
    png_identity={r.get('file',r.get('path')):r['sha256'] for r in feeder['pictures']}
    for path in ['output/spin-head/spin-work-section.png','output/spin-head/spin-held-section.png']:
        rows=[r for r in spin.get('rendered_views',[]) if r.get('file',r.get('path'))==path]
        if len(rows)!=1:raise RuntimeError('Missing spin picture identity: '+path)
        png_identity[path]=rows[0]['sha256']
    stage=Path(tempfile.mkdtemp(prefix='launcher-review-',dir=ROOT/'output'))
    parts=[];assets=[]
    def copy(source,dest):
        expected=packaged.get(source,png_identity.get(source))
        if expected:verify(source,expected)
        source=ROOT/source;target=stage/dest;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,target)
        if expected and sha(target)!=expected:raise RuntimeError('Copy identity changed: '+str(source))
        assets.append({'source':str(source.relative_to(ROOT)),'file':dest,'sha256':sha(target)})
        return target
    def part(source,identity,name,group,role,color,opacity=1,expected=None):
        if expected:verify(source,expected)
        target=copy(source,'models/'+identity+'.stl')
        parts.append({'id':identity,'name':name,'file':str(target.relative_to(stage)),
            'group':group,'role':role,'color':color,'opacity':opacity,
            'bytes':target.stat().st_size,'mtime':sha(target)[:12]})
    for row in feeder['parts']:
        key=row['id'];color=('#28566c' if key=='beam-grip' else '#287f8a' if key.startswith(('capture','pipe-clamp'))
            else '#dfa233' if key=='frame' or key.startswith(('finger','pin-block','x-gib','y-gib'))
            else '#53a785' if key=='spring-reference' else '#a9bdc9')
        if key=='hardware':color='#525b62'
        part(row['file'],'feeder/'+key,row['name'],'feeder',row['role'],color,.25 if key in ('pc-reference','hose-reference','liner-reference') else 1,row['sha256'])
    names={'body':'主体与PC管夹','carriage':'浮动载体','pad':'TPU 95A HF 摩擦垫','pad-keeper':'摩擦垫压条',
        'opposite-guide':'对侧PETG导向块','cover':'外盖','spring-cage':'弹簧导向笼','spring-seat':'弹簧座',
        'pull-cap':'主动拉帽','hold-fork':'退出保持叉（退出档单独装入）'}
    for row in spin['parts']:
        key=row['part'];group='hold' if key=='hold-fork' else 'spin'
        part(row['mesh']['file'],'spin/'+key,names[key],group,'printed',
             '#54a98c' if key=='pad' else '#eaa740' if key in ('carriage','pull-cap','hold-fork') else '#779ba8',expected=row['mesh']['sha256'])
    for filename,name,color in [('hardware-work.stl','旋转头金属五金参考','#545d63'),
                                ('spring-work-envelope.stl','压缩弹簧安装包络','#51a782')]:
        path='output/spin-complete-hardware/'+filename
        row=next(x for x in metal['artifacts'] if Path(x['path']).name==filename)
        part(path,'spin/'+filename[:-4],name,'spin','purchased',color,expected=row['sha256'])
    groups=[{'id':'feeder','name':'点射送料总成'},{'id':'spin','name':'可调旋转头 · 工作档'},
            {'id':'hold','name':'退出保持叉 · 单件'}]
    for g in groups:g['count']=sum(x['group']==g['id'] for x in parts)
    feeder_prints=sum(p['role']=='printed' for p in feeder['parts'])
    spin_prints=len(spin['parts'])
    printed_count=feeder_prints+spin_prints
    manifest={'title':'点射送料与可调旋转头','units':'mm','up':'z','parts':parts,'groups':groups,
        'partCount':len(parts),'groupCount':len(groups),'manufacturing_release':False,'physical_acceptance':'OPEN'}
    (stage/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    revision={'status':'DIGITAL_CANDIDATE_PUBLISHED_PHYSICAL_OPEN',
        'printed_instances':printed_count,'feeder_instances':feeder_prints,'spin_instances':spin_prints,
        'geometry_report_sha256':sha(ROOT/'output/launcher-final/report.json'),
        'package_sha256':package['sha256'],'download_offered_on_page':True,
        'manufacturing_release':False,'physical_acceptance':False}
    (stage/'revision-status.json').write_text(json.dumps(revision,ensure_ascii=False,indent=2)+'\n')
    viewer=(VIEWER/'index.html').read_text().replace(
        '左键旋转 · 滚轮缩放 · 右键平移。单位 mm。零件多时先列清单，勾选或点「加载筛选结果」再拉 STL。',
        '左键旋转 · 滚轮缩放 · 右键平移。<a href="/">返回装配与下载</a>。两组分别安装于原三通进球侧和出球管末端。')
    for file in ['build/three.module.js','examples/jsm/controls/OrbitControls.js','examples/jsm/loaders/STLLoader.js','LICENSE']:
        copy('output/viewer-vendor/three/'+file,'vendor/three/'+file)
    viewer=viewer.replace('https://cdn.jsdelivr.net/npm/three@0.160.0/','./vendor/three/')
    (stage/'models.html').write_text(viewer)
    app=(VIEWER/'app.js').read_text().replace('const AUTOLOAD_MAX = 12;','const AUTOLOAD_MAX = 64;')
    app=app.replace('void refreshListing();\n  });\n  els.roleFilter',
        'void (async () => { await Promise.all([...state.items.keys()].map(id => setPartVisible(id, false))); await refreshListing({ autoload: true }); })();\n  });\n  els.roleFilter')
    app=app.replace('refreshListing({ autoload: true }).catch((error) => {',
        '(async () => { await refreshListing(); els.groupFilter.value = new URLSearchParams(location.search).get("group") || "feeder"; await refreshListing({ autoload: true }); })().catch((error) => {')
    app=app.replace('if (mode === "simple") state.explode = 0;\n  applyExplode();',
        'if (mode === "simple") state.explode = 0;\n  applyExplode();\n  fitCamera();')
    (stage/'app.js').write_text(app)
    for source,dest in [('output/launcher-final/assembly.png','feeder.png'),('output/launcher-final/front.png','feeder-front.png'),
        ('output/spin-head/spin-work-section.png','spin-work.png'),('output/spin-head/spin-held-section.png','spin-held.png'),
        ('docs/final-assembly.md','assembly.md'),('docs/final-sealing-process.md','sealing.md'),
        ('docs/final-feeder-print.md','feeder-print.md'),('docs/final-spin-print.md','spin-print.md'),
        ('docs/spin-complete-hardware.md','spin-hardware.md'),('docs/spin-material-selection.md','materials.md'),
        ('docs/final-feeder-hardware.md','feeder-hardware.md'),
        ('docs/feeder-frame-y-guide.md','frame-y-guide.md'),('docs/inlet-retention-final.md','inlet.md'),
        ('output/manufacturing/feeder-hardware-bom.json','feeder-hardware-bom.json'),
        ('output/manufacturing/launcher-candidate.zip','launcher-candidate.zip')]:copy(source,dest)
    with (stage/'printed-parts.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['编号','名称','数量','材料','STL'])
        for p in parts:
            if p['role']=='printed':w.writerow([p['id'],p['name'],1,'Bambu TPU 95A HF' if p['id']=='spin/pad' else 'PETG',p['file']])
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>点射送料与可调旋转头</title><style>
body{margin:0;background:#eef3f5;color:#203844;font:16px/1.8 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}main{max-width:1100px;margin:32px auto;padding:0 22px}h1{font-size:34px;line-height:1.3}h2{font-size:23px;margin-top:30px}a{color:#12687a}.button{display:inline-block;background:#236d7a;color:white;padding:10px 18px;text-decoration:none;border-radius:9px;margin:5px 10px 5px 0}.cards{display:grid;grid-template-columns:1fr 1fr;gap:18px}figure{margin:0;background:white;border-radius:12px;overflow:hidden}img{display:block;width:100%}figcaption{padding:12px 16px}.route{background:#fff;padding:18px;border-radius:10px;font-weight:600}.note{border-left:4px solid #dba43c;background:#fff7e8;padding:12px 18px}small{color:#596c77}@media(max-width:720px){.cards{grid-template-columns:1fr}h1{font-size:27px}}</style>
<main><small>当前数字总装 · X1C / 0.4 mm</small><h1>点射送料与可调旋转头</h1>
<p>送料机构__FEEDER_COUNT__件，旋转头__SPIN_COUNT__件。__PETG_COUNT__件用PETG；摩擦垫单独用TPU 95A HF。模型包含V定位挡指、公共架双向调隙、回位弹簧端头及金属五金参考。</p>
<p><a class="button" href="models.html?group=feeder">送料总成 / 爆炸图</a><a class="button" href="models.html?group=spin">旋转头 / 爆炸图</a><a href="models.html?group=hold">退出保持叉</a></p>
<div class="route">球仓 → 原软管 → 点射送料模块 → PC短节 → 原斜三通 → 原出球管 → 旋转头<br><small>风机仍接原斜三通的风口；预览中的两组模型分别显示，不是沿同一轴叠装。</small></div>
<div class="cards"><figure><img src="feeder.png"><figcaption>送料模块：固定握把承接扣动力，金色公共架沿轴向移动20 mm。</figcaption></figure><figure><img src="feeder-front.png"><figcaption>四个V定位挡指配独立压块；绿色件为采购弹簧参考，不是打印件。</figcaption></figure></div>
<h2>旋转调节</h2><div class="cards"><figure><img src="spin-work.png"><figcaption>工作档：旋钮调摩擦垫预压；旋转整头改变施加旋转的方向。</figcaption></figure><figure><img src="spin-held.png"><figcaption>退出档：主动拉回载体，再装保持叉。退出只表示垫离开球道。</figcaption></figure></div>
<h2>制作与装配</h2><p><a class="button" href="launcher-candidate.zip">下载制作候选包 · STL / 3MF / 说明</a></p><p><a href="assembly.md">统一装配说明</a> · <a href="printed-parts.csv">__PRINTED_COUNT__件打印清单</a> · <a href="feeder-print.md">送料切片说明</a> · <a href="spin-print.md">旋转头切片说明</a> · <a href="feeder-hardware.md">送料五金总表</a> · <a href="spin-hardware.md">旋转头装配</a> · <a href="materials.md">摩擦垫材料</a> · <a href="sealing.md">密封施工</a></p>
<p class="note">这是数字制作候选。实际总公差、软管夹持、带载回位及整机单发/旋转尚未验收，不能据预览或切片承诺一次制作必过。无需先打印试片才能继续设计。</p>
<p><small>STL单位mm；金属与弹簧标为采购参考，勿打印。材料表默认纹理PEI，用户只确认了PEI。来源与文件身份见 <a href="evidence.json">evidence.json</a>。</small></p></main></html>'''
    for key,value in {'FEEDER_COUNT':feeder_prints,'SPIN_COUNT':spin_prints,'PETG_COUNT':printed_count-1,'PRINTED_COUNT':printed_count}.items():
        page=page.replace('__'+key+'__',str(value))
    (stage/'index.html').write_text(page)
    reports=['output/launcher-final/report.json','output/analysis/spin-head-geometry.json',
        'output/spin-complete-hardware/report.json','output/feeder-frame-y-guide/report.json',
        'output/inlet-retention-final/report.json','output/printed-pair-fit/report.json',
        'output/manufacturing/launcher-candidate-package-report.json']
    (stage/'evidence.json').write_text(json.dumps({'reports':{p:sha(ROOT/p)for p in reports},
        'source_sha256':{**feeder['source_sha256'],**spin['source_sha256'],**metal['source_sha256']},
        'assets':assets,'printed_instances':printed_count,'physical_acceptance':False},ensure_ascii=False,indent=2)+'\n')
    # All dependent evidence was checked before any served file is replaced.
    backup=ROOT/'output/preview-history'/time.strftime('%Y%m%d-%H%M%S')
    backup.parent.mkdir(parents=True,exist_ok=True)
    shutil.copytree(OUT,backup)
    for source in sorted(stage.rglob('*')):
        if source.is_file() and source.name not in ('manifest.json','index.html'):
            dest=OUT/source.relative_to(stage);dest.parent.mkdir(parents=True,exist_ok=True);source.replace(dest)
    for name in ('manifest.json','index.html'):(stage/name).replace(OUT/name)
    shutil.rmtree(stage)
    print(f'Published {len(parts)} entries, {printed_count} printed instances; previous preview retained at {backup}')

if __name__=='__main__':main()
