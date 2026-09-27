// Isolated diagnostic copy; canonical CAD unchanged. Seats reach existing flat back.
// Cable trigger INPUT candidate. Units mm; X1C / .4 nozzle / PETG.
// Every public part returns FEEDER CAD coordinates. No host geometry is added.
// Local +X muzzle, +Y up, +Z outward. Clockwise is a rearward finger pull.
// Purchased hardware is an envelope candidate, NOT a printable component.
cip_part="assembly";
cip_u=0;
cip_probe_kind="motion";
cip_eps=.02;
cip_origin=[75,-82,5];
cip_s=sqrt(.5);
cip_R=60;
cip_r=36;
cip_stroke=20;
cip_wire_d=1.5;
cip_wire_z=2;
cip_ball_d=5; // selected norelem core; nominal spherical terminal confirmed by 03096-14 drawing.
cip_ball_seat_d=5.6;
cip_adjuster_cone_display=1; // UNDIMENSIONED in supplier drawing; reference only.
cip_ferrule_cone_display=1; // same: L-L1=2, but division between taper/bore is unknown.
cip_ferrule_tip_display=-54.5+(7-5.5)/(7-3)*cip_adjuster_cone_display;
cip_ferrule_mouth_display=cip_ferrule_tip_display-11;
cip_adjuster_nut_part="07212-106"; // DIN439 / ISO4035 M6 SW10 H3.2, candidate supply.
cip_adjuster_nut_t=3.2;
cip_adjuster_washer_part="07300-106"; // M6 flat washer nominal OD12 / ID6.4 / t1.6.
cip_adjuster_washer_t=1.6;
cip_adjuster_nut_x=[-49.8,-35.4];
cip_adjuster_washer_x=[-46.6,-37];
cip_adjuster_tool_x=[-49.7,-35.3]; // 3 mm thin SW10 open-end tool budget; cover OFF.
cip_stop_setting=20; // adjustable equivalent output 16..22; install without balls/air
cip_theta_max=cip_stroke/cip_R*180/PI;
cip_cheek_posts=[[-30,20],[74,20]];
cip_axis_body_z=[-12,-4];
cip_axis_lever_z=[-3.5,7.5];
cip_axis_cover_z=[8,14];
cip_axis_sleeve_z=[-5.5,9.5];
cip_mount_key_x=[12.4,19.6]; // .4 from output bridge X12 and original grip arm X20.
cip_shoulder_clearance=.25;
$fn=72;
assert(cip_stop_setting>=16&&cip_stop_setting<=22,"Stop adjustment candidate range is 16..22 mm equivalent output");

