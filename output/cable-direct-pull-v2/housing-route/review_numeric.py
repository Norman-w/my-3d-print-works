"""Independent numerical check of a constant-length, three-fillet route family.

Sampling is reported as sampling. This is not a physical equilibrium solver.
"""
from pathlib import Path
import math, json, hashlib
import numpy as np

B = Path(__file__).resolve().parent
ROOT = B.parents[2]
R = 75.0
D = np.array([math.sqrt(.5), 0, -math.sqrt(.5)])
P = np.array([75 + math.sqrt(.5)*123, -80, 5-math.sqrt(.5)*3])
Q = np.array([-58., 35.5, 111.])
BASE = np.array([P, P+100*D, P+100*D+[0,195,0], [-58,35.5,400], Q])

def unit(v):
    return v/np.linalg.norm(v)

def route(delta, shift):
    v = BASE.copy()
    v[0] -= delta*D
    v[1] += shift*D
    arcs = []
    for i in range(1, 4):
        a, b = unit(v[i]-v[i-1]), unit(v[i+1]-v[i])
        dot = np.clip(a@b, -1, 1)
        theta = math.acos(dot)
        trim = R*math.tan(theta/2)
        normal = unit(b-a*dot)
        start, end = v[i]-a*trim, v[i]+b*trim
        centre = start+R*normal
        arcs.append(dict(start=start, end=end, centre=centre,
                         radial=-normal, tangent=a, theta=theta, trim=trim))
    lines = []
    for i in range(4):
        a = v[0] if i == 0 else arcs[i-1]['end']
        b = v[4] if i == 3 else arcs[i]['start']
        lines.append(dict(start=a, end=b, length=float(np.linalg.norm(b-a)),
                          signed_length=float((b-a)@unit(v[i+1]-v[i]))))
    length = sum(l['length'] for l in lines)+R*sum(a['theta'] for a in arcs)
    return dict(vertices=v, arcs=arcs, lines=lines, length=length)

TARGET = route(0,0)['length']
def solve(delta):
    lo, hi = -12., 12.
    assert route(delta,lo)['length'] < TARGET < route(delta,hi)['length']
    for _ in range(48):
        mid=(lo+hi)/2
        if route(delta,mid)['length'] < TARGET: lo=mid
        else: hi=mid
    return (lo+hi)/2

def points(r):
    # Matched normalised arc parameters for comparing two family members.
    p=[r['vertices'][0]]
    for a in r['arcs']:
        for t in np.linspace(0,1,101):
            angle=t*a['theta']
            p.append(a['centre']+R*(math.cos(angle)*a['radial']+math.sin(angle)*a['tangent']))
    p.append(r['vertices'][4])
    return np.array(p)

def serial(obj):
    if isinstance(obj,np.ndarray): return obj.tolist()
    if isinstance(obj,np.generic): return obj.item()
    raise TypeError(type(obj))

