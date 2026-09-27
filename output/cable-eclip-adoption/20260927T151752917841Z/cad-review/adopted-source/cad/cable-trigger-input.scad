// Fixed-guide direct-pull input with HCDG8-30 pin / supplied NETW7 retention.
// Engineering design adopted; installed E-clip form, load and physical acceptance open.
// Nominal 5 mm lead, assembly setting +/-2 mm. See ci_spec() for one source contract.
include <parameters.scad>
// Cable trigger INPUT candidate. Units mm; X1C / .4 nozzle / PETG.
// Every public part returns FEEDER CAD coordinates. No host geometry is added.
// Local +X muzzle, +Y up, +Z outward. Clockwise is a rearward finger pull.
// Purchased hardware is an envelope candidate, NOT a printable component.
ci_part="assembly";
ci_u=0;
ci_probe_kind="motion";
ci_eps=.02;
ci_origin=[75,-85,5]; // Global host mounting holes and load faces remain unchanged.
ci_s=sqrt(.5);
ci_R=60;
ci_r=36;
ci_stroke=20;
ci_wire_d=1.5;
ci_wire_z=2;
ci_ball_d=5; // selected norelem core; nominal spherical terminal confirmed by 03096-14 drawing.
ci_ball_seat_d=5.6;
ci_adjuster_cone_display=1; // UNDIMENSIONED in supplier drawing; reference only.
ci_ferrule_cone_display=1; // same: L-L1=2, but division between taper/bore is unknown.
ci_ferrule_tip_display=-54.5+(7-5.5)/(7-3)*ci_adjuster_cone_display;
ci_ferrule_mouth_display=ci_ferrule_tip_display-11;
ci_adjuster_nut_part="07212-106"; // DIN439 / ISO4035 M6 SW10 H3.2, candidate supply.
ci_adjuster_nut_t=3.2;
ci_adjuster_washer_part="07300-106"; // M6 flat washer nominal OD12 / ID6.4 / t1.6.
ci_adjuster_washer_t=1.6;
ci_adjuster_nut_x=[-49.8,-35.4];
ci_adjuster_washer_x=[-46.6,-37];
ci_adjuster_tool_x=[-49.7,-35.3]; // 3 mm thin SW10 open-end tool budget; cover OFF.
ci_stop_setting=20; // adjustable equivalent output 16..22; install without balls/air

ci_cheek_posts=[[-30,20],[74,20]];
ci_axis_body_z=[-12,-4];
ci_axis_lever_z=[-3.5,7.5];
ci_axis_cover_z=[8,14];
// Axis design source. Purchased geometry below is nominal display, not factory CAD.
ci_axis_pin_part="HCDG8-30";
ci_axis_clip_part="NETW7"; // supplied member of the pin kit, not an extra purchase
ci_axis_pin_q=.7; // display pose only; instantaneous allowed coaxial float is 0..1.54
ci_axis_pin_L=30.05; // under-head to NEAR groove wall
ci_axis_pin_N=3;
ci_axis_pin_groove_M=.95;
ci_axis_pin_groove_d=7.045;
ci_axis_pin_D=7.9905;
ci_axis_pin_head_D=12;
ci_axis_pin_head_T=2;
ci_axis_bore_D=8.3;
ci_axis_root_relief_D=9.2;
ci_axis_root_relief_z=[11.3,14.3];
ci_axis_tail_washer_part="HRDW-M8-A2";
ci_axis_tail_washer_od_id_t=[15,8.5,1.6];
ci_axis_tail_washer_z=[-15.2,-13.6];
ci_axis_thrust_part="SWSPS16-10-.25";
ci_axis_thrust_od_id_t=[16,10,.25];
ci_axis_thrust_z=[-3.75,7.5];
ci_bush_af=12;
ci_bush_socket_af=12.4;
ci_bush_id=8.2;
ci_bush_length=11;
ci_bush_edge=.05;
ci_bush_bore_edge=.1;
ci_mount_key_x=[12.4,19.6]; // .4 from output bridge X12 and original grip arm X20.
ci_shoulder_clearance=.25;
$fn=72;
assert(ci_stop_setting>=16&&ci_stop_setting<=22,"Stop adjustment candidate range is 16..22 mm equivalent output");



// The adjuster/ferrule move; clamping nuts/washers and the guide stay fixed.
ci_delta=0;
ci_delta_bounds=[-2,2];
ci_adjuster_nominal_exit=[-29,60,2];
ci_fairlead_C=[-24,0,2];
ci_fairlead_R=60;
ci_fairlead_surface_R=ci_fairlead_R-ci_wire_d/2;
ci_fairlead_inner_R=53;
ci_fairlead_extent_deg=8;
ci_fairlead_step_deg=.1;
ci_terminal=[0,60,2];
ci_ball_arm_R=60;
ci_cap_bolts=[[2,54],[2,66]];
assert(ci_delta>=ci_delta_bounds[0]&&ci_delta<=ci_delta_bounds[1],"Input M6 candidate budget is -2..2 mm only");
function ci_exit(delta=ci_delta)=[ci_adjuster_nominal_exit[0]+delta,ci_adjuster_nominal_exit[1],ci_adjuster_nominal_exit[2]];
function ci_axial_leadin(delta=ci_delta)=ci_fairlead_C[0]-ci_exit(delta)[0];
function ci_ferrule_mouth(delta=ci_delta)=ci_ferrule_mouth_display+delta;
function ci_B(a)=[ci_ball_arm_R*sin(a),ci_ball_arm_R*cos(a),ci_wire_z];
function ci_phi(a)=let(p=ci_B(a),x=p[0]-ci_fairlead_C[0],y=p[1]-ci_fairlead_C[1],d=sqrt(x*x+y*y)) max(0,atan2(x,y)-acos(ci_fairlead_R/d));
function ci_T(a)=let(p=ci_phi(a))ci_fairlead_C+[ci_fairlead_R*sin(p),ci_fairlead_R*cos(p),0];
function ci_path_length(a,delta=ci_delta)=let(p=ci_B(a),x=p[0]-ci_fairlead_C[0],y=p[1]-ci_fairlead_C[1]) ci_axial_leadin(delta)+ci_fairlead_R*ci_phi(a)*PI/180+sqrt(x*x+y*y-ci_fairlead_R*ci_fairlead_R);
function ci_takeup(a,delta=ci_delta)=ci_path_length(a,delta)-ci_path_length(0,delta);
function ci_angle(u,delta=ci_delta,lo=0,hi=30,n=0)=assert(is_num(u)&&u>=0&&u<=22,"Input travel is restricted to 0..22 mm; system work stroke is 20")assert(abs(delta)<=2,"Input setting outside +/-2 mm")n>=48?(lo+hi)/2:let(m=(lo+hi)/2)ci_takeup(m,delta)<u?ci_angle(u,delta,m,hi,n+1):ci_angle(u,delta,lo,m,n+1);
function ci_effective_arm(u)=ci_ball_arm_R*cos(ci_angle(u)-ci_phi(ci_angle(u)));
function ci_delta_max()=ci_angle(22)-ci_phi(ci_angle(22));
function ci_thread_exposure(delta=ci_delta)=[3.2-delta,3.2+delta];
assert(ci_axial_leadin()>=3,"At least 3 mm nominal straight core remains throughout the +/-2 budget");
ci_theta_max=ci_angle(ci_stroke);

