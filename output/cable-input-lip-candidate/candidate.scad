// Independent direct-pull / fixed fairlead diagnosis. NOT RELEASED.
include </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/parameters.scad>
// Cable trigger INPUT candidate. Units mm; X1C / .4 nozzle / PETG.
// Every public part returns FEEDER CAD coordinates. No host geometry is added.
// Local +X muzzle, +Y up, +Z outward. Clockwise is a rearward finger pull.
// Purchased hardware is an envelope candidate, NOT a printable component.
cil_part="none";
cil_u=0;
cil_probe_kind="motion";
cil_eps=.02;
cil_origin=[75,-82,5];
cil_s=sqrt(.5);
cil_R=60;
cil_r=36;
cil_stroke=20;
cil_wire_d=1.5;
cil_wire_z=2;
cil_ball_d=5; // selected norelem core; nominal spherical terminal confirmed by 03096-14 drawing.
cil_ball_seat_d=5.6;
cil_adjuster_cone_display=1; // UNDIMENSIONED in supplier drawing; reference only.
cil_ferrule_cone_display=1; // same: L-L1=2, but division between taper/bore is unknown.
cil_ferrule_tip_display=-54.5+(7-5.5)/(7-3)*cil_adjuster_cone_display;
cil_ferrule_mouth_display=cil_ferrule_tip_display-11;
cil_adjuster_nut_part="07212-106"; // DIN439 / ISO4035 M6 SW10 H3.2, candidate supply.
cil_adjuster_nut_t=3.2;
cil_adjuster_washer_part="07300-106"; // M6 flat washer nominal OD12 / ID6.4 / t1.6.
cil_adjuster_washer_t=1.6;
cil_adjuster_nut_x=[-49.8,-35.4];
cil_adjuster_washer_x=[-46.6,-37];
cil_adjuster_tool_x=[-49.7,-35.3]; // 3 mm thin SW10 open-end tool budget; cover OFF.
cil_stop_setting=20; // adjustable equivalent output 16..22; install without balls/air
cil_theta_max=cil_angle(cil_stroke);
cil_cheek_posts=[[-30,20],[74,20]];
cil_axis_body_z=[-12,-4];
cil_axis_lever_z=[-3.5,7.5];
cil_axis_cover_z=[8,14];
cil_axis_sleeve_z=[-5.5,9.5];
cil_mount_key_x=[12.4,19.6]; // .4 from output bridge X12 and original grip arm X20.
cil_shoulder_clearance=.25;
$fn=72;
assert(cil_stop_setting>=16&&cil_stop_setting<=22,"Stop adjustment candidate range is 16..22 mm equivalent output");


// Fixed core centreline bend: R60, tangent to the existing axial bore.
// The .2 mm axial gap keeps the new guide clear of the metal end face.
cil_fairlead_C=[-28.8,0,2];
cil_fairlead_R=60;
cil_terminal=[0,60,2];
cil_cap_bolts=[[2,54],[2,66]];
function cil_B(a)=[60*sin(a),60*cos(a),2];
function cil_phi(a)=let(p=cil_B(a),x=p[0]+28.8,y=p[1],d=sqrt(x*x+y*y)) max(0,atan2(x,y)-acos(60/d));
function cil_T(a)=let(p=cil_phi(a))[-28.8+60*sin(p),60*cos(p),2];
function cil_path_length(a)=let(p=cil_B(a),x=p[0]+28.8,y=p[1]) .2+60*cil_phi(a)*PI/180+sqrt(x*x+y*y-3600);
function cil_takeup(a)=cil_path_length(a)-29;
function cil_angle(u,lo=0,hi=30,n=0)=n>=48?(lo+hi)/2:let(m=(lo+hi)/2)cil_takeup(m)<u?cil_angle(u,m,hi,n+1):cil_angle(u,lo,m,n+1);
function cil_effective_arm(u)=60*cos(cil_angle(u)-cil_phi(cil_angle(u)));
function cil_delta_max()=cil_angle(22)-cil_phi(cil_angle(22));