function cip_angle(u)=u/cip_R*180/PI;
function cip_stop_tip(u=cip_stop_setting)=-4*cos(cip_angle(u))-26*sin(cip_angle(u))-5.5;
function cip_point(r,a,z=0)=[r*cos(a),r*sin(a),z];
function cip_local_to_cad(p)=[cip_origin[0]+cip_s*(-p[0]+p[1]),cip_origin[1]+p[2],cip_origin[2]+cip_s*(p[0]+p[1])];
function cip_cad_to_local(p)=[cip_s*(-p[0]+cip_origin[0]+p[2]-cip_origin[2]),cip_s*(p[0]-cip_origin[0]+p[2]-cip_origin[2]),p[1]-cip_origin[1]];
function cip_spec()=[
 ["units","mm"],["status","unreleased-input-candidate"],
 ["public_coordinate_basis","feeder CAD"],["origin",cip_origin],
 ["basis_x",[-cip_s,0,cip_s]],["basis_y",[cip_s,0,cip_s]],["basis_z",[0,1,0]],
 ["radius_cable",cip_R],["radius_finger",cip_r],["stroke",cip_stroke],
 ["angle_full_deg",cip_theta_max],["finger_rearward_full",cip_r*sin(cip_theta_max)],
 ["wire_d",cip_wire_d],["wire_z",cip_wire_z],["ball_d_candidate",cip_ball_d],
 ["wire_tangent_local",[0,60,2]],["adjuster_seat_local",[-45,60,2]],
 ["adjuster_exit_local",[-29,60,2]],
 ["housing_stop_local",undef],
 ["housing_stop_reason","supplier taper length and ferrule nose chamfer are undimensioned"],
 ["adjuster_head_x",[-63,-53]],["adjuster_head_sw",8],
 ["adjuster_inlet_d_depth",[7,8.5]],["adjuster_wire_bore",3],
 ["adjuster_cone_display_only",cip_adjuster_cone_display],
 ["adjuster_taper_depth_interval",[8.5,10]],["ferrule_nose_chamfer",undef],
 ["ferrule_part","03096-25-0350"],["ferrule_od_length",[5.5,11]],
 ["ferrule_inlet_d_depth",[5,9]],["ferrule_wire_bore",2.5],
 ["ferrule_mouth_display_local",[cip_ferrule_mouth_display,60,2]],
 ["ferrule_tip_display_local",[cip_ferrule_tip_display,60,2]],
 ["housing_end_display_local",[cip_ferrule_mouth_display+9,60,2]],
 ["adjuster_thread_x",[-53,-29]],["adjuster_overall_x",[-63,-29]],
 ["adjuster_shank_d",6],["housing_od",5],
 ["adjuster_nut_part",cip_adjuster_nut_part],["adjuster_nut_sw_t",[10,cip_adjuster_nut_t]],
 ["adjuster_nut_x",[for(x=cip_adjuster_nut_x)[x,x+cip_adjuster_nut_t]]],
 ["adjuster_washer_part",cip_adjuster_washer_part],
 ["adjuster_washer_od_id_t",[12,6.4,cip_adjuster_washer_t]],
 ["adjuster_washer_x",[for(x=cip_adjuster_washer_x)[x,x+cip_adjuster_washer_t]]],
 ["adjuster_seat_x",[-45,-37]],["adjuster_exposed_thread_each",3.2],
 ["adjuster_tool_budget",["SW10 thin open end, cover removed",3,20,25]],
 ["adjuster_tool_x",[for(x=cip_adjuster_tool_x)[x,x+3]]],
 ["body_axis_z",cip_axis_body_z],["lever_axis_z",cip_axis_lever_z],
 ["cover_axis_z",cip_axis_cover_z],["metal_sleeve_z",cip_axis_sleeve_z],
 ["metal_sleeve_od_id_length",[8,4.3,15]],["replaceable_bush_od_id_length",[12,8.2,11]],
 ["thrust_washer_od_id_t",[16,8.4,.25]],["total_axial_float",.5],
 ["stop_setting",cip_stop_setting],["stop_setting_range",[16,22]],
 ["stop_tip_x",cip_stop_tip()],["stop_tip_x_range",[cip_stop_tip(16),cip_stop_tip(22)]],
 ["stop_axis_local_yz",[-24,2]],["stop_screw","M3x30; captured nut plus locknut"],
 ["mount_holes_cad",[for(x=[-16,16],z=[-60,3])[x,-94,z]]],
 ["mount_plate_y",[-94,-86]],["mount_rib_y",[-86,-54]],
 ["mount_rib_lower_z",-65.7],["right_mount_rib_outer_x",21.7],
 ["upper_mount_key_x",cip_mount_key_x],
 ["mount_bolt","M4x60; replace old M4x20"],
 ["mount_bolt_underhead_y",-94.8],["mount_bolt_tip_y",-34.8],
 ["part_selectors",["assembly","body","lever","cover","fixed-hardware","moving-hardware","adjuster","ferrule","cable","probe","contract"]]
];
module cip_contract(){echo(cip_contract=cip_spec());}
module cip_to_cad(){multmatrix([
 [-cip_s,cip_s,0,cip_origin[0]],[0,0,1,cip_origin[1]],[cip_s,cip_s,0,cip_origin[2]],[0,0,0,1]])children();}
module cip_from_cad(){multmatrix([
 [-cip_s,0,cip_s,(cip_origin[0]-cip_origin[2])*cip_s],[cip_s,0,cip_s,-(cip_origin[0]+cip_origin[2])*cip_s],[0,1,0,-cip_origin[1]],[0,0,0,1]])children();}