function ci_stop_tip(u=ci_stop_setting)=-4*cos(ci_angle(u))-26*sin(ci_angle(u))-5.5;
function ci_point(r,a,z=0)=[r*cos(a),r*sin(a),z];
function ci_local_to_cad(p)=[ci_origin[0]+ci_s*(-p[0]+p[1]),ci_origin[1]+p[2],ci_origin[2]+ci_s*(p[0]+p[1])];
function ci_cad_to_local(p)=[ci_s*(-p[0]+ci_origin[0]+p[2]-ci_origin[2]),ci_s*(p[0]-ci_origin[0]+p[2]-ci_origin[2]),p[1]-ci_origin[1]];
function ci_install_delta()=ci_delta;
function ci_spec()=[
 ["units","mm"],["status","eclip-axis-and-direct-pull-adopted-physical-acceptance-open"],
 ["public_coordinate_basis","feeder CAD"],["origin",ci_origin],
 ["basis_x",[-ci_s,0,ci_s]],["basis_y",[ci_s,0,ci_s]],["basis_z",[0,1,0]],
 ["motion_law","fixed-guide-direct-pull-v2"],
 ["ball_orbit_radius",ci_ball_arm_R],["fairlead_center",ci_fairlead_C],
 ["fairlead_core_radius",ci_fairlead_R],["fairlead_surface_radius",ci_fairlead_surface_R],
 ["fairlead_extent_deg",ci_fairlead_extent_deg],["wire_terminal_local",ci_terminal],
 ["angle_solve_deg",[0,30]],["input_u_domain",[0,22]],
 ["adjuster_delta",ci_delta],["adjuster_delta_range",ci_delta_bounds],
 ["axial_leadin",ci_axial_leadin()],["radius_cable",ci_R],
 ["radius_cable_semantics","legacy alias of guide core radius; not constant takeup arm"],["radius_finger",ci_r],["stroke",ci_stroke],
 ["angle_full_deg",ci_theta_max],["finger_rearward_full",ci_r*sin(ci_theta_max)],
 ["wire_d",ci_wire_d],["wire_z",ci_wire_z],["ball_d_candidate",ci_ball_d],
 ["wire_tangent_local",ci_fairlead_C+[0,ci_fairlead_R,0]],["adjuster_seat_local",[-45,60,2]],
 ["adjuster_exit_local",ci_exit()],
 ["housing_stop_local",undef],
 ["housing_stop_reason","supplier taper length and ferrule nose chamfer are undimensioned"],
 ["adjuster_head_x",[-63+ci_delta,-53+ci_delta]],["adjuster_head_sw",8],
 ["adjuster_inlet_d_depth",[7,8.5]],["adjuster_wire_bore",3],
 ["adjuster_cone_display_only",ci_adjuster_cone_display],
 ["adjuster_taper_depth_interval",[8.5,10]],["ferrule_nose_chamfer",undef],
 ["ferrule_part","03096-25-0350"],["ferrule_od_length",[5.5,11]],
 ["ferrule_inlet_d_depth",[5,9]],["ferrule_wire_bore",2.5],
 ["ferrule_mouth_display_local",[ci_ferrule_mouth(),60,2]],
 ["ferrule_tip_display_local",[ci_ferrule_tip_display+ci_delta,60,2]],
 ["housing_end_display_local",[ci_ferrule_mouth()+9,60,2]],
 ["adjuster_thread_x",[-53+ci_delta,-29+ci_delta]],["adjuster_overall_x",[-63+ci_delta,-29+ci_delta]],
 ["adjuster_shank_d",6],["housing_od",5],
 ["adjuster_nut_part",ci_adjuster_nut_part],["adjuster_nut_sw_t",[10,ci_adjuster_nut_t]],
 ["adjuster_nut_x",[for(x=ci_adjuster_nut_x)[x,x+ci_adjuster_nut_t]]],
 ["adjuster_washer_part",ci_adjuster_washer_part],
 ["adjuster_washer_od_id_t",[12,6.4,ci_adjuster_washer_t]],
 ["adjuster_washer_x",[for(x=ci_adjuster_washer_x)[x,x+ci_adjuster_washer_t]]],
 ["adjuster_seat_x",[-45,-37]],["adjuster_exposed_thread_each",min(ci_thread_exposure())],["adjuster_exposed_thread_sides",ci_thread_exposure()],
 ["adjuster_tool_budget",["SW10 thin open end, cover removed",3,20,25]],
 ["adjuster_tool_x",[for(x=ci_adjuster_tool_x)[x,x+3]]],
 ["body_axis_z",ci_axis_body_z],["lever_axis_z",ci_axis_lever_z],
 ["cover_axis_z",ci_axis_cover_z],
 ["axis_design","HCDG8-30-grooved-pin-with-supplied-NETW7"],
 ["axis_pin_part",ci_axis_pin_part],["axis_clip_part",ci_axis_clip_part],
 ["axis_bom_columns",["id","part","quantity","accounting","nominal"]],["axis_bom",ci_axis_bom()],
 ["axis_pin_nominal",[["L_near_groove",ci_axis_pin_L],["N_tail",ci_axis_pin_N],
  ["groove_width",ci_axis_pin_groove_M],["groove_root_d",ci_axis_pin_groove_d],
  ["shaft_d",ci_axis_pin_D],["head_d",ci_axis_pin_head_D],["head_t",ci_axis_pin_head_T]]],
 ["axis_pin_catalog_bounds",[["L_near_groove",[30,30.1]],["shaft_g6_d",[7.986,7.995]],
  ["groove_width",[.9,1]],["groove_root_d",[7,7.09]],["head_t",[1.9,2.1]]]],
 ["axis_pin_display_q",ci_axis_pin_q],["axis_pin_q_domain_nominal_H26",[0,1.54]],
 ["axis_pin_capture_float_limit_nominal_H26",[.4,1.54]],
 ["axis_capture_span_bounds",[26.4,27.54]],["axis_plastic_outer_span_nominal",26],
 ["axis_actual_span_acceptance_requirement",[25.7,26.3]],
 ["axis_pin_capture_float_limit_at_required_actual_span",[.1,1.84]],
 ["axis_bore_d",ci_axis_bore_D],["axis_root_relief_d_z",[ci_axis_root_relief_D,ci_axis_root_relief_z]],
 ["axis_engineering_bounds_not_supplier_guarantees",[["head_d_max",16],["tail_N_max",6],
  ["root_d_max",9],["root_length_max",2.5],["washer_od_nominal",15],
  ["installed_clip_radius_max",10],["clip_axial_overhang_beyond_groove_max",1]]],
 ["axis_space_scope","coaxial nominal H26; q0..1.54 only; actual H acceptance does not enlarge verified envelope"],
 ["axis_clip_space_local_z",[-18.1,-13.46]],["axis_clip_space_role","reference requirement, NOT actual installed E-ring solid"],
 ["axis_clip_actual_installed_envelope_verified",false],
 ["axis_clip_insertion_removal_tool_verified",false],
 ["axis_tail_washer_part",ci_axis_tail_washer_part],
 ["axis_tail_washer_od_id_t",ci_axis_tail_washer_od_id_t],["axis_tail_washer_z",ci_axis_tail_washer_z],
 ["axis_tail_washer_bounds",[["ID",[8.4,8.62]],["thickness",[1.4,1.8]],["OD_nominal",15]]],
 ["bush_shape","hexagonal external; cylindrical bore; machined unfilled POM-C"],
 ["bush_af_id_length",[ci_bush_af,ci_bush_id,ci_bush_length]],
 ["bush_acceptance_requirements",[["AF",[11.97,12]],["ID",[8.2,8.25]],["L",[10.97,11]],
  ["bore_cylindricity_max",.02],["bore_to_hex_position_diameter_max",.05],
  ["end_parallelism_max",.02],["end_perpendicularity_to_bore_max",.03],
  ["outer_edge_break_max",ci_bush_edge],["bore_edge_break_max",ci_bush_bore_edge]]],
 ["bush_supplier_grade_confirmed",false],["bush_socket_af",ci_bush_socket_af],
 ["bush_socket_actual_acceptance_af",[12.2,12.6]],
 ["thrust_washer_part",ci_axis_thrust_part],["thrust_washer_od_id_t",ci_axis_thrust_od_id_t],
 ["thrust_washer_z",ci_axis_thrust_z],["thrust_washer_bounds",[["OD",[15.5,16]],["ID",[10,10.5]],["thickness",[.225,.275]]]],
 ["rotor_nominal_axial_float",.5],["rotor_float_semantics","12 mm inner cheek span minus 11 mm bush/lever and two .25 mm internal washers; independent of whole-pin capture float"],
 ["axis_adoption","engineering geometry and parts contract adopted; manufacturing and physical acceptance false"],
 ["axis_physical_acceptance",false],["manufacturing_release",false],
 ["stop_setting",ci_stop_setting],["stop_setting_range",[16,22]],
 ["stop_tip_x",ci_stop_tip()],["stop_tip_x_range",[ci_stop_tip(16),ci_stop_tip(22)]],
 ["stop_axis_local_yz",[-24,2]],["stop_screw","M3x30; captured nut plus locknut"],
 ["mount_holes_cad",[for(x=[-16,16],z=[-60,3])[x,-94,z]]],
 ["mount_plate_y",[-94,-86]],["mount_rib_y",[-86,-54]],
 ["mount_rib_lower_z",-65.7],["right_mount_rib_outer_x",21.7],
 ["upper_mount_key_x",ci_mount_key_x],
 ["mount_bolt","M4x60; replace old M4x20"],
 ["mount_bolt_underhead_y",-94.8],["mount_bolt_tip_y",-34.8],
 ["cap_bolts_local_xy",ci_cap_bolts],["cap_split_local_z",3.1],
 ["cap_fasteners",[["M3x8 socket screw D5.5 H3",2],["M3 nut SW5.5 H2.4",2]]],
 ["setup","Lock delta after reseating housing and resetting output core zero; stop coordinated to output stroke"],
 ["part_selectors",["assembly","body","lever","terminal-cap","cover","fixed-hardware","moving-hardware","axis-pin","tail-washers","bush","thrust-washers","axis-space","eclip-space","adjuster","ferrule","cable","probe","contract"]]
];

