#!/usr/bin/env python3
"""Four current-source rigid service probes. No production CAD modification."""
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,re,subprocess,sys

ROOT=Path(__file__).resolve().parents[2]
BASE=Path(__file__).resolve().parent
EXE='/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
sys.path.insert(0,str(ROOT/'analysis'))
from feeder_integration import classify

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rel(p):return str(Path(p).resolve().relative_to(ROOT))
def dependencies(initial):
    seen=set();todo=list(initial)
    while todo:
        p=todo.pop().resolve()
        if p in seen:continue
        seen.add(p)
        if p.suffix=='.scad':
            todo.extend(p.parent/n for n in re.findall(r'\b(?:use|include)\s*<([^>]+)>',p.read_text()))
    return {rel(p):sha(p)for p in sorted(seen)}

def main():
    out=BASE/'runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True)
    inventory=json.loads((ROOT/'docs/cable-assembly-inventory.json').read_text())
    for p,h in inventory['source_sha256'].items():assert sha(ROOT/p)==h,p
    feeder=[p for p in inventory['parts']if p['group']=='feeder']
    route_ids={'feeder/cable-route-base','feeder/cable-route-cap','feeder/cable-route-lower','feeder/cable-route-hardware'}
    flexible={'feeder/cable-housing','feeder/cable-core-route','feeder/cable-core-input','feeder/cable-core-output'}
    rigid=[p for p in feeder if p['id']not in route_ids|flexible]
    def call(p):
        d=p['definitions'];part=d['cse_part']
        if part=='legacy':return 'la_item('+','.join(json.dumps(v)for v in [d['cse_legacy'],d.get('cse_side',1),d.get('cse_rear',False),0])+');'
        if part=='follower-hardware':return 'cse_follower_hardware('+','.join(json.dumps(v)for v in [d['cse_side'],d['cse_rear'],0])+');'
        return 'cse_item('+json.dumps(part)+',0);'
    scene=out/'scene-obstacles.scad'
    scene.write_text('include <'+str(ROOT/'cad/parameters.scad')+'>\nuse <'+str(ROOT/'cad/cable-scene-export.scad')+'>\nuse <'+str(ROOT/'cad/launcher-final-assembly.scad')+'>\nuse <'+str(ROOT/'cad/feeder-return-spring.scad')+'>\n'+
        'module rs_current_rigid(){\n'+''.join('  // '+p['id']+'\n  '+call(p)+'\n'for p in rigid)+'}\n'+
        'module rs_nominal_flexible(){\n'+''.join('  // '+p['id']+'\n  '+call(p)+'\n'for p in feeder if p['id']in flexible)+'}\n'+
        'module rs_original_feeder_only(){la_fixed();la_moving(0);rs_spring(0,true);la_item("liner-reference");}\n')
    probe=out/'probe.scad'
    probe.write_text('include <'+str(ROOT/'cad/parameters.scad')+'>\nuse <'+str(scene)+'>\nuse <'+str(ROOT/'cad/cable-route-retention.scad')+'>\n'+r'''
kind="cap-current";
function rs_get(k)=crr_contract()[search([k],crr_contract())[0]][1];
module rs_mount_hardware(){for(p=rs_get("clamp_bolt_centres")){
    crr_washer(p,99.3);crr_bolt(p,99.8,25);crr_nut(p,78.9);
}}
module rs_cap_nuts(){crr_basis()for(p=crr_bolt_points())crr_nut(p,-6.4);}
module rs_fixed_retainer(){crr_base();rs_cap_nuts();
    if(kind=="cap-current"){crr_lower();rs_mount_hardware();}
}
module rs_external(){
    if(kind=="lower-baseline")rs_original_feeder_only();
    else rs_current_rigid();
    if(kind=="cap-current")rs_nominal_flexible();
}
if(kind=="contract")echo("RS_CONTRACT",crr_contract(),"N",crr_N(),"C",crr_C());
else intersection(){
    if(kind=="cap-current")crr_cap_sweep(50);
    else if(kind=="lower-wrong-straight-down")crr_lower_sweep(70);
    else crr_lower_service_sweep();
    union(){rs_fixed_retainer();rs_external();}
}
''')
    watched=dependencies([probe,scene,Path(__file__),ROOT/'docs/cable-assembly-inventory.json',ROOT/'analysis/feeder_integration.py'])
    def run(kind,extension='stl'):
        target=out/(kind+'.'+extension);assert not target.exists()
        cmd=[EXE,'--hardwarnings','--backend','Manifold','-D','kind='+json.dumps(kind)]
        if extension=='stl':cmd+=['--export-format','asciistl']
        cmd+=['-o',str(target),str(probe)]
        started=datetime.now(timezone.utc).isoformat();r=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
        log=r.stdout+r.stderr;(out/(kind+'.log')).write_text(log)
        empty='Current top level object is empty' in log and not target.exists()
        execution=not re.search(r'(?m)(ERROR|WARNING):',log)and(r.returncode==0 or empty)
        row={'case':kind,'started_utc':started,'command':cmd,'returncode':r.returncode,'native_empty_message':empty,'execution_ok':bool(execution),'log':rel(out/(kind+'.log')),'log_sha256':sha(out/(kind+'.log')),'artifact':rel(target)if target.exists()else None,'artifact_sha256':sha(target)if target.exists()else None}
        if extension=='stl'and target.exists():row['raw_mesh_classification']=classify(target)
        print(kind,'execution_ok',execution,'empty',empty,flush=True)
        return row
    contract=run('contract','echo')
    if not contract['execution_ok']:raise RuntimeError('Contract/syntax failure')
    jobs=['cap-current','lower-current','lower-wrong-straight-down','lower-baseline']
    with ThreadPoolExecutor(max_workers=2)as pool:rows=list(pool.map(run,jobs))
    old_path=ROOT/'output/cable-retention-service/20260927T070337333817Z/report.json';old=json.loads(old_path.read_text())
    mismatch=[{'source':p,'old_sha256':h,'current_sha256':sha(ROOT/p)}for p,h in old['source_sha256'].items()if sha(ROOT/p)!=h]
    stable=all(sha(ROOT/p)==h for p,h in watched.items())
    result={'status':'NATIVE_PROBES_COMPLETE_CLASSIFICATION_REQUIRED','created_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':watched,'sources_stable':stable,'original_source_export_inventory':{'file':'docs/cable-assembly-inventory.json','sha256':sha(ROOT/'docs/cable-assembly-inventory.json'),'feeder_group_instances':len(feeder),'current_rigid_external_instances':[p['id']for p in rigid],'nominal_flexible_instances':sorted(flexible),'guide_own_instances_handled_separately':sorted(route_ids)},'contract':contract,'cases':rows,'old_report':{'path':rel(old_path),'sha256':sha(old_path),'scope':old['scope'],'unverified':old['unverified'],'changed_sources':mismatch},'scope':'Released t=0 only. Current feeder/cable inventory group, not unknown blower/Y fitting or illustrative spin-head world placement. Continuous rigid cap/lower sweeps only; no whole actuation repeat.','preconditions':{'cap-current':'All six M3x16 cap screws and cap washers removed; main mount four M3x25 remain installed; nuts retained at their modeled base positions; nominal fixed cable envelope retained for geometric comparison only.','lower-current':'Cap/six screws/washers and flexible cable released/removed. All four M3x25 clamp screws and their top washers removed. Base AND lower externally supported; lower nuts removed or held within filled lower sweep. No live actuation.','lower-wrong-straight-down':'Same removals and support as lower-current, but intentionally incorrect -Z70 path.','lower-baseline':'Same lower sweep against current original-feeder-only la_fixed/la_moving set plus retainer base; this is a reduced-set diagnostic, NOT a preserved historical full assembly.'},'manufacturing_release':False,'physical_acceptance':False,'sent_to_printer':False}
    (out/'report.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print('REPORT',out/'report.json',flush=True)
if __name__=='__main__':main()
