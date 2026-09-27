#!/usr/bin/env python3
"""Finite logical interlock and rigid-sphere feasibility, NOT implemented CAD.

Reads current parameters; writes an independent report. No CAD mutation, CFD,
time/velocity simulation, material-force inference, or print operation.
"""
from pathlib import Path
from collections import deque
import hashlib,json,math
from gate_geometry import read_parameters,cam_positions
from guide_openings import center_offset_bound
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/analysis/point-shot-interlock.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def search(remove_ready=False,remove_stroke=False,remove_exit=False):
    # State: phase, chamber ball, one-use permission, exit event, emitted balls.
    start=('rest',0,0,0,0);queue=deque([(start,[])]);seen={start};faults=[]
    while queue:
        s,history=queue.popleft();phase,ball,ticket,exit_seen,n=s;edges=[]
        if n>1 or (phase.startswith('return') and n!=1):
            faults.append({'state':s,'trace':history});continue
        if phase=='rest':
            if not ball:edges.append(('ball arrives',(phase,1,0,0,0)))
            edges.append(('press to dual-closed station',('check',ball,0,0,0)))
        elif phase=='check':
            # An empty abort is not a full pull or a counted firing cycle.
            if ball or remove_ready:edges.append(('occupancy permits commitment',('committed',ball,1,0,0)))
            # Abort/retry represented at the identical rest node.
            edges.append(('abort before opening',('rest',ball,0,0,0)))
        elif phase=='committed':
            edges.append(('finish pull to20',('held',ball,ticket,exit_seen,n)))
            if remove_stroke:edges.append(('reverse before full pull',('return_closed',ball,ticket,exit_seen,n)))
        if phase in ['committed','held'] and ball and ticket:
            edges.append(('this ball reaches downstream trip',(phase,0,0,1,n+1)))
        if phase=='held' and (exit_seen or remove_exit):
            edges.append(('user releases after endpoint',('return_closed',ball,ticket,exit_seen,n)))
        if phase=='return_closed':edges.append(('front actually closed before rear opens',('return_feed',ball,0,exit_seen,n)))
        if phase=='return_feed' and not ball:edges.append(('next ball may load behind closed front',(phase,1,0,exit_seen,n)))
        # Stop at complete reset; a subsequent complete pull is a NEW cycle.
        # No forward transition is allowed on the return branch until reset.
        for event,next_state in edges:
            if next_state not in seen:seen.add(next_state);queue.append((next_state,history+[event]))
    return {'reachable_states':len(seen),'faults':faults,'empty_full_pull_possible':any(s[0]=='held'and s[1]==0 and s[4]==0 for s in seen),'scope':'Exhaustive finite logical state graph only; signal truth and hardware enforcement are separate geometry/load obligations.'}