// Physical member count includes the supplied clip once; purchase roots do not.
function ci_axis_bom()=[
 ["axis-pin-kit",ci_axis_pin_part,1,"purchase-root-kit",[["supplied_clip",ci_axis_clip_part],["L_near_groove",ci_axis_pin_L]]],
 ["axis-supplied-clip",ci_axis_clip_part,1,"nonadditive-member-of-axis-pin-kit",[["actual_installed_geometry_verified",false]]],
 ["axis-tail-washer",ci_axis_tail_washer_part,2,"separate-purchase",[["OD_ID_t",ci_axis_tail_washer_od_id_t]]],
 ["axis-bush","machined-unfilled-POM-C",1,"machined-part-not-PETG-print",[["AF_ID_L",[ci_bush_af,ci_bush_id,ci_bush_length]]]],
 ["axis-thrust-washer",ci_axis_thrust_part,2,"separate-purchase",[["OD_ID_t",ci_axis_thrust_od_id_t]]]
];
module ci_contract(){echo(ci_contract=ci_spec());}
module ci_to_cad(){multmatrix([
 [-ci_s,ci_s,0,ci_origin[0]],[0,0,1,ci_origin[1]],[ci_s,ci_s,0,ci_origin[2]],[0,0,0,1]])children();}
module ci_from_cad(){multmatrix([
 [-ci_s,0,ci_s,(ci_origin[0]-ci_origin[2])*ci_s],[ci_s,0,ci_s,-(ci_origin[0]+ci_origin[2])*ci_s],[0,1,0,-ci_origin[1]],[0,0,0,1]])children();}