function cil_stop_tip(u=cil_stop_setting)=-4*cos(cil_angle(u))-26*sin(cil_angle(u))-5.5;
function cil_point(r,a,z=0)=[r*cos(a),r*sin(a),z];
function cil_local_to_cad(p)=[cil_origin[0]+cil_s*(-p[0]+p[1]),cil_origin[1]+p[2],cil_origin[2]+cil_s*(p[0]+p[1])];
function cil_cad_to_local(p)=[cil_s*(-p[0]+cil_origin[0]+p[2]-cil_origin[2]),cil_s*(p[0]-cil_origin[0]+p[2]-cil_origin[2]),p[1]-cil_origin[1]];
function cil_legacy_wrap_spec_DO_NOT_USE()=[
 ["units","mm"],["status","unreleased-input-candidate"],
 ["public_coordinate_basis","feeder CAD"],["origin",cil_origin],
 ["basis_x",[-cil_s,0,cil_s]],["basis_y",[cil_s,0,cil_s]],["basis_z",[0,1,0]],
 ["radius_cable",cil_R],["radius_finger",cil_r],["stroke",cil_stroke],
 ["angle_full_deg",cil_theta_max],["finger_rearward_full",cil_r*sin(cil_theta_max)],
 ["wire_d",cil_wire_d],["wire_z",cil_wire_z],["ball_d_candidate",cil_ball_d],
 ["wire_tangent_local",[0,60,2]],["adjuster_seat_local",[-45,60,2]],
 ["adjuster_exit_local",[-29,60,2]],
 ["housing_stop_local",undef],
 ["housing_stop_reason","supplier taper length and ferrule nose chamfer are undimensioned"],
 ["adjuster_head_x",[-63,-53]],["adjuster_head_sw",8],
 ["adjuster_inlet_d_depth",[7,8.5]],["adjuster_wire_bore",3],
 ["adjuster_cone_display_only",cil_adjuster_cone_display],
 ["adjuster_taper_depth_interval",[8.5,10]],["ferrule_nose_chamfer",undef],
 ["ferrule_part","03096-25-0350"],["ferrule_od_length",[5.5,11]],
 ["ferrule_inlet_d_depth",[5,9]],["ferrule_wire_bore",2.5],
 ["ferrule_mouth_display_local",[cil_ferrule_mouth_display,60,2]],
 ["ferrule_tip_display_local",[cil_ferrule_tip_display,60,2]],
 ["housing_end_display_local",[cil_ferrule_mouth_display+9,60,2]],
 ["adjuster_thread_x",[-53,-29]],["adjuster_overall_x",[-63,-29]],
 ["adjuster_shank_d",6],["housing_od",5],
 ["adjuster_nut_part",cil_adjuster_nut_part],["adjuster_nut_sw_t",[10,cil_adjuster_nut_t]],
 ["adjuster_nut_x",[for(x=cil_adjuster_nut_x)[x,x+cil_adjuster_nut_t]]],
 ["adjuster_washer_part",cil_adjuster_washer_part],
 ["adjuster_washer_od_id_t",[12,6.4,cil_adjuster_washer_t]],
 ["adjuster_washer_x",[for(x=cil_adjuster_washer_x)[x,x+cil_adjuster_washer_t]]],
 ["adjuster_seat_x",[-45,-37]],["adjuster_exposed_thread_each",3.2],
 ["adjuster_tool_budget",["SW10 thin open end, cover removed",3,20,25]],
 ["adjuster_tool_x",[for(x=cil_adjuster_tool_x)[x,x+3]]],
 ["body_axis_z",cil_axis_body_z],["lever_axis_z",cil_axis_lever_z],
 ["cover_axis_z",cil_axis_cover_z],["metal_sleeve_z",cil_axis_sleeve_z],
 ["metal_sleeve_od_id_length",[8,4.3,15]],["replaceable_bush_od_id_length",[12,8.2,11]],
 ["thrust_washer_od_id_t",[16,8.4,.25]],["total_axial_float",.5],
 ["stop_setting",cil_stop_setting],["stop_setting_range",[16,22]],
 ["stop_tip_x",cil_stop_tip()],["stop_tip_x_range",[cil_stop_tip(16),cil_stop_tip(22)]],
 ["stop_axis_local_yz",[-24,2]],["stop_screw","M3x30; captured nut plus locknut"],
 ["mount_holes_cad",[for(x=[-16,16],z=[-60,3])[x,-94,z]]],
 ["mount_plate_y",[-94,-86]],["mount_rib_y",[-86,-54]],
 ["mount_rib_lower_z",-65.7],["right_mount_rib_outer_x",21.7],
 ["upper_mount_key_x",cil_mount_key_x],
 ["mount_bolt","M4x60; replace old M4x20"],
 ["mount_bolt_underhead_y",-94.8],["mount_bolt_tip_y",-34.8],
 ["part_selectors",["assembly","body","lever","cover","fixed-hardware","moving-hardware","adjuster","ferrule","cable","probe","contract"]]
];
module cil_contract(){cil_direct_contract();}
module cil_to_cad(){multmatrix([
 [-cil_s,cil_s,0,cil_origin[0]],[0,0,1,cil_origin[1]],[cil_s,cil_s,0,cil_origin[2]],[0,0,0,1]])children();}
