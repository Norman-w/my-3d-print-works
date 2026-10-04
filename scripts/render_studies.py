#!/usr/bin/env python3
"""Render labelled engineering studies; this does not release printable parts."""
from pathlib import Path
import hashlib
import html
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OPENSCAD = Path('/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD')
OUTPUT = ROOT / 'output/preview'
sys.path.insert(0, str(ROOT / 'analysis'))
from gate_geometry import read_parameters


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    sources = list((ROOT/'cad').glob('*.scad'))
    source_hashes_before = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in sources}
    parameters, _ = read_parameters(ROOT / 'cad/parameters.scad')
    entries = []
    poses = [
        ('gate-loading', '前挡关闭，后挡开放', '0'),
        ('gate-overlap', '两挡均关闭', '0.5'),
        ('gate-front-open', '前挡开放，后挡关闭', '1'),
    ]
    source = ROOT / 'cad/kinematic-study.scad'
    for name, title, fraction in poses:
        target = OUTPUT / f'{name}.png'
        command = [str(OPENSCAD), '--hardwarnings', '--backend', 'Manifold',
                   '--imgsize', '1300,1000', '--camera', '125,-200,90,0,0,-22',
                   '--projection', 'o', '--viewall', '--colorscheme', 'Tomorrow',
                   '--render', '-D', f'stroke_fraction={fraction}',
                   '-o', str(target), str(source)]
        subprocess.run(command, cwd=ROOT, check=True)
        entries.append({'title': title, 'image': target.name,
                        'source': source.relative_to(ROOT).as_posix(),
                        'stroke_fraction': float(fraction), 'command': command})

    candidates = [
        ('feeder-assembly-review', '原导向基线：已发现超出 ±1 mm 的位姿',
         'feeder-assembly.scad', 'assembly_part="review"', '150,-250,130,0,0,-25'),
        ('feeder-section-review', '壳体剖开：内导向、旁通腔和挡指',
         'feeder-assembly.scad', 'assembly_part="section"', '-210,-160,90,0,0,-25'),
        ('spin-section-review', '旋转头剖面：软垫退让与预压分别运动',
         'spin-head.scad', 'part="section"', '135,185,115,8,0,25'),
        ('spin-exploded-review', '旋转头拆解候选；弹簧和软垫材料待选',
         'spin-head.scad', 'part="exploded"', '180,-210,160,25,0,30'),
        ('guide-revision-review', '改进候选：从背面调节的可拆压条',
         'feeder-guide-revision.scad', 'revision_part="assembly"', '155,-220,105,0,0,-25'),
        ('guide-revision-exploded-review', '压条与后盖拆出；完整误差仍未验证',
         'feeder-guide-revision.scad', 'revision_exploded=true', '155,-220,105,0,0,-25'),
        ('seam-face-review', '分缝候选：定位与浅储胶槽；材料和端口密封未定',
         'feeder-seam-candidate.scad', 'seam_part="negative_face"', '210,100,75,0,0,-25'),
        ('seam-exploded-review', '两半壳与定位销：保持 X=0 硬止挡',
         'feeder-seam-candidate.scad', 'seam_part="exploded"', '190,-230,130,0,0,-25'),
        ('fit-coupons-review', '七件配合试片：实测后再收敛尺寸',
         'fit-coupons.scad', 'coupon_part="layout"', '190,-190,185,70,30,5'),
        ('revised-feeder-review', '合并审阅：新导向与分缝候选，未冻结制造',
         'revised-feeder-review.scad', 'revised_mode="review"', '155,-220,105,0,0,-25'),
        ('revised-feeder-section', '合并剖面：球道、旁通与两组挡指',
         'revised-feeder-review.scad', 'revised_mode="section"', '-210,-160,90,0,0,-25'),
    ]
    for name, title, filename, definition, camera in candidates:
        candidate_source = ROOT / 'cad' / filename
        target = OUTPUT / f'{name}.png'
        command = [str(OPENSCAD), '--hardwarnings', '--backend', 'Manifold',
                   '--imgsize', '1300,1000', '--camera', camera,
                   '--projection', 'o', '--viewall', '--colorscheme', 'Tomorrow',
                   '--render', '-D', definition, '-o', str(target), str(candidate_source)]
        subprocess.run(command, cwd=ROOT, check=True)
        entries.append({'title': title, 'image': target.name,
                        'source': candidate_source.relative_to(ROOT).as_posix(),
                        'definition': definition, 'command': command})
    hashes = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sources}
    if hashes != source_hashes_before:
        raise RuntimeError('CAD changed during rendering; regenerate a consistent review page')
    manifest = {'status': 'RENDERED_STUDY_ONLY', 'source_sha256': hashes,
                'dynamic_simulation': False, 'physical_validation': 'OPEN',
                'entries': entries}
    (OUTPUT / 'render-manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    cards = '\n'.join(f'<figure><img src="{html.escape(e["image"])}" '
                      f'alt="{html.escape(e["title"])}"><figcaption>'
                      f'{html.escape(e["title"])}</figcaption></figure>' for e in entries)
    page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>点射与可调旋转：工程候选</title><style>