module ci_box(x0,x1,y0,y1,z0,z1){translate([x0,y0,z0])cube([x1-x0,y1-y0,z1-z0]);}
module ci_zcyl(x,y,z,h,d){translate([x,y,z])cylinder(h=h,d=d);}
module ci_xcyl(y,z,x,h,d){translate([x,y,z])rotate([0,90,0])cylinder(h=h,d=d);}
module ci_ycyl(x,z,y,h,d){translate([x,y,z])rotate([-90,0,0])cylinder(h=h,d=d);}
module ci_zhex(x,y,z,h,af){translate([x,y,z])rotate([0,0,30])cylinder(h=h,d=af/cos(30),$fn=6);}
module ci_xhex(y,z,x,h,af){translate([x,y,z])rotate([0,90,0])rotate([0,0,30])cylinder(h=h,d=af/cos(30),$fn=6);}
module ci_yhex(x,z,y,h,af){translate([x,y,z])rotate([-90,0,0])rotate([0,0,30])cylinder(h=h,d=af/cos(30),$fn=6);}
module ci_sector(r0,r1,a0,a1,z0,z1){
 n=max(2,ceil((a1-a0)/2));
 translate([0,0,z0])linear_extrude(height=z1-z0)polygon(concat(
  [for(i=[0:n])[r1*cos(a0+(a1-a0)*i/n),r1*sin(a0+(a1-a0)*i/n)]],
  [for(i=[n:-1:0])[r0*cos(a0+(a1-a0)*i/n),r0*sin(a0+(a1-a0)*i/n)]]));
}
module ci_web(a,b,r,z0,z1){hull(){ci_zcyl(a[0],a[1],z0,z1-z0,2*r);ci_zcyl(b[0],b[1],z0,z1-z0,2*r);}}
module ci_zring(x,y,z,h,od,id){difference(){ci_zcyl(x,y,z,h,od);ci_zcyl(x,y,z-ci_eps,h+2*ci_eps,id);}}
module ci_xring(x,h,od,id){difference(){ci_xcyl(60,2,x,h,od);ci_xcyl(60,2,x-ci_eps,h+2*ci_eps,id);}}
module ci_xnut(x,af,h,id){difference(){ci_xhex(60,2,x,h,af);ci_xcyl(60,2,x-ci_eps,h+2*ci_eps,id);}}
module ci_zbolt(x,y,z_under,length,d,head_d,head_h,socket){
 ci_zcyl(x,y,z_under-length,length,d);
 difference(){ci_zcyl(x,y,z_under,head_h,head_d);ci_zhex(x,y,z_under+head_h/2,head_h/2+ci_eps,socket);}
}

// An H section has continuous 32 mm-deep webs. It is not four isolated posts.
// Keys straddle the ORIGINAL beam edges, without changing its source.
module ci_mount_cad_blank(){
 ci_box(-28.2,28.2,-94,-86,-68,28);
 // Clearance from the old strain-relief end Z=-66 and grip arm X=22.
 // These are not datum faces; retain the actual Y=-54 load face unchanged.
 for(x=[-16,16])ci_box(x-6,x>0?21.7:x+6,-86.1,-54,-65.7,9);
 ci_box(-22,22,-86.1,-54,-33,-27);
 // Side keys are over the original flat panel, away from its grip arms.
 for(s=[-1,1]){
  ci_box(s>0?20:-28.2,s>0?28.2:-20,-86.1,-54,-50,-20);
  ci_box(s>0?24.2:-28.2,s>0?28.2:-24.2,-54.1,-49,-50,-20);
 }
 // Key's full-depth root overlaps the backplate at Z22..28, Y-94..-86.
 // Narrow it between the actual output bridge X12 and old grip arm X20.
 ci_box(ci_mount_key_x[0],ci_mount_key_x[1],-94,-54,22,32.2);
 ci_box(ci_mount_key_x[0],ci_mount_key_x[1],-54.1,-49,28.2,32.2);
}
module ci_mount_cad(){difference(){ci_mount_cad_blank();
 for(x=[-16,16],z=[-60,3])ci_ycyl(x,z,-96,44,4.5);
}}
module ci_local_body_blank(){union(){
 ci_from_cad()ci_mount_cad();
 ci_web([0,0],ci_cad_to_local([0,-90,-28]),12,-12,-4);
 // Back cheek and continuous planar ribs join grip, cable reaction and host.
 ci_web([0,0],[-52,6],12,-12,-4);
 ci_web([-52,6],[-45,60],10,-12,-4);
 ci_web([0,0],[-45,60],7,-12,-4);
 ci_web([0,0],[74,20],7,-12,-4);
 ci_web([-52,6],[-64,-99],15,-12,14);
 for(p=ci_cheek_posts){ci_zcyl(p[0],p[1],-12,20,14);
  translate([p[0]-4,p[1]-4,7.9])cube([8,8,1.6]);}
 // M6 thin nuts + metal washers clamp this seat; tighten on bench before cover.
 ci_box(-45,-37,49,71,-12,12);
 // Adjustable trigger stop; rear tool entry tunnels through the fixed grip.
 ci_box(-42,-29,-34,-18,-12,12);