module cil_from_cad(){multmatrix([
 [-cil_s,0,cil_s,(cil_origin[0]-cil_origin[2])*cil_s],[cil_s,0,cil_s,-(cil_origin[0]+cil_origin[2])*cil_s],[0,1,0,-cil_origin[1]],[0,0,0,1]])children();}
module cil_box(x0,x1,y0,y1,z0,z1){translate([x0,y0,z0])cube([x1-x0,y1-y0,z1-z0]);}
module cil_zcyl(x,y,z,h,d){translate([x,y,z])cylinder(h=h,d=d);}
module cil_xcyl(y,z,x,h,d){translate([x,y,z])rotate([0,90,0])cylinder(h=h,d=d);}
module cil_ycyl(x,z,y,h,d){translate([x,y,z])rotate([-90,0,0])cylinder(h=h,d=d);}
module cil_zhex(x,y,z,h,af){translate([x,y,z])rotate([0,0,30])cylinder(h=h,d=af/cos(30),$fn=6);}
module cil_xhex(y,z,x,h,af){translate([x,y,z])rotate([0,90,0])rotate([0,0,30])cylinder(h=h,d=af/cos(30),$fn=6);}
module cil_yhex(x,z,y,h,af){translate([x,y,z])rotate([-90,0,0])rotate([0,0,30])cylinder(h=h,d=af/cos(30),$fn=6);}
module cil_sector(r0,r1,a0,a1,z0,z1){
 n=max(2,ceil((a1-a0)/2));
 translate([0,0,z0])linear_extrude(height=z1-z0)polygon(concat(
  [for(i=[0:n])[r1*cos(a0+(a1-a0)*i/n),r1*sin(a0+(a1-a0)*i/n)]],
  [for(i=[n:-1:0])[r0*cos(a0+(a1-a0)*i/n),r0*sin(a0+(a1-a0)*i/n)]]));
}
module cil_web(a,b,r,z0,z1){hull(){cil_zcyl(a[0],a[1],z0,z1-z0,2*r);cil_zcyl(b[0],b[1],z0,z1-z0,2*r);}}
module cil_zring(x,y,z,h,od,id){difference(){cil_zcyl(x,y,z,h,od);cil_zcyl(x,y,z-cil_eps,h+2*cil_eps,id);}}
module cil_xring(x,h,od,id){difference(){cil_xcyl(60,2,x,h,od);cil_xcyl(60,2,x-cil_eps,h+2*cil_eps,id);}}
module cil_xnut(x,af,h,id){difference(){cil_xhex(60,2,x,h,af);cil_xcyl(60,2,x-cil_eps,h+2*cil_eps,id);}}
module cil_zbolt(x,y,z_under,length,d,head_d,head_h,socket){
 cil_zcyl(x,y,z_under-length,length,d);
 difference(){cil_zcyl(x,y,z_under,head_h,head_d);cil_zhex(x,y,z_under+head_h/2,head_h/2+cil_eps,socket);}
}

