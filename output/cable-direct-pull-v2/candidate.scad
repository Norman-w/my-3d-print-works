// Direct pull v2: 5 mm nominal axial lead-in; input adjuster budget +/-2 mm. NOT RELEASED.
include </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/parameters.scad>
// Cable trigger INPUT candidate. Units mm; X1C / .4 nozzle / PETG.
// Every public part returns FEEDER CAD coordinates. No host geometry is added.
// Local +X muzzle, +Y up, +Z outward. Clockwise is a rearward finger pull.
// Purchased hardware is an envelope candidate, NOT a printable component.
cdp_part="none";
cdp_u=0;
cdp_probe_kind="motion";
cdp_eps=.02;
cdp_origin=[75,-82,5];
cdp_s=sqrt(.5);
cdp_R=60;
cdp_r=36;
cdp_stroke=20;
cdp_wire_d=1.5;
cdp_wire_z=2;
cdp_ball_d=5; // selected norelem core; nominal spherical terminal confirmed by 03096-14 drawing.
cdp_ball_seat_d=5.6;
cdp_adjuster_cone_display=1; // UNDIMENSIONED in supplier drawing; reference only.
cdp_ferrule_cone_display=1; // same: L-L1=2, but division between taper/bore is unknown.
cdp_ferrule_tip_display=-54.5+(7-5.5)/(7-3)*cdp_adjuster_cone_display;
cdp_ferrule_mouth_display=cdp_ferrule_tip_display-11;
cdp_adjuster_nut_part="07212-106"; // DIN439 / ISO4035 M6 SW10 H3.2, candidate supply.
cdp_adjuster_nut_t=3.2;
cdp_adjuster_washer_part="07300-106"; // M6 flat washer nominal OD12 / ID6.4 / t1.6.
cdp_adjuster_washer_t=1.6;
cdp_adjuster_nut_x=[-49.8,-35.4];
cdp_adjuster_washer_x=[-46.6,-37];
cdp_adjuster_tool_x=[-49.7,-35.3]; // 3 mm thin SW10 open-end tool budget; cover OFF.
cdp_stop_setting=20; // adjustable equivalent output 16..22; install without balls/air

cdp_cheek_posts=[[-30,20],[74,20]];
cdp_axis_body_z=[-12,-4];
cdp_axis_lever_z=[-3.5,7.5];
cdp_axis_cover_z=[8,14];
cdp_axis_sleeve_z=[-5.5,9.5];
cdp_mount_key_x=[12.4,19.6]; // .4 from output bridge X12 and original grip arm X20.
cdp_shoulder_clearance=.25;
$fn=72;
assert(cdp_stop_setting>=16&&cdp_stop_setting<=22,"Stop adjustment candidate range is 16..22 mm equivalent output");



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

function cdp_stop_tip(u=cdp_stop_setting)=-4*cos(cdp_angle(u))-26*sin(cdp_angle(u))-5.5;
function cdp_point(r,a,z=0)=[r*cos(a),r*sin(a),z];
function cdp_local_to_cad(p)=[cdp_origin[0]+cdp_s*(-p[0]+p[1]),cdp_origin[1]+p[2],cdp_origin[2]+cdp_s*(p[0]+p[1])];
function cdp_cad_to_local(p)=[cdp_s*(-p[0]+cdp_origin[0]+p[2]-cdp_origin[2]),cdp_s*(p[0]-cdp_origin[0]+p[2]-cdp_origin[2]),p[1]-cdp_origin[1]];
module cdp_contract(){cdp_direct_contract();}
module cdp_to_cad(){multmatrix([
 [-cdp_s,cdp_s,0,cdp_origin[0]],[0,0,1,cdp_origin[1]],[cdp_s,cdp_s,0,cdp_origin[2]],[0,0,0,1]])children();}
module cdp_from_cad(){multmatrix([
 [-cdp_s,0,cdp_s,(cdp_origin[0]-cdp_origin[2])*cdp_s],[cdp_s,0,cdp_s,-(cdp_origin[0]+cdp_origin[2])*cdp_s],[0,1,0,-cdp_origin[1]],[0,0,0,1]])children();}