 // Fixed R59.25 guide surface + .75 wire radius gives R60 centreline.
 // All additions grow from Z=-12. The back rib joins the existing M6 root.
 ci_box(-45,ci_fairlead_C[0]+ci_fairlead_surface_R*sin(ci_fairlead_extent_deg)+1,49,55,-12,-4);
 ci_guide_solid();
 // Actual end stops: lug lives at 177..183 degrees at rest.
 ci_sector(14,22,183,193,-4.1,8);
}}
module ci_local_body(){difference(){
 ci_local_body_blank();
 ci_zcyl(0,0,-13,28,ci_axis_bore_D); // free through pin; no old distance-tube seat
 for(p=ci_cheek_posts){
  ci_zcyl(p[0],p[1],-13,30,3.4);
  ci_zhex(p[0],p[1],-12.1,3.1,5.8); // nuts enter from rear before mounting
 }
 ci_xcyl(60,2,-51,24,6.4);
 // OD12 washer edges would merely kiss the back rib Z=-4. Give .3 radial
 // clearance outside the load faces only; preserve the full 8 mm seat.
 ci_xcyl(60,2,-46.9,1.9,12.6);
 ci_xcyl(60,2,-37,1.9,12.6);
 // Thin wrench plane pockets: continuous rear material remains >=3.7 mm.
 // These are bench-service recesses, not in-place cover-on adjustment claims.
 for(x=ci_adjuster_tool_x)hull(){
  ci_xcyl(60,2,x-.2,3.4,20.6);ci_xcyl(85,2,x-.2,3.4,20.6);
 }
 ci_xcyl(-24,2,-90,63,3.4);
 ci_xcyl(-24,2,-90,51.8,7.2); // screw head + hex tool access from local -X
 // M3 nut loaded against X=-32.6; enters from rear before the screw.
 translate([-38.3,-24,2])rotate([0,90,0])rotate([0,0,30])cylinder(h=5.7,d=5.8/cos(30),$fn=6);
 // Re-cut host bolt paths after ALL brace unions; do not refill the holes.
 ci_from_cad()for(x=[-16,16],z=[-60,3])ci_ycyl(x,z,-100,50,4.5);
}}


module ci_direct_fan(z0=.9,z1=3.2){
 // Exact angular bound of terminal -> tangent line in rotating coordinates.
 // The .01 extra radial offset encloses polygonal/numeric error; no mesh welding.
 translate([0,60,z0])linear_extrude(height=z1-z0)offset(r=1.11,$fn=72)
 polygon(concat([[0,0]],[for(a=[180:.25:180+ci_delta_max()]) [65*cos(a),65*sin(a)]],
 [[65*cos(180+ci_delta_max()),65*sin(180+ci_delta_max())]]));
}
module ci_local_lever_blank(){union(){
 // Axis, finger silhouette and return-stop lug are preserved literally.
 ci_zcyl(0,0,-3.5,11,24);
 ci_web([0,0],[-4,-26],5.5,-3.5,7.5);
 ci_web([-4,-26],[1,-42],5,-3.5,7.5);
 ci_sector(10,22,177,183,-3.5,7.5);
 // The former spool spokes/rim are replaced by a 14 mm planar pull arm.
 ci_web([0,0],[0,54],7,-3.5,3.1);
 ci_web([0,54],[0,66],7,-3.5,3.1);
}}
// Retain the frozen Boolean construction partition for exact export comparison.
// The old round construction opening is wholly contained by the new hex socket.
module ci_local_lever_before_hex_socket(){difference(){
 ci_local_lever_blank();
 ci_zcyl(0,0,-4,12,12.2);
 translate(ci_terminal)sphere(d=5.6);
 ci_zcyl(0,60,2,3,5.6); // upward load entry before cap installation
 ci_direct_fan();
 for(p=ci_cap_bolts){
  ci_zcyl(p[0],p[1],-4,9,3.4);
  ci_zhex(p[0],p[1],-3.6,3.0,5.8); // M3 nut roof at -.6; nut -3..-.6
 }
}}
module ci_local_lever_zero(){difference(){
 ci_local_lever_before_hex_socket();
 translate([0,0,-4])linear_extrude(height=12)ci_bush_hex_2d(ci_bush_socket_af);
}}
module ci_local_terminal_cap(sweep=0){difference(){
 ci_web([0,54],[0,66],7,3.1,7.5+sweep);
 translate(ci_terminal)sphere(d=5.6);
 for(p=ci_cap_bolts){
  ci_zcyl(p[0],p[1],3,5+sweep,3.4);
  ci_zcyl(p[0],p[1],4.5+sweep,3.1,6.2);
 }
}}
module ci_local_lever(u=ci_u){rotate([0,0,-ci_angle(u)])ci_local_lever_zero();}
module ci_terminal_cap(u=ci_u){ci_to_cad()rotate([0,0,-ci_angle(u)])ci_local_terminal_cap();}
module ci_local_terminal_fasteners(){for(p=ci_cap_bolts){
 // Candidate standard M3x8 socket-head: D5.5 H3, SW2.5; M3 nut SW5.5 H2.4.
 ci_zbolt(p[0],p[1],4.5,8,3,5.5,3,2.5);
 difference(){ci_zhex(p[0],p[1],-3,2.4,5.5);ci_zcyl(p[0],p[1],-3.1,2.6,3.1);}
}}

