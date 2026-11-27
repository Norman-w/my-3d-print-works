#!/usr/bin/env python3
"""Package explicit, frozen review selections; never promote manufacturing state.

No folder-wide STL/3MF globbing. Both report hashes are required so an actively
changing slice report cannot silently become the delivery selection.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/manufacturing'
FEEDER = 'output/print-review/final-feeder/report.json'
SPIN = 'output/print-review/final-spin/report.json'
GEOMETRY = 'output/launcher-final/report.json'
REPORTS = [GEOMETRY, FEEDER, SPIN, 'output/analysis/spin-head-geometry.json',
    'output/spin-complete-hardware/report.json', 'output/feeder-frame-y-guide/report.json',
    'output/inlet-retention-final/report.json', 'output/frame-y-guide-bound/report.json']
DOCS = ['final-assembly.md', 'final-feeder-print.md', 'spin-complete-hardware.md',
    'spin-material-selection.md', 'final-sealing-process.md', 'final-gate-error-bound.md',
    'final-spin-print.md', 'spin-head.md', 'feeder-frame-y-guide.md',
    'frame-y-guide-bound.md', 'inlet-retention-final.md', 'point-shot-interlock.md',
    'final-feeder-hardware.md']
ENTRYPOINTS = ['cad/launcher-final-assembly.scad', 'cad/spin-head.scad',
    'cad/spin-complete-hardware.scad']


def sha(data): return hashlib.sha256(data).hexdigest()
def require(test, message):
    if not test: raise ValueError(message)


class Snapshot:
    def __init__(self): self.data = {}; self.roles = {}; self.hash_checks = []
    def add(self, name, role, expected=None):
        path = (ROOT / name).resolve()
        require(path.is_relative_to(ROOT), f'Outside project: {name}')
        rel = path.relative_to(ROOT).as_posix()
        require(not (ROOT / name).is_symlink(), f'Symlink refused: {name}')
        require(path.is_file(), f'Missing file: {rel}')
        b = path.read_bytes()
        if rel in self.data:
            require(self.data[rel] == b, f'File changed during collection: {rel}')
        if expected:
            require(sha(b) == expected, f'Hash mismatch: {rel}')
            self.hash_checks.append({'path': rel, 'sha256': expected})
        self.data[rel] = b
        self.roles.setdefault(rel, set()).add(role)
        return rel
    def report(self, name, expected=None):
        key = self.add(name, 'report', expected)
        return json.loads(self.data[key])
    def sources(self, mapping):
        require(isinstance(mapping, dict), 'Source identity must be a mapping')
        for p, h in mapping.items(): self.add(p, 'source', h)
    def historical_sources(self, mapping):
        """Retain original identities without claiming the old source is current."""
        for p, h in mapping.items():
            candidate = ROOT / p
            if candidate.is_file() and sha(candidate.read_bytes()) == h:
                self.add(p, 'historical-source-still-identical', h)
            else:
                archived = 'output/launcher-final-history/before-frame-y-guide/' + p
                self.add(archived, 'historical-source-snapshot', h)
    def current(self):
        for p, b in self.data.items():
            require((ROOT / p).read_bytes() == b, f'Changed before ZIP commit: {p}')


def cad_dependencies(snap, name, seen):
    if name in seen: return
    seen.add(name); key = snap.add(name, 'CAD')
    for dep in re.findall(r'\b(?:include|use)\s*<([^>]+)>', snap.data[key].decode()):
        path = (ROOT / name).parent / dep
        rel = path.resolve().relative_to(ROOT).as_posix()
        require(rel.startswith('cad/') and rel.endswith('.scad'), f'Unexpected CAD dependency: {rel}')
        cad_dependencies(snap, rel, seen)


def selected(snap, report, group):
    rows = report['selected_plates']; result = []
    require(len(rows) == (24 if group == 'feeder' else 10), f'{group}: wrong selected plate count')
    require(len({r['id'] for r in rows}) == len(rows), 'Duplicate plate id')
    for row in rows:
        inputs = row.get('source_stls', row.get('inputs'))
        require(isinstance(inputs, list) and inputs, f'Missing selected inputs: {row["id"]}')
        quantity = row.get('quantity', len(inputs))
        require(quantity == len(inputs), f'Instance count mismatch: {row["id"]}')
        for inp in inputs:
            prefix = 'output/launcher-final/' if group == 'feeder' else 'output/spin-head/'
            require(inp['path'].startswith(prefix) and inp['path'].endswith('.stl'), 'Unexpected input STL')
            snap.add(inp['path'], 'printable-STL', inp['sha256'])
        mf = row.get('gcode_3mf_path', row.get('three_mf_path'))
        mh = row.get('gcode_3mf_sha256', row.get('three_mf_sha256'))
        require(mf and mh and mf.endswith('.3mf'), 'Missing selected 3MF identity')
        snap.add(mf, 'selected-review-3MF', mh)
        folder = Path(row.get('slice_folder', str(Path(mf).parent)))
        inv_name = (folder / 'invocation.json').as_posix()
        inv = snap.report(inv_name, row.get('original_invocation_sha256'))
        original_sources = inv.get('source_sha256_at_start', inv.get('cad_sha256', {}))
        if row.get('provenance') == 'reused_identical_stl':
            reuse = snap.report(row['revalidation_path'], row['revalidation_sha256'])
            require(reuse['status'] == 'REUSED_IDENTICAL_STL_CURRENT_IDENTITY_PASS'
                    and all(reuse['checks'].values()), 'Failed slice reuse identity')
            require(reuse['source_stls'] == inputs, 'Reused STL selection mismatch')
            require(reuse['original_invocation_path'] == inv_name
                    and reuse['original_invocation_sha256'] == row['original_invocation_sha256'],
                    'Reused invocation mismatch')
            require(reuse['original_source_sha256_at_slice'] == original_sources,
                    'Historical source identity changed')
            snap.sources(reuse['current_source_sha256'])
            snap.historical_sources(original_sources)
            for path, expected in reuse['original_evidence_sha256'].items():
                require(sha((ROOT/path).read_bytes()) == expected, 'Historical slice changed: ' + path)
        else:
            snap.sources(original_sources)
        require(inv.get('sent_to_printer') is False, f'Unexpected print state: {inv_name}')
        profiles = inv.get('local_profile_sha256', inv.get('private_profiles'))
        require(isinstance(profiles, dict) and len(profiles) == 3, f'Missing profile identities: {inv_name}')
        for name, h in profiles.items():
            profile = folder / (name if name.endswith('.json') else name + '.json')
            snap.add(profile.as_posix(), 'slice-profile', h)
        gcode_path = row.get('gcode_path', str(folder / 'plate_1.gcode'))
        gbytes = (ROOT / gcode_path).read_bytes()
        gh = row.get('gcode_sha256', sha(gbytes))
        require(sha(gbytes) == gh, f'G-code mismatch: {row["id"]}')
        # CRC-check every member and verify packaged G-code is the reviewed
        # external G-code. No need to duplicate huge raw G-code beside the 3MF.
        with zipfile.ZipFile(ROOT / mf) as archive:
            require(archive.testzip() is None, f'Broken 3MF ZIP: {mf}')
            members = [n for n in archive.namelist() if n.endswith('.gcode')]
            require(len(members) == 1, f'Expected exactly one G-code plate: {mf}')
            require(sha(archive.read(members[0])) == gh, f'Embedded G-code mismatch: {mf}')
        for name in ['plate-review.json', 'review.json', 'result.json']:
            f = folder / name
            if (ROOT / f).is_file(): snap.add(f.as_posix(), 'selected-plate-evidence')
        result.append({'group': group, 'id': row['id'], 'quantity': quantity,
            'source_stls': inputs, 'review_3mf': mf, 'review_3mf_sha256': mh,
            'embedded_gcode_sha256': gh, 'external_gcode_verified_not_duplicated': gcode_path,
            'material': row['material'], 'orientation': row.get('orientation'),
            'provenance': row.get('provenance', 'original_slice_current_source'),
            'revalidation_path': row.get('revalidation_path'),
            'source_report_status': report['status']})
    return result


def readme(feeder, spin):
    flagged = {k: v for k, v in feeder.get('checks', {}).items() if not v}
    return f'''# 点射可调旋转版：数字制作候选包

这是供审阅、切片设置复核和成品制作准备的候选快照，**不是制造发布，也不保证首次实物一次通过**。没有连接打印机、发送打印任务或下单。

包内含 48 个打印 STL：送料 38 件、旋转头 10 件；审查 3MF 为送料 24 板、旋转头 10 板。每板已经包含清单所示数量，同一板不要再按数量重复打印。金属五金、PC 管和弹簧参考体、历史失败板及诊断相交体均不作为打印件收入。

先读 `docs/final-assembly.md`；送料姿态和支撑清理见 `docs/final-feeder-print.md`，旋转头见 `docs/final-spin-print.md`、`docs/spin-complete-hardware.md`。密封按 `docs/final-sealing-process.md`，误差边界见 `docs/final-gate-error-bound.md`。CAD 入口为 `cad/launcher-final-assembly.scad` 与 `cad/spin-head.scad`，二者接在原机不同位置，不能同轴叠装。

所选板以 `manifest.json` 的 `selected_plates` 为准，文件保持原仓库相对路径。3MF 自带实际 G-code；打包时已核对其与所选报告、源 STL、源 CAD 和外部 G-code 的哈希关系，不额外复制裸 G-code。保留审查结果原状态：送料 `{feeder['status']}`；旋转头 `{spin['status']}`。送料未关闭的报告检查：`{json.dumps(flagged, ensure_ascii=False)}`。

机器配置为 X1C / 0.4 mm；送料 38 件及旋转头 9 件用 PETG，唯一柔性件 `spin-pad.stl` 用 Bambu TPU 95A HF、100% 填充、外置料盘。Generic PETG 品牌和纹理 PEI 为分析配置假设；用户确认了 PETG 和 PEI，尚未确认实际 PETG 品牌及 PEI 纹理。打开审查板后核对实际机器、床面、材料和支撑清理安排；本包不自动发打印。

尚未关闭的边界：

- 入口采用22 mm宽的分体外夹和刚性背梁支承；3 mm柔衬是名义包络，实际软管夹压、抗拔和气密尚未验收。织带负责自由软管卸载。
- 公共架已增加独立Y调隙；全行程总位置误差仍未认证为 ±1 mm，不能把轨姿态条件界当作整机实测公差。
- 真实打印配合、支撑去除后的表面、V 座/M2 预紧保持、PETG 变形/蠕变、密封、夹持及弹簧回位均未实物验收。
- 点射一次一球与旋转效果没有完成整机测试；初始球就位、完整扣动和完整回位仍是操作前提。

`manifest.json` 是包内文件哈希、来源与板/实例清单；`SHA256SUMS` 包含其自身以外的所有包内文件（包括 manifest）。可在解压根目录运行 `shasum -a 256 -c SHA256SUMS` 检查传输完整性。哈希通过只证明文件未变，不提升任何制造或物理状态。
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--feeder-report-sha256', required=True)
    ap.add_argument('--spin-report-sha256', required=True)
    ap.add_argument('--check-only', action='store_true')
    args = ap.parse_args(); snap = Snapshot()
    feeder = snap.report(FEEDER, args.feeder_report_sha256)
    spin = snap.report(SPIN, args.spin_report_sha256)
    geometry = snap.report(GEOMETRY)
    require(feeder['manufacturing_release'] is False and feeder['physical_acceptance'] is False,
            'Unexpected feeder manufacturing state')
    require(spin['physical_acceptance'] is False, 'Unexpected spin physical state')
    require(spin['status'] == 'OFFLINE_SPIN_SLICES_AND_BOUNDED_SUPPORT_ACCESS_PASS_PHYSICAL_OPEN'
            and spin['shared_unchanged'] and spin['sent_to_printer'] is False
            and len(spin['parts']) == 10 and all(all(r['checks'].values()) for r in spin['parts']),
            'Current spin slice review has not passed')
    require(geometry['manufacturing_release'] is False, 'Unexpected geometry manufacturing state')
    require(geometry['status'] == 'INTEGRATED_FEEDER_DIGITAL_CHECKS_PASS'
            and geometry['sources_stable'] and all(r['passed'] for r in geometry['cases']),
            'Current integrated geometry has not passed')
    require(feeder['status'] == 'BOUNDED_OFFLINE_SLICE_REVIEW_PASS_PHYSICAL_OPEN'
            and all(feeder['checks'].values()), 'Current feeder slice review has not passed')
    require(feeder['printed_instances'] == 38, 'Wrong feeder instance count')
    require(all(feeder['input_identity'].values()), 'Feeder input identity check failed')
    snap.add(GEOMETRY, 'report', feeder['final_geometry_report_sha256'])
    for name in REPORTS:
        r = snap.report(name)
        if 'source_sha256' in r: snap.sources(r['source_sha256'])
    # The original error analysis describes the archived 33-part guide geometry.
    historical = snap.report('output/final-gate-error-bound/report.json')
    snap.historical_sources(historical.get('source_sha256', {}))
    pairs = snap.report('output/printed-pair-fit/report.json')
    require(pairs['status'] == 'PRINTED_PAIR_POSE_PASS' and pairs['printed_instances'] == 38,
            'Printed assembly pair audit failed')
    snap.add(GEOMETRY, 'pair-audit-input', pairs['source_report_sha256'])
    snap.add('analysis/printed_pair_fit.py', 'review-source', pairs['script_sha256'])
    snap.add('output/manufacturing/material-contract.json', 'material-and-hardware-contract')
    bom = snap.report('output/manufacturing/feeder-hardware-bom.json')
    snap.sources(bom['source_sha256'])
    require(bom['printed_instances'] == 38 and bom['hardware_units_total'] == 195,
            'Unexpected current feeder hardware contract')
    snap.add('scripts/review_final_feeder_slice.py', 'review-source', feeder['review_script_sha256'])
    snap.add('scripts/review_spin_head_slice.py', 'review-source', spin['script_sha256'])
    # Reports referenced by the final slice selections, not a directory glob.
    for k, name in [('support_access_report_sha256', 'output/print-review/final-feeder/support-access.json'),
                    ('shell_feature_report_sha256', 'output/print-review/final-feeder/shell-critical-features.json')]:
        snap.add(name, 'support-and-feature-evidence', feeder[k])
    spin_access = 'output/print-review/spin-head/support-access-review.json'
    require(spin['support_access_review']['path'] == spin_access, 'Unexpected spin support report')
    access = snap.report(spin_access, spin['support_access_review']['sha256'])
    snap.add('analysis/spin_slice_support.py', 'review-source', access['script_sha256'])
    for name in DOCS: snap.add('docs/' + name, 'assembly-and-review-instructions')
    cad = set()
    for name in ENTRYPOINTS: cad_dependencies(snap, name, cad)
    plates = selected(snap, feeder, 'feeder') + selected(snap, spin, 'spin')
    printed = [r for r in geometry['parts'] if r['role'] == 'printed']
    require(len(printed) == 38 and all(r['passed'] for r in printed), 'Wrong/failed final print geometry')
    actual = {i['path'] for p in plates if p['group'] == 'feeder' for i in p['source_stls']}
    require(actual == {p['file'] for p in printed}, 'Selected plates do not cover the exact 38 final STL instances')
    for p in printed: snap.add(p['file'], 'printable-STL', p['sha256'])
    stls = [n for n, roles in snap.roles.items() if 'printable-STL' in roles]
    require(len(stls) == 48 and sum(p['quantity'] for p in plates) == 48, 'Expected 48 printed instances')
    require(len([p for p in stls if '/spin-' in p]) == 10, 'Expected 10 spin STL instances')
    snap.add(Path(__file__).relative_to(ROOT).as_posix(), 'package-source')
    snap.current()
    if args.check_only:
        print(json.dumps({'status': 'PACKAGE_INPUT_IDENTITY_CHECK_PASS', 'printed_instances': 48,
              'selected_plates': 34, 'manufacturing_release': False})); return
    OUT.mkdir(parents=True, exist_ok=True)
    payload = dict(snap.data)
    payload['README.md'] = readme(feeder, spin).encode()
    files = [{'path': n, 'sha256': sha(b), 'bytes': len(b),
              'roles': sorted(snap.roles.get(n, {'package-readme'}))} for n, b in sorted(payload.items())]
    manifest = {'status': 'DIGITAL_FABRICATION_CANDIDATE_NOT_MANUFACTURING_RELEASE',
        'manufacturing_release': False, 'physical_acceptance': False, 'sent_to_printer': False,
        'printed_instances': 48, 'feeder_instances': 38, 'spin_instances': 10,
        'selected_plate_count': 34, 'selected_feeder_plates': 24, 'selected_spin_plates': 10,
        'selected_plates': plates, 'frozen_slice_reports': {FEEDER: args.feeder_report_sha256,
            SPIN: args.spin_report_sha256}, 'CAD_dependencies': sorted(cad),
        'preserved_slice_status': {'feeder': feeder['status'], 'spin': spin['status']},
        'source_and_artifact_hash_checks': snap.hash_checks, 'files': files,
        'exclusions': ['historical/failed/diagnostic STL', 'unselected 3MF', 'procurement/orders',
            'credentials/pairing material', 'raw G-code duplicated outside 3MF', 'metal/PC/spring reference STL'],
        'scope': 'Hash/selection/package integrity only; upstream geometric and slice claims remain at their original evidence level.'}
    payload['manifest.json'] = (json.dumps(manifest, indent=2, ensure_ascii=False) + '\n').encode()
    payload['SHA256SUMS'] = ''.join(f'{sha(b)}  {n}\n' for n, b in sorted(payload.items())).encode()
    tmp = OUT / 'launcher-candidate.zip.tmp'; target = OUT / 'launcher-candidate.zip'
    with zipfile.ZipFile(tmp, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for n, b in sorted(payload.items()):
            info = zipfile.ZipInfo(n, date_time=(2026, 9, 25, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED; info.external_attr = 0o100644 << 16
            archive.writestr(info, b)
    with zipfile.ZipFile(tmp) as archive:
        require(archive.testzip() is None, 'Final ZIP CRC failed')
        require(set(archive.namelist()) == set(payload), 'Final ZIP member mismatch')
        for n, b in payload.items(): require(sha(archive.read(n)) == sha(b), f'Final ZIP content mismatch: {n}')
    snap.current(); tmp.replace(target)
    (OUT / 'launcher-candidate-manifest.json').write_bytes(payload['manifest.json'])
    (OUT / 'launcher-candidate-README.md').write_bytes(payload['README.md'])
    (OUT / 'launcher-candidate-SHA256SUMS').write_bytes(payload['SHA256SUMS'])
    receipt = {'status': 'CANDIDATE_PACKAGE_INTEGRITY_PASS', 'path': str(target.relative_to(ROOT)),
        'sha256': sha(target.read_bytes()), 'bytes': target.stat().st_size,
        'file_count': len(payload), 'STL_count': 48, 'review_3MF_count': 34,
        'printed_instances': 48, 'manufacturing_release': False, 'physical_acceptance': False,
        'frozen_slice_reports': manifest['frozen_slice_reports']}
    (OUT / 'launcher-candidate-package-report.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    try: main()
    except (ValueError, OSError, KeyError, zipfile.BadZipFile) as exc:
        print(f'PACKAGE NOT BUILT: {exc}', file=sys.stderr); raise SystemExit(1)