module cdp_box(x0,x1,y0,y1,z0,z1){translate([x0,y0,z0])cube([x1-x0,y1-y0,z1-z0]);}
module cdp_zcyl(x,y,z,h,d){translate([x,y,z])cylinder(h=h,d=d);}
module cdp_xcyl(y,z,x,h,d){translate([x,y,z])rotate([0,90,0])cylinder(h=h,d=d);}
module cdp_ycyl(x,z,y,h,d){translate([x,y,z])rotate([-90,0,0])cylinder(h=h,d=d);}
module cdp_zhex(x,y,z,h,af){translate([x,y,z])rotate([0,0,30])cylinder(h=h,d=af/cos(30),$fn=6);}
module cdp_xhex(y,z,x,h,af){translate([x,y,z])rotate([0,90,0])rotate([0,0,30])cylinder(h=h,d=af/cos(30),$fn=6);}
module cdp_yhex(x,z,y,h,af){translate([x,y,z])rotate([-90,0,0])rotate([0,0,30])cylinder(h=h,d=af/cos(30),$fn=6);}
module cdp_sector(r0,r1,a0,a1,z0,z1){
 n=max(2,ceil((a1-a0)/2));
 translate([0,0,z0])linear_extrude(height=z1-z0)polygon(concat(
  [for(i=[0:n])[r1*cos(a0+(a1-a0)*i/n),r1*sin(a0+(a1-a0)*i/n)]],
  [for(i=[n:-1:0])[r0*cos(a0+(a1-a0)*i/n),r0*sin(a0+(a1-a0)*i/n)]]));
}
module cdp_web(a,b,r,z0,z1){hull(){cdp_zcyl(a[0],a[1],z0,z1-z0,2*r);cdp_zcyl(b[0],b[1],z0,z1-z0,2*r);}}
module cdp_zring(x,y,z,h,od,id){difference(){cdp_zcyl(x,y,z,h,od);cdp_zcyl(x,y,z-cdp_eps,h+2*cdp_eps,id);}}
module cdp_xring(x,h,od,id){difference(){cdp_xcyl(60,2,x,h,od);cdp_xcyl(60,2,x-cdp_eps,h+2*cdp_eps,id);}}
module cdp_xnut(x,af,h,id){difference(){cdp_xhex(60,2,x,h,af);cdp_xcyl(60,2,x-cdp_eps,h+2*cdp_eps,id);}}
module cdp_zbolt(x,y,z_under,length,d,head_d,head_h,socket){
 cdp_zcyl(x,y,z_under-length,length,d);
 difference(){cdp_zcyl(x,y,z_under,head_h,head_d);cdp_zhex(x,y,z_under+head_h/2,head_h/2+cdp_eps,socket);}
}

