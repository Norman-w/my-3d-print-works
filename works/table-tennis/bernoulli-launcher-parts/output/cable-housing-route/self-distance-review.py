#!/usr/bin/env python3
"""Read-only line/arc non-neighbour clearance evidence. No CAD execution."""
from pathlib import Path
from fractions import Fraction
import ast,hashlib,json,math,re,sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sub=lambda a,b:[x-y for x,y in zip(a,b)]
add=lambda a,b:[x+y for x,y in zip(a,b)]
mul=lambda a,k:[x*k for x in a]
dot=lambda a,b:sum(x*y for x,y in zip(a,b))
norm=lambda a:math.sqrt(dot(a,a))
clamp=lambda x:max(0.,min(1.,x))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def segment_distance(p0,p1,q0,q1):
    """Minimum convex quadratic on [0,1]^2: interior + all four edges."""
    u,v,w=sub(p1,p0),sub(q1,q0),sub(p0,q0)
    a,b,c,d,e=dot(u,u),dot(u,v),dot(v,v),dot(u,w),dot(v,w)
    assert a>0 and c>0
    candidates=[(0,clamp(e/c)),(1,clamp((e+b)/c)),
                (clamp(-d/a),0),(clamp((b-d)/a),1)]
    det=a*c-b*b
    if det>1e-12*a*c:
        s,t=(b*e-c*d)/det,(a*e-b*d)/det
        if 0<=s<=1 and 0<=t<=1:candidates.append((s,t))
    else:
        # Parallel-looking floating arithmetic must not erase an interior
        # crossing. Solve the small determinant using exact input rationals.
        P,Q,U,V=[tuple(Fraction(str(x)) for x in p) for p in (p0,p1,q0,q1)]
        eu,ev,ew=sub(Q,P),sub(V,U),sub(P,U)
        ea,eb,ec,ed,ee=dot(eu,eu),dot(eu,ev),dot(ev,ev),dot(eu,ew),dot(ev,ew)
        exact_det=ea*ec-eb*eb
        if exact_det:
            s,t=(eb*ee-ec*ed)/exact_det,(ea*ee-eb*ed)/exact_det
            if 0<=s<=1 and 0<=t<=1:candidates.append((float(s),float(t)))
    return min(norm(sub(add(p0,mul(u,s)),add(q0,mul(v,t)))) for s,t in candidates)

