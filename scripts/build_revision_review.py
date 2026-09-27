#!/usr/bin/env python3
"""Publish the current changed CAD meshes as a local review, never a print release."""
from pathlib import Path
import hashlib
import html
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/revision-review'
VIEWER = Path('/Users/norman/.codex/skills/stl-http-preview/preview')

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def copy_asset(source, name):
    source = ROOT / source
    target = OUT / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return {'source': str(source.relative_to(ROOT)), 'file': name, 'sha256': digest(target)}

def check_known_findings():
    audit = json.loads((ROOT/'output/integrated-review-parts/degeneracy-audit.json').read_text())
    if (audit['status'] != 'NO_LISTED_DEFECT_FOUND'
            or not all(row['no_defect_found_in_this_check'] for row in audit['parts'])):
        raise RuntimeError('Integrated preview publication held: exported support mesh defects remain. Existing LAN preview is unchanged.')
    if (digest(ROOT/'analysis/export_degeneracy_audit.py') != audit['script_sha256']
            or digest(ROOT/'output/integrated-review-parts/report.json') != audit['instance_report_sha256']):
        raise RuntimeError('Integrated mesh area audit identity is stale')
    for row in audit['parts']:
        if digest(ROOT/row['file']) != row['sha256']:
            raise RuntimeError(f'Stale exact-area mesh audit: {row["file"]}')
    review = json.loads((ROOT/'output/integrated-review-parts/known-open-findings.json').read_text())
    if review['status'] != 'CLEARED' or not review.get('resolution_evidence'):
        raise RuntimeError('Integrated preview publication held: right-support Boolean reimport failed; CAD instance parity does not resolve it. Existing LAN preview is unchanged.')
    for path, expected in review['evidence_sha256'].items():
        if digest(ROOT/path) != expected:
            raise RuntimeError(f'Stale integrated export resolution evidence: {path}')