module cip_box(x0,x1,y0,y1,z0,z1){translate([x0,y0,z0])cube([x1-x0,y1-y0,z1-z0]);}
module cip_zcyl(x,y,z,h,d){translate([x,y,z])cylinder(h=h,d=d);}
module cip_xcyl(y,z,x,h,d){translate([x,y,z])rotate([0,90,0])cylinder(h=h,d=d);}
module cip_ycyl(x,z,y,h,d){translate([x,y,z])rotate([-90,0,0])cylinder(h=h,d=d);}
module cip_zhex(x,y,z,h,af){translate([x,y,z])rotate([0,0,30])cylinder(h=h,d=af/cos(30),$fn=6);}
module cip_xhex(y,z,x,h,af){translate([x,y,z])rotate([0,90,0])rotate([0,0,30])cylinder(h=h,d=af/cos(30),$fn=6);}
module cip_yhex(x,z,y,h,af){translate([x,y,z])rotate([-90,0,0])rotate([0,0,30])cylinder(h=h,d=af/cos(30),$fn=6);}
module cip_sector(r0,r1,a0,a1,z0,z1){
 n=max(2,ceil((a1-a0)/2));
 translate([0,0,z0])linear_extrude(height=z1-z0)polygon(concat(
  [for(i=[0:n])[r1*cos(a0+(a1-a0)*i/n),r1*sin(a0+(a1-a0)*i/n)]],
  [for(i=[n:-1:0])[r0*cos(a0+(a1-a0)*i/n),r0*sin(a0+(a1-a0)*i/n)]]));
}
module cip_web(a,b,r,z0,z1){hull(){cip_zcyl(a[0],a[1],z0,z1-z0,2*r);cip_zcyl(b[0],b[1],z0,z1-z0,2*r);}}
module cip_zring(x,y,z,h,od,id){difference(){cip_zcyl(x,y,z,h,od);cip_zcyl(x,y,z-cip_eps,h+2*cip_eps,id);}}
module cip_xring(x,h,od,id){difference(){cip_xcyl(60,2,x,h,od);cip_xcyl(60,2,x-cip_eps,h+2*cip_eps,id);}}
module cip_xnut(x,af,h,id){difference(){cip_xhex(60,2,x,h,af);cip_xcyl(60,2,x-cip_eps,h+2*cip_eps,id);}}
module cip_zbolt(x,y,z_under,length,d,head_d,head_h,socket){
 cip_zcyl(x,y,z_under-length,length,d);
 difference(){cip_zcyl(x,y,z_under,head_h,head_d);cip_zhex(x,y,z_under+head_h/2,head_h/2+cip_eps,socket);}
}

// An H section has continuous 32 mm-deep webs. It is not four isolated posts.
// Keys straddle the ORIGINAL beam edges, without changing its source.
module cip_mount_cad_blank(){
 cip_box(-28.2,28.2,-94,-86,-68,28);
 // Clearance from the old strain-relief end Z=-66 and grip arm X=22.
 // These are not datum faces; retain the actual Y=-54 load face unchanged.
 for(x=[-16,16])cip_box(x-6,x>0?21.7:x+6,-86.1,-54,-65.7,9);
 cip_box(-22,22,-86.1,-54,-33,-27);
 // Side keys are over the original flat panel, away from its grip arms.
 for(s=[-1,1]){
  cip_box(s>0?20:-28.2,s>0?28.2:-20,-86.1,-54,-50,-20);
  cip_box(s>0?24.2:-28.2,s>0?28.2:-24.2,-54.1,-49,-50,-20);
 }
 // Key's full-depth root overlaps the backplate at Z22..28, Y-94..-86.
 // Narrow it between the actual output bridge X12 and old grip arm X20.
 cip_box(cip_mount_key_x[0],cip_mount_key_x[1],-94,-54,22,32.2);
 cip_box(cip_mount_key_x[0],cip_mount_key_x[1],-54.1,-49,28.2,32.2);
}
module cip_mount_cad(){difference(){cip_mount_cad_blank();
 for(x=[-16,16],z=[-60,3])cip_ycyl(x,z,-96,44,4.5);
}}
module cip_local_body_blank(){union(){
 cip_from_cad()cip_mount_cad();
 cip_web([0,0],cip_cad_to_local([0,-90,-28]),12,-12,-4);
 // Back cheek and continuous planar ribs join grip, cable reaction and host.
 cip_web([0,0],[-52,6],12,-12,-4);
 cip_web([-52,6],[-45,60],10,-12,-4);
 cip_web([0,0],[-45,60],7,-12,-4);
 cip_web([0,0],[74,20],7,-12,-4);
 cip_web([-52,6],[-64,-99],15,-12,14);
 for(p=cip_cheek_posts){cip_zcyl(p[0],p[1],-12,20,14);
  translate([p[0]-4,p[1]-4,7.9])cube([8,8,1.6]);}
 // M6 thin nuts + metal washers clamp this seat; tighten on bench before cover.
 cip_box(-45,-37,49,71,-12,12);
 // Adjustable trigger stop; rear tool entry tunnels through the fixed grip.
 cip_box(-42,-29,-34,-18,-12,12);
 // Actual end stops: lug lives at 177..183 degrees at rest.
 cip_sector(14,22,183,193,-4.1,8);
}}
module cip_local_body(){difference(){
 cip_local_body_blank();
 cip_zcyl(0,0,-13,28,4.5);
 cip_zcyl(0,0,-5.5,1.6,8.3); // steel spacer end seat, NOT the rotating bearing
 for(p=cip_cheek_posts){
  cip_zcyl(p[0],p[1],-13,30,3.4);
  cip_zhex(p[0],p[1],-12.1,3.1,5.8); // nuts enter from rear before mounting
 }
 cip_xcyl(60,2,-51,24,6.4);
 // OD12 washer edges would merely kiss the back rib Z=-4. Give .3 radial
 // clearance outside the load faces only; preserve the full 8 mm seat.
 cip_xcyl(60,2,-46.9,1.9,12.6);
 cip_xcyl(60,2,-37,1.9,12.6);
 // Thin wrench plane pockets: continuous rear material remains >=3.7 mm.
 // These are bench-service recesses, not in-place cover-on adjustment claims.
 for(x=cip_adjuster_tool_x)hull(){
  cip_xcyl(60,2,x-.2,3.4,20.6);cip_xcyl(85,2,x-.2,3.4,20.6);
 }
 cip_xcyl(-24,2,-90,63,3.4);
 cip_xcyl(-24,2,-90,51.8,7.2); // screw head + hex tool access from local -X
 // M3 nut loaded against X=-32.6; enters from rear before the screw.
 translate([-38.3,-24,2])rotate([0,90,0])rotate([0,0,30])cylinder(h=5.7,d=5.8/cos(30),$fn=6);
 // Re-cut host bolt paths after ALL brace unions; do not refill the holes.
 cip_from_cad()for(x=[-16,16],z=[-60,3])cip_ycyl(x,z,-100,50,4.5);
}}

