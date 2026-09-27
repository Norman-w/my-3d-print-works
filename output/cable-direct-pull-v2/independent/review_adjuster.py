#!/usr/bin/env python3
"""Bounded, independent analytic review. Does not edit CAD or export geometry."""
from pathlib import Path
import argparse, hashlib, json, math

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def local_to_cad(p):
    x,y,z=p;s=math.sqrt(.5)
    return [75+s*(-x+y),-82+z,5+s*(x+y)]
def geometry(deg,delta=0):
    a=math.radians(deg);R=60;c=24
    B=[R*math.sin(a),R*math.cos(a),2]
    D=math.hypot(B[0]+c,B[1])
    phi=max(0,math.atan2(B[0]+c,B[1])-math.acos(R/D))
    tangent=math.sqrt(D*D-R*R)
    gap=5-delta
    length=gap+R*phi+tangent
    return {'theta_deg':deg,'delta_mm':delta,'ball_local':B,'phi_deg':math.degrees(phi),
      'guide_tangent_local':[-c+R*math.sin(phi),R*math.cos(phi),2],
      'rho_mm':D,'straight_entry_gap_mm':gap,'guide_arc_length_mm':R*phi,
      'tangent_to_ball_length_mm':tangent,'Q_to_ball_path_mm':length,
      'Q_to_ball_rest_length_mm':29-delta,'takeup_mm':length-(29-delta),
      'effective_arm_mm_per_rad':R*math.cos(a-phi)}
def inverse(u):
    lo,hi=0.,30.
    for _ in range(64):
        mid=(lo+hi)/2
        if geometry(mid)['takeup_mm']<u:lo=mid
        else:hi=mid
    return (lo+hi)/2