def main():
    baseline = route(0,0)
    baseline_points=points(baseline)
    rows=[]
    for d in np.linspace(-2,2,81):
        shift=solve(d); r=route(d,shift)
        third=r['arcs'][2]
        assert all(np.array_equal(third[k],baseline['arcs'][2][k]) for k in third)
        # Numerical derivative in the root bracket, explicitly not an interval proof.
        derivative=[(route(d,s+.0001)['length']-route(d,s-.0001)['length'])/.0002
                    for s in np.linspace(-12,12,25)]
        tangent_errors=[]
        for i,a in enumerate(r['arcs']):
            end_t=-math.sin(a['theta'])*a['radial']+math.cos(a['theta'])*a['tangent']
            tangent_errors += [np.linalg.norm(a['tangent']-unit(r['lines'][i]['end']-r['lines'][i]['start'])),
                               np.linalg.norm(end_t-unit(r['lines'][i+1]['end']-r['lines'][i+1]['start']))]
        rows.append(dict(delta=d, shift=shift, length=r['length'], error=r['length']-TARGET,
                         straight_lengths=[l['signed_length'] for l in r['lines']],
                         sampled_min_dlength_dshift=min(derivative),
                         max_tangent_error=max(tangent_errors),
                         max_matched_point_displacement=float(np.max(np.linalg.norm(points(r)-baseline_points,axis=1))),
                         third_arc_identical=True))
    assert max(abs(r['error']) for r in rows)<1e-9
    assert min(min(r['straight_lengths']) for r in rows)>15
    assert min(r['sampled_min_dlength_dshift'] for r in rows)>0
    assert max(r['max_tangent_error'] for r in rows)<1e-12
    # A continuous existence argument on |s|<=2. Angles in this proof are radians.
    # theta1'=195/h^2 > 0; theta2'=195*(195*c_d+s*c_y)/(h^3*sin(theta2)) < 0.
    # Consequently the theta2 term in L_s' is nonnegative and can be discarded
    # when forming a conservative lower bound.
    c=unit(BASE[3]-BASE[2]); cd=float(c@D); cy=float(c[1])
    theta1max=route(0,2)['arcs'][0]['theta']
    theta2max=route(0,-2)['arcs'][1]['theta']
    theta2_sign_upper=195*cd+2*abs(cy)
    derivative_lower=1-2/195-R*math.tan(theta1max/2)**2/195
    bracket=[route(2,-2)['length']-TARGET,route(-2,2)['length']-TARGET]
    trim1max=R*math.tan(theta1max/2); trim2max=R*math.tan(theta2max/2)
    trim3=baseline['arcs'][2]['trim']
    line_lower=[100-2-2-trim1max,195-trim1max-trim2max,
                float(np.linalg.norm(BASE[3]-BASE[2]))-trim2max-trim3,
                baseline['lines'][3]['signed_length']]
    assert theta2_sign_upper<0 and derivative_lower>0
    assert bracket[0]<0<bracket[1] and min(line_lower)>15
    proof=dict(status='CONTINUOUS_EXISTENCE_BY_ANALYTIC_INEQUALITIES',
               corner_shift_interval=[-2,2], theta2_derivative_sign_numerator_upper=theta2_sign_upper,
               length_derivative_wrt_shift_lower_bound=derivative_lower,
               bracket_extreme_length_errors=bracket, conservative_straight_lower_bounds=line_lower,
               reasoning='L(delta,s)=L(0,s)+delta. For every delta in [-2,2], the endpoint signs bracket a root in [-2,2]; the positive derivative lower bound makes it unique. All line lower bounds are positive, so the circular fillets do not overlap.',
               scope='Analytic route geometry; this does not certify continuous clearance, physical retention, or exact arithmetic intervals.')
    sources=['cad/cable-housing-route.scad','cad/cable-trigger-input.scad',
             'cad/cable-output-interface.scad',str((B/'equal-length-route.scad').relative_to(ROOT)),
             str(Path(__file__).relative_to(ROOT))]
    hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources}
    report=dict(status='SAMPLED_EQUAL_LENGTH_FAMILY_PASS', source_sha256=hashes,
                delta_range=[-2,2], delta_sample_step=.05, sample_count=len(rows),
                outside_port_route_length=TARGET, fillet_radius=R, supplier_housing_min_radius=65,
                port_datum='Input adjuster outside end x=-63+delta; not an identified sheath seating stop',
                physical_shape_retained=False, manufactured_cut_length=None,
                analytic_invariants=['All three fillets constructed with radius 75',
                  'Second/third virtual corners and output unchanged: entire third arc exactly unchanged',
                  'Input point moves along the fixed adjuster axis; output point and tangent fixed'],
                limitations=['Dense numerical sampling, not continuous interval enclosure',
                  'First two bends are free: this family is a possible installation geometry, not a retained shape',
                  'No equilibrium, friction, wire compression, fatigue or unknown obstacles are modelled',
                  'Absolute cut length still needs actual ferrule seating corrections'],
                continuous_existence=proof, rows=rows)
    (B/'numeric'/'report.json').write_text(json.dumps(report,indent=2,default=serial)+'\n')
    summary={k:report[k] for k in ['status','sample_count','outside_port_route_length','fillet_radius']}
    summary.update(max_abs_length_error=max(abs(r['error']) for r in rows),
       minimum_straight=min(min(r['straight_lengths']) for r in rows),
       sampled_max_displacement=max(r['max_matched_point_displacement'] for r in rows),
       endpoint_rows=[rows[0],rows[40],rows[-1]])
    print(json.dumps(summary,indent=2,default=serial))

if __name__=='__main__':main()
