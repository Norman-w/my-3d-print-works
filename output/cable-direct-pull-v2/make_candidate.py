from pathlib import Path
import hashlib,json
O=Path(__file__).resolve().parent
B=O.parent/'cable-input-lip-candidate'/'candidate.scad'
assert hashlib.sha256(B.read_bytes()).hexdigest()=='491ded77149a2147f010092f7f715f59ef50a2dd714abb56677d596fb6544c9d'
s=B.read_text().replace('cil_','cdp_')
s=s.replace('cdp_theta_max=cdp_angle(cdp_stroke);','')
s=s.replace('// Independent direct-pull / fixed fairlead diagnosis. NOT RELEASED.','// Direct pull v2: 5 mm nominal axial lead-in; input adjuster budget +/-2 mm. NOT RELEASED.')
start=s.index('// Fixed core centreline bend:')
end=s.index('function cdp_stop_tip',start)
s=s[:start]+r'''
// The adjuster/ferrule move; clamping nuts/washers and the guide stay fixed.
cdp_delta=0;
cdp_delta_bounds=[-2,2];
cdp_adjuster_nominal_exit=[-29,60,2];
cdp_fairlead_C=[-24,0,2];
cdp_fairlead_R=60;
cdp_fairlead_surface_R=cdp_fairlead_R-cdp_wire_d/2;
cdp_fairlead_inner_R=53;
cdp_fairlead_extent_deg=8;
cdp_fairlead_step_deg=.1;
cdp_terminal=[0,60,2];
cdp_ball_arm_R=60;
cdp_cap_bolts=[[2,54],[2,66]];
assert(cdp_delta>=cdp_delta_bounds[0]&&cdp_delta<=cdp_delta_bounds[1],"Input M6 candidate budget is -2..2 mm only");
function cdp_exit(delta=cdp_delta)=[cdp_adjuster_nominal_exit[0]+delta,cdp_adjuster_nominal_exit[1],cdp_adjuster_nominal_exit[2]];
function cdp_axial_leadin(delta=cdp_delta)=cdp_fairlead_C[0]-cdp_exit(delta)[0];
function cdp_ferrule_mouth(delta=cdp_delta)=cdp_ferrule_mouth_display+delta;
function cdp_B(a)=[cdp_ball_arm_R*sin(a),cdp_ball_arm_R*cos(a),cdp_wire_z];
function cdp_phi(a)=let(p=cdp_B(a),x=p[0]-cdp_fairlead_C[0],y=p[1]-cdp_fairlead_C[1],d=sqrt(x*x+y*y)) max(0,atan2(x,y)-acos(cdp_fairlead_R/d));
function cdp_T(a)=let(p=cdp_phi(a))cdp_fairlead_C+[cdp_fairlead_R*sin(p),cdp_fairlead_R*cos(p),0];
function cdp_path_length(a,delta=cdp_delta)=let(p=cdp_B(a),x=p[0]-cdp_fairlead_C[0],y=p[1]-cdp_fairlead_C[1]) cdp_axial_leadin(delta)+cdp_fairlead_R*cdp_phi(a)*PI/180+sqrt(x*x+y*y-cdp_fairlead_R*cdp_fairlead_R);
function cdp_takeup(a,delta=cdp_delta)=cdp_path_length(a,delta)-cdp_path_length(0,delta);
function cdp_angle(u,delta=cdp_delta,lo=0,hi=30,n=0)=n>=48?(lo+hi)/2:let(m=(lo+hi)/2)cdp_takeup(m,delta)<u?cdp_angle(u,delta,m,hi,n+1):cdp_angle(u,delta,lo,m,n+1);
function cdp_effective_arm(u)=cdp_ball_arm_R*cos(cdp_angle(u)-cdp_phi(cdp_angle(u)));
function cdp_delta_max()=cdp_angle(22)-cdp_phi(cdp_angle(22));
function cdp_thread_exposure(delta=cdp_delta)=[3.2-delta,3.2+delta];
assert(cdp_axial_leadin()>=3,"At least 3 mm nominal straight core remains throughout the +/-2 budget");
cdp_theta_max=cdp_angle(cdp_stroke);

'''+s[end:]
# Remove misleading historical wrap API instead of carrying stale fields.
start=s.index('function cdp_legacy_wrap_spec_DO_NOT_USE()')
end=s.index('module cdp_contract()',start)
s=s[:start]+s[end:]
start=s.index('module cdp_legacy_wrap_probe_DO_NOT_USE(')
end=s.index('module cdp_assembly()',start)
s=s[:start]+s[end:]
s=s.replace('cdp_box(-45,-20,49,55,-12,-4);','cdp_box(-45,cdp_fairlead_C[0]+cdp_fairlead_surface_R*sin(cdp_fairlead_extent_deg)+1,49,55,-12,-4);')
s=s.replace('module cdp_local_fixed_hardware(){','module cdp_local_fixed_hardware(delta=cdp_delta){')
s=s.replace('cdp_local_adjuster();cdp_local_ferrule();','cdp_local_adjuster(delta);cdp_local_ferrule(delta);')
s=s.replace('module cdp_local_adjuster(){difference(){','module cdp_local_adjuster(delta=cdp_delta){translate([delta,0,0])difference(){')
s=s.replace('module cdp_local_ferrule(){difference(){','module cdp_local_ferrule(delta=cdp_delta){translate([delta,0,0])difference(){')
s=s.replace('module cdp_local_cable(u=cdp_u){','module cdp_local_cable(u=cdp_u,delta=cdp_delta){')
s=s.replace('cdp_xcyl(60,2,cdp_ferrule_mouth_display,-28.8-cdp_ferrule_mouth_display,1.5);','cdp_xcyl(cdp_exit(delta)[1],cdp_exit(delta)[2],cdp_ferrule_mouth(delta),cdp_fairlead_C[0]-cdp_ferrule_mouth(delta),cdp_wire_d);')
s=s.replace('translate([60,0,0])circle(d=1.5,$fn=24);','translate([cdp_fairlead_R,0,0])circle(d=cdp_wire_d,$fn=24);')
s=s.replace('cdp_seg(q,b,1.5);','cdp_seg(q,b,cdp_wire_d);')
s=s.replace('module cdp_fixed_hardware(){cdp_mount_hardware_cad();cdp_to_cad()cdp_local_fixed_hardware();}','module cdp_fixed_hardware(delta=cdp_delta){cdp_mount_hardware_cad();cdp_to_cad()cdp_local_fixed_hardware(delta);}')
s=s.replace('module cdp_cable(u=cdp_u){cdp_to_cad()cdp_local_cable(u);}','module cdp_cable(u=cdp_u,delta=cdp_delta){cdp_to_cad()cdp_local_cable(u,delta);}')
s=s.replace('module cdp_adjuster(){cdp_to_cad()cdp_local_adjuster();}','module cdp_adjuster(delta=cdp_delta){cdp_to_cad()cdp_local_adjuster(delta);}')
s=s.replace('module cdp_ferrule(){cdp_to_cad()cdp_local_ferrule();}','module cdp_ferrule(delta=cdp_delta){cdp_to_cad()cdp_local_ferrule(delta);}')
s=s.replace('module cdp_hardware(u=cdp_u){cdp_fixed_hardware();cdp_moving_hardware(u);cdp_cable(u);}','module cdp_hardware(u=cdp_u,delta=cdp_delta){cdp_fixed_hardware(delta);cdp_moving_hardware(u);cdp_cable(u,delta);}')
s=s.replace('module cdp_fixed(){cdp_body();cdp_cover();cdp_fixed_hardware();}','module cdp_fixed(delta=cdp_delta){cdp_body();cdp_cover();cdp_fixed_hardware(delta);}')
s=s.replace('// nuts enter from rear before mounting','// nuts enter from rear before mounting')
s=s.replace('// M3 nut roof at -.6; nut -.3? see hardware','// M3 nut roof at -.6; nut -3..-.6')
start=s.index('module cdp_guide_solid(){')
end=s.index('if(cdp_part=="assembly")',start)
s=s[:start]+r'''
module cdp_guide_solid(){
 n=ceil(cdp_fairlead_extent_deg/cdp_fairlead_step_deg);
 translate([cdp_fairlead_C[0],cdp_fairlead_C[1],-12])linear_extrude(height=19.5)polygon(concat(
  [for(i=[0:n])let(a=90-cdp_fairlead_extent_deg+i*cdp_fairlead_extent_deg/n)[cdp_fairlead_surface_R*cos(a),cdp_fairlead_surface_R*sin(a)]],
  [for(i=[n:-1:0])let(a=90-cdp_fairlead_extent_deg+i*cdp_fairlead_extent_deg/n)[cdp_fairlead_inner_R*cos(a),cdp_fairlead_inner_R*sin(a)]]));
}
module cdp_direct_contract(){echo(cdp_direct_contract=[
 ["status","DIAGNOSTIC_V2_NOT_RELEASED"],["units","mm"],["basis","feeder CAD"],["origin",cdp_origin],
 ["basis_x",[-cdp_s,0,cdp_s]],["basis_y",[cdp_s,0,cdp_s]],["basis_z",[0,1,0]],
 ["preserved","host mounting, axis stack, finger silhouette, two-screw terminal cap, main cover"],
 ["delta",cdp_delta],["delta_budget",cdp_delta_bounds],["nominal_exit",cdp_adjuster_nominal_exit],["actual_exit",cdp_exit()],
 ["fairlead_center",cdp_fairlead_C],["fairlead_core_R",cdp_fairlead_R],["fairlead_surface_R",cdp_fairlead_surface_R],
 ["fairlead_extent_deg",cdp_fairlead_extent_deg],["fairlead_facet_step_deg",cdp_fairlead_step_deg],
 ["axial_leadin",cdp_axial_leadin()],["adjuster_thread_x",[-53+cdp_delta,-29+cdp_delta]],
 ["adjuster_head_x",[-63+cdp_delta,-53+cdp_delta]],["ferrule_mouth_display_local",[cdp_ferrule_mouth(),60,2]],
 ["ferrule_tip_display_local",[cdp_ferrule_tip_display+cdp_delta,60,2]],["housing_stop_local",undef],
 ["nut_x_fixed",[for(x=cdp_adjuster_nut_x)[x,x+cdp_adjuster_nut_t]]],
 ["washer_x_fixed",[for(x=cdp_adjuster_washer_x)[x,x+cdp_adjuster_washer_t]]],
 ["thread_exposure",cdp_thread_exposure()],["u_samples",[for(u=[0,10,20,22])[u,cdp_angle(u),cdp_phi(cdp_angle(u)),cdp_path_length(cdp_angle(u)),cdp_effective_arm(u),36*sin(cdp_angle(u))]]],
 ["delta_samples",[for(d=[-2,0,2])[d,cdp_exit(d),cdp_axial_leadin(d),cdp_thread_exposure(d),cdp_path_length(0,d),cdp_path_length(cdp_angle(20),d),cdp_takeup(cdp_angle(20),d)]]],
 ["cap_bolts",cdp_cap_bolts],["cap_split_z",3.1],["cap_screw","2x M3x8 socket head D5.5 H3"],["cap_nut","2x M3 SW5.5 H2.4; z[-3,-.6]"],
 ["setup","delta is an assembly adjustment only: reseat housing/ferrule, retension at output and lock both nuts before defining zero"],
 ["unknown","actual cable friction/preload/bend endurance, ferrule seating, thread runout, print fit, housing route/service at delta bounds"],
 ["selectors",["body","lever","terminal-cap","cover","adjuster","ferrule","fixed-hardware","moving-hardware","cable","contract","assembly"]]
]);}
'''+s[end:]
s=s.replace('else if(cdp_part=="fixed-hardware")cdp_fixed_hardware();','else if(cdp_part=="adjuster")cdp_adjuster();\nelse if(cdp_part=="ferrule")cdp_ferrule();\nelse if(cdp_part=="fixed-hardware")cdp_fixed_hardware();')
assert '-28.8' not in s
(O/'candidate.scad').write_text(s)
(O/'source-identity.json').write_text(json.dumps({'baseline':str(B),'baseline_sha256':hashlib.sha256(B.read_bytes()).hexdigest(),'candidate_sha256':hashlib.sha256(s.encode()).hexdigest(),'official_cad_modified':False,'status':'DIAGNOSTIC_V2_UNVALIDATED'},indent=2)+'\n')
print(O/'candidate.scad')
