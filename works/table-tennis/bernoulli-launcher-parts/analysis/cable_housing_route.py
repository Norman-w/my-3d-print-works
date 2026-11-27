#!/usr/bin/env python3
"""Check the nominal housing route against source CAD; never a cut list."""
from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
import ast,hashlib,json,math,re,subprocess
from feeder_integration import classify

ROOT=Path(__file__).resolve().parents[1]
CAD=ROOT/'cad/cable-housing-route.scad'
SYSTEM=ROOT/'cad/cable-trigger-system.scad'
EXE='/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def hashes():
    paths={Path(__file__).resolve(),ROOT/'analysis/feeder_integration.py'}
    todo=[CAD,SYSTEM]
    while todo:
        p=todo.pop().resolve()
        if p in paths:continue
        paths.add(p)
        todo.extend(p.parent/name for name in re.findall(r'\b(?:use|include)\s*<([^>]+)>',p.read_text()))
    return {str(p.relative_to(ROOT)):sha(p) for p in sorted(paths)}
def sub(a,b):return [x-y for x,y in zip(a,b)]
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def norm(a):return math.sqrt(dot(a,a))
def unit(a):return [x/norm(a) for x in a]
def angle(a,b):return math.acos(max(-1,min(1,dot(unit(a),unit(b)))))

def run(out,name,source,defs,ext='stl'):
    target=out/(name+'.'+ext)
    cmd=[EXE,'--hardwarnings','--backend','Manifold']
    if ext=='stl':cmd+=['--export-format','asciistl']
    for k,v in defs.items():cmd+=['-D',k+'='+json.dumps(v)]
    cmd+=['-o',str(target),str(source)]
    result=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
    log=result.stdout+result.stderr
    (out/(name+'.log')).write_text(log)
    empty='Current top level object is empty' in log and not target.exists()
    ok=not ('ERROR:' in log or 'WARNING:' in log) and (result.returncode==0 or empty) and (target.exists() or empty)
    return {'name':name,'command':cmd,'returncode':result.returncode,'execution_ok':ok,
        'empty':empty,'file':str(target.relative_to(ROOT)) if target.exists() else None}

