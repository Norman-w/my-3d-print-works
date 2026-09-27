#!/usr/bin/env python3
"""Export and check the integrated feeder; offline, no physical acceptance."""
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import struct
import subprocess
from feeder_integration import classify
from exact_mesh import exact_area_and_links

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/launcher-final'
CAD = ROOT/'cad/launcher-final-assembly.scad'
EXE = '/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
SPEC = importlib.util.spec_from_file_location('mesh', '/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py')
MESH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MESH)


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def sources():
    paths = {Path(__file__).resolve(), ROOT/'analysis/feeder_integration.py', ROOT/'analysis/exact_mesh.py'}
    pending = [CAD]
    while pending:
        path = pending.pop().resolve()
        if path in paths:continue
        paths.add(path)
        pending.extend(path.parent/dep for dep in re.findall(r'\b(?:use|include)\s*<([^>]+)>',path.read_text()))
    return {str(path.relative_to(ROOT)):sha(path) for path in sorted(paths)}


def run(name, defs, backend='Manifold', suffix='.stl', extra=()):
    path = OUT/(name+suffix)
    path.unlink(missing_ok=True)
    cmd = [EXE,'--hardwarnings','--backend',backend]
    if suffix=='.stl':cmd += ['--export-format','asciistl']
    for k,v in defs.items():cmd += ['-D',f'{k}={json.dumps(v)}']
    cmd += list(extra)+['-o',str(path),str(CAD)]
    proc = subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
    log = proc.stdout+proc.stderr
    (OUT/(name+'.log')).write_text(log)
    empty = 'Current top level object is empty' in log and not path.exists()
    if ('WARNING:' in log or 'ERROR:' in log
            or (proc.returncode and not(suffix=='.stl' and empty))):
        raise RuntimeError(f'{name}: {log}')
    return path,cmd





def reimport(path):
    source=OUT/(path.stem+'-reimport.scad');target=OUT/(path.stem+'-reimport.stl')
    source.write_text('intersection(){import('+json.dumps(path.name)+');cube([10000,10000,10000],center=true);}\n')
    target.unlink(missing_ok=True)
    cmd=[EXE,'--hardwarnings','--backend','CGAL','--export-format','asciistl','-o',str(target),str(source)]
    p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True);log=p.stdout+p.stderr
    (OUT/(path.stem+'-reimport.log')).write_text(log)
    passed=p.returncode==0 and target.exists() and 'ERROR:' not in log and 'WARNING:' not in log
    return {'passed':passed,'returncode':p.returncode,'command':cmd}


def inventory():
    rows=[]
    def add(part,name,side=1,rear=False,role='printed',family=None):
        suffix=(('-right'if side>0 else'-left')+('-rear'if rear else'-front'))if part in ('finger','pin-block','y-gib','y-keeper') else (('-right'if side>0 else'-left')if part in ('capture','pipe-clamp','y-cap','frame-y-gib')else'')
        rows.append({'id':part+suffix,'name':name,'role':role,'family':family or part,
                     'definitions':{'la_part':part,'la_side':side,'la_rear':rear,'la_t':0}})
    for p,n in [('positive-half','送料右半壳'),('negative-half','送料左半壳'),('beam-grip','背梁握把'),('liner','出口内衬'),('right-support','右导向支座'),('left-support','左导向及弹簧座'),('x-gib','X调隙压条'),('x-cover','X调节外盖'),('frame','凸轮架与指环'),('fixed-spacer','弹簧固定端间隔套'),('moving-spacer','弹簧运动端间隔套')]:add(p,n)
    for s,label in [(1,'右'),(-1,'左')]:
        for p,n in [('capture','出口捕获座'),('pipe-clamp','PC管夹'),('y-cap','公共架Y调节盖'),('frame-y-gib','公共架Y压条')]:add(p,label+n,side=s,family=p if p in ('y-cap','frame-y-gib') else f'{p}-{s}')
        for rear,end in [(False,'前'),(True,'后')]:
            for p,n in [('y-gib','Y调隙压条'),('y-keeper','Y外盖'),('finger','V定位挡指'),('pin-block','肩销压块')]:add(p,label+end+n,side=s,rear=rear)
    for p,n in [('inlet-rear','入口后夹与背梁锚固'),('inlet-front','入口前夹'),('inlet-backplate','入口后压板')]:add(p,n)
    add('hardware','全部金属五金参考',role='purchased')
    add('pc-reference','PC硬管参考',role='purchased')
    add('spring-reference','回位弹簧参考',role='purchased')
    add('hose-reference','软管名义包络参考',role='purchased')
    add('liner-reference','3mm柔衬名义包络参考',role='purchased')
    return rows


