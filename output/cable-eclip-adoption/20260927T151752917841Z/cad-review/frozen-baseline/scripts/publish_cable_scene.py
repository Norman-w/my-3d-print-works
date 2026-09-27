#!/usr/bin/env python3
"""Publish a verified mesh snapshot into the existing local review service.

Publication is a viewing update, not a fabrication release. New asset paths are
versioned; prior files and every overwritten public entry are retained.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import csv
import hashlib
import html
import json
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'output/revision-review'
WEB = ['feeder-motion.html', 'feeder-motion.mjs', 'feeder-motion-kinematics.mjs',
       'feeder-overview.mjs', 'trigger-concept-kinematics.mjs', 'trigger-overlay.mjs',
       'scene-assets.mjs', 'cable-scene-kinematics.mjs']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_sources(report):
    for name, expected in report['source_sha256'].items():
        if sha(ROOT / name) != expected:
            raise RuntimeError('Stale scene export: ' + name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--render-report', type=Path, required=True,
                        help='Visually checked current-source native CAD render report')
    args = parser.parse_args()
    report_path = args.report.resolve()
    report = json.loads(report_path.read_text())
    if report['status'] != 'CURRENT_SCENE_EXPORT_PASS' or not report['sources_stable']:
        raise RuntimeError('Scene mesh export did not pass')
    verify_sources(report)
    render_path = args.render_report.resolve()
    render = json.loads(render_path.read_text())
    if render.get('status') != 'NATIVE_CAD_PNG_VISUALLY_CHECKED' or not render.get('sources_stable') or not render.get('visual_review', {}).get('performed'):
        raise RuntimeError('Current-source render has not been visually checked')
    verify_sources(render)
    render_rows = [r for r in render['renders'] if r['name'] == 'whole-pulled-reverse']
    if len(render_rows) != 1 or not render_rows[0]['execution_ok']:
        raise RuntimeError('Missing verified assembly render')
    assembly_image = render_rows[0]
    inventory = json.loads((report_path.parent / 'inventory.json').read_text())
    if sha(report_path.parent / 'inventory.json') != sha(ROOT / 'docs/cable-assembly-inventory.json'):
        # The inventory snapshot is pretty-printed by the exporter. Compare data
        # as well, rather than pretending formatting changes the contract.
        if inventory != json.loads((ROOT / 'docs/cable-assembly-inventory.json').read_text()):
            raise RuntimeError('Inventory changed after export')
    if not all(row['passed'] for row in report['parts']):
        raise RuntimeError('At least one scene asset failed')
    snapshot = report_path.parent.name
    stage = Path(tempfile.mkdtemp(prefix='cable-scene-stage-', dir=ROOT / 'output'))
    assets = []

    def copy(source, destination, expected=None):
        source = ROOT / source
        if expected and sha(source) != expected:
            raise RuntimeError('Asset changed: ' + str(source))
        target = stage / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        if sha(target) != sha(source):
            raise RuntimeError('Copy identity mismatch')
        assets.append({'source': str(source.relative_to(ROOT)), 'file': destination, 'sha256': sha(target)})
        return target

    def write(name, value):
        target = stage / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(value)
        assets.append({'source': 'generated from current inventory', 'file': name, 'sha256': sha(target)})

    parts = []
    for row in report['parts']:
        destination = f'cable-models/{snapshot}/{row["id"]}.stl'
        target = copy(row['file'], destination, row['sha256'])
        part = {k: row[k] for k in ('id', 'name', 'role', 'group', 'family', 'motion') if k in row}
        part.update(file=destination, sha256=sha(target), bytes=target.stat().st_size, mtime=sha(target)[:12])
        if row['role'] != 'printed':
            part['color'] = '#bfcdd4' if 'hardware' in row['id'] else '#78949e'
        if row['id'] == 'spin/pad':
            part['color'] = '#73d7a5'
        parts.append(part)
    for name in WEB:
        copy('web/' + name, name)
    for name in ('models.html', 'app.js'):
        copy('output/revision-review/' + name, name)
    # Vendor files are already part of this local service and remain unchanged.
    for name in ('build/three.module.js', 'examples/jsm/controls/OrbitControls.js', 'examples/jsm/loaders/STLLoader.js'):
        copy('output/revision-review/vendor/three/' + name, 'vendor/three/' + name)
    copy(assembly_image['file'], f'cable-models/{snapshot}/assembly.png', assembly_image['sha256'])
    copy(str(render_path.relative_to(ROOT)), f'cable-models/{snapshot}/render-report.json', sha(render_path))
    copy(str(report_path.relative_to(ROOT)), f'cable-models/{snapshot}/export-report.json', sha(report_path))
    copy('docs/cable-assembly-inventory.json', 'cable-assembly-inventory.json')
    count = sum(p['role'] == 'printed' for p in parts)
    feeder_count = sum(p['role'] == 'printed' and p['group'] == 'feeder' for p in parts)
    spin_count = count - feeder_count
    groups = [{'id': 'feeder', 'name': '点射送料与拉线扳机'},
              {'id': 'spin', 'name': '可调旋转头 · 工作档'},
              {'id': 'hold', 'name': '退出保持叉 · 旁置参考'}]
    for group in groups:
        group['count'] = sum(p['group'] == group['id'] for p in parts)
    manifest = {'title': '当前拉线点射与可调旋转候选', 'units': 'mm', 'up': 'z',
                'parts': parts, 'groups': groups, 'partCount': len(parts), 'groupCount': len(groups),
                'manufacturing_release': False, 'physical_acceptance': False}
    motion = {'snapshot': 'current-cable-candidate', 'snapshot_id': snapshot,
              'parts': parts, 'assembly_catalog': parts, 'catalogue_count': len(parts),
              'printed_instances': count, 'scene_contract': inventory['scene_contract'],
              'source_report': str(report_path.relative_to(ROOT)), 'source_report_sha256': sha(report_path),
              'source_sha256': report['source_sha256'],
              'web_sources': {'web/' + n: sha(ROOT / 'web' / n) for n in WEB},
              'motion_units': 'mm; t0 assembly coordinates, source-derived motion contract',
              'ball_timing': 'Illustrated ready-ball sequence; not airflow or contact dynamics.',
              'system_layout': 'Blower, tee, hopper and external pipe layout are unmeasured references.',
              'manufacturing_release': False, 'physical_acceptance': False}
    write('motion-manifest.json', json.dumps(motion, ensure_ascii=False, indent=2) + '\n')
    write('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    revision = {'status': 'CURRENT_CABLE_SCENE_PUBLISHED_MANUFACTURING_OPEN',
                'printed_instances': count, 'feeder_instances': feeder_count, 'spin_instances': spin_count,
                'snapshot_id': snapshot, 'download_offered_on_page': False,
                'pending_validation': 'Unified manufacturing orientation/slicing, tolerance/load/return and physical launch acceptance remain open.',
                'manufacturing_release': False, 'physical_acceptance': False}
    write('revision-status.json', json.dumps(revision, ensure_ascii=False, indent=2) + '\n')
    with (stage / 'printed-parts.csv').open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['编号', '名称', '数量', '设计材料', '装配姿态STL', '状态'])
        for row in parts:
            if row['role'] == 'printed':
                writer.writerow([row['id'], row['name'], 1, 'Bambu TPU 95A HF' if row['id'] == 'spin/pad' else 'PETG', row['file'], '仅审查，制作未放行'])
    assets.append({'source': 'current inventory', 'file': 'printed-parts.csv', 'sha256': sha(stage / 'printed-parts.csv')})
    page = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>拉线点射与可调旋转 · 当前装配</title><style>
body{{margin:0;background:#eef3f5;color:#203844;font:16px/1.8 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}}main{{max-width:1080px;margin:32px auto;padding:0 22px}}h1{{font-size:32px;line-height:1.35}}a{{color:#12687a}}.button{{display:inline-block;background:#236d7a;color:white;padding:11px 18px;text-decoration:none;border-radius:8px;margin:5px 8px 5px 0}}figure{{margin:24px 0;background:white;border-radius:12px;overflow:hidden}}img{{display:block;width:100%}}figcaption{{padding:12px 18px}}.note{{background:#fff7e8;border-left:4px solid #dba43c;padding:12px 18px}}small{{color:#596c77}}</style>
<main><small>X1C / 0.4 mm · 当前设计审查</small><h1>拉线点射与可调旋转</h1>
<p>送料与拉线机构 {feeder_count} 件，旋转头 {spin_count} 件。共 {count} 个打印零件实例，金属五金和管路参考另列；退出保持叉仅在退出档装入。</p>
<p><a class="button" href="feeder-motion.html?view=system">打开完整三维场景 ▶</a><a class="button" href="feeder-motion.html?view=trigger">观察拉线扳机</a><a class="button" href="models.html?group=feeder">送料零件 / 爆炸图</a><a class="button" href="models.html?group=spin">旋转头零件</a></p>
<p>向虎口勾扣 → 端球拉动钢芯 → 滑架移动 → 先关后挡、再开前挡。外套两端固定，钢芯经过固定导向；松手由送料弹簧带回。完整场景可切换视角、单独显隐零件及观察一轮动作。</p>
<figure><img src="cable-models/{snapshot}/assembly.png" alt="当前拉线送料机构CAD渲染"><figcaption>拉线送料机构：实际支架、护套导向、轴系和五金。完整场景中还可查看旋转头及原机连接示意。</figcaption></figure>
<p class="note">当前模型已按源文件重新导出并检查。打印摆向与切片尚未统一完成，实际夹线、回位、强度和单球发射仍待验证；本页不提供已放行制作包。风机、三通和外部管路位置是示意。</p>
<p><a href="printed-parts.csv">{count} 件设计清单</a> · <a href="cable-assembly-inventory.json">实例与替换关系</a> · <a href="motion-manifest.json">模型来源记录</a></p>
</main></html>'''
    write('index.html', page)
    evidence = {'reports': {str(report_path.relative_to(ROOT)): sha(report_path),
                            str(render_path.relative_to(ROOT)): sha(render_path)},
                'source_sha256': report['source_sha256'], 'assets': assets,
                'printed_instances': count, 'manufacturing_release': False, 'physical_acceptance': False,
                'motion_page': {'manifest': 'motion-manifest.json', 'snapshot': 'current-cable-candidate',
                                'snapshot_id': snapshot, 'physical_acceptance': False}}
    (stage / 'evidence.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
    # Recheck identities immediately before touching served files.
    verify_sources(report)
    verify_sources(render)
    for name, expected in motion['web_sources'].items():
        if sha(ROOT / name) != expected:
            raise RuntimeError('Frontend changed while staging: ' + name)
    for asset in assets:
        if sha(stage / asset['file']) != asset['sha256']:
            raise RuntimeError('Staged asset changed: ' + asset['file'])
    backup = ROOT / 'output/preview-history' / ('before-cable-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    entries = sorted(p for p in stage.rglob('*') if p.is_file())
    for source in entries:
        relative = source.relative_to(stage)
        target = PUBLIC / relative
        if target.exists():
            saved = backup / relative
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, saved)
    # Dependencies first, manifests and visible entry points last.
    last = {'motion-manifest.json', 'manifest.json', 'feeder-motion.html', 'index.html', 'evidence.json'}
    entries.sort(key=lambda p: (p.name in last, p.name == 'index.html', str(p)))
    for source in entries:
        target = PUBLIC / source.relative_to(stage)
        target.parent.mkdir(parents=True, exist_ok=True)
        source.replace(target)
    receipt = {'status': 'CURRENT_CABLE_SCENE_PUBLISHED', 'snapshot_id': snapshot,
               'parts': len(parts), 'printed_instances': count, 'backup': str(backup.relative_to(ROOT)),
               'public': str(PUBLIC), 'report': str(report_path.relative_to(ROOT)),
               'published_manifest_sha256': sha(PUBLIC / 'motion-manifest.json'),
               'manufacturing_release': False, 'physical_acceptance': False}
    (report_path.parent / 'publication.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