// An H section has continuous 32 mm-deep webs. It is not four isolated posts.
// Keys straddle the ORIGINAL beam edges, without changing its source.
module cil_mount_cad_blank(){
 cil_box(-28.2,28.2,-94,-86,-68,28);
 // Clearance from the old strain-relief end Z=-66 and grip arm X=22.
 // These are not datum faces; retain the actual Y=-54 load face unchanged.
 for(x=[-16,16])cil_box(x-6,x>0?21.7:x+6,-86.1,-54,-65.7,9);
 cil_box(-22,22,-86.1,-54,-33,-27);
 // Side keys are over the original flat panel, away from its grip arms.
 for(s=[-1,1]){
  cil_box(s>0?20:-28.2,s>0?28.2:-20,-86.1,-54,-50,-20);
  cil_box(s>0?24.2:-28.2,s>0?28.2:-24.2,-54.1,-49,-50,-20);
 }
 // Key's full-depth root overlaps the backplate at Z22..28, Y-94..-86.
 // Narrow it between the actual output bridge X12 and old grip arm X20.
 cil_box(cil_mount_key_x[0],cil_mount_key_x[1],-94,-54,22,32.2);
 cil_box(cil_mount_key_x[0],cil_mount_key_x[1],-54.1,-49,28.2,32.2);
}
module cil_mount_cad(){difference(){cil_mount_cad_blank();
 for(x=[-16,16],z=[-60,3])cil_ycyl(x,z,-96,44,4.5);
}}
module cil_local_body_blank(){union(){
 cil_from_cad()cil_mount_cad();
 cil_web([0,0],cil_cad_to_local([0,-90,-28]),12,-12,-4);
 // Back cheek and continuous planar ribs join grip, cable reaction and host.
 cil_web([0,0],[-52,6],12,-12,-4);
 cil_web([-52,6],[-45,60],10,-12,-4);
 cil_web([0,0],[-45,60],7,-12,-4);
 cil_web([0,0],[74,20],7,-12,-4);
 cil_web([-52,6],[-64,-99],15,-12,14);
 for(p=cil_cheek_posts){cil_zcyl(p[0],p[1],-12,20,14);
  translate([p[0]-4,p[1]-4,7.9])cube([8,8,1.6]);}
 // M6 thin nuts + metal washers clamp this seat; tighten on bench before cover.
 cil_box(-45,-37,49,71,-12,12);
 // Adjustable trigger stop; rear tool entry tunnels through the fixed grip.
 cil_box(-42,-29,-34,-18,-12,12);