body{margin:0;background:#f4f6f8;color:#18212c;font:16px/1.7 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}
main{max-width:1200px;margin:36px auto;padding:0 24px}h1{font-size:30px;margin:12px 0}
.status{display:inline-block;background:#fff1cf;color:#704600;padding:4px 12px;border-radius:6px;font-weight:600}
.note{background:white;padding:18px 24px;border-left:4px solid #287996;margin:24px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px}
figure{margin:0;background:white;border:1px solid #dce3e8;border-radius:10px;overflow:hidden}
img{width:100%;display:block}figcaption{padding:12px 18px;font-weight:600}a{color:#176084}
td,th{text-align:left;padding:8px 14px;border-bottom:1px solid #dce3e8}table{border-collapse:collapse;background:white}
</style><main><span class="status">工程候选 · 未发布打印包 · 实物验证未完成</span>
<h1>点射与可调球旋转：当前实体候选</h1>
<p>目标：一次完整扣动释放一颗球，保持按住不补球；同时保留可调球旋转的改造目标。</p>
<div class="note"><strong>机构已细化为零件，但还不能承诺首次制作成功。</strong><br>
三张图中的球始终是同一组静止参考球位，没有求解气流、球的运动或接触变形。
前三张为挡指原理研究，其后为具体零件候选和配合试片。
实际气路和固定导向已建模；完整机构误差、密封、接口适配、弹簧与软垫仍有开放项。</div>
<div class="note"><strong>新发现：原导向的 ±1 mm 位置保证未成立。</strong><br>
真实 CAD 容许一个向外偏移约 1.006 mm 的挡指位姿。新导向已恢复中心基准，但仍找到
沿开合方向偏差约 0.931 mm 的有效位姿；这只是最坏偏差的下界，完整误差仍未通过。
分缝已形成独立候选，材料和端口密封未确定。配合试片用于收集真实尺寸，不是整套制造包。
<a href="../../docs/feeder-tolerance.md">误差反例</a> ·
<a href="../../docs/feeder-guide-revision.md">调隙候选</a> ·
<a href="../../docs/guide-revision-tolerance.md">新导向游隙复核</a> ·
<a href="../../docs/feeder-seam-candidate.md">分缝候选</a> ·
<a href="../../docs/fit-coupons.md">试片说明</a> ·
<a href="../../docs/candidate-bom.md">候选零件清单</a></div>
<div class="grid">''' + cards + '''</div>
<h2>当前输入和边界</h2><table>
<tr><th>已提供</th><td>40+ 球；出球管内 48 / 外 50 mm；软管内 50 / 外 55 mm；X1C。</td></tr>
<tr><th>分析候选</th><td>__BALL_MIN__–__BALL_MAX__ mm 球径包络，__GUIDE_ID__ mm 导向孔、__GATE_SPACING__ mm 挡距；并非已测公差或冻结尺寸。</td></tr>
<tr><th>已发现并修正</th><td>两球导向覆盖、侧孔额外偏移、内衬支撑肋搭接、部分导轨/抽出路径干涉。固定摩擦垫已改为独立退让候选。</td></tr>
<tr><th>接口已明确</th><td>48内/50外硬管可任意裁长；硬管插入斜三通，50内/55外钢丝软管套在硬管外面。模块出口接硬管短节，25 mm是模块插接段。</td></tr>
<tr><th>待实测与细化</th><td>接头固定和密封、实际球样、原机气路、打印配合及弹簧力；不再要求测现有管口夹持直段。</td></tr></table>
<h2>已确认的接口与裁管安排</h2><img src="../../docs/interface-measurements.svg" alt="硬管插三通、软管套硬管及改装后的短节连接示意">
<p><a href="../../docs/interface-contract.md">接口契约和裁管方法</a></p>
<p><a href="../../docs/first-build-decision.md">首次完整制作的判断与下一步实配证据</a></p>
<h2>出口连接剖面研究</h2>
<p>外套、箍和带肩内衬的装配空间；密封压缩、抗拔、薄壁强度和独立支架仍未确定。研究中的内衬肩使有效插深从25减至23.5 mm，未更改基线壳体或打印清单。</p>
<figure><img src="../interface-study/section-isometric.png" alt="出口连接剖面：硬管、带肩内衬及一体化阶梯分体箍"><figcaption>橙色为内衬；绿色为一体化阶梯分体箍，深灰为一对参考 M3 螺钉。没有实物验收结论。</figcaption></figure>
<p><a href="../../docs/interface-study.md">装配顺序、尺寸与检查边界</a></p>
<p>名义不相交、网格闭合、误差预算和实物试球是不同检查；任何一项通过都不能替代其余项。</p>
<p><a href="../../docs/design-review.md">工程评审记录</a> ·
<a href="../../docs/current-status.md">当前状态和未关闭项</a> ·
<a href="../../docs/physical-validation.md">实物验证流程</a> ·
<a href="../analysis/gate-geometry.json">挡球几何计算</a> ·
<a href="../analysis/airflow-spin.json">通气截面与旋转分析</a> ·
<a href="../analysis/assembly-budget.json">机构游隙与分析预算的交叉检查</a></p>
<p>渲染及理想几何检查不构成“一次通过”的保证。只有对应实物工况的装配、单发及旋转证据才能关闭验收。</p>
</main></html>'''
    for token, key in [('__BALL_MIN__','ball_min_d'),('__BALL_MAX__','ball_max_d'),
                       ('__GUIDE_ID__','guide_id'),('__GATE_SPACING__','gate_spacing')]:
        page = page.replace(token, f'{parameters[key]:g}')
    (OUTPUT / 'index.html').write_text(page, encoding='utf-8')
    print(OUTPUT / 'index.html')


if __name__ == '__main__':
    main()
