#!/usr/bin/env python3
"""Export explicit feeder assembly instances; no print release or arrangement."""
from pathlib import Path
import concurrent.futures
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import argparse
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/integrated-review-parts'
CAD = ROOT / 'cad/feeder-review-parts.scad'
EXE = '/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
sys.path.insert(0, str(ROOT / 'analysis'))
from feeder_integration import classify


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sources():
    paths = {Path(__file__).resolve()}
    pending = [CAD]
    while pending:
        path = pending.pop().resolve()
        if path in paths:
            continue
        paths.add(path)
        pending.extend(path.parent / dep for dep in re.findall(
            r'\b(?:use|include)\s*<([^>]+)>', path.read_text()))
    return {str(path.relative_to(ROOT)): digest(path) for path in sorted(paths)}


def disconnected_vertex_links(path, inspector):
    _, triangles = inspector._read_triangles(path)
    links = defaultdict(lambda: defaultdict(set))
    for triangle in triangles:
        vertices = [tuple(round(x,7) for x in vertex) for vertex in triangle]
        for index, center in enumerate(vertices):
            a,b = vertices[(index+1)%3], vertices[(index+2)%3]
            links[center][a].add(b)
            links[center][b].add(a)
    faults = []
    for point, graph in links.items():
        seen = set()
        count = 0
        for start in graph:
            if start in seen:
                continue
            count += 1
            pending = [start]
            while pending:
                vertex = pending.pop()
                if vertex in seen:
                    continue
                seen.add(vertex)
                pending.extend(graph[vertex]-seen)
        if count>1:
            faults.append({'point_mm':point,'disconnected_fans':count})
    return faults


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reuse-exports',action='store_true',help='Recheck identical existing exports; only if their CAD sources and commands match')
    options=parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    integrated = json.loads((ROOT / 'output/feeder-integrated-candidate/report.json').read_text())
    assert integrated['status'] == 'INTEGRATED_NOMINAL_CANDIDATE_PASS'
    assert integrated['sources_stable'] and integrated['frame_sweep_input_stable']
    for path, expected in integrated['source_sha256'].items():
        assert digest(ROOT / path) == expected, f'Stale integrated report: {path}'
    before = sources()
    previous={}
    if options.reuse_exports:
        old=json.loads((OUT/'report.json').read_text())
        own=str(Path(__file__).resolve().relative_to(ROOT))
        if {k:v for k,v in old['source_sha256'].items()if k!=own}!={k:v for k,v in before.items()if k!=own}:
            raise RuntimeError('CAD dependencies changed; cannot reuse exports')
        previous={row['id']:row for row in old['parts']}
    spec = importlib.util.spec_from_file_location('mesh_inspector',
        '/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py')
    inspector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inspector)
    items = []

    def add(part, name, family=None, role='printed', side=None, rear=None):
        definitions = {'rp_part': part, 'rp_t': 0}
        suffix = ''
        if side is not None:
            definitions['rp_side'] = side
            suffix += '-right' if side > 0 else '-left'
        if rear is not None:
            definitions['rp_rear'] = rear
            suffix += '-rear' if rear else '-front'
        items.append({'id': part + suffix, 'name': name, 'family': family or part,
                      'role': role, 'definitions': definitions})

    for part, name in [('positive-half','联合主壳右半'),('negative-half','联合主壳左半'),
                       ('beam-grip','支承背梁与握把'),('liner','出口带肩内衬'),
                       ('right-support','X导向右主支座'),('left-support','左支座与弹簧接口'),
                       ('x-gib','公共架X压条'),('x-cover','X压条调节外盖'),
                       ('frame','公共凸轮架与扣动指环')]:
        add(part,name)
    for side, label in [(1,'右'),(-1,'左')]:
        for part, name in [('capture','出口法兰捕获座'),('pipe-clamp','硬管分体夹'),('y-cap','公共架导向盖')]:
            add(part,label+name, family=(part if part=='y-cap' else f'{part}-{side}'),side=side)
        for rear, end in [(False,'前'),(True,'后')]:
            for part, name in [('y-gib','载体Y压条'),('y-keeper','Y压条外盖'),('finger','挡指载体')]:
                add(part,label+end+name,side=side,rear=rear)
    add('hardware','标准五金与定位销（参考组）',role='purchased')
    add('pc-reference','50外/48内PC硬管（长度示意）',role='purchased')

    def export(item):
        path = OUT / (item['id'] + '.stl')
        backend = 'Manifold' if item['id'] in ('hardware','positive-half','negative-half') else 'CGAL'
        command = [EXE,'--hardwarnings','--backend',backend,'--export-format','asciistl']
        for key,value in item['definitions'].items():
            command += ['-D', f'{key}={json.dumps(value)}']
        command += ['-o',str(path),str(CAD)]
        old=previous.get(item['id'])
        reused=bool(old and old['command']==command and path.is_file()and digest(path)==old['sha256'])
        if not reused:
            path.unlink(missing_ok=True)
            result = subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
            log = result.stdout + result.stderr
            (OUT / (item['id'] + '.log')).write_text(log)
            if result.returncode or 'WARNING:' in log or 'ERROR:' in log:
                raise RuntimeError(log)
        mesh = inspector.inspect(path,1e-6)
        components = len(classify(path)['components'])
        fans = disconnected_vertex_links(path,inspector)
        # Purchased metal references may meet at edges when united. They are
        # display solids, never printable parts; retain their full mesh report.
        passed = (mesh['watertightByEdgeTopology'] and components==1 and not fans) if item['role']=='printed' else (
            mesh['triangleCount']>0 and mesh['volume']>0 and mesh['boundaryEdgeCount']==0
            and mesh['degenerateTriangleCount']==0 and mesh['inconsistentOrientationEdgeCount']==0)
        print(item['id'],passed,components,flush=True)
        return {**item,'file':str(path.relative_to(ROOT)),'sha256':digest(path),
                'mesh':mesh,'components':components,'disconnected_vertex_links':fans,
                'passed':passed,'command':command,'reused_identical_export':reused}

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(export,items))
    # Compare the CAD instance list to the authoritative assembled solids.
    # Export topology is checked above separately. Do not call this a proof of
    # mesh round-trip equality: whole imported-set CSG is unreliable at contacts.
    native = OUT / 'assembly-parity.scad'
    instances = '\n'.join('rp_item('+','.join(
        f'{key[3:]}={json.dumps(value)}' for key,value in row['definitions'].items())+');' for row in rows)
    native.write_text(f'include <../../cad/parameters.scad>\n'
                      f'use <../../cad/feeder-integrated-candidate.scad>\n'
                      f'use <../../cad/feeder-cam-guide-revision.scad>\n'
                      f'use <../../cad/feeder-review-parts.scad>\n'
                      f'module exported(){{{instances}}}\n'
                      'module reference(){ic_fixed();cg_moving(0);}\n'
                      'union(){difference(){exported();reference();}'
                      'difference(){reference();exported();}}\n')
    parity = OUT / 'assembly-parity.stl'
    parity.unlink(missing_ok=True)
    result = subprocess.run([EXE,'--hardwarnings','--backend','CGAL','--export-format','asciistl',
                             '-o',str(parity),str(native)],cwd=ROOT,capture_output=True,text=True)
    log = result.stdout + result.stderr
    (OUT / 'assembly-parity.log').write_text(log)
    empty = 'Current top level object is empty' in log and not parity.exists()
    if 'WARNING:' in log or 'ERROR:' in log or (result.returncode and not empty):
        raise RuntimeError(log)
    info = classify(parity) if parity.exists() else {'has_solid_or_unclassified_overlap':False,'components':[]}
    pictures=[]
    for name, camera in [('assembly','12,0,-10,64,0,28,1000'),
                         ('front','12,-4,-10,90,0,0,1000'),('top','0,0,-4,0,0,0,850')]:
        path=OUT/(name+'.png')
        result=subprocess.run([EXE,'--hardwarnings','--backend','Manifold','--render',
            '--imgsize=1500,1250','--projection=o',f'--camera={camera}',
            '-D','ic_part="assembly"','-o',str(path),str(ROOT/'cad/feeder-integrated-candidate.scad')],
            cwd=ROOT,capture_output=True,text=True)
        log=result.stdout+result.stderr
        (OUT/(name+'-render.log')).write_text(log)
        if result.returncode or 'WARNING:'in log or 'ERROR:'in log or not path.exists():
            raise RuntimeError(log)
        pictures.append({'file':str(path.relative_to(ROOT)),'sha256':digest(path)})
    stable = before == sources()
    printed = [r for r in rows if r['role']=='printed']
    passed = stable and all(r['passed'] for r in rows) and not info['has_solid_or_unclassified_overlap']
    report = {'status':'ASSEMBLY_INSTANCE_EXPORT_PASS' if passed else 'FAIL_OR_STALE',
              'source_sha256':before,'sources_stable':stable,'parts':rows,
              'printed_instances':len(printed),'printed_families':len({r['family'] for r in printed}),
              'assembly_parity':{'method':'CAD instance list symmetric difference; mesh topology is checked separately',
                                 'passed':not info['has_solid_or_unclassified_overlap'],**info},
              'pictures':pictures,
              'manufacturing_release':False,'scope':'Nominal rest pose of the integrated feeder. Standard metal parts are a visual reference group; PC pipe length is illustrative. Actual spring, hose and Y fitting remain absent.'}
    (OUT / 'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(report['status'],len(rows),'instances',len(printed),'printed')
    return 0 if passed else 1


if __name__=='__main__':
    raise SystemExit(main())