module ci_local_cover_blank(sweep=0){union(){
 ci_zcyl(0,0,8,6+sweep,24);
 ci_sector(49,67,15,122,8,14+sweep);
 ci_web([0,0],[-30,20],7,8,14+sweep);
 ci_web([0,0],[74,20],7,8,14+sweep);
 ci_web([-30,20],[-28,54],6.5,8,14+sweep);
 ci_web([74,20],[62,30],7,8,14+sweep);
 for(p=ci_cheek_posts)ci_zcyl(p[0],p[1],8,6+sweep,16);
}}
// These construction holes are fully swallowed by the final D8.3 through bore;
// no old spacer seat survives. Preserve the reviewed native Boolean partition.
module ci_local_cover_before_through_bore(sweep=0){difference(){
 ci_local_cover_blank(sweep);
 ci_zcyl(0,0,7,8+sweep,4.5);
 ci_zcyl(0,0,7.9,1.6,8.3);
 for(p=ci_cheek_posts){
  ci_zcyl(p[0],p[1],7,9+sweep,3.4);
  translate([p[0]-4.2,p[1]-4.2,7.9])cube([8.4,8.4,1.8]);
 }
}}

module ci_local_cover_through(sweep=0){difference(){
 ci_local_cover_before_through_bore(sweep);
 ci_zcyl(0,0,7,8+sweep,ci_axis_bore_D);
}}
module ci_local_cover(sweep=0){difference(){
 ci_local_cover_through(sweep);
 // Continuous +Z sweep: the wider recess stays at the leading outer end.
 ci_zcyl(0,0,ci_axis_root_relief_z[0]+sweep,
   ci_axis_root_relief_z[1]-ci_axis_root_relief_z[0],ci_axis_root_relief_D);
}}
module ci_mount_hardware_cad(){for(x=[-16,16],z=[-60,3]){
 // Original four host nuts remain in parent. Replace old screws AND their washers once.
 ci_ycyl(x,z,-94.8,60,4);
 difference(){ci_ycyl(x,z,-98.8,4,7);ci_yhex(x,z,-98.9,2.1,3);}
 difference(){ci_ycyl(x,z,-94.8,.8,9);ci_ycyl(x,z,-94.9,1,4.3);}
}}
// Other fixed hardware excludes all central axis parts and global mount bolts.
module ci_local_other_fixed_hardware(delta=ci_delta){
 for(p=ci_cheek_posts){
  ci_zbolt(p[0],p[1],14.5,30,3,5.5,3,2.5);
  ci_zring(p[0],p[1],14,.5,7,3.2);
  difference(){ci_zhex(p[0],p[1],-11.4,2.4,5.5);ci_zcyl(p[0],p[1],-11.5,2.6,3.1);}
 }
 ci_local_adjuster(delta);ci_local_ferrule(delta);
 for(x=ci_adjuster_nut_x)ci_xnut(x,10,ci_adjuster_nut_t,6.1);
 for(x=ci_adjuster_washer_x)ci_xring(x,ci_adjuster_washer_t,12,6.4);
 // Adjustable M3 end stop: real screw, rear captive nut and accessible locknut.
 sx=ci_stop_tip();
 ci_xcyl(-24,2,sx-30,30,3);
 difference(){ci_xcyl(-24,2,sx-33,3,5.5);
  translate([sx-33.1,-24,2])rotate([0,90,0])rotate([0,0,30])cylinder(h=1.7,d=2.5/cos(30),$fn=6);}
 for(x=[-35,-29])difference(){
  translate([x,-24,2])rotate([0,90,0])rotate([0,0,30])cylinder(h=2.4,d=5.5/cos(30),$fn=6);
  ci_xcyl(-24,2,x-.1,2.6,3.1);
 }
}
// Drawing-derived outside/bores. The unmarked taper is a display parameter,
// never used to certify an exact housing reaction coordinate.
module ci_local_adjuster(delta=ci_delta){translate([delta,0,0])difference(){
 union(){ci_xhex(60,2,-63,10,8);ci_xcyl(60,2,-53,24,6);}
 ci_xcyl(60,2,-63.1,8.6,7);
 translate([-54.5,60,2])rotate([0,90,0])cylinder(h=ci_adjuster_cone_display,d1=7,d2=3);
 ci_xcyl(60,2,-54.5+ci_adjuster_cone_display-ci_eps,
   25.6-ci_adjuster_cone_display,3);
}}
module ci_local_ferrule(delta=ci_delta){translate([delta,0,0])difference(){
 ci_xcyl(60,2,ci_ferrule_mouth_display,11,5.5);
 ci_xcyl(60,2,ci_ferrule_mouth_display-ci_eps,9+ci_eps,5);
 translate([ci_ferrule_mouth_display+9,60,2])rotate([0,90,0])
  cylinder(h=ci_ferrule_cone_display,d1=5,d2=2.5);
 ci_xcyl(60,2,ci_ferrule_mouth_display-ci_eps,11+2*ci_eps,2.5);
}}