def export(row):
    selector=row['definitions']['la_part']
    backend='CGAL' if selector in ('right-support','left-support','finger','pin-block','frame','y-cap','frame-y-gib','y-keeper','inlet-rear','inlet-front','inlet-backplate') else 'Manifold'
    path,cmd=run(row['id'],row['definitions'],backend)
    mesh=MESH.inspect(path,1e-6);topology=exact_area_and_links(path)
    components=len(classify(path)['components'])
    imported=reimport(path)if row['role']=='printed'else{'passed':None,'scope':'Purchased multi-body display; no printable-solid claim'}
    passed=(mesh['watertightByEdgeTopology'] and components==1 and not topology['exact_zero_area_face_indices']
            and not topology['non_ring_vertex_links'] and imported['passed'])if row['role']=='printed'else mesh['triangleCount']>0
    print('export',row['id'],passed,flush=True)
    return {**row,'file':str(path.relative_to(ROOT)),'sha256':sha(path),'command':cmd,'mesh':mesh,
            'exact_area_and_vertex_links':topology,'components':components,'boolean_reimport':imported,'passed':passed}


def probe(job):
    name,defs,expected=job;path,cmd=run(name,{'la_part':'probe',**defs})
    info=classify(path)if path.exists()else{'components':[],'has_solid_or_unclassified_overlap':False}
    passed=info['has_solid_or_unclassified_overlap']==expected
    print('probe',name,passed,flush=True)
    return {'name':name,'definitions':defs,'command':cmd,'expected_overlap':expected,'passed':passed,**info}


def main():
    OUT.mkdir(parents=True,exist_ok=True);before=sources()
    items=inventory()
    (OUT/'inventory.json').write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n')
    with ThreadPoolExecutor(max_workers=2)as pool:parts=list(pool.map(export,items))
    jobs=[]
    for t in [0,.2,.4,.5,.6,.8,1]:
        for kind in ['motion','frame-vs-followers','spring-neighbors','spring-hardware','pin-tools','spring-tools']:
            jobs.append((f'{kind}-{t}',{'la_probe':kind,'la_t':t},False))
    jobs += [(k,{'la_probe':k},False)for k in ['spring-sweep','spring-relative-sweep','spring-fastener-fit','v-hardware-fit','all-fixed-hardware-fit']]
    jobs.append(('misplacement-control',{'la_probe':'fault-control','la_fault':-10},True))
    with ThreadPoolExecutor(max_workers=2)as pool:cases=list(pool.map(probe,jobs))
    images=[]
    for name,camera in [('assembly','12,0,-10,64,0,28,1000'),('front','12,-4,-10,90,0,0,1000'),('top','0,0,-4,0,0,0,850')]:
        path,_=run(name,{'la_part':'assembly'},suffix='.png',extra=['--render','--imgsize=1500,1250','--projection=o',f'--camera={camera}'])
        images.append({'file':str(path.relative_to(ROOT)),'sha256':sha(path)})
    stable=before==sources();passed=stable and all(r['passed']for r in parts+cases)
    report={'status':'INTEGRATED_FEEDER_DIGITAL_CHECKS_PASS'if passed else'FAIL_OR_STALE',
            'source_sha256':before,'sources_stable':stable,'parts':parts,'cases':cases,'pictures':images,
            'printed_instances':sum(r['role']=='printed'for r in parts),'manufacturing_release':False,
            'scope':'Integrated V followers, public-frame X/Y guides, spring endpoints, cleared keepers and inlet retention. Nominal geometry and exported-mesh checks; liner/hose envelope, total dimensional error, operating loads and actual machine behaviour remain separate.'}
    (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(report['status'],flush=True)
    return 0 if passed else 1


if __name__=='__main__':raise SystemExit(main())
