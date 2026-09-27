"""Route-family service checks at three installation settings, not a motion proof."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import subprocess, json, hashlib, re, sys

B=Path(__file__).resolve().parent
ROOT=B.parents[2]
sys.path.insert(0,str(ROOT/'analysis'))
from feeder_integration import classify
EXE='/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
KINDS=['input-mount-tools','input-mount-bolts','input-stop-tools','input-stop-locknut',
 'output-tools','output-cap-bolts','output-cap-removal','output-washer-removal',
 'output-terminal-removal','spring-tools','follower-tools','guide-tools',
 'outlet-tools','inlet-tools','seam-tools','original-tools']

def hashes():
    paths=set(); todo=[B/'equal-length-route.scad',B.parent/'candidate.scad',ROOT/'cad/cable-service-review.scad',Path(__file__)]
    while todo:
        p=todo.pop().resolve()
        if p in paths: continue
        paths.add(p)
        if p.suffix=='.scad':
            todo.extend(p.parent/n for n in re.findall(r'\b(?:use|include)\s*<([^>]+)>',p.read_text()))
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}

def main():
    out=B/'service'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True)
    source=out/'probe.scad'
    source.write_text(f'''use <{B/'equal-length-route.scad'}>
use <{B.parent/'candidate.scad'}>
use <{ROOT/'cad/cable-service-review.scad'}>
delta=0;kind="input-mount-tools";fault=false;
module updated_service(){{
 if(kind=="input-stop-tools")for(setting=[16,20,22]){{
  sx=cdp_stop_tip(setting);
  cdp_to_cad(){{
   cdp_xcyl(-24,2,-100,sx-33+100,4);
   translate([sx-33,-24,2])rotate([0,90,0])rotate([0,0,30])cylinder(h=1.5,d=2.5/cos(30),$fn=6);
  }}
 }}else csr_service_envelope(kind);
}}
intersection(){{cv_envelope(delta,1,false);union(){{updated_service();
 if(fault)translate(cv_points(delta)[40])sphere(d=10,$fn=24);
}}}}
''')
    before=hashes()
    def run(job):
        delta,kind,fault=job
        name=f'{kind}-d{delta}'+('-positive' if fault else '')
        p=out/(name+'.stl')
        cmd=[EXE,'--hardwarnings','--backend','Manifold','--export-format','asciistl',
             '-D',f'delta={delta}','-D','kind='+json.dumps(kind),'-D','fault='+str(fault).lower(),'-o',str(p),str(source)]
        r=subprocess.run(cmd,capture_output=True,text=True)
        log=r.stdout+r.stderr;(out/(name+'.log')).write_text(log)
        empty='Current top level object is empty' in log and not p.exists()
        ok='ERROR:' not in log and 'WARNING:' not in log and (r.returncode==0 or empty)
        info=classify(p) if p.exists() else {'components':[],'has_solid_or_unclassified_overlap':False}
        passed=ok and info['has_solid_or_unclassified_overlap']==fault
        row=dict(name=name,delta=delta,kind=kind,command=cmd,returncode=r.returncode,empty=empty,
                 execution_ok=ok,expected_overlap=fault,passed=passed,classification=info,
                 file=str(p.relative_to(ROOT)) if p.exists() else None)
        print(name,passed,flush=True)
        return row
    jobs=[(d,k,False) for d in [-2,0,2] for k in KINDS]+[(0,KINDS[0],True)]
    with ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(run,jobs))
    stable=before==hashes()
    report=dict(status='THREE_SETTING_ROUTE_SERVICE_PASS' if stable and all(x['passed'] for x in rows) else 'FAIL_OR_STALE',
                source_sha256=before,sources_stable=stable,results=rows,
                wrapper_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                scope='Full route including ports plus 1 mm conservative clearance versus 16 existing service envelopes at delta -2/0/+2. Input stop tool uses the v2 angle law. Service sweeps retain their original continuous or sampled limits.',
                exclusions=['Input module and bench cover are serviced after disconnecting and parking the sheath',
                            'Actual fittings, SW8/SW10 tools and loose nuts are reviewed separately',
                            'Three installation settings do not prove all intermediate route clearances',
                            'No arbitrary flex shape, real hand/tool, or physical retention claim'],
                manufacturing_release=False,physical_acceptance=False)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    (B/'service-latest.json').write_text(json.dumps(dict(report=str((out/'report.json').relative_to(ROOT)),status=report['status']),indent=2)+'\n')
    print(report['status'],out,flush=True)
    return 0 if report['status'].endswith('_PASS') else 1

if __name__=='__main__':raise SystemExit(main())