module ci_bush_hex_2d(af=ci_bush_af){rotate(30)circle(d=af/cos(30),$fn=6);}
module ci_local_bush_zero(){z=2-ci_bush_length/2;difference(){
 union(){
  translate([0,0,z])linear_extrude(height=ci_bush_edge,scale=ci_bush_af/(ci_bush_af-2*ci_bush_edge))ci_bush_hex_2d(ci_bush_af-2*ci_bush_edge);
  translate([0,0,z+ci_bush_edge])linear_extrude(height=ci_bush_length-2*ci_bush_edge)ci_bush_hex_2d();
  translate([0,0,z+ci_bush_length-ci_bush_edge])linear_extrude(height=ci_bush_edge,scale=(ci_bush_af-2*ci_bush_edge)/ci_bush_af)ci_bush_hex_2d();
 }
 ci_zcyl(0,0,z-.01,ci_bush_length+.02,ci_bush_id);
 translate([0,0,z])cylinder(h=ci_bush_bore_edge,d1=ci_bush_id+2*ci_bush_bore_edge,d2=ci_bush_id);
 translate([0,0,z+ci_bush_length-ci_bush_bore_edge])cylinder(h=ci_bush_bore_edge,d1=ci_bush_id,d2=ci_bush_id+2*ci_bush_bore_edge);
}}
module ci_local_axis_ring(z,h,od,id){difference(){
 ci_zcyl(0,0,z,h,od);ci_zcyl(0,0,z-.01,h+.02,id);
}}
// Catalogue nominal pin only, not supplier exact shape or a clearance proof.
module ci_local_axis_pin(q=ci_axis_pin_q){
 zhead=14+q;
 difference(){union(){
  ci_zcyl(0,0,zhead-ci_axis_pin_L-ci_axis_pin_N,ci_axis_pin_L+ci_axis_pin_N,ci_axis_pin_D);
  ci_zcyl(0,0,zhead,ci_axis_pin_head_T,ci_axis_pin_head_D);
 }
 ci_local_axis_ring(zhead-ci_axis_pin_L-ci_axis_pin_groove_M,ci_axis_pin_groove_M,ci_axis_pin_head_D+1,ci_axis_pin_groove_d);
 // These under-head relief dimensions are reference dimensions, not tolerances.
 ci_local_axis_ring(zhead-1.5,1.5,ci_axis_pin_head_D+1,7.75);
}}
module ci_local_tail_washers(){for(z=ci_axis_tail_washer_z)
 ci_local_axis_ring(z,ci_axis_tail_washer_od_id_t[2],ci_axis_tail_washer_od_id_t[0],ci_axis_tail_washer_od_id_t[1]);}
module ci_local_thrust_washers(){for(z=ci_axis_thrust_z)
 ci_local_axis_ring(z,ci_axis_thrust_od_id_t[2],ci_axis_thrust_od_id_t[0],ci_axis_thrust_od_id_t[1]);}
module ci_local_fixed_axis_hardware(){ci_local_axis_pin();ci_local_tail_washers();ci_local_thrust_washers();}
module ci_local_fixed_hardware(delta=ci_delta){ci_local_fixed_axis_hardware();ci_local_other_fixed_hardware(delta);}
module ci_local_bush(u=ci_u){rotate([0,0,-ci_angle(u)])ci_local_bush_zero();}
module ci_local_other_moving_hardware(u=ci_u){rotate([0,0,-ci_angle(u)]){
 translate(ci_terminal)sphere(d=5);ci_local_terminal_fasteners();
}}
module ci_local_moving_hardware(u=ci_u){ci_local_bush(u);ci_local_other_moving_hardware(u);}
// Engineering acceptance SPACE only. Never union these volumes into real hardware.
module ci_local_eclip_space(){ci_zcyl(0,0,-18.1,4.64,20/cos(180/72));}
module ci_local_axis_space(){k=1/cos(180/72);
 ci_zcyl(0,0,-22.1,37.64,8*k);ci_zcyl(0,0,11.5,4.04,9*k);
 ci_zcyl(0,0,14,3.64,16*k);ci_local_axis_ring(-17.1,5.1,15*k,8.4);
}
module ci_seg(a,b,d=1.5){hull(){translate(a)sphere(d=d,$fn=24);translate(b)sphere(d=d,$fn=24);}}
module ci_local_cable(u=ci_u,delta=ci_delta){
 a=ci_angle(u);p=ci_phi(a);q=ci_T(a);b=ci_B(a);
 ci_xcyl(ci_exit(delta)[1],ci_exit(delta)[2],ci_ferrule_mouth(delta),ci_fairlead_C[0]-ci_ferrule_mouth(delta),ci_wire_d);
 if(p>.00001)translate(ci_fairlead_C)rotate([0,0,90-p])rotate_extrude(angle=p,$fn=7200)
  translate([ci_fairlead_R,0,0])circle(d=ci_wire_d,$fn=24);
 ci_seg(q,b,ci_wire_d);
}