// An H section has continuous 32 mm-deep webs. It is not four isolated posts.
// Keys straddle the ORIGINAL beam edges, without changing its source.
module cdp_mount_cad_blank(){
 cdp_box(-28.2,28.2,-94,-86,-68,28);
 // Clearance from the old strain-relief end Z=-66 and grip arm X=22.
 // These are not datum faces; retain the actual Y=-54 load face unchanged.
 for(x=[-16,16])cdp_box(x-6,x>0?21.7:x+6,-86.1,-54,-65.7,9);
 cdp_box(-22,22,-86.1,-54,-33,-27);
 // Side keys are over the original flat panel, away from its grip arms.
 for(s=[-1,1]){
  cdp_box(s>0?20:-28.2,s>0?28.2:-20,-86.1,-54,-50,-20);
  cdp_box(s>0?24.2:-28.2,s>0?28.2:-24.2,-54.1,-49,-50,-20);
 }
 // Key's full-depth root overlaps the backplate at Z22..28, Y-94..-86.
 // Narrow it between the actual output bridge X12 and old grip arm X20.
 cdp_box(cdp_mount_key_x[0],cdp_mount_key_x[1],-94,-54,22,32.2);
 cdp_box(cdp_mount_key_x[0],cdp_mount_key_x[1],-54.1,-49,28.2,32.2);
}
module cdp_mount_cad(){difference(){cdp_mount_cad_blank();
 for(x=[-16,16],z=[-60,3])cdp_ycyl(x,z,-96,44,4.5);
}}
module cdp_local_body_blank(){union(){
 cdp_from_cad()cdp_mount_cad();
 cdp_web([0,0],cdp_cad_to_local([0,-90,-28]),12,-12,-4);
 // Back cheek and continuous planar ribs join grip, cable reaction and host.
 cdp_web([0,0],[-52,6],12,-12,-4);
 cdp_web([-52,6],[-45,60],10,-12,-4);
 cdp_web([0,0],[-45,60],7,-12,-4);
 cdp_web([0,0],[74,20],7,-12,-4);
 cdp_web([-52,6],[-64,-99],15,-12,14);
 for(p=cdp_cheek_posts){cdp_zcyl(p[0],p[1],-12,20,14);
  translate([p[0]-4,p[1]-4,7.9])cube([8,8,1.6]);}
 // M6 thin nuts + metal washers clamp this seat; tighten on bench before cover.
 cdp_box(-45,-37,49,71,-12,12);
 // Adjustable trigger stop; rear tool entry tunnels through the fixed grip.
 cdp_box(-42,-29,-34,-18,-12,12);

 // Fixed R59.25 guide surface + .75 wire radius gives R60 centreline.
 // All additions grow from Z=-12. The back rib joins the existing M6 root.
 cdp_box(-45,cdp_fairlead_C[0]+cdp_fairlead_surface_R*sin(cdp_fairlead_extent_deg)+1,49,55,-12,-4);
 cdp_guide_solid();
 // Actual end stops: lug lives at 177..183 degrees at rest.
 cdp_sector(14,22,183,193,-4.1,8);
}}
module cdp_local_body(){difference(){
 cdp_local_body_blank();
 cdp_zcyl(0,0,-13,28,4.5);
 cdp_zcyl(0,0,-5.5,1.6,8.3); // steel spacer end seat, NOT the rotating bearing
 for(p=cdp_cheek_posts){
  cdp_zcyl(p[0],p[1],-13,30,3.4);
  cdp_zhex(p[0],p[1],-12.1,3.1,5.8); // nuts enter from rear before mounting
 }
 cdp_xcyl(60,2,-51,24,6.4);
 // OD12 washer edges would merely kiss the back rib Z=-4. Give .3 radial
 // clearance outside the load faces only; preserve the full 8 mm seat.
 cdp_xcyl(60,2,-46.9,1.9,12.6);
 cdp_xcyl(60,2,-37,1.9,12.6);
 // Thin wrench plane pockets: continuous rear material remains >=3.7 mm.
 // These are bench-service recesses, not in-place cover-on adjustment claims.
 for(x=cdp_adjuster_tool_x)hull(){
  cdp_xcyl(60,2,x-.2,3.4,20.6);cdp_xcyl(85,2,x-.2,3.4,20.6);
 }
 cdp_xcyl(-24,2,-90,63,3.4);
 cdp_xcyl(-24,2,-90,51.8,7.2); // screw head + hex tool access from local -X
 // M3 nut loaded against X=-32.6; enters from rear before the screw.
 translate([-38.3,-24,2])rotate([0,90,0])rotate([0,0,30])cylinder(h=5.7,d=5.8/cos(30),$fn=6);
 // Re-cut host bolt paths after ALL brace unions; do not refill the holes.
 cdp_from_cad()for(x=[-16,16],z=[-60,3])cdp_ycyl(x,z,-100,50,4.5);
}}