def main():
    out=ROOT/'output/cable-housing-route'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out.mkdir(parents=True)
    before=hashes()
    meta=run(out,'contract',CAD,{'cr_part':'contract'},'echo')
    raw=(ROOT/meta['file']).read_text()
    if 'ERROR:' in raw or 'WARNING:' in raw:raise RuntimeError(raw)
    text=raw.split('ECHO: "CR_CONTRACT", ',1)[1].strip()
    text=re.sub(r'\bundef\b','None',text)
    text=re.sub(r'\bfalse\b','False',text)
    text=re.sub(r'\btrue\b','True',text)
    c=dict(ast.literal_eval(text))
    v=c['virtual_vertices'];R=c['arc_radius']
    turns=[angle(sub(v[i],v[i-1]),sub(v[i+1],v[i])) for i in range(1,len(v)-1)]
    trims=[R*math.tan(a/2) for a in turns]
    edge_lengths=[norm(sub(b,a)) for a,b in zip(v,v[1:])]
    remaining=[L-(trims[i-1] if i else 0)-(trims[i] if i<len(trims) else 0)
               for i,L in enumerate(edge_lengths)]
    L=sum(remaining)+R*sum(turns)
    checks={'minimum_radius':R>=c['minimum_supplier_radius'],
        'nonoverlapping_tangent_fillets':min(remaining)>0,
        'port_straights':min(remaining[0],remaining[-1])>c['port_clearance_test_exclusion'],
        'length_matches_scad_to_echo_precision':abs(L-c['outside_port_route_length'])<.02,
        'input_tangent':norm(sub(unit(sub(v[1],v[0])),c['input_outward_tangent']))<2e-5,
        'output_tangent':norm(sub(unit(sub(v[-1],v[-2])),c['output_arrival_tangent']))<2e-5}
    wrapper=out/'probes.scad'
    wrapper.write_text(f'''use <{SYSTEM}>\nuse <{CAD}>\nuse <{ROOT/'cad/launcher-final-assembly.scad'}>\nuse <{ROOT/'cad/cable-trigger-input.scad'}>\nuse <{ROOT/'cad/cable-output-interface.scad'}>\nuse <{ROOT/'cad/feeder-return-spring.scad'}>\nuse <{ROOT/'cad/outlet-retention.scad'}>\nuse <{ROOT/'cad/inlet-retention-final.scad'}>\nt=0;fault=false;nominal=false;\nintersection(){{
    // Full-length OD envelope excludes only the two intended mating ferrules
    // and the cable's own core. Both end ferrules remain in the 1 mm interior
    // clearance test. End seating/fit is NOT certified by this route test.
    if(nominal)cr_sweep(cr_points(),
        (cr_get(ci_spec(),"housing_od")+2*cr_sagitta())/pow(cos(180/24),2));
    else cr_clearance();
    union(){{ct_fixed_printed();ct_moving_printed(t);ct_original_fixed_hardware();
      la_moving_hardware(t);or_pipe();ir_hose_reference();
      if(nominal)difference(){{ci_fixed_hardware();ci_ferrule();}}
      else ci_fixed_hardware();
      ci_moving_hardware(20*t);
      co_terminal_hardware(t);co_adjuster_hardware();
      if(!nominal)co_ferrule_reference();
      rs_spring(t,true);
      if(fault)translate(cr_points()[floor(len(cr_points())/2)])sphere(d=10,$fn=24);
    }}
}}\n''')
    def probe(job):
        t,nominal,fault=job
        name=('nominal' if nominal else 'clearance')+f'-{t:.2f}'+('-fault' if fault else '')
        row=run(out,name,wrapper,{'t':t,'nominal':nominal,'fault':fault})
        info=classify(ROOT/row['file']) if row['file'] else {'has_solid_or_unclassified_overlap':False,'components':[]}
        row.update(classification=info,expected_overlap=fault,
                   passed=row['execution_ok'] and info['has_solid_or_unclassified_overlap']==fault)
        print(name,row['passed'],flush=True)
        return row
    # Static sheath route, moving assembly sampled every 1 mm of its 20 mm travel.
    jobs=[(i/20,False,False) for i in range(21)]+[(t,True,False) for t in [0,.5,1]]+[(0,False,True)]
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(probe,jobs))
    negative=run(out,'radius-negative-control',CAD,{'cr_part':'housing','cr_R':40})
    neg_log=(out/'radius-negative-control.log').read_text()
    checks['radius_negative_control']='Below selected housing supplier minimum bend radius' in neg_log and not negative['execution_ok']
    stable=before==hashes()
    passed=stable and all(checks.values()) and all(r['passed'] for r in results)
    report={'status':'NOMINAL_ROUTE_LOCAL_GEOMETRY_PASS' if passed else 'FAIL_OR_STALE',
      'sources_stable':stable,'source_sha256':before,'contract':c,
      'analytic_checks':checks,'independent_length_mm':L,
      'cumulative_absolute_turn_degrees':math.degrees(sum(turns)),
      'results':results,'radius_negative_control':negative,
      'scope':'Radius/tangency for ideal line-and-circle route; 21 nominal poses against current local CAD. '
              '1 mm clearance capsule excludes 15 mm at each mating port. Full-length conservative OD '
              'capsule excludes only the mating ferrules and own core; it does not certify seating or mating fit.',
      'unverified':['intermediate physical route supports','real complete blower/tee/hand/backpack envelopes',
        'housing cut length/end seating','printed or cable variation','friction and loaded return'],
      'manufacturing_release':False,'physical_acceptance':False}
    target=out/'report.json';target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(report['status'],target,flush=True)
    return 0 if passed else 1
if __name__=='__main__':raise SystemExit(main())