 // Fixed R59.25 guide surface + .75 wire radius gives R60 centreline.
 // All additions grow from Z=-12. The back rib joins the existing M6 root.
 cil_box(-45,-20,49,55,-12,-4);
 cil_guide_solid();
 // Actual end stops: lug lives at 177..183 degrees at rest.
 cil_sector(14,22,183,193,-4.1,8);
}}
module cil_local_body(){difference(){
 cil_local_body_blank();
 cil_zcyl(0,0,-13,28,4.5);
 cil_zcyl(0,0,-5.5,1.6,8.3); // steel spacer end seat, NOT the rotating bearing
 for(p=cil_cheek_posts){
  cil_zcyl(p[0],p[1],-13,30,3.4);
  cil_zhex(p[0],p[1],-12.1,3.1,5.8); // nuts enter from rear before mounting
 }
 cil_xcyl(60,2,-51,24,6.4);
 // OD12 washer edges would merely kiss the back rib Z=-4. Give .3 radial
 // clearance outside the load faces only; preserve the full 8 mm seat.
 cil_xcyl(60,2,-46.9,1.9,12.6);
 cil_xcyl(60,2,-37,1.9,12.6);
 // Thin wrench plane pockets: continuous rear material remains >=3.7 mm.
 // These are bench-service recesses, not in-place cover-on adjustment claims.
 for(x=cil_adjuster_tool_x)hull(){
  cil_xcyl(60,2,x-.2,3.4,20.6);cil_xcyl(85,2,x-.2,3.4,20.6);
 }
 cil_xcyl(-24,2,-90,63,3.4);
 cil_xcyl(-24,2,-90,51.8,7.2); // screw head + hex tool access from local -X
 // M3 nut loaded against X=-32.6; enters from rear before the screw.
 translate([-38.3,-24,2])rotate([0,90,0])rotate([0,0,30])cylinder(h=5.7,d=5.8/cos(30),$fn=6);
 // Re-cut host bolt paths after ALL brace unions; do not refill the holes.
 cil_from_cad()for(x=[-16,16],z=[-60,3])cil_ycyl(x,z,-100,50,4.5);
}}


module cil_direct_fan(z0=.9,z1=3.2){
 // Exact angular bound of terminal -> tangent line in rotating coordinates.
 // The .01 extra radial offset encloses polygonal/numeric error; no mesh welding.
 translate([0,60,z0])linear_extrude(height=z1-z0)offset(r=1.11,$fn=72)
 polygon(concat([[0,0]],[for(a=[180:.25:180+cil_delta_max()]) [65*cos(a),65*sin(a)]],
 [[65*cos(180+cil_delta_max()),65*sin(180+cil_delta_max())]]));
}
module cil_local_lever_blank(){union(){
 // Axis, finger silhouette and return-stop lug are preserved literally.
 cil_zcyl(0,0,-3.5,11,24);
 cil_web([0,0],[-4,-26],5.5,-3.5,7.5);
 cil_web([-4,-26],[1,-42],5,-3.5,7.5);
 cil_sector(10,22,177,183,-3.5,7.5);
 // The former spool spokes/rim are replaced by a 14 mm planar pull arm.
 cil_web([0,0],[0,54],7,-3.5,3.1);
 cil_web([0,54],[0,66],7,-3.5,3.1);
}}
module cil_local_lever_zero(){difference(){
 cil_local_lever_blank();
 cil_zcyl(0,0,-4,12,12.2);
 translate(cil_terminal)sphere(d=5.6);
 cil_zcyl(0,60,2,3,5.6); // upward load entry before cap installation
 cil_direct_fan();
 for(p=cil_cap_bolts){
  cil_zcyl(p[0],p[1],-4,9,3.4);
  cil_zhex(p[0],p[1],-3.6,3.0,5.8); // M3 nut roof at -.6; nut -.3? see hardware
 }
}}
module cil_local_terminal_cap(sweep=0){difference(){
 cil_web([0,54],[0,66],7,3.1,7.5+sweep);
 translate(cil_terminal)sphere(d=5.6);
 for(p=cil_cap_bolts){
  cil_zcyl(p[0],p[1],3,5+sweep,3.4);
  cil_zcyl(p[0],p[1],4.5+sweep,3.1,6.2);
 }
}}
module cil_local_lever(u=cil_u){rotate([0,0,-cil_angle(u)])cil_local_lever_zero();}
module cil_terminal_cap(u=cil_u){cil_to_cad()rotate([0,0,-cil_angle(u)])cil_local_terminal_cap();}
module cil_local_terminal_fasteners(){for(p=cil_cap_bolts){
 // Candidate standard M3x8 socket-head: D5.5 H3, SW2.5; M3 nut SW5.5 H2.4.
 cil_zbolt(p[0],p[1],4.5,8,3,5.5,3,2.5);
 difference(){cil_zhex(p[0],p[1],-3,2.4,5.5);cil_zcyl(p[0],p[1],-3.1,2.6,3.1);}
}}