module cip_local_lever_blank(){union(){
 cip_zcyl(0,0,-3.5,11,24);
 cip_web([0,0],[-4,-26],5.5,-3.5,7.5);
 cip_web([-4,-26],[1,-42],5,-3.5,7.5);
 cip_web([0,0],[56*cos(55),56*sin(55)],6,-3.5,7.5);
 cip_web([0,0],[56*cos(105),56*sin(105)],6,-3.5,7.5);
 cip_sector(53,64,40,115,-3.5,7.5);
 cip_sector(10,22,177,183,-3.5,7.5);
}}
module cip_local_lever_zero(){difference(){
 cip_local_lever_blank();
 cip_zcyl(0,0,-4,12,12.2); // removable POM bush, positively retained by washers
 // Face-open channel: wire centre is R60, Z2; fixed cover closes its top.
 cip_sector(58.9,61.1,44,116,.9,8);
 // A straight tangent must pass the outer rim on entry at every angle.
 cip_sector(60.8,66,89,116,.9,3.1);
 p=cip_point(cip_R,45,cip_wire_z);
 translate(p)sphere(d=cip_ball_seat_d);
 cip_zcyl(p[0],p[1],p[2],6,cip_ball_seat_d); // actual terminal insertion entry
}}
module cip_local_lever(u=cip_u){rotate([0,0,-cip_angle(u)])cip_local_lever_zero();}

module cip_local_cover_blank(sweep=0){union(){
 cip_zcyl(0,0,8,6+sweep,24);
 cip_sector(49,67,15,122,8,14+sweep);
 cip_web([0,0],[-30,20],7,8,14+sweep);
 cip_web([0,0],[74,20],7,8,14+sweep);
 cip_web([-30,20],[-28,54],6.5,8,14+sweep);
 cip_web([74,20],[62,30],7,8,14+sweep);
 for(p=cip_cheek_posts)cip_zcyl(p[0],p[1],8,6+sweep,16);
}}
module cip_local_cover(sweep=0){difference(){
 cip_local_cover_blank(sweep);
 cip_zcyl(0,0,7,8+sweep,4.5);
 cip_zcyl(0,0,7.9,1.6,8.3);
 for(p=cip_cheek_posts){
  cip_zcyl(p[0],p[1],7,9+sweep,3.4);
  translate([p[0]-4.2,p[1]-4.2,7.9])cube([8.4,8.4,1.8]);
 }
}}