def main():
    check_known_findings()
    OUT.mkdir(parents=True, exist_ok=True)
    spin = json.loads((ROOT/'output/analysis/spin-head-geometry.json').read_text())
    for path, expected in spin['source_sha256'].items():
        if digest(ROOT/path) != expected:
            raise RuntimeError(f'Stale spin-head report: {path}')
    if not all(spin[key] for key in ('all_expected_intersections_match',
                                    'all_part_meshes_watertight',
                                    'all_parts_single_component')):
        raise RuntimeError('Spin-head geometry checks have unresolved failures')
    if not all(spin['independent_geometry_from_exported_meshes']['section_checks'].values()):
        raise RuntimeError('Spin-head measured sections have unresolved failures')
    for row in spin.get('rendered_views', []):
        if digest(ROOT/row['file']) != row['sha256']:
            raise RuntimeError(f'Stale spin-head picture: {row["file"]}')
    for row in spin['parts']:
        if digest(ROOT/row['mesh']['file']) != row['mesh']['sha256']:
            raise RuntimeError(f'Stale spin-head mesh: {row["mesh"]["file"]}')
    cam_path = ROOT/'output/feeder-cam-guide-revision/report.json'
    cam = json.loads(cam_path.read_text())
    for path, expected in cam['source_sha256'].items():
        if digest(ROOT/path) != expected:
            raise RuntimeError(f'Stale cam-guide report: {path}')
    if (cam['status'] != 'NOMINAL_GEOMETRY_PASS_PHYSICAL_AND_TOTAL_ERROR_OPEN'
            or not cam['sources_stable']
            or not all(row['passed'] for row in cam['cases'] + cam['load_path_connections'] + cam['fixed_stop_bearings'])
            or not all(row['mesh_passed'] for row in cam['printable_parts'])):
        raise RuntimeError('Cam-guide geometry checks have unresolved failures')
    for row in cam['printable_parts']:
        if digest(ROOT/row['path']) != row['sha256']:
            raise RuntimeError(f'Stale cam-guide mesh: {row["path"]}')
    integrated_path=ROOT/'output/integrated-review-parts/report.json'
    integrated=json.loads(integrated_path.read_text())
    if (integrated['status']!='ASSEMBLY_INSTANCE_EXPORT_PASS' or not integrated['sources_stable']
            or not integrated['assembly_parity']['passed']
            or not all(row['passed'] for row in integrated['parts'])):
        raise RuntimeError('Integrated feeder export has unresolved failures')
    for path,expected in integrated['source_sha256'].items():
        if digest(ROOT/path)!=expected:
            raise RuntimeError(f'Stale integrated feeder: {path}')
    for row in integrated['parts']:
        if digest(ROOT/row['file'])!=row['sha256']:
            raise RuntimeError(f'Stale integrated mesh: {row["file"]}')
    for row in integrated['pictures']:
        if digest(ROOT/row['file'])!=row['sha256']:
            raise RuntimeError(f'Stale integrated picture: {row["file"]}')
    parts, assets = [], []
    names = {'body':'主体与管夹', 'carriage':'浮动载体与导柱',
             'pad':'柔性摩擦垫形状（材料待定）', 'pad-keeper':'摩擦垫压条',
             'opposite-guide':'对侧导向块', 'cover':'外盖与保持块支座',
             'spring-cage':'弹簧导向笼', 'spring-seat':'弹簧座',
             'pull-cap':'新增拉帽', 'hold-fork':'新增退出保持块'}
    colors = ['#6591ae','#efae43','#51a78c','#edb465','#a5b6be',
              '#677c8a','#a9b8bc','#d28549','#ed8343','#db7449']
    for index, row in enumerate(spin['parts']):
        part = row['part']
        group = 'hold-part' if part == 'hold-fork' else 'spin'
        file = f'models/spin/{part}.stl'
        assets.append(copy_asset(row['mesh']['file'], file))
        parts.append({'id':f'spin/{part}', 'name':names.get(part,part),
                      'file':file,'group':group,'role':'printed',
                      'color':colors[index % len(colors)],'opacity':1,
                      'bytes':(OUT/file).stat().st_size,'mtime':digest(OUT/file)[:12]})
    for key, name in [('right-support','右主导向支座'),('cam-gib','新增X导向压条'),
                      ('cam-cover','新增调节外盖')]:
        # The original Manifold right-support export has a disconnected vertex
        # fan missed by its edge-only check. The CGAL export also needs the
        # explicit Boolean reimport finding cleared before publication.
        source = ('output/integrated-review-parts/right-support.stl' if key=='right-support'
                  else f'output/feeder-cam-guide-revision/{key}.stl')
        file = f'models/feeder/{key}.stl'
        assets.append(copy_asset(source,file))
        parts.append({'id':f'feeder/{key}','name':name,'file':file,'group':'feeder',
                      'role':'printed','color':'#7296ad' if key=='right-support' else '#eeac41',
                      'opacity':1,'bytes':(OUT/file).stat().st_size,
                      'mtime':digest(OUT/file)[:12]})
    for row in integrated['parts']:
        key=row['id'];file=f'models/integrated/{key}.stl'
        assets.append(copy_asset(row['file'],file))
        color=('#204f68' if key=='beam-grip' else '#267b87' if key.startswith(('capture','pipe-clamp'))
               else '#d98f28' if key=='frame' or key.startswith(('finger','x-gib','y-gib'))
               else '#f1bb52' if key=='liner' else '#a7bac5')
        if key=='hardware':color='#545d63'
        if key=='pc-reference':color='#97cede'
        parts.append({'id':f'integrated/{key}','name':row['name'],'file':file,'group':'integrated',
                      'role':row['role'],'color':color,'opacity':.24 if key=='pc-reference' else 1,
                      'bytes':(OUT/file).stat().st_size,'mtime':digest(OUT/file)[:12]})
    groups = [{'id':'integrated','name':'联合送料总成 · 27件与五金参考'},
              {'id':'spin','name':'旋转头工作档 · 保持块另列'},
              {'id':'hold-part','name':'退出保持块 · 单件'},
              {'id':'feeder','name':'点射X导向 · 新增及替换件'}]
    for group in groups:
        group['count'] = sum(p['group']==group['id'] for p in parts)
    manifest={'title':'机械点射送料与旋转调节 · 联合候选', 'units':'mm','up':'z',
              'parts':parts,'groups':groups,'partCount':len(parts),'groupCount':len(groups),
              'manufacturing_release':False,'physical_acceptance':'OPEN'}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    viewer_html=(VIEWER/'index.html').read_text().replace(
        '左键旋转 · 滚轮缩放 · 右键平移。单位 mm。零件多时先列清单，勾选或点「加载筛选结果」再拉 STL。',
        '左键旋转 · 滚轮缩放 · 右键平移。单位 mm。送料组含五金参考，旋转头组只显示零件；<a href="/">查看装配顺序与范围</a>。')
    (OUT/'models.html').write_text(viewer_html)
    app=(VIEWER/'app.js').read_text().replace('const AUTOLOAD_MAX = 12;','const AUTOLOAD_MAX = 40;')
    app=app.replace('void refreshListing();\n  });\n  els.roleFilter',
                    'void (async () => {\n      await Promise.all([...state.items.keys()].map(id => setPartVisible(id, false)));\n      await refreshListing({ autoload: true });\n    })();\n  });\n  els.roleFilter')
    app=app.replace('refreshListing({ autoload: true }).catch((error) => {',
                    '(async () => {\n    await refreshListing();\n    els.groupFilter.value = new URLSearchParams(location.search).get("group") || "integrated";\n    await refreshListing({ autoload: true });\n  })().catch((error) => {')
    app=app.replace('if (mode === "simple") state.explode = 0;\n  applyExplode();',
                    'if (mode === "simple") state.explode = 0;\n  applyExplode();\n  fitCamera();')
    (OUT/'app.js').write_text(app)
    # Keep all assets inside this dedicated HTTP root; no order data are served.
    images = [('output/spin-head/spin-work-section.png','spin-work.png'),
              ('output/spin-head/spin-held-section.png','spin-held.png'),
              ('output/feeder-cam-guide-revision/assembly.png','feeder.png'),
              ('output/feeder-cam-guide-revision/working-section.png','feeder-section.png'),
              ('output/integrated-review-parts/assembly.png','integrated.png'),
              ('output/integrated-review-parts/front.png','integrated-front.png'),
              ('output/integrated-review-parts/top.png','integrated-top.png')]
    for source, target in images:
        assets.append(copy_asset(source,target))
    gap=spin['pad_held_clear_only_not_zero_spin']['nominal_full_bore_clearance_mm']
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>改装件 · 本轮模型更新</title>
<style>body{margin:0;background:#edf2f4;color:#20343e;font:16px/1.7 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}
main{max-width:1160px;margin:32px auto;padding:0 24px}h1{font-size:34px;margin:8px 0 12px}h2{font-size:23px;margin:28px 0 12px}
p{max-width:900px}.label{color:#286d72;font-weight:650}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}figure{margin:0;background:#fff;border-radius:12px;overflow:hidden}img{width:100%;display:block}figcaption{padding:12px 18px}a{color:#176d7a}.button{display:inline-block;background:#216d78;color:#fff;text-decoration:none;border-radius:8px;padding:9px 16px;margin:5px 10px 6px 0}.note{background:#fff5dd;padding:14px 20px;border-radius:10px}small{color:#50636c}@media(max-width:720px){.grid{grid-template-columns:1fr}h1{font-size:27px}}</style>
<main><div class="label">本轮 CAD 更新 · 2026-09-24</div><h1>点射送料总成与可调旋转头</h1>
<p>保留你的 48内/50外 PC 管、50内/55外软管接口。点射由机械机构控制；旋转调节由摩擦头实现，不依赖风机具备调速功能。</p>
<p><a class="button" href="models.html?group=integrated">查看整套送料模块 / 爆炸视图</a><a class="button" href="models.html?group=spin">查看可调旋转头</a><a href="models.html?group=feeder">只看X导向改件</a></p>
<h2>送料总成：主壳、导向、握把和出口连接</h2>
<p>同一对主壳已经合入定位耳、背梁连接耳和出口防转法兰。送料组显示27个打印件实例，以及五金和PC管参考；原三通、软管、风机及回位弹簧尚未包含。图中送料方向沿模型轴线向上，旋转头另列，不能将两组叠在一起当成已核实的整机位置。</p>
<div class="grid"><figure><img src="integrated.png"><figcaption>蓝色背梁与固定握把承接模块载荷；出口捕获座、两根长杆和管夹负责硬管连接。</figcaption></figure><figure><img src="integrated-front.png"><figcaption>正面：中间主壳、两侧导向和独立握把。金色公共架通过指环沿轴向扣动20 mm。</figcaption></figure></div>
<p class="note"><strong>装配顺序已经影响结构可达性：</strong>先合主壳，再装凸轮架；先装紧出口连接，再装背梁。操作合壳螺钉要先卸公共架及背梁，拆右Y压盖或操作出口下螺母也需先卸背梁。</p>
<h2>1. 旋转头：工作档与退出保持档</h2><p>拉帽主动拉回载体，叉形保持块承受弹簧回弹。保持位置后退 5 mm，摩擦垫与最大分析孔径的名义净空为 __GAP__ mm；它只代表垫退出球道，不承诺球完全无旋转。</p>
<div class="grid"><figure><img src="spin-work.png"><figcaption>工作档：解除保持，摩擦垫可随球退让，旋钮调预压。</figcaption></figure><figure><img src="spin-held.png"><figcaption>退出保持档：拉回后放入保持块并固定，摩擦垫保持在球道外。</figcaption></figure></div>
<h2>2. 点射：公共凸轮架增加 X 向可调压条</h2><p>在右侧设置固定基准和两端可调压条，减少公共架横移与摆动。20 mm 扣动行程、原球道和原左侧支承保留；调节展示位置的纯 X 平移范围为 0～0.10 mm，不是打印精度承诺。</p>
<div class="grid"><figure><img src="feeder.png"><figcaption>点射机构当前装配：新导向连接在右支座上。</figcaption></figure><figure><img src="feeder-section.png"><figcaption>导向工作面剖面：固定基准、压条、调节螺钉和拆卸外盖。</figcaption></figure></div>
<h2>做到了哪一步</h2><p class="note">送料联合候选已完成名义干涉及装配顺序检查，分件额外核对边与顶点邻域的网格连通性。当前肩销误差、回位弹簧端头仍在独立修订，尚未混入本版；完整点射公差、实际夹持/密封、软垫材料和整机发球仍待关闭。本页不是整套可直接打印的发布包，无需先打印试片才能继续设计。</p>
<p><small>模型单位 mm。3D 页中的柔性摩擦垫保留形状供审查，其材料尚未选定；不要把它按 PETG 直接制造。导出网格与检查报告身份记录在 evidence.json。</small></p></main></html>'''
    (OUT/'index.html').write_text(page.replace('__GAP__',f'{gap:.2f}'))
    (OUT/'evidence.json').write_text(json.dumps({'source_sha256':{**spin['source_sha256'], **cam['source_sha256'], **integrated['source_sha256']},
        'spin_report_sha256':digest(ROOT/'output/analysis/spin-head-geometry.json'),
        'cam_report_sha256':digest(cam_path),
        'integrated_report_sha256':digest(integrated_path),
        'assets':assets,'manufacturing_release':False},ensure_ascii=False,indent=2)+'\n')
    print(OUT/'index.html')

if __name__=='__main__':main()
