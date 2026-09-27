#!/usr/bin/env python3
"""Review the actual cable-actuator CAD against the current feeder source.

This is an offline geometric check, never a release or a physical guarantee.
Each run has its own directory. Failed geometry and logs are retained.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
from exact_mesh import exact_area_and_links
from feeder_integration import classify

ROOT = Path(__file__).resolve().parents[1]
CAD = ROOT / 'cad/cable-trigger-system.scad'
EXE = '/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
spec = importlib.util.spec_from_file_location('stl_inspector',
    '/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py')
mesh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mesh)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes():
    paths = {Path(__file__).resolve(), ROOT/'analysis/exact_mesh.py',
             ROOT/'analysis/feeder_integration.py', Path(spec.origin)}
    pending = [CAD]
    while pending:
        path = pending.pop().resolve()
        if path in paths:
            continue
        paths.add(path)
        source = path.read_text()
        pending.extend(path.parent/name for name in
                       re.findall(r'\b(?:include|use)\s*<([^>]+)>', source))
    return {str(p): sha(p) for p in sorted(paths)}


def execute(out, name, definitions, *, image=False, camera=None, backend='Manifold'):
    target = out/(name + ('.png' if image else '.stl'))
    cmd = [EXE, '--hardwarnings', '--backend', backend]
    if image:
        cmd += ['--render', '--imgsize=1600,1300', '--projection=o',
                '--autocenter', '--viewall', '--colorscheme=Tomorrow']
        if camera:
            cmd += ['--camera='+camera]
    else:
        cmd += ['--export-format', 'asciistl']
    for key, value in definitions.items():
        cmd += ['-D', key+'='+json.dumps(value)]
    cmd += ['-o', str(target), str(CAD)]
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    log = result.stdout+result.stderr
    (out/(name+'.log')).write_text(log)
    empty = 'Current top level object is empty' in log and not target.exists()
    failed = ('ERROR:' in log or 'WARNING:' in log or
              (result.returncode != 0 and not empty) or
              (result.returncode == 0 and not target.exists() and not empty))
    return {'name':name, 'definitions':definitions, 'command':cmd,
            'returncode':result.returncode, 'execution_ok':not failed,
            'empty':empty, 'file':str(target.relative_to(ROOT)) if target.exists() else None,
            'sha256':sha(target) if target.exists() else None}


def export_part(out, part):
    # The unchanged source frame produces one collinear triangle with Manifold.
    # Keep that failed export in its earlier run; CGAL resolves this tessellation.
    row = execute(out, part, {'ct_part':part}, backend='CGAL' if part in ['output-frame','input-body'] else 'Manifold')
    row['kind'] = 'printed-part'
    row['passed'] = False
    if row['execution_ok'] and row['file']:
        path = ROOT/row['file']
        row['mesh'] = info = mesh.inspect(path, 1e-6)
        row['topology'] = topo = exact_area_and_links(path)
        row['components'] = len(classify(path)['components'])
        row['passed'] = (info['watertightByEdgeTopology'] and row['components']==1
                         and not topo['exact_zero_area_face_indices']
                         and not topo['non_ring_vertex_links'])
    print('part', part, row['passed'], flush=True)
    return row


def probe(out, item):
    kind, t, expected_overlap = item
    name = kind+'-'+format(t, '.3f').replace('.', '_')
    # Mounting contacts may join along an edge and need independent analysis.
    # Both backends can emit these non-manifold surfaces. Do not hide them by
    # relaxing the volume threshold or treating a backend warning as success.
    row = execute(out, name, {'ct_part':'probe', 'ct_probe':kind, 'ct_t':t})
    row.update(kind='intersection', expected_solid_overlap=expected_overlap)
    row['passed'] = False
    if row['execution_ok']:
        row['classification'] = info = (classify(ROOT/row['file']) if row['file']
            else {'components':[], 'has_solid_or_unclassified_overlap':False})
        row['passed'] = info['has_solid_or_unclassified_overlap'] == expected_overlap
        if kind=='input-mount-thread-engagement':
            # Four separate nominal threaded pairs at the existing host holes.
            # These are not modeled as detailed helical threads.
            bounds = sorted([c['bounds'] for c in info['components']])
            expected = sorted([[[x-2,x+2],[-39,-35.8],[z-2,z+2]]
                               for x in [-16,16] for z in [-60,3]])
            row['expected_engagement_bounds'] = expected
            row['four_full_length_pairs'] = (len(bounds)==4 and
                all(abs(a-b)<1e-6 for actual,wanted in zip(bounds,expected)
                    for actual_axis,wanted_axis in zip(actual,wanted)
                    for a,b in zip(actual_axis,wanted_axis)))
            row['passed'] = row['passed'] and row['four_full_length_pairs']
    print('probe', name, row['passed'], flush=True)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--quick', action='store_true', help='Three poses for early diagnosis; not full traversal')
    parser.add_argument('--render', action='store_true')
    parser.add_argument('--only-probe', choices=['input-host','input-host-static','input-host-dynamic','input-output','input-hardware-host','input-mount-thread-engagement','output-hardware-host','frame-fixed',
        'baseline-frame-fixed','output-bridge-moving','input-motion','input-core-free','spring-added',
        'spring-continuous-fixed','spring-continuous-relative','output-screw-exit','output-screw-exit-control','solid-overlap-control'])
    args = parser.parse_args()
    before = source_hashes()
    out = ROOT/'output/cable-trigger-system'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out.mkdir(parents=True)
    parts = ['input-body','input-cover','input-lever','input-terminal-cap','output-beam','output-frame','output-cap']
    rows = []
    if not args.only_probe:
        with ThreadPoolExecutor(max_workers=2) as pool:
            rows.extend(pool.map(lambda part:export_part(out, part), parts))
    poses = [0, .5, 1] if args.quick else [n/20 for n in range(21)]
    kinds = ['input-host-dynamic','input-output','input-hardware-host','output-hardware-host','frame-fixed','baseline-frame-fixed',
             'output-bridge-moving','input-motion','input-core-free','spring-added','output-screw-exit']
    if args.only_probe:
        kinds = [args.only_probe]
    jobs = [(kind,t,kind in ['solid-overlap-control','input-mount-thread-engagement','output-screw-exit-control']) for kind in kinds
            for t in ([0] if kind in ['input-host-static','input-mount-thread-engagement'] else poses)]
    if not args.only_probe:
        jobs += [('input-host-static',0,False)]
        jobs += [('input-mount-thread-engagement',0,True)]
        jobs += [(k,0,False) for k in ['spring-continuous-fixed','spring-continuous-relative']]
        jobs += [('solid-overlap-control',0,True)]
        jobs += [('output-screw-exit-control',0,True)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        rows.extend(pool.map(lambda job:probe(out, job), jobs))
    pictures = []
    if args.render:
        for name, camera, t in [('rest','0,0,0,60,0,135,800',0),
                                ('pulled','0,0,0,60,0,135,800',1),
                                ('back','0,0,0,90,0,180,800',0)]:
            pictures.append(execute(out, name, {'ct_part':'assembly','ct_t':t},image=True,camera=camera))
    stable = before == source_hashes()
    passed = stable and all(row['passed'] for row in rows)
    report = {'status':'SAMPLED_GEOMETRY_PASS' if passed else 'FAIL_OR_STALE',
              'sources_stable':stable,'source_sha256':before,'results':rows,
              'pictures':pictures,'sampled_normalized_poses':poses,
              'scope':'Current feeder CAD with adopted direct-pull input, terminal cap and output actuator. '
                      'Finite nominal poses; the two spring-envelope tests are separately continuous. '
                      'input-core-free excludes only the named fixed guide, where core contact is intended; '
                      'it checks the body remainder, main cover, lever and terminal cap.',
              'intentional_hardware_mating':'The four input M4 bolts against original M4 nuts are excluded '
                    'from the unrelated-hardware collision test and checked as four separate full-length '
                    'nominal thread engagements. Detailed threads and tightening capacity are not modeled.',
              'not_validated':['unsampled actuator interference','printed dimensional variation',
                'physical cable housing retention and supplier end fitting detail','complete hardware and tool access',
                'clamp force and friction','strength and creep','assembly and loaded return',
                'ball delivery and adjustable spin on the physical blower'],
              'manufacturing_release':False,'physical_acceptance':False}
    report_path = out/'report.json'
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(report['status'], report_path, flush=True)
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