def main():
    source=ROOT/'cad/parameters.scad';p,_=read_parameters(source)
    R0,R1=p['ball_min_d']/2,p['ball_max_d']/2;A=p['guide_id']/2+p['guide_clearance_budget'];b=p['gate_position_budget'];r=p['finger_tip_radius']
    E=center_offset_bound(A,R0,r+p['radial_print_clearance']);c0=p['finger_closed_center_r']-b;c1=p['finger_closed_center_r']+b
    hmin=math.sqrt((R0+r)**2-c1*c1-E*E)
    hmax=max(math.sqrt((R+r)**2-(c0-center_offset_bound(A,R,r+p['radial_print_clearance']))**2)for R in [R0,R1])
    stop_z=[-b-hmax,b-hmin];rear_ball_nose_max=-p['gate_spacing']+b-hmin+R1
    # Proposed radial feeler, same X-oriented narrow-Y opening family as gates.
    ready={'axial_z_mm':-8.,'spherical_tip_radius_mm':1.5,'rest_center_x_mm':18.,'trip_center_x_mm':18.5,'cam_retracted_center_x_mm':24.5,'new_hole_radius_mm':1.75}
    dz=max(abs(z-ready['axial_z_mm'])for z in stop_z)
    at_trip=math.hypot(ready['trip_center_x_mm']+E,dz)
    ready['all_parked_balls_force_beyond_trip_sufficient_margin_mm']=R0+ready['spherical_tip_radius_mm']-at_trip
    ready['upstream_held_ball_separation_mm']=ready['axial_z_mm']-ready['spherical_tip_radius_mm']-rear_ball_nose_max
    ready['retracted_minimum_ball_clearance_mm']=ready['cam_retracted_center_x_mm']-(R0+E)-ready['spherical_tip_radius_mm']
    ready['claim']='Bounds require existing sphere/guide/gate budgets. New hole is not accepted by current CAD source-contract checker; it must be integrated and revalidated.'
    # An OUTWARD TRIP is used, never the return of a lever: a ball can retreat.
    departure={'minimum_local_design_plane_z_mm':38.,'preferred_separate_collar_plane_z_mm':80.,'proposed_axial_placement_budget_mm':.5,'tip_radius_mm':1.5,'opposed_tip_rest_r_mm':18.5,'opposed_tip_trip_r_mm':19.,'opposed_tip_clear_r_mm':26.5,'collar_bore_nominal_mm':48.,'proposed_collar_radius_budget_mm':.25,'hole_radius_mm':1.75}
    DA=departure['collar_bore_nominal_mm']/2+departure['proposed_collar_radius_budget_mm'];DE=center_offset_bound(DA,R0,departure['hole_radius_mm'])
    departure['all_lateral_centers_trigger_at_least_one_probe_margin_mm']=R0+departure['tip_radius_mm']-math.hypot(departure['opposed_tip_trip_r_mm'],DE)
    departure['both_fully_out_minimum_clearance_mm']=departure['opposed_tip_clear_r_mm']-(R0+DE)-departure['tip_radius_mm']
    departure['front_gate_entire_sweep_downstream_clear_center_z_mm']=b+hmax
    departure['sufficient_sensor_plane_lower_bound_mm']=b+hmax+R1+departure['tip_radius_mm']+departure['proposed_axial_placement_budget_mm']
    earliest=departure['minimum_local_design_plane_z_mm']-departure['proposed_axial_placement_budget_mm']-R1-departure['tip_radius_mm']
    departure['earliest_center_at_any_sensor_contact_mm']=earliest
    departure['front_sweep_clearance_when_any_probe_trips_mm']=earliest-b-hmax
    departure['preferred_collar_clearance_mm']=departure['preferred_separate_collar_plane_z_mm']-departure['minimum_local_design_plane_z_mm']+departure['front_sweep_clearance_when_any_probe_trips_mm']
    dx=departure['opposed_tip_rest_r_mm']-DE
    departure['conservative_axial_resistance_per_radial_probe_force_ratio']=math.sqrt((R1+departure['tip_radius_mm'])**2-dx*dx)/dx
    normal=search();controls={'no_occupancy_latch':search(remove_ready=True),'no_full_stroke_ratchet':search(remove_stroke=True),'no_departure_latch':search(remove_exit=True)}
    # Occupancy omission also permits an empty FULL pull that stalls at exit.
    partial_u=1.;front,rear=cam_positions(partial_u/p['cam_stroke'],p)
    baseline=[
      {'name':'empty full pull','trace':['empty chamber','u0→20','rear closed/front open','late ball stays upstream'],'output_count':0},
      {'name':'early full return before motion','trace':['one parked ball','u0→20','ball has not moved','u20→0','same ball stays behind front gate'],'output_count':0},
      {'name':'second discharge without full reset','trace':['one parked ball','u0→20; first ball exits',f'return only to u{partial_u}','another ball loads','u1→20; second ball exits'],'output_count':2,'partial_return_u_mm':partial_u,'front_r_mm':front,'rear_r_mm':rear,'rear_clearance_in_same_budget_mm':rear-b-(R0+E)-r},
      {'name':'downstream feeler rebound false confirmation','trace':['one feeler is pushed','ball retreats before passing it','feeler springs back'],'reason':'pressed-then-released alone does not establish forward departure; proposal uses a fresh outward event far enough downstream'}]
    checks={'ready_detects_every_parked_ball_in_superset':ready['all_parked_balls_force_beyond_trip_sufficient_margin_mm']>0,'rear_held_ball_cannot_touch_ready_sensor':ready['upstream_held_ball_separation_mm']>0,'ready_sensor_can_be_cam_cleared':ready['retracted_minimum_ball_clearance_mm']>0,'departure_pair_cannot_be_bypassed_in_declared_collar':departure['all_lateral_centers_trigger_at_least_one_probe_margin_mm']>0,'departure_implies_ball_beyond_front_sweep_at_event':departure['front_sweep_clearance_when_any_probe_trips_mm']>0,'abstract_sequence_has_no_count_fault':not normal['faults'],'missing_stroke_and_exit_controls_fail':bool(controls['no_full_stroke_ratchet']['faults'])and bool(controls['no_departure_latch']['faults']),'missing_occupancy_control_reaches_empty_full_pull':controls['no_occupancy_latch']['empty_full_pull_possible']and not normal['empty_full_pull_possible']}
    files=['cad/parameters.scad','cad/cam-study.scad','cad/feeder-supports.scad','cad/kinematic-study.scad','analysis/gate_geometry.py','analysis/guide_openings.py','analysis/point_shot_interlock.py']
    report={'status':'CONDITIONAL_INTERLOCK_CONTRACT_NOT_IMPLEMENTED_IN_CAD','source_sha256':{f:sha(ROOT/f)for f in files},'checks':checks,'front_stopped_center_interval_mm':stop_z,'gate_stop_depth_interval_mm':[hmin,hmax],'ready_feeler':ready,'departure_feelers':departure,'existing_mechanism_counterexamples':baseline,'finite_logical_review':normal,'failure_controls':controls,'normal_exactly_one_contract':['First ball inside current rigid 40–41mm envelope arrives and is parked.','Actual four followers satisfy the budget and cannot override a blocked gate.','Fresh ready and downstream-clear conditions allow commitment.','User completes pull; actual ball progresses forward to downstream trip in finite time.','While held, rear remains closed; only full released reset rearms.'],'necessary_load_conditions':['Ball-induced radial feeler force must exceed feeler spring + slide friction + sear release force.','Unloaded air/turbulence/acceleration must not trip the ready or exit sensor.','Pawl reaction goes to fixed housing; user force must not pass through sphere or sensing plunger.','Available forward force must exceed sensor resistance, existing friction and spin load; fixed fan speed alone supplies no numerical lower bound.','A fresh downstream outward trip certifies clearance at that instant; arbitrary reverse motion before front closure is not covered without a separate one-way restraint.'],'limits':['No CAD, assembled collision check, actual spring selection, printed fit or force validation for this proposal.','The existing1mm full mechanical error budget has not yet been certified.','A blocked or starved mechanism may stop; that is abnormal containment, not claimed successful one-ball output.','No source file in the frozen assembly was edited.'],'sent_to_printer':False}
    pitch=math.sqrt((2*R0)**2-(2*E)**2)
    report['ordinary_point_shot_scope']={'definition':'One ball already loaded; full pull; held trigger does not refill; ball clears before full reset. Empty pull and partial reversal are separate optional fault-tolerance features, not inherent violations of ordinary point-shot operation.','closed_pocket_center_span_max_mm':p['gate_spacing']+2*b-2*hmin,'two_ball_pitch_min_mm':pitch,'one_ball_capacity_margin_mm':pitch-(p['gate_spacing']+2*b-2*hmin),'held_rear_radial_center_mm':cam_positions(1,p)[1],'held_closed_blocking_margin_mm':R0+r-math.hypot(c1,E),'at_least_one_successful_exit_requires':'Finite forward progress against all drag; not established by fixed fan speed alone.'}
    report['recommendation']='Do not integrate three new interlocks as a mandatory change to this normal-point-shot version. If extra anti-partial-cycle behavior is desired, first model only the external full-stroke direction latch; occupancy/departure hardware remains an optional separate development with additional drag and force requirements.'
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'status':report['status'],'checks':checks,'ready':ready,'departure':departure},indent=2,ensure_ascii=False))
    return 0 if all(checks.values()) else 1
if __name__=='__main__':raise SystemExit(main())