module cip_mount_hardware_cad(){for(x=[-16,16],z=[-60,3]){
 // Original nuts/host washers remain in parent. THESE replace old screws.
 cip_ycyl(x,z,-94.8,60,4);
 difference(){cip_ycyl(x,z,-98.8,4,7);cip_yhex(x,z,-98.9,2.1,3);}
 difference(){cip_ycyl(x,z,-94.8,.8,9);cip_ycyl(x,z,-94.9,1,4.3);}
}}
module cip_local_fixed_hardware(){
 // Precision steel distance tube supports both cheeks and carries clamp load.
 cip_zring(0,0,-5.5,15,8,4.3);
 for(z=[-3.75,7.5])cip_zring(0,0,z,.25,16,8.4);
 cip_zbolt(0,0,14.8,35,4,7,4,3);
 cip_zring(0,0,14,.8,9,4.3);
 cip_zring(0,0,-12.8,.8,9,4.3);
 difference(){cip_zhex(0,0,-16,3.2,7);cip_zcyl(0,0,-16.1,3.4,4.1);}
 for(p=cip_cheek_posts){
  cip_zbolt(p[0],p[1],14.5,30,3,5.5,3,2.5);
  cip_zring(p[0],p[1],14,.5,7,3.2);
  difference(){cip_zhex(p[0],p[1],-11.4,2.4,5.5);cip_zcyl(p[0],p[1],-11.5,2.6,3.1);}
 }
 cip_local_adjuster();cip_local_ferrule();
 for(x=cip_adjuster_nut_x)cip_xnut(x,10,cip_adjuster_nut_t,6.1);
 for(x=cip_adjuster_washer_x)cip_xring(x,cip_adjuster_washer_t,12,6.4);
 // Adjustable M3 end stop: real screw, rear captive nut and accessible locknut.
 sx=cip_stop_tip();
 cip_xcyl(-24,2,sx-30,30,3);
 difference(){cip_xcyl(-24,2,sx-33,3,5.5);
  translate([sx-33.1,-24,2])rotate([0,90,0])rotate([0,0,30])cylinder(h=1.7,d=2.5/cos(30),$fn=6);}
 for(x=[-35,-29])difference(){
  translate([x,-24,2])rotate([0,90,0])rotate([0,0,30])cylinder(h=2.4,d=5.5/cos(30),$fn=6);
  cip_xcyl(-24,2,x-.1,2.6,3.1);
 }
}
// Drawing-derived outside/bores. The unmarked taper is a display parameter,
// never used to certify an exact housing reaction coordinate.
module cip_local_adjuster(){difference(){
 union(){cip_xhex(60,2,-63,10,8);cip_xcyl(60,2,-53,24,6);}
 cip_xcyl(60,2,-63.1,8.6,7);
 translate([-54.5,60,2])rotate([0,90,0])cylinder(h=cip_adjuster_cone_display,d1=7,d2=3);
 cip_xcyl(60,2,-54.5+cip_adjuster_cone_display-cip_eps,
   25.6-cip_adjuster_cone_display,3);
}}
module cip_local_ferrule(){difference(){
 cip_xcyl(60,2,cip_ferrule_mouth_display,11,5.5);
 cip_xcyl(60,2,cip_ferrule_mouth_display-cip_eps,9+cip_eps,5);
 translate([cip_ferrule_mouth_display+9,60,2])rotate([0,90,0])
  cylinder(h=cip_ferrule_cone_display,d1=5,d2=2.5);
 cip_xcyl(60,2,cip_ferrule_mouth_display-cip_eps,11+2*cip_eps,2.5);
}}
module cip_local_moving_hardware(u=cip_u){rotate([0,0,-cip_angle(u)]){
 cip_zring(0,0,-3.5,11,12,8.2); // replaceable POM reference, not printed PETG
 translate(cip_point(cip_R,45,cip_wire_z))sphere(d=cip_ball_d);
}}
module cip_local_cable(u=cip_u){
 // Constant tangent plus increasing wrapped length. This is ONE steel core.
 cip_xcyl(60,2,cip_ferrule_mouth_display,-cip_ferrule_mouth_display,cip_wire_d);
 a=45-cip_angle(u);
 translate([0,0,2])rotate([0,0,a])rotate_extrude(angle=90-a,$fn=180)
  translate([60,0,0])circle(d=cip_wire_d,$fn=24);
}

