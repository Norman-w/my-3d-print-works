#!/usr/bin/env python3
"""Auditable V-seat error transfer, not a global mechanism tolerance proof.

No sampling/optimization. The table is a DESIGN envelope, not measured FDM.
Optional --radius-low/--radius-high are signed radius errors in mm, not diameters.
"""
from pathlib import Path
import argparse
import ast
import hashlib
import itertools
import json
import math
import re

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/pin-v-seat-error'
CAD=ROOT/'cad/feeder-pin-seat-revision.scad'

def load():
    ordered=[];seen=set()
    def visit(p):
        p=p.resolve()
        if p in seen:return
        seen.add(p)
        for d in re.findall(r'\b(?:include|use)\s*<([^>]+)>',p.read_text()):visit(p.parent/d)
        ordered.append(p)
    visit(CAD)
    expr={}
    for p in ordered:
        expr.update(re.findall(r'^(\w+)\s*=\s*([^;]+);',p.read_text(),re.M))
    cache={}
    def node(n):
        if isinstance(n,ast.Constant)and isinstance(n.value,(float,int)):return n.value
        if isinstance(n,ast.Name):return value(n.id)
        if isinstance(n,ast.UnaryOp):return -node(n.operand)if isinstance(n.op,ast.USub)else node(n.operand)
        if isinstance(n,ast.BinOp):
            a,b=node(n.left),node(n.right)
            for t,f in [(ast.Add,lambda:a+b),(ast.Sub,lambda:a-b),(ast.Mult,lambda:a*b),(ast.Div,lambda:a/b)]:
                if isinstance(n.op,t):return f()
        if isinstance(n,ast.Call)and isinstance(n.func,ast.Name)and len(n.args)==1:
            x=node(n.args[0]);f={'sin':lambda:math.sin(math.radians(x)),
                'cos':lambda:math.cos(math.radians(x)),'sqrt':lambda:math.sqrt(x)}.get(n.func.id)
            if f:return f()
        raise ValueError(f'Unsupported parameter expression: {ast.dump(n)}')
    def value(k):
        if k not in cache:cache[k]=float(node(ast.parse(expr[k],mode='eval').body))
        return cache[k]
    keys=['cam_pin_d','cam_follower_offset','cam_pin_shoulder_start_y','cam_pin_shoulder_end_y',
        'cam_carrier_width','cam_carrier_axial','cam_carrier_inner_offset','cam_carrier_length',
        'cam_plate_y','cam_plate_thickness','ps_v_apex','ps_v_z','ps_v_half_angle','ps_seat_y0','ps_seat_y1',
        'ps_block_front','ps_block_back','ps_block_y0','ps_nose_y0','ps_lower_front_setback',
        'ps_block_half_z','ps_lip_x0','ps_lip_x1','ps_lip_y0','ps_lip_half_z','ps_clear',
        'ps_adjust_advance','ps_adjust_retracted','ps_advance_stop','ps_retract_stop',
        'ps_jack_length','ps_jack_y','ps_nut_x0','ps_nut_x1','revision_datum_z0','revision_datum_z1',
        'revision_datum_y','revision_x0','revision_x1','finger_closed_center_r','finger_open_center_r',
        'cam_stroke','gate_overlap_fraction']
    p={k:value(k)for k in keys}
    compact=re.sub(r'\s+','',CAD.read_text())
    assert '[ps_v_apex+ps_v_z,ps_v_z]'in compact
    assert '[ps_v_apex+ps_v_z,-ps_v_z]'in compact
    assert 'rotate([90,0,0])'in compact and p['ps_v_half_angle']==45
    source={str(q.relative_to(ROOT)):hashlib.sha256(q.read_bytes()).hexdigest()for q in ordered}
    source[str(Path(__file__).resolve().relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return p,source

def inverse2(a):
    d=a[0][0]*a[1][1]-a[0][1]*a[1][0]
    if abs(d)<1e-12:raise ValueError('V face normals are singular')
    return [[a[1][1]/d,-a[0][1]/d],[-a[1][0]/d,a[0][0]/d]]
def mv(a,x):return [sum(v*b for v,b in zip(row,x))for row in a]
def transfer(d1,d2,dr):return [(d1+d2)/math.sqrt(2)+math.sqrt(2)*dr,(d2-d1)/math.sqrt(2)]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--radius-low',type=float);ap.add_argument('--radius-high',type=float)
    args=ap.parse_args()
    if (args.radius_low is None)!=(args.radius_high is None):ap.error('Provide both signed radius limits, or neither.')
    if args.radius_low is not None and args.radius_low>args.radius_high:ap.error('Reversed radius interval.')
    OUT.mkdir(parents=True,exist_ok=True);p,identity=load()
    root_report=json.loads((ROOT/'output/feeder-pin-seat-revision/report.json').read_text())
    identity_ok=all(hashlib.sha256((ROOT/k).read_bytes()).hexdigest()==v for k,v in root_report['source_sha256'].items())
    # Derive normals from the actual two XZ polygon edges, not an assumed hole.
    a=[p['ps_v_apex'],0.];edge=p['ps_v_z'];length=math.hypot(edge,edge)
    normals=[[edge/length,-edge/length],[edge/length,edge/length]]
    inv=inverse2(normals);r=p['cam_pin_d']/2
    center=[a[i]+mv(inv,[r,r])[i]for i in range(2)]
    tests=[]
    for d1,d2,dr in itertools.product([-.2,0.,.2],[-.2,0.,.2],[-.02,0.,.02]):
        numeric=[a[i]+mv(inv,[r+dr+d1,r+dr+d2])[i]-center[i]for i in range(2)]
        exact=transfer(d1,d2,dr);res=max(abs(x-y)for x,y in zip(numeric,exact))
        tests.append(res)
    work=[-p['ps_adjust_advance'],p['ps_adjust_retracted']]
    stops=[-p['ps_advance_stop'],p['ps_retract_stop']]
    table=[]
    for e in [0,.05,.10,.15,.20]:
        bound=math.sqrt(2)*e
        corners=[transfer(d1,d2,0)for d1,d2 in itertools.product([-e,e],repeat=2)]
        assert abs(max(math.hypot(*x)for x in corners)-bound)<1e-12
        table.append({'per_face_normal_design_envelope_mm':e,'radius_error_assumed_for_this_row_mm':0,
            'abs_center_x_bound_mm':bound,'abs_center_z_bound_mm':bound,
            'center_euclidean_bound_mm':bound,'required_block_dx_interval_mm':[-bound,bound],
            'working_compensation_covers_row':work[0]<=-bound and bound<=work[1],
            'minimum_working_range_reserve_mm':min(-bound-work[0],work[1]-bound)})
    radius_rows=None
    if args.radius_low is not None:
        lo,hi=args.radius_low,args.radius_high;radius_rows=[]
        for row in table:
            e=row['per_face_normal_design_envelope_mm'];xlo=math.sqrt(2)*(lo-e);xhi=math.sqrt(2)*(hi+e)
            blo=-math.sqrt(2)*e+(1+math.sqrt(2))*lo;bhi=math.sqrt(2)*e+(1+math.sqrt(2))*hi
            radius_rows.append({'E_mm':e,'center_x_interval_mm':[xlo,xhi],
                'center_z_interval_mm':[-math.sqrt(2)*e,math.sqrt(2)*e],
                'required_block_dx_mm':[blo,bhi],'working_range_covers_interval':work[0]<=blo and bhi<=work[1]})
    engagement=[]
    for dx in [stops[0],work[0],0,work[1],stops[1]]:
        x0=p['ps_block_back']+dx;x1=x0+p['ps_jack_length']
        overlap=max(0,min(x1,p['ps_nut_x1'])-max(x0,p['ps_nut_x0']))
        engagement.append({'block_dx_mm':dx,'screw_x_mm':[x0,x1],
            'nominal_thread_envelope_overlap_mm':overlap,
            'outer_end_recess_mm':p['cam_carrier_inner_offset']+p['cam_carrier_length']-x1})
    y0,y1=p['ps_seat_y0'],p['ps_seat_y1'];span=y1-y0
    extrap=[]
    for y in [p['cam_plate_y'],p['cam_plate_y']+p['cam_plate_thickness']]:
        w=[(y1-y)/span,(y-y0)/span]
        extrap.append({'cam_face_y_mm':y,'endpoint_weights':w,'absolute_weight_sum':sum(abs(x)for x in w),
            'meaning':'Amplification if independent endpoint CENTER errors are established; not itself a certified face-error/tilt bound.'})
    cam_slope=(p['finger_open_center_r']-p['finger_closed_center_r'])/(p['cam_stroke']*(1-p['gate_overlap_fraction'])/2)
    before=OUT/'before-compensation'
    baseline=json.loads((before/'identity.json').read_text());collision=json.loads((before/'hardstop-classification.json').read_text())
    assert hashlib.sha256((before/'feeder-pin-seat-revision.scad').read_bytes()).hexdigest()==baseline['cad_sha256']
    assert collision['has_solid_or_unclassified_overlap']
    report={'status':'ANALYTIC_TRANSFER_AND_NOMINAL_COMPENSATION_REVIEW',
        'source_sha256':identity,'candidate_report_current':identity_ok,'sources_stable':False,
        'candidate_nominal_geometry_status':root_report['status'],
        'parameter_snapshot':p,'coordinate_convention':'local X outward; Y pin axis; Z feed. Left side mirrors X.',
        'face_normals_xz':normals,'face_anchor_xz_mm':a,'normal_matrix_inverse':inv,
        'face_normals_xyz':[[n[0],0,n[1]]for n in normals],
        'nominal_center_xz_mm':center,'nominal_contact_y_mm':[y0,y1],
        'pressure_nose_y_mm':[p['ps_nose_y0'],y1],
        'normal_error_sign':'Positive delta moves that solid face along its normal INTO the V opening.',
        'exact_equations':{'center':'c=a+inverse(A)*((R+delta_r)*ones+delta)',
            'delta_x':'(delta1+delta2)/sqrt(2)+sqrt(2)*delta_r',
            'delta_z':'(delta2-delta1)/sqrt(2)',
            'block_contact_dx':'(delta1+delta2)/sqrt(2)+(1+sqrt(2))*delta_r'},
        'scope':'Exact for two parallel-to-Y planar V faces, circular shoulder, axis parallel Y, and maintained simultaneous contacts.',
        'symmetric_bounds':{'inputs':'abs(delta1/2)<=E; abs(delta_r)<=rho',
            'abs_delta_x':'sqrt(2)*(E+rho)','abs_delta_z':'sqrt(2)*E',
            'euclidean':'sqrt(2)*(E+rho), sharp over this input box',
            'required_block_dx':'[-sqrt(2)*E-(1+sqrt(2))*rho, +sqrt(2)*E+(1+sqrt(2))*rho]'},
        'correlated_domain':'abs(delta_x-sqrt(2)*delta_r)+abs(delta_z)<=sqrt(2)*E; do not replace by independently attained X/Z maxima.',
        'linear_projection':{'general':'For row w, bound = E*(abs((w*A^-1)[0])+abs((w*A^-1)[1])) + rho*abs(w*A^-1*ones).',
            'nominal_cam_slope_abs':cam_slope,'nominal_delta_x_plus_m_delta_z_bound':'sqrt(2)*E*max(1,abs(m))+sqrt(2)*rho',
            'scope':'Contribution of this seat only, with identity carrier/frame orientation. Not a whole tip-error bound.'},
        'face_angle_extension':{'exact':'Use measured unit normals as rows of A; c=a+inverse(A)*((R+delta_r)*ones+delta).',
            'conditional_bound':'If each normal angle differs <=alpha from nominal, epsilon=2*sqrt(2)*sin(alpha/2)<1, ||delta_c||2 <= (sqrt(2)*(E+rho)+epsilon*sqrt(2)*R)/(1-epsilon).',
            'reference':'Plane offsets measured at the SAME nominal anchor a. No actual angle bound has been supplied.'},
        'design_table_NOT_PRINT_MEASUREMENT':table,'provided_radius_error_interval_mm':None if radius_rows is None else[args.radius_low,args.radius_high],
        'provided_radius_results_NOT_CATALOGUE_ACCEPTANCE':radius_rows,
        'diameter_catalogue':{'part':'norelem 07534-04X12','nominal_diameter_mm':p['cam_pin_d'],
            'verified_diameter_tolerance_class':None,'verified_diameter_limits_mm':None,
            'official_page':'https://www.norelemusa.com/en-us/Product-Overview/Flexible-standard-component-system/07000/Nuts-screws-washers-securing-elements/Shoulder-screws-similar-to-ISO-7379/p/agid.27418',
            'result':'Official page verifies ground shaft family only; legacy full PDF links returned404, accessible cached1-page text does not resolve diameter tolerance drawing. No f9/h8 assumption.'},
        'actual_compensation':{'work_mm':work,'mechanical_stop_mm':stops,
            'work_end_to_stop_reserve_mm':[work[0]-stops[0],stops[1]-work[1]],
            'engagement':engagement,'thread_engagement_note':'Geometric nominal overlap; thread runout/chamfer/end socket strength and torque remain inputs.'},
        'baseline_failure':{'cad_sha256':baseline['cad_sha256'],'block_dx_mm':-.05,
            'interference_volume_mm3':sum(c['volume_mm3']for c in collision['components']),
            'meaning':'Old lower heel hit X22 wall before pin preload could be guaranteed; correction is a stepped heel plus extended ear pocket.'},
        'preload':{'frictionless_2d_contact_forces':'N1=(P-Fx+Fz)/sqrt(2), N2=(P-Fx-Fz)/sqrt(2)',
            'strict_contact_condition':'P-Fx>abs(Fz), plus moment/axial-contact feasibility',
            'proved':False,'unknowns':['minimum retained block preload','operating cam force/wrench','plastic creep and indentation','M2 anti-loosening','M3 shoulder seating/flatness/chamfer']},
        'carrier_contact_change':{'removed_front_patch_local_x_mm':[p['ps_lip_x0']-p['ps_advance_stop'],p['ps_lip_x1']+p['ps_retract_stop']],
            'removed_front_patch_abs_z_mm':[p['revision_datum_z0'],p['ps_lip_half_z']+p['ps_clear']],
            'remaining_full_front_band_abs_z_mm':[p['ps_lip_half_z']+p['ps_clear'],p['cam_carrier_axial']/2],
            'block_ear_contact_abs_z_mm':[p['revision_datum_z0'],p['ps_lip_half_z']],
            'block_not_rigidly_part_of_carrier':True,
            'instruction':'Intersect actual transformed faces with guide X43.8..57.8 and lead-ins. Model block relative movement; do not use old full-height slab as global constraint.'},
        'tilt_projection':extrap,'formula_self_checks':{'exact_matrix_cases':len(tests),'max_residual_mm':max(tests),
            'corner_bound_checks':len(table),'passed':max(tests)<1e-12},
        'complete_tip_error_bound_mm':None,'manufacturing_release':False,
        'next_proof_inputs':['four actual V face profiles/angles with spatial correlation',
            'actual shoulder diameter interval, form, chamfer and perpendicularity',
            'effective cylindrical contact span and shoulder/nut axial contact',
            'block pose range, positive contact preload and load wrench',
            'remaining carrier front-band geometry and independent captured ear contact',
            'all existing frame/slot/guide clearances including differential gib settings',
            'joint four-follower constraints over the entire cam stroke, with a certified enclosure rather than local maxima']}
    report['sources_stable']=all(hashlib.sha256((ROOT/k).read_bytes()).hexdigest()==v for k,v in identity.items())
    assert report['sources_stable']and identity_ok and report['formula_self_checks']['passed']
    (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(report['status'],'matrix residual',max(tests),'work',work,'source current',identity_ok)
    for row in table:print(row)
if __name__=='__main__':main()
