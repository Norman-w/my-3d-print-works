#!/usr/bin/env python3
"""Isolated -3mm input/+3mm side-run route. No production edits or assembly release."""
from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
import ast,hashlib,json,math,re,subprocess

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[2]
EXE='/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
add=lambda a,b:[x+y for x,y in zip(a,b)]
sub=lambda a,b:[x-y for x,y in zip(a,b)]
mul=lambda a,k:[x*k for x in a]
dot=lambda a,b:sum(x*y for x,y in zip(a,b))
norm=lambda a:math.sqrt(dot(a,a))
unit=lambda a:mul(a,1/norm(a))

def hashes():
    paths={Path(__file__).resolve(),OUT/'source.patch'}
    todo=[OUT/'candidate-contract.scad',OUT/'original-contract.scad']
    while todo:
        p=todo.pop().resolve()
        if p in paths:continue
        paths.add(p)
        todo += [(p.parent/n).resolve() for n in re.findall(r'\b(?:use|include)\s*<([^>]+)>',p.read_text())]
    return {str(p.relative_to(ROOT)):sha(p) for p in sorted(paths)}

def decode(v):
    if isinstance(v,list):
        if len(v)==4 and v[0]=='__q9':return v[1]+v[2]/1e6+v[3]/1e9
        return [decode(x) for x in v]
    return v

def parse(raw,label):
    s=raw.split('ECHO: "'+label+'", ',1)[1].splitlines()[0]
    for a,b in [('undef','None'),('true','True'),('false','False')]:s=re.sub(r'\b'+a+r'\b',b,s)
    return decode(ast.literal_eval(s))

def difference(a,b):
    if isinstance(a,list):return max([difference(x,y) for x,y in zip(a,b)]+[0]) if len(a)==len(b) else math.inf
    if isinstance(a,(int,float)) and not isinstance(a,bool):return abs(a-b)
    return 0 if a==b else math.inf

def geometry(side=198,origin_y=-85,delta=0,shift=0):
    q=[-58.,35.5,111.];d=[math.sqrt(.5),0.,-math.sqrt(.5)]
    p=[75+123*math.sqrt(.5),origin_y+2,5-3*math.sqrt(.5)]
    a=add(p,mul(d,100));b=add(a,[0,side,0]);v0=[p,a,b,[q[0],q[1],400.],q]
    v=[sub(p,mul(d,delta)),add(a,mul(d,shift)),b,v0[3],q]
    arcs=[]
    for i in range(1,4):
        w=v0 if i==3 else v
        u1=unit(sub(w[i],w[i-1]));u2=unit(sub(w[i+1],w[i]))
        c=max(-1,min(1,dot(u1,u2)));theta=math.acos(c);trim=75*math.tan(theta/2)
        n=unit(sub(u2,mul(u1,c)));A=sub(w[i],mul(u1,trim));B=add(w[i],mul(u2,trim));C=add(A,mul(n,75))
        arcs.append([A,B,C,mul(n,-1),u1,math.degrees(theta),trim])
    lines=[]
    for i in range(4):
        A=v[0] if i==0 else arcs[i-1][1];B=v[4] if i==3 else arcs[i][0]
        lines.append([A,B,norm(sub(B,A)),dot(sub(B,A),unit(sub(v[i+1],v[i])))])
    return {'virtual_vertices':v,'arcs':arcs,'lines':lines,
      'length':sum(x[2] for x in lines)+75*sum(math.radians(a[5]) for a in arcs)}

def solve(side,y,delta):
    target=geometry(side,y)['length'];lo=-2.;hi=2.
    for _ in range(60):
        m=(lo+hi)/2
        if geometry(side,y,delta,m)['length']<target:lo=m
        else:hi=m
    return (lo+hi)/2