def evaluate(contract,echo_error_mm=.01,each_side_margin_mm=1):
    R=contract['arc_radius'];D=contract['housing_od'];pieces=[]
    local_checks={'one_plane_circle_arcs_under_180':all(0<a[5]<180 for a in contract['arcs']),
                  'arc_radius_exceeds_expanded_tube':R>D/2+each_side_margin_mm,
                  'positive_straights':all(x[3]>0 for x in contract['lines']),
                  'arc_bases_orthonormal_to_echo_precision':True,
                  'arc_endpoints_and_tangencies_match_lines':True}
    for i,line in enumerate(contract['lines']):
        pieces.append(dict(name=f'line-{i}',points=line[:2],chord_error=0))
        if i<len(contract['arcs']):
            A,B,C,radial,tangent,degrees,trim=contract['arcs'][i]
            n=math.ceil(degrees/2)
            points=[add(C,mul(add(mul(radial,math.cos(math.radians(degrees*k/n))),
                                   mul(tangent,math.sin(math.radians(degrees*k/n)))),R)) for k in range(n+1)]
            pieces.append(dict(name=f'arc-{i}',points=points,
                               chord_error=R*(1-math.cos(math.radians(degrees/n/2)))))
            next_line=contract['lines'][i+1]
            incoming=sub(line[1],line[0]);incoming=mul(incoming,1/norm(incoming))
            outgoing=sub(next_line[1],next_line[0]);outgoing=mul(outgoing,1/norm(outgoing))
            arc_end_tangent=add(mul(radial,-math.sin(math.radians(degrees))),mul(tangent,math.cos(math.radians(degrees))))
            local_checks['arc_bases_orthonormal_to_echo_precision'] &= max(abs(norm(radial)-1),abs(norm(tangent)-1),abs(dot(radial,tangent)))<3e-6
            local_checks['arc_endpoints_and_tangencies_match_lines'] &= (max(norm(sub(points[0],line[1])),norm(sub(points[-1],next_line[0])))<echo_error_mm and max(norm(sub(tangent,incoming)),norm(sub(arc_end_tangent,outgoing)))<2e-5)
    rows=[]
    for i,a in enumerate(pieces):
        for j in range(i+2,len(pieces)):
            b=pieces[j]
            raw=min(segment_distance(p,q,r,s) for p,q in zip(a['points'],a['points'][1:])
                for r,s in zip(b['points'],b['points'][1:]))
            error=a['chord_error']+b['chord_error']+2*echo_error_mm+1e-6
            lower=raw-error;required=D+2*each_side_margin_mm
            rows.append(dict(a=a['name'],b=b['name'],polyline_distance_mm=raw,
                circle_centerline_distance_lower_bound_mm=lower,required_mm=required,
                passed=lower>required))
    return dict(status='DIAGNOSTIC_NON_NEIGHBOUR_CLEARANCE' if all(local_checks.values()) and all(x['passed'] for x in rows) else 'FAIL_OR_UNRESOLVED',
                local_analytic_preconditions=local_checks,primitive_pairs=rows,
                minimum_lower_bound_mm=min(x['circle_centerline_distance_lower_bound_mm'] for x in rows),
                echo_point_error_budget_mm=echo_error_mm,
                each_side_margin_mm=each_side_margin_mm,
                adjacent_pair_rule='Only immediate line-circle joints are skipped. Each is tangent; arc angle <180 and tube radius < circle radius. Distinct non-adjacent analytic primitives are checked, even if separated by just one straight.',
                limits=['Uses rounded exported contract with an explicit 0.01 mm point error budget.',
                        'Only non-neighbour local tube self-clearance; no environment/tool/physical-retention conclusion.',
                        'A near-boundary result must be recomputed from full-precision source parameters, never waived.'])

def main():
    tests=[('crossing',[0,0,0],[2,0,0],[1,-1,0],[1,1,0],0),
           ('parallel',[0,0,0],[2,0,0],[0,2,0],[2,2,0],2),
           ('skew',[0,0,0],[2,0,0],[1,-1,1],[1,1,1],1),
           ('near_parallel_crossing',[0,0,0],[1000,0,0],[0,-1e-6,0],[1000,1e-6,0],0),
           ('endpoint',[0,0,0],[1,0,0],[2,1,0],[2,2,0],math.sqrt(2))]
    for name,a,b,c,d,expected in tests:assert abs(segment_distance(a,b,c,d)-expected)<1e-10,name
    p=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else HERE/'initial.echo'
    if p.suffix=='.json':
        supplied=json.loads(p.read_text());contract=supplied['contract']
        assert supplied['sources_stable']
        assert all(sha(ROOT/k)==v for k,v in supplied['source_sha256'].items()),'Source identity changed'
    else:
        raw=p.read_text().split('ECHO: "CR_CONTRACT", ',1)[1].strip()
        for a,b in [('undef','None'),('false','False'),('true','True')]:raw=re.sub(r'\b'+a+r'\b',b,raw)
        contract=dict(ast.literal_eval(raw))
    r=evaluate(contract)
    r.update(contract_file=str(p),contract_sha256=sha(p),script_sha256=sha(Path(__file__)),
             source_sha256={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'cad/cable-housing-route.scad',ROOT/'cad/cable-trigger-input.scad',ROOT/'cad/cable-output-interface.scad']},
             segment_distance_self_tests_passed=len(tests),not_a_manufacturing_release=True)
    (HERE/'self-distance-review.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:r[k] for k in ['status','minimum_lower_bound_mm','local_analytic_preconditions','segment_distance_self_tests_passed']},indent=2))

if __name__=='__main__':main()