module cdp_direct_fan(z0=.9,z1=3.2){
 // Exact angular bound of terminal -> tangent line in rotating coordinates.
 // The .01 extra radial offset encloses polygonal/numeric error; no mesh welding.
 translate([0,60,z0])linear_extrude(height=z1-z0)offset(r=1.11,$fn=72)
 polygon(concat([[0,0]],[for(a=[180:.25:180+cdp_delta_max()]) [65*cos(a),65*sin(a)]],
 [[65*cos(180+cdp_delta_max()),65*sin(180+cdp_delta_max())]]));
}
module cdp_local_lever_blank(){union(){
 // Axis, finger silhouette and return-stop lug are preserved literally.
 cdp_zcyl(0,0,-3.5,11,24);
 cdp_web([0,0],[-4,-26],5.5,-3.5,7.5);
 cdp_web([-4,-26],[1,-42],5,-3.5,7.5);
 cdp_sector(10,22,177,183,-3.5,7.5);
 // The former spool spokes/rim are replaced by a 14 mm planar pull arm.
 cdp_web([0,0],[0,54],7,-3.5,3.1);
 cdp_web([0,54],[0,66],7,-3.5,3.1);
}}
module cdp_local_lever_zero(){difference(){
 cdp_local_lever_blank();
 cdp_zcyl(0,0,-4,12,12.2);
 translate(cdp_terminal)sphere(d=5.6);
 cdp_zcyl(0,60,2,3,5.6); // upward load entry before cap installation
 cdp_direct_fan();
 for(p=cdp_cap_bolts){
  cdp_zcyl(p[0],p[1],-4,9,3.4);
  cdp_zhex(p[0],p[1],-3.6,3.0,5.8); // M3 nut roof at -.6; nut -3..-.6
 }
}}
module cdp_local_terminal_cap(sweep=0){difference(){
 cdp_web([0,54],[0,66],7,3.1,7.5+sweep);
 translate(cdp_terminal)sphere(d=5.6);
 for(p=cdp_cap_bolts){
  cdp_zcyl(p[0],p[1],3,5+sweep,3.4);
  cdp_zcyl(p[0],p[1],4.5+sweep,3.1,6.2);
 }
}}
module cdp_local_lever(u=cdp_u){rotate([0,0,-cdp_angle(u)])cdp_local_lever_zero();}
module cdp_terminal_cap(u=cdp_u){cdp_to_cad()rotate([0,0,-cdp_angle(u)])cdp_local_terminal_cap();}
module cdp_local_terminal_fasteners(){for(p=cdp_cap_bolts){
 // Candidate standard M3x8 socket-head: D5.5 H3, SW2.5; M3 nut SW5.5 H2.4.
 cdp_zbolt(p[0],p[1],4.5,8,3,5.5,3,2.5);
 difference(){cdp_zhex(p[0],p[1],-3,2.4,5.5);cdp_zcyl(p[0],p[1],-3.1,2.6,3.1);}
}}

module cdp_local_cover_blank(sweep=0){union(){
 cdp_zcyl(0,0,8,6+sweep,24);
 cdp_sector(49,67,15,122,8,14+sweep);
 cdp_web([0,0],[-30,20],7,8,14+sweep);
 cdp_web([0,0],[74,20],7,8,14+sweep);
 cdp_web([-30,20],[-28,54],6.5,8,14+sweep);
 cdp_web([74,20],[62,30],7,8,14+sweep);
 for(p=cdp_cheek_posts)cdp_zcyl(p[0],p[1],8,6+sweep,16);
}}
module cdp_local_cover(sweep=0){difference(){
 cdp_local_cover_blank(sweep);
 cdp_zcyl(0,0,7,8+sweep,4.5);
 cdp_zcyl(0,0,7.9,1.6,8.3);
 for(p=cdp_cheek_posts){
  cdp_zcyl(p[0],p[1],7,9+sweep,3.4);
  translate([p[0]-4.2,p[1]-4.2,7.9])cube([8.4,8.4,1.8]);
 }
}}