module cil_local_cover_blank(sweep=0){union(){
 cil_zcyl(0,0,8,6+sweep,24);
 cil_sector(49,67,15,122,8,14+sweep);
 cil_web([0,0],[-30,20],7,8,14+sweep);
 cil_web([0,0],[74,20],7,8,14+sweep);
 cil_web([-30,20],[-28,54],6.5,8,14+sweep);
 cil_web([74,20],[62,30],7,8,14+sweep);
 for(p=cil_cheek_posts)cil_zcyl(p[0],p[1],8,6+sweep,16);
}}
module cil_local_cover(sweep=0){difference(){
 cil_local_cover_blank(sweep);
 cil_zcyl(0,0,7,8+sweep,4.5);
 cil_zcyl(0,0,7.9,1.6,8.3);
 for(p=cil_cheek_posts){
  cil_zcyl(p[0],p[1],7,9+sweep,3.4);
  translate([p[0]-4.2,p[1]-4.2,7.9])cube([8.4,8.4,1.8]);
 }
}}

module cil_mount_hardware_cad(){for(x=[-16,16],z=[-60,3]){
 // Original nuts/host washers remain in parent. THESE replace old screws.
 cil_ycyl(x,z,-94.8,60,4);
 difference(){cil_ycyl(x,z,-98.8,4,7);cil_yhex(x,z,-98.9,2.1,3);}
 difference(){cil_ycyl(x,z,-94.8,.8,9);cil_ycyl(x,z,-94.9,1,4.3);}
}}
module cil_local_fixed_hardware(){
 // Precision steel distance tube supports both cheeks and carries clamp load.
 cil_zring(0,0,-5.5,15,8,4.3);
 for(z=[-3.75,7.5])cil_zring(0,0,z,.25,16,8.4);
 cil_zbolt(0,0,14.8,35,4,7,4,3);
 cil_zring(0,0,14,.8,9,4.3);
 cil_zring(0,0,-12.8,.8,9,4.3);
 difference(){cil_zhex(0,0,-16,3.2,7);cil_zcyl(0,0,-16.1,3.4,4.1);}
 for(p=cil_cheek_posts){
  cil_zbolt(p[0],p[1],14.5,30,3,5.5,3,2.5);
  cil_zring(p[0],p[1],14,.5,7,3.2);
  difference(){cil_zhex(p[0],p[1],-11.4,2.4,5.5);cil_zcyl(p[0],p[1],-11.5,2.6,3.1);}
 }
 cil_local_adjuster();cil_local_ferrule();
 for(x=cil_adjuster_nut_x)cil_xnut(x,10,cil_adjuster_nut_t,6.1);
 for(x=cil_adjuster_washer_x)cil_xring(x,cil_adjuster_washer_t,12,6.4);
 // Adjustable M3 end stop: real screw, rear captive nut and accessible locknut.
 sx=cil_stop_tip();
 cil_xcyl(-24,2,sx-30,30,3);
 difference(){cil_xcyl(-24,2,sx-33,3,5.5);
  translate([sx-33.1,-24,2])rotate([0,90,0])rotate([0,0,30])cylinder(h=1.7,d=2.5/cos(30),$fn=6);}
 for(x=[-35,-29])difference(){
  translate([x,-24,2])rotate([0,90,0])rotate([0,0,30])cylinder(h=2.4,d=5.5/cos(30),$fn=6);
  cil_xcyl(-24,2,x-.1,2.6,3.1);
 }
}
// Drawing-derived outside/bores. The unmarked taper is a display parameter,
// never used to certify an exact housing reaction coordinate.
module cil_local_adjuster(){difference(){
 union(){cil_xhex(60,2,-63,10,8);cil_xcyl(60,2,-53,24,6);}
 cil_xcyl(60,2,-63.1,8.6,7);
 translate([-54.5,60,2])rotate([0,90,0])cylinder(h=cil_adjuster_cone_display,d1=7,d2=3);
 cil_xcyl(60,2,-54.5+cil_adjuster_cone_display-cil_eps,
   25.6-cil_adjuster_cone_display,3);
}}
module cil_local_ferrule(){difference(){
 cil_xcyl(60,2,cil_ferrule_mouth_display,11,5.5);
 cil_xcyl(60,2,cil_ferrule_mouth_display-cil_eps,9+cil_eps,5);
 translate([cil_ferrule_mouth_display+9,60,2])rotate([0,90,0])
  cylinder(h=cil_ferrule_cone_display,d1=5,d2=2.5);
 cil_xcyl(60,2,cil_ferrule_mouth_display-cil_eps,11+2*cil_eps,2.5);
}}