// Explicit tool budget, not an assertion that an unspecified purchased wrench fits.
// Opens toward -Y and enters from +Y. Flat gap10.4 clears the SW10 nut.
// sweep=25 is its continuous straight entry; actual tool width/thickness must fit.
module ci_local_adjuster_tool(index=0,sweep=0){
 x=ci_adjuster_tool_x[index];
 difference(){
  hull(){ci_xcyl(60,2,x,3,20);ci_xcyl(60+sweep,2,x,3,20);}
  ci_box(x-.1,x+3.1,-100,66,-3.2,7.2);
 }
 ci_box(x,x+3,69,105+sweep,-1,5);
}
module ci_axis_pin(){ci_to_cad()ci_local_axis_pin();}
module ci_tail_washers(){ci_to_cad()ci_local_tail_washers();}
module ci_thrust_washers(){ci_to_cad()ci_local_thrust_washers();}
module ci_bush(u=ci_u){ci_to_cad()ci_local_bush(u);}
module ci_axis_space(){ci_to_cad()ci_local_axis_space();}
module ci_eclip_space(){ci_to_cad()ci_local_eclip_space();}
module ci_body(){ci_to_cad()ci_local_body();}
module ci_lever(u=ci_u){ci_to_cad()ci_local_lever(u);}
module ci_cover(){ci_to_cad()ci_local_cover();}
module ci_fixed_hardware(delta=ci_delta){ci_mount_hardware_cad();ci_to_cad()ci_local_fixed_hardware(delta);}
module ci_moving_hardware(u=ci_u){ci_to_cad()ci_local_moving_hardware(u);}
module ci_cable(u=ci_u,delta=ci_delta){ci_to_cad()ci_local_cable(u,delta);}
module ci_adjuster(delta=ci_delta){ci_to_cad()ci_local_adjuster(delta);}
module ci_ferrule(delta=ci_delta){ci_to_cad()ci_local_ferrule(delta);}
module ci_hardware(u=ci_u,delta=ci_delta){ci_fixed_hardware(delta);ci_moving_hardware(u);ci_cable(u,delta);}
module ci_fixed(delta=ci_delta){ci_body();ci_cover();ci_fixed_hardware(delta);}
module ci_moving(u=ci_u){ci_lever(u);ci_terminal_cap(u);ci_moving_hardware(u);}
module ci_probe(kind=ci_probe_kind,u=ci_u){
 if(kind=="motion")intersection(){ci_fixed();ci_moving(u);}
 else if(kind=="printed-fixed")intersection(){ci_body();ci_cover();}
 else if(kind=="hardware-fit")intersection(){union(){ci_body();ci_cover();ci_lever(u);ci_terminal_cap(u);}ci_hardware(u);}
 else if(kind=="cable-fit")intersection(){union(){ci_body();ci_cover();ci_lever(u);ci_terminal_cap(u);}ci_cable(u);}
 else if(kind=="adjuster-washer-fit")intersection(){union(){ci_body();ci_cover();ci_lever(u);ci_terminal_cap(u);}ci_to_cad()for(x=ci_adjuster_washer_x)ci_xring(x,ci_adjuster_washer_t,12,6.4);}
 else if(kind=="adjuster-tool")intersection(){union(){ci_body();ci_lever(u);ci_terminal_cap(u);ci_fixed_hardware();}ci_to_cad()for(i=[0,1])ci_local_adjuster_tool(i,25);}
 else if(kind=="terminal-entry")intersection(){ci_lever(u);ci_to_cad()rotate([0,0,-ci_angle(u)])hull(){
  translate(ci_terminal)sphere(d=5);translate(ci_terminal+[0,0,20])sphere(d=5);}}
 else if(kind=="stop-contact")intersection(){ci_lever(u);ci_to_cad()ci_xcyl(-24,2,ci_stop_tip()-30,30,3);}
 else if(kind=="stop-tool")intersection(){union(){ci_body();ci_cover();ci_lever(u);ci_terminal_cap(u);}ci_to_cad(){
  ci_xcyl(-24,2,-100,100+ci_stop_tip()-33,4);
  translate([ci_stop_tip()-33,-24,2])rotate([0,90,0])rotate([0,0,30])cylinder(h=1.5,d=2.5/cos(30),$fn=6);}}
 // Continuous extrusion sweep preserves concave outline and every opening.
 else if(kind=="cover-removal")intersection(){union(){ci_body();ci_lever(u);ci_terminal_cap(u);ci_moving_hardware(u);}ci_to_cad()ci_local_cover(25);}
 else assert(false,str("Unknown ci_probe: ",kind));
}

module ci_assembly(){
 color([.19,.35,.45])ci_body();color([.12,.65,.85]){ci_lever();ci_terminal_cap();}
 color([.54,.68,.75,.7])ci_cover();color([.73,.75,.79])ci_hardware();
}


module ci_guide_solid(){
 n=ceil(ci_fairlead_extent_deg/ci_fairlead_step_deg);
 translate([ci_fairlead_C[0],ci_fairlead_C[1],-12])linear_extrude(height=19.5)polygon(concat(
  [for(i=[0:n])let(a=90-ci_fairlead_extent_deg+i*ci_fairlead_extent_deg/n)[ci_fairlead_surface_R*cos(a),ci_fairlead_surface_R*sin(a)]],
  [for(i=[n:-1:0])let(a=90-ci_fairlead_extent_deg+i*ci_fairlead_extent_deg/n)[ci_fairlead_inner_R*cos(a),ci_fairlead_inner_R*sin(a)]]));
}
// Compatibility echo entry with the SAME current contract, not old axis claims.
module ci_direct_contract(){echo(ci_direct_contract=ci_spec());}

if(ci_part=="assembly")ci_assembly();
else if(ci_part=="body")ci_body();
else if(ci_part=="lever")ci_lever();
else if(ci_part=="terminal-cap")ci_terminal_cap();
else if(ci_part=="cover")ci_cover();
else if(ci_part=="adjuster")ci_adjuster();
else if(ci_part=="ferrule")ci_ferrule();
else if(ci_part=="fixed-hardware")ci_fixed_hardware();
else if(ci_part=="moving-hardware")ci_moving_hardware();
else if(ci_part=="axis-pin")ci_axis_pin();
else if(ci_part=="tail-washers")ci_tail_washers();
else if(ci_part=="bush")ci_bush();
else if(ci_part=="thrust-washers")ci_thrust_washers();
else if(ci_part=="axis-space")ci_axis_space();
else if(ci_part=="eclip-space")ci_eclip_space();
else if(ci_part=="cable")ci_cable();
else if(ci_part=="probe")ci_probe();
else if(ci_part=="contract")ci_contract();
else if(ci_part!="none")assert(false,str("Unknown ci_part: ",ci_part));