module cdp_mount_hardware_cad(){for(x=[-16,16],z=[-60,3]){
 // Original nuts/host washers remain in parent. THESE replace old screws.
 cdp_ycyl(x,z,-94.8,60,4);
 difference(){cdp_ycyl(x,z,-98.8,4,7);cdp_yhex(x,z,-98.9,2.1,3);}
 difference(){cdp_ycyl(x,z,-94.8,.8,9);cdp_ycyl(x,z,-94.9,1,4.3);}
}}
module cdp_local_fixed_hardware(delta=cdp_delta){
 // Precision steel distance tube supports both cheeks and carries clamp load.
 cdp_zring(0,0,-5.5,15,8,4.3);
 for(z=[-3.75,7.5])cdp_zring(0,0,z,.25,16,8.4);
 cdp_zbolt(0,0,14.8,35,4,7,4,3);
 cdp_zring(0,0,14,.8,9,4.3);
 cdp_zring(0,0,-12.8,.8,9,4.3);
 difference(){cdp_zhex(0,0,-16,3.2,7);cdp_zcyl(0,0,-16.1,3.4,4.1);}
 for(p=cdp_cheek_posts){
  cdp_zbolt(p[0],p[1],14.5,30,3,5.5,3,2.5);
  cdp_zring(p[0],p[1],14,.5,7,3.2);
  difference(){cdp_zhex(p[0],p[1],-11.4,2.4,5.5);cdp_zcyl(p[0],p[1],-11.5,2.6,3.1);}
 }
 cdp_local_adjuster(delta);cdp_local_ferrule(delta);
 for(x=cdp_adjuster_nut_x)cdp_xnut(x,10,cdp_adjuster_nut_t,6.1);
 for(x=cdp_adjuster_washer_x)cdp_xring(x,cdp_adjuster_washer_t,12,6.4);
 // Adjustable M3 end stop: real screw, rear captive nut and accessible locknut.
 sx=cdp_stop_tip();
 cdp_xcyl(-24,2,sx-30,30,3);
 difference(){cdp_xcyl(-24,2,sx-33,3,5.5);
  translate([sx-33.1,-24,2])rotate([0,90,0])rotate([0,0,30])cylinder(h=1.7,d=2.5/cos(30),$fn=6);}
 for(x=[-35,-29])difference(){
  translate([x,-24,2])rotate([0,90,0])rotate([0,0,30])cylinder(h=2.4,d=5.5/cos(30),$fn=6);
  cdp_xcyl(-24,2,x-.1,2.6,3.1);
 }
}
// Drawing-derived outside/bores. The unmarked taper is a display parameter,
// never used to certify an exact housing reaction coordinate.
module cdp_local_adjuster(delta=cdp_delta){translate([delta,0,0])difference(){
 union(){cdp_xhex(60,2,-63,10,8);cdp_xcyl(60,2,-53,24,6);}
 cdp_xcyl(60,2,-63.1,8.6,7);
 translate([-54.5,60,2])rotate([0,90,0])cylinder(h=cdp_adjuster_cone_display,d1=7,d2=3);
 cdp_xcyl(60,2,-54.5+cdp_adjuster_cone_display-cdp_eps,
   25.6-cdp_adjuster_cone_display,3);
}}
module cdp_local_ferrule(delta=cdp_delta){translate([delta,0,0])difference(){
 cdp_xcyl(60,2,cdp_ferrule_mouth_display,11,5.5);
 cdp_xcyl(60,2,cdp_ferrule_mouth_display-cdp_eps,9+cdp_eps,5);
 translate([cdp_ferrule_mouth_display+9,60,2])rotate([0,90,0])
  cylinder(h=cdp_ferrule_cone_display,d1=5,d2=2.5);
 cdp_xcyl(60,2,cdp_ferrule_mouth_display-cdp_eps,11+2*cdp_eps,2.5);
}}