module cil_local_moving_hardware(u=cil_u){rotate([0,0,-cil_angle(u)]){
 cil_zring(0,0,-3.5,11,12,8.2);
 translate(cil_terminal)sphere(d=5);
 cil_local_terminal_fasteners();
}}
module cil_seg(a,b,d=1.5){hull(){translate(a)sphere(d=d,$fn=24);translate(b)sphere(d=d,$fn=24);}}
module cil_local_cable(u=cil_u){
 a=cil_angle(u);p=cil_phi(a);q=cil_T(a);b=cil_B(a);
 cil_xcyl(60,2,cil_ferrule_mouth_display,-28.8-cil_ferrule_mouth_display,1.5);
 if(p>.00001)translate(cil_fairlead_C)rotate([0,0,90-p])rotate_extrude(angle=p,$fn=7200)
  translate([60,0,0])circle(d=1.5,$fn=24);
 cil_seg(q,b,1.5);
}

// Explicit tool budget, not an assertion that an unspecified purchased wrench fits.
// Opens toward -Y and enters from +Y. Flat gap10.4 clears the SW10 nut.
// sweep=25 is its continuous straight entry; actual tool width/thickness must fit.
module cil_local_adjuster_tool(index=0,sweep=0){
 x=cil_adjuster_tool_x[index];
 difference(){
  hull(){cil_xcyl(60,2,x,3,20);cil_xcyl(60+sweep,2,x,3,20);}
  cil_box(x-.1,x+3.1,-100,66,-3.2,7.2);
 }
 cil_box(x,x+3,69,105+sweep,-1,5);
}
module cil_body(){cil_to_cad()cil_local_body();}
module cil_lever(u=cil_u){cil_to_cad()cil_local_lever(u);}
module cil_cover(){cil_to_cad()cil_local_cover();}
module cil_fixed_hardware(){cil_mount_hardware_cad();cil_to_cad()cil_local_fixed_hardware();}
module cil_moving_hardware(u=cil_u){cil_to_cad()cil_local_moving_hardware(u);}
module cil_cable(u=cil_u){cil_to_cad()cil_local_cable(u);}
module cil_adjuster(){cil_to_cad()cil_local_adjuster();}
module cil_ferrule(){cil_to_cad()cil_local_ferrule();}
module cil_hardware(u=cil_u){cil_fixed_hardware();cil_moving_hardware(u);cil_cable(u);}
module cil_fixed(){cil_body();cil_cover();cil_fixed_hardware();}
module cil_moving(u=cil_u){cil_lever(u);cil_terminal_cap(u);cil_moving_hardware(u);}
module cil_legacy_wrap_probe_DO_NOT_USE(kind=cil_probe_kind,u=cil_u){
 if(kind=="motion")intersection(){cil_fixed();cil_moving(u);}
 else if(kind=="printed-fixed")intersection(){cil_body();cil_cover();}
 else if(kind=="hardware-fit")intersection(){union(){cil_body();cil_cover();cil_lever(u);}cil_hardware(u);}
 else if(kind=="cable-fit")intersection(){union(){cil_body();cil_cover();cil_lever(u);}cil_cable(u);}
 else if(kind=="adjuster-washer-fit")intersection(){union(){cil_body();cil_cover();cil_lever(u);}cil_to_cad()for(x=cil_adjuster_washer_x)cil_xring(x,cil_adjuster_washer_t,12,6.4);}
 else if(kind=="adjuster-tool")intersection(){union(){cil_body();cil_lever(u);cil_fixed_hardware();}cil_to_cad()for(i=[0,1])cil_local_adjuster_tool(i,25);}
 else if(kind=="terminal-entry")intersection(){cil_lever(u);cil_to_cad()rotate([0,0,-cil_angle(u)])hull(){
  translate(cil_point(cil_R,45,2))sphere(d=5);translate(cil_point(cil_R,45,22))sphere(d=5);}}
 else if(kind=="stop-contact")intersection(){cil_lever(u);cil_to_cad()cil_xcyl(-24,2,cil_stop_tip()-30,30,3);}
 else if(kind=="stop-tool")intersection(){union(){cil_body();cil_cover();cil_lever(u);}cil_to_cad(){
  cil_xcyl(-24,2,-100,100+cil_stop_tip()-33,4);
  translate([cil_stop_tip()-33,-24,2])rotate([0,90,0])rotate([0,0,30])cylinder(h=1.5,d=2.5/cos(30),$fn=6);}}
 // Continuous extrusion sweep preserves concave outline and every opening.
 else if(kind=="cover-removal")intersection(){union(){cil_body();cil_lever(u);cil_moving_hardware(u);}cil_to_cad()cil_local_cover(25);}
 else assert(false,str("Unknown cil_probe: ",kind));
}
module cil_assembly(){
 color([.19,.35,.45])cil_body();color([.12,.65,.85]){cil_lever();cil_terminal_cap();}
 color([.54,.68,.75,.7])cil_cover();color([.73,.75,.79])cil_hardware();
}