def continuous_bounds():
    g=geometry();v=g['virtual_vertices'];c=198.;S=2.;R=75.
    d=unit(sub(v[1],v[0]));w=unit(sub(v[3],v[2]));dw=dot(d,w);ew=w[1]
    # For s in [-S,S], h=sqrt(c²+s²), incoming middle direction=(c*e-s*d)/h.
    # Absolute cosine bounds enclose both turning angles and all derivatives.
    C1=S/c;C2=abs(ew)+S*abs(dw)/c
    T1=(1+C1)/(1-C1);T2=(1+C2)/(1-C2)
    theta1_prime=1/c
    theta2_prime=(abs(dw)+abs(ew)*S/c)/(c*math.sqrt(1-C2*C2))
    derivative_lower=1-S/c-R*(T1*theta1_prime+T2*theta2_prime)
    max_trims=[R*math.sqrt(T1),R*math.sqrt(T2),g['arcs'][2][6]]
    edge_min=[100-2*S,c,norm(sub(v[3],v[2])),norm(sub(v[4],v[3]))]
    remains=[edge_min[i]-(max_trims[i-1] if i else 0)-(max_trims[i] if i<3 else 0) for i in range(4)]
    base=g['length']
    return {'s_interval_mm':[-S,S],'delta_interval_mm':[-2,2],
      'derivative_formula':'dL/ds=1+s/h-R*(tan(theta1/2)^2*theta1_prime + tan(theta2/2)^2*theta2_prime)',
      'derivative_lower_bound':derivative_lower,'turn_cosine_absolute_upper_bounds':[C1,C2],
      'bracket_at_s_minus_2_worst_delta_plus_2_mm':geometry(delta=2,shift=-2)['length']-base,
      'bracket_at_s_plus_2_worst_delta_minus_2_mm':geometry(delta=-2,shift=2)['length']-base,
      'straight_length_lower_bounds_mm':remains,
      'scope':'Real-arithmetic interval bound with a1e-8 acceptance guard; not directed-rounding interval arithmetic. Length is affine in delta with derivative1. No physical equilibrium/route retention claimed.'}