module cdp_local_moving_hardware(u=cdp_u){rotate([0,0,-cdp_angle(u)]){
 cdp_zring(0,0,-3.5,11,12,8.2);
 translate(cdp_terminal)sphere(d=5);
 cdp_local_terminal_fasteners();
}}
module cdp_seg(a,b,d=1.5){hull(){translate(a)sphere(d=d,$fn=24);translate(b)sphere(d=d,$fn=24);}}
module cdp_local_cable(u=cdp_u,delta=cdp_delta){
 a=cdp_angle(u);p=cdp_phi(a);q=cdp_T(a);b=cdp_B(a);
 cdp_xcyl(cdp_exit(delta)[1],cdp_exit(delta)[2],cdp_ferrule_mouth(delta),cdp_fairlead_C[0]-cdp_ferrule_mouth(delta),cdp_wire_d);
 if(p>.00001)translate(cdp_fairlead_C)rotate([0,0,90-p])rotate_extrude(angle=p,$fn=7200)
  translate([cdp_fairlead_R,0,0])circle(d=cdp_wire_d,$fn=24);
 cdp_seg(q,b,cdp_wire_d);
}

// Explicit tool budget, not an assertion that an unspecified purchased wrench fits.
// Opens toward -Y and enters from +Y. Flat gap10.4 clears the SW10 nut.
// sweep=25 is its continuous straight entry; actual tool width/thickness must fit.
module cdp_local_adjuster_tool(index=0,sweep=0){
 x=cdp_adjuster_tool_x[index];
 difference(){
  hull(){cdp_xcyl(60,2,x,3,20);cdp_xcyl(60+sweep,2,x,3,20);}
  cdp_box(x-.1,x+3.1,-100,66,-3.2,7.2);
 }
 cdp_box(x,x+3,69,105+sweep,-1,5);
}
module cdp_body(){cdp_to_cad()cdp_local_body();}
module cdp_lever(u=cdp_u){cdp_to_cad()cdp_local_lever(u);}
module cdp_cover(){cdp_to_cad()cdp_local_cover();}
module cdp_fixed_hardware(delta=cdp_delta){cdp_mount_hardware_cad();cdp_to_cad()cdp_local_fixed_hardware(delta);}
module cdp_moving_hardware(u=cdp_u){cdp_to_cad()cdp_local_moving_hardware(u);}
module cdp_cable(u=cdp_u,delta=cdp_delta){cdp_to_cad()cdp_local_cable(u,delta);}
module cdp_adjuster(delta=cdp_delta){cdp_to_cad()cdp_local_adjuster(delta);}
module cdp_ferrule(delta=cdp_delta){cdp_to_cad()cdp_local_ferrule(delta);}
module cdp_hardware(u=cdp_u,delta=cdp_delta){cdp_fixed_hardware(delta);cdp_moving_hardware(u);cdp_cable(u,delta);}
module cdp_fixed(delta=cdp_delta){cdp_body();cdp_cover();cdp_fixed_hardware(delta);}
module cdp_moving(u=cdp_u){cdp_lever(u);cdp_terminal_cap(u);cdp_moving_hardware(u);}
module cdp_assembly(){
 color([.19,.35,.45])cdp_body();color([.12,.65,.85]){cdp_lever();cdp_terminal_cap();}
 color([.54,.68,.75,.7])cdp_cover();color([.73,.75,.79])cdp_hardware();
}


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
if(cdp_part=="assembly")cdp_assembly();
else if(cdp_part=="body")cdp_body();
else if(cdp_part=="lever")cdp_lever();
else if(cdp_part=="terminal-cap")cdp_terminal_cap();
else if(cdp_part=="cover")cdp_cover();
else if(cdp_part=="adjuster")cdp_adjuster();
else if(cdp_part=="ferrule")cdp_ferrule();
else if(cdp_part=="fixed-hardware")cdp_fixed_hardware();
else if(cdp_part=="moving-hardware")cdp_moving_hardware();
else if(cdp_part=="cable")cdp_cable();
else if(cdp_part=="contract")cdp_direct_contract();
else if(cdp_part!="none")assert(false,str("Unknown cdp_part: ",cdp_part));