module cil_guide_solid(){
 // Only this functional face uses .1 degree segmentation, not global $fn.
 translate([-28.8,0,-12])linear_extrude(height=19.5)polygon(concat(
  [for(i=[0:80])[59.25*cos(82+i*.1),59.25*sin(82+i*.1)]],
  [for(i=[80:-1:0])[53*cos(82+i*.1),53*sin(82+i*.1)]]));
}
module cil_direct_contract(){echo(cil_direct_contract=[
 ["status","DIAGNOSTIC_NOT_RELEASED"],["basis","feeder CAD"],["origin",cil_origin],
 ["preserved","axis stack, finger silhouette, mounting, M6 bore/seat, main cover"],
 ["changed","upper pull arm; terminal at local [0,60,2]; two-screw moving cap; fixed R60 fairlead"],
 ["fairlead_center",cil_fairlead_C],["fairlead_core_R",60],["fairlead_surface_R",59.25],
 ["u_samples",[for(u=[0,10,20,22])[u,cil_angle(u),cil_phi(cil_angle(u)),cil_path_length(cil_angle(u)),cil_effective_arm(u),36*sin(cil_angle(u))]]],
 ["cap_bolts",cil_cap_bolts],["cap_split_z",3.1],["cap_screw","2x M3x8 socket head; D5.5 H3"],
 ["cap_nut","2x M3 SW5.5 H2.4; z[-3,-.6]"],
 ["unknown","actual cable bend endurance, friction/preload, terminal shape tolerance, printed guide wear and layer surfaces"]]);}
if(cil_part=="assembly")cil_assembly();
else if(cil_part=="body")cil_body();
else if(cil_part=="lever")cil_lever();
else if(cil_part=="terminal-cap")cil_terminal_cap();
else if(cil_part=="cover")cil_cover();
else if(cil_part=="fixed-hardware")cil_fixed_hardware();
else if(cil_part=="moving-hardware")cil_moving_hardware();
else if(cil_part=="cable")cil_cable();
else if(cil_part=="contract")cil_direct_contract();
else if(cil_part!="none")assert(false,str("Unknown cil_part: ",cil_part));