def main():
    run=OUT/'runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');run.mkdir(parents=True)
    before=hashes();checks=[]
    def check(name,ok):checks.append({'name':name,'passed':bool(ok)});assert ok,name
    def native(job):
        mode,delta,extra=job;name=mode+'-'+str(delta).replace('-','m').replace('.','_')+('negative-'+next(iter(extra)) if extra else '')
        target=run/(name+'.echo');defs={'ci_delta':delta,**extra}
        cmd=[EXE,'--hardwarnings']
        for k,v in defs.items():cmd+=['-D',k+'='+json.dumps(v)]
        cmd+=['-o',str(target),str(OUT/(mode+'-contract.scad'))]
        p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True);log=p.stdout+p.stderr
        (run/(name+'.log')).write_text(log);raw=target.read_text() if target.exists() else ''
        valid=p.returncode==0 and 'ERROR:' not in raw+log and 'WARNING:' not in raw+log
        r={'name':name,'mode':mode,'delta':delta,'definitions':defs,'command':cmd,'returncode':p.returncode,
          'valid':valid,'echo_file':str(target.relative_to(ROOT)) if target.exists() else None,
          'echo_sha256':sha(target) if target.exists() else None,'log_sha256':sha(run/(name+'.log'))}
        if valid:r.update(contract=dict(parse(raw,'CONTRACT_Q9')),input_contract=dict(parse(raw,'CI_Q9')),local_motion=parse(raw,'CI_MOTION_Q9'))
        else:r['error_excerpt']=(raw+log)[:1500]
        return r
    jobs=[('original',d,{}) for d in [-2,0,2]]+[('candidate',d,{}) for d in [-2,-1,0,1,2]]
    with ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(native,jobs))
    check('native_contracts_all_valid',all(r['valid'] for r in rows))
    original={r['delta']:r for r in rows if r['mode']=='original'};candidate={r['delta']:r for r in rows if r['mode']=='candidate'}
    old0=original[0]['contract'];new0=candidate[0]['contract'];comparisons=[]
    for delta,row in candidate.items():
        c=row['contract'];g=geometry(delta=delta,shift=solve(198,-85,delta))
        errors={k:difference(c[k],g[k]) for k in ['virtual_vertices','arcs','lines']}
        errors['length']=abs(c['outside_port_route_length']-g['length'])
        errors['equal_length']=abs(g['length']-geometry()['length'])
        check('independent_numeric_'+str(delta),max(errors.values())<2e-7)
        check('fixed_third_arc_'+str(delta),difference(c['arcs'][2],old0['arcs'][2])<2e-9)
        check('fixed_late_vertices_'+str(delta),difference(c['virtual_vertices'][2:],old0['virtual_vertices'][2:])<2e-9)
        check('fixed_output_'+str(delta),c['output_port']==old0['output_port'] and difference(c['lines'][3],old0['lines'][3])<2e-9)
        check('input_shift_and_tangent_'+str(delta),difference(c['input_port'],sub(old0['input_port'],[0,3,0]) if delta==0 else geometry(delta=delta)['virtual_vertices'][0])<2e-8 and c['input_outward_tangent']==old0['input_outward_tangent'])
        comparisons.append({'delta':delta,'first_corner_shift_mm':c['first_corner_shift'],'errors_mm_or_deg':errors})
    for delta in [-2,0,2]:
        old=original[delta];new=candidate[delta]
        check('local_v2_motion_unchanged_'+str(delta),old['local_motion']==new['local_motion'])
        ci_old={k:v for k,v in old['input_contract'].items() if k!='origin'};ci_new={k:v for k,v in new['input_contract'].items() if k!='origin'}
        check('input_contract_only_origin_changed_'+str(delta),ci_old==ci_new)
        check('nominal_family_length_plus3_'+str(delta),abs(new['contract']['outside_port_route_length']-old['contract']['outside_port_route_length']-3)<2e-9)
    b=continuous_bounds()
    check('continuous_unique_root',b['derivative_lower_bound']>1e-8)
    check('continuous_root_bracket',b['bracket_at_s_minus_2_worst_delta_plus_2_mm']<-1e-8 and b['bracket_at_s_plus_2_worst_delta_minus_2_mm']>1e-8)
    check('continuous_no_fillets_overlap',min(b['straight_length_lower_bounds_mm'])>1e-8)
    check('continuous_port_straights_over15',min(b['straight_length_lower_bounds_mm'][::3])>15+1e-8)
    negatives=[native(('candidate',0,{'cr_R':64})),native(('candidate',2.01,{})),native(('candidate',0,{'cr_side_run':195})),native(('candidate',0,{'ci_origin':[75,-82,5]}))]
    for n in negatives:check('negative_control_'+n['name'],not n['valid'] and 'ERROR: Assertion' in n['error_excerpt'])
    check('formal_sources_unchanged',before==hashes())
    report={'status':'ISOLATED_OFFSET_ROUTE_CONTRACT_AND_FAMILY_PASS','source_sha256':before,'sources_stable':True,
      'checks':checks,'native_runs':rows,'negative_controls':negatives,
      'comparison':{'original_origin':original[0]['input_contract']['origin'],'candidate_origin':candidate[0]['input_contract']['origin'],
        'old_side_run_mm':195,'new_side_run_mm':198,'input_shift_CAD_mm':[0,-3,0],
        'original_outside_length_mm':old0['outside_port_route_length'],'candidate_outside_length_mm':new0['outside_port_route_length'],
        'outside_length_change_mm':new0['outside_port_route_length']-old0['outside_port_route_length'],
        'unchanged':['local fixed-guide direct-pull v2 motion','virtual vertices2,3,4','third arc','output port and final straight','R75, supplier minimumR65','line/arc construction and equal-length solve'],
        'per_delta':comparisons},'continuous_family_bounds':b,
      'scope':'Radius, positive trimmed lines, tangency, fixed downstream interface and constant length for ideal line-and-circle route delta[-2,2]. Original/new native source contracts plus independent numeric reconstruction. No host collision rerun, no retention equilibrium, no cut-length certification.',
      'manufactured_housing_cut_length_mm':None,'manufacturing_release':False,'physical_acceptance':False,'adopted':False}
    (run/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (OUT/'latest.json').write_text(json.dumps({'directory':str(run.relative_to(ROOT)),'report_sha256':sha(run/'report.json')},indent=2)+'\n')
    print(json.dumps({'run':str(run.relative_to(ROOT)),'checks':len(checks),'length_change':report['comparison']['outside_length_change_mm'],'bounds':b,'sha256':sha(run/'report.json')},indent=2))

if __name__=='__main__':main()