def budget(delta):
    thread=[-53+delta,-29+delta];head=[-63+delta,-53+delta]
    nuts=[[-49.8,-46.6],[-35.4,-32.2]];washers=[[-46.6,-45],[-37,-35.4]]
    overlaps=[max(0,min(b,thread[1])-max(a,thread[0])) for a,b in nuts]
    return {'delta_mm':delta,'thread_x':thread,'head_x':head,'nut_x':nuts,'washer_x':washers,
      'nut_nominal_thread_overlap_mm':overlaps,
      'left_thread_margin_and_head_shoulder_clearance_mm':nuts[0][0]-thread[0],
      'right_thread_margin_mm':thread[1]-nuts[1][1],
      'wire_exit_Q_local':[-29+delta,60,2],
      'housing_reference_port_local':[-63+delta,60,2],
      'housing_reference_port_cad':local_to_cad([-63+delta,60,2]),
      'ferrule_mouth_DISPLAY_ONLY_local':[-65.125+delta,60,2],
      'ferrule_tip_DISPLAY_ONLY_local':[-54.125+delta,60,2],
      'housing_end_DISPLAY_ONLY_local':[-56.125+delta,60,2],
      'Q_to_guide_start_mm':5-delta,
      'route_first_straight_if_downstream_unchanged_mm':25+delta,
      'route_length_change_if_downstream_unchanged_mm':delta}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--candidate',type=Path)
    args=parser.parse_args()
    sources=[ROOT/'cad/cable-trigger-input.scad',ROOT/'cad/cable-housing-route.scad',
             ROOT/'cad/cable-service-contract.scad',ROOT/'cad/cable-service-review.scad',
             ROOT/'cad/cable-output-interface.scad',Path(__file__)]
    if args.candidate:sources.append(args.candidate.resolve())
    before={str(p):sha(p) for p in sources}
    samples=[]
    for i in range(441):
        u=i*.05;a=inverse(u);row=geometry(a);row['u_requested_mm']=u
        row['delta_extreme_takeup_difference_mm']=abs(geometry(a,-2)['takeup_mm']-geometry(a,2)['takeup_mm'])
        samples.append(row)
    key=[dict(geometry(inverse(u)),u_requested_mm=u) for u in (0,16,20,22)]
    min_arm=min(x['effective_arm_mm_per_rad'] for x in samples)
    result={
     'scope':'Independent algebra/source-contract review of the planned fixed C=[-24,0], R60 guide and M6 delta +/-2 mm. No CAD changes, no physical fit or preload acceptance.',
     'status':'ANALYTIC_BUDGET_COMPLETE_CANDIDATE_SOURCE_CONFIRMATION_PENDING' if not args.candidate else 'CANDIDATE_FILE_CAPTURED_FUNCTION_IDENTITY_REQUIRES_SEPARATE_CONFIRMATION',
     'source_hashes_before':before,
     'planned_parameters':{'guide_C_local':[-24,0,2],'core_radius_mm':.75,'guide_contact_surface_radius_mm':59.25,'core_centerline_R_mm':60,'ball_orbit_R_mm':60,'delta_range_mm':[-2,2],'thread_length_mm':24,'seat_x':[-45,-37],'nut_thickness_mm':3.2,'washer_thickness_mm':1.6},
     'thread_budget':{'stack_mm':8+2*3.2+2*1.6,'total_unused_thread_mm':24-(8+2*3.2+2*1.6),
       'delta_endpoints_and_zero':[budget(d) for d in (-2,0,2)],
       'minimum_nominal_full_thread_end_margin_mm':1.2,
       'full_thread_claim_condition':'Actual end chamfer / incomplete thread and head-side runout must each fit within the corresponding remaining margin (minimum 1.2 mm); source cylinders do not certify this. Nominal 3.2 mm nut overlap is not bolt strength or tightening approval.',
       'range_enforcement':'No physical +/-2 mm stop is proved here. A measurable assembly setting and min/max witness marks are required if the final design uses the bounded budget.'},
     'kinematics':{'formula':'phi=atan2(60*sin(theta)+24,60*cos(theta))-acos(60/rho); rho^2=24^2+60^2+2*24*60*sin(theta); L(theta,delta)=5-delta+60*phi+sqrt(rho^2-3600); L(0,delta)=29-delta. Angles in radians in this formula.',
       'incremental_formula':'u(theta)=60*phi+sqrt(rho^2-3600)-24, independent of delta under the listed conditions.',
       'derivative':'du/dtheta=60*cos(theta-phi)>0 on theta 0..30 deg; the forward tangent branch is used.',
       'key_positions':key,'domain_upper_theta_deg':30,'takeup_at_upper_theta_mm':geometry(30)['takeup_mm'],
       'u_grid_mm':[0,22,.05],'max_inverse_residual_mm':max(abs(x['takeup_mm']-x['u_requested_mm']) for x in samples),
       'max_delta_takeups_difference_mm':max(x['delta_extreme_takeup_difference_mm'] for x in samples),
       'min_effective_arm_u_0_to_22_mm_per_rad':min_arm,
       'guide_8deg_margin_at_u22_deg':8-key[-1]['phi_deg'],
       'conditions':['Guide centre, radius and tangent start S=[-24,60,2] remain fixed; only Q shifts along the same local X line, with positive gap 5-delta (3..7 mm).','The core remains taut and follows the intended convex guide contact and forward tangent branch; axial confinement, real groove contact/friction, flexible-core stretch and preload are separate physical requirements.','Delta is held fixed during a trigger stroke. The rest position is re-established after changing delta. Adjustment changes absolute cable-length/slack/preload balance even though the same-delta increment cancels algebraically.','Ferrule seating and the core passage move with the adjuster, stay coaxial, and contribute theta-independent length; their supplier-undimensioned tapers cannot be used as exact fixed reaction coordinates.'],
       'samples':samples},
     'route_review':{'existing_input_source':'cr_input_port() reads old ci_spec().adjuster_overall_x[0], still -63; no delta parameter.',
       'existing_route_radius_mm':75,'existing_input_run_mm':100,'first_arc_turn_deg':90,'first_arc_trim_mm':75,'first_straight_mm':25,
       'minimal_geometric_endpoint_variant':'Keep first arc and all downstream curves fixed; move only P to P+delta*basis_x. Its initial collinear segment is 25+delta mm (23..27). This describes endpoint geometry only.',
       'constant_cut_length_problem':'That variant changes the outside route length by delta. One already cut, non-stretched housing cannot keep every downstream curve unchanged at all delta values. Free upstream bends need an explicit compensating route family or must be re-laid and checked during installation before the adjustment is locked.',
       'required_bounded_update':['Use the same delta in adjuster, ferrule, actual housing end, entrance port, internal core straight and render/contract; do not leave cr_housing at the old endpoint.','Include the continuous +/-2 mm sweep of the metal/ferrule/port against body, rotating parts, neighbours and actual tool corridors. For any chosen flexible route family, check its full envelope, length compatibility and R>=65; endpoint-only translation is not a bound on arbitrary hose deformation.','Recheck the 16 csr service envelopes against the chosen full housing-route envelope. csr_route_envelope currently uses full nominal cr_points plus 1 mm clearance and explicitly excludes end fittings, so ferrule/adjuster sweeps require separate checks.','Retain cover-off, module-on-bench nut adjustment; verify the fixed 3 mm SW10 wrench envelopes against the shifted fittings. A tool/hold method for the SW8 adjuster head and any loosened-nut state is not certified by the existing fixed-nut tool model.','Define delta=0 datum, +/-2 max settings or witness marks, and assembly sequence: seat and route housing, set zero/slack, tighten both nuts, then set the feeder hard-stop range. Recheck zero after any later adjuster movement.'],
       'not_proved':['Exact ferrule seating depth due to undimensioned supplier taper/chamfer','Constant physical housing cut length across the full adjustment range with downstream route fixed','Complete in-place SW8 turning access or loosened nut state','Bare core bending lifetime, friction, preload, real print clearance and structural strength']},
     'source_hashes_after':{str(p):sha(p) for p in sources}}
    result['sources_unchanged']=result['source_hashes_before']==result['source_hashes_after']
    if args.candidate:
        source=args.candidate.resolve();lines=source.read_text().splitlines()
        needles=['cdp_delta_bounds=','cdp_fairlead_C=','function cdp_exit(',
                 'function cdp_path_length(','function cdp_takeup(','function cdp_angle(',
                 'module cdp_local_fixed_hardware(','cdp_local_adjuster(delta);cdp_local_ferrule(delta);',
                 'for(x=cdp_adjuster_nut_x)','for(x=cdp_adjuster_washer_x)',
                 'module cdp_local_adjuster(','module cdp_local_ferrule(',
                 'module cdp_local_cable(','cdp_xcyl(cdp_exit(delta)[1]',
                 '["setup",','["unknown",']
        result['candidate_source_read_evidence']=[{'needle':needle,'line':i+1,'source_text':line}
            for needle in needles for i,line in enumerate(lines) if needle in line]
        native_path=HERE/'native-verification.json'
        if native_path.exists():
            native=json.loads(native_path.read_text())
            if native['passed'] and native['source_sha256_after']==sha(source):
                result['native_function_verification']={'report':str(native_path),'sha256':sha(native_path),
                    'verified_candidate_sha256':sha(source),'passed':True,'angle_takeup_delta_combinations':1323,
                    'absolute_assertion_tolerance':1e-8}
                result['status']='NOMINAL_HARDWARE_BUDGET_AND_NATIVE_KINEMATICS_CONFIRMED_ROUTE_AND_SERVICE_PENDING'
        result['route_review']['followup_owned_by_root']='Root is constructing an equal-length family by moving only the first virtual corner along the input axis while fixing the second/third/output vertices. That family is not inspected or accepted by this report yet.'
    (HERE/'adjuster-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'sources_unchanged':result['sources_unchanged'],'key_positions':key,'minimum_nominal_thread_margin_mm':1.2},indent=2))

if __name__=="__main__":main()