// Explicit tool budget, not an assertion that an unspecified purchased wrench fits.
// Opens toward -Y and enters from +Y. Flat gap10.4 clears the SW10 nut.
// sweep=25 is its continuous straight entry; actual tool width/thickness must fit.
module cip_local_adjuster_tool(index=0,sweep=0){
 x=cip_adjuster_tool_x[index];
 difference(){
  hull(){cip_xcyl(60,2,x,3,20);cip_xcyl(60+sweep,2,x,3,20);}
  cip_box(x-.1,x+3.1,-100,66,-3.2,7.2);
 }
 cip_box(x,x+3,69,105+sweep,-1,5);
}
module cip_body(){cip_to_cad()cip_local_body();}
module cip_lever(u=cip_u){cip_to_cad()cip_local_lever(u);}
module cip_cover(){cip_to_cad()cip_local_cover();}
module cip_fixed_hardware(){cip_mount_hardware_cad();cip_to_cad()cip_local_fixed_hardware();}
module cip_moving_hardware(u=cip_u){cip_to_cad()cip_local_moving_hardware(u);}
module cip_cable(u=cip_u){cip_to_cad()cip_local_cable(u);}
module cip_adjuster(){cip_to_cad()cip_local_adjuster();}
module cip_ferrule(){cip_to_cad()cip_local_ferrule();}
module cip_hardware(u=cip_u){cip_fixed_hardware();cip_moving_hardware(u);cip_cable(u);}
module cip_fixed(){cip_body();cip_cover();cip_fixed_hardware();}
module cip_moving(u=cip_u){cip_lever(u);cip_moving_hardware(u);}
module cip_probe(kind=cip_probe_kind,u=cip_u){
 if(kind=="motion")intersection(){cip_fixed();cip_moving(u);}
 else if(kind=="printed-fixed")intersection(){cip_body();cip_cover();}
 else if(kind=="hardware-fit")intersection(){union(){cip_body();cip_cover();cip_lever(u);}cip_hardware(u);}
 else if(kind=="cable-fit")intersection(){union(){cip_body();cip_cover();cip_lever(u);}cip_cable(u);}
 else if(kind=="adjuster-washer-fit")intersection(){union(){cip_body();cip_cover();cip_lever(u);}cip_to_cad()for(x=cip_adjuster_washer_x)cip_xring(x,cip_adjuster_washer_t,12,6.4);}
 else if(kind=="adjuster-tool")intersection(){union(){cip_body();cip_lever(u);cip_fixed_hardware();}cip_to_cad()for(i=[0,1])cip_local_adjuster_tool(i,25);}
 else if(kind=="terminal-entry")intersection(){cip_lever(u);cip_to_cad()rotate([0,0,-cip_angle(u)])hull(){
  translate(cip_point(cip_R,45,2))sphere(d=5);translate(cip_point(cip_R,45,22))sphere(d=5);}}
 else if(kind=="stop-contact")intersection(){cip_lever(u);cip_to_cad()cip_xcyl(-24,2,cip_stop_tip()-30,30,3);}
 else if(kind=="stop-tool")intersection(){union(){cip_body();cip_cover();cip_lever(u);}cip_to_cad(){
  cip_xcyl(-24,2,-100,100+cip_stop_tip()-33,4);
  translate([cip_stop_tip()-33,-24,2])rotate([0,90,0])rotate([0,0,30])cylinder(h=1.5,d=2.5/cos(30),$fn=6);}}
 // Continuous extrusion sweep preserves concave outline and every opening.
 else if(kind=="cover-removal")intersection(){union(){cip_body();cip_lever(u);cip_moving_hardware(u);}cip_to_cad()cip_local_cover(25);}
 else assert(false,str("Unknown cip_probe: ",kind));
}
module cip_assembly(){
 color([.19,.35,.45])cip_body();color([.12,.65,.85])cip_lever();
 color([.54,.68,.75,.7])cip_cover();color([.73,.75,.79])cip_hardware();
}
if(cip_part=="assembly")cip_assembly();
else if(cip_part=="body")cip_body();
else if(cip_part=="lever")cip_lever();
else if(cip_part=="cover")cip_cover();
else if(cip_part=="fixed-hardware")cip_fixed_hardware();
else if(cip_part=="moving-hardware")cip_moving_hardware();
else if(cip_part=="adjuster")cip_adjuster();
else if(cip_part=="ferrule")cip_ferrule();
else if(cip_part=="cable")cip_cable();
else if(cip_part=="probe")cip_probe();
else if(cip_part=="contract")cip_contract();
else assert(false,str("Unknown cip_part: ",cip_part));
