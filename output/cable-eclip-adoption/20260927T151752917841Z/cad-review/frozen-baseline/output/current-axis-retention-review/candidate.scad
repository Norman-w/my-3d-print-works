// Isolated positive-retention study; input-local coordinates, NOT adopted CAD.
include <../../cad/parameters.scad>
use <../../cad/cable-trigger-input.scad>
$fn=72;
ar_part="rotor";
ar_u=0;
ar_af=12;
ar_socket_af=12.4;
ar_id=8.2;
ar_length=11;
ar_edge=.05; // nominal outer edge break; design maximum .05
ar_bore_edge=.1; // inner edge break maximum .1
module ar_hex_2d(af=ar_af){rotate(30)circle(d=af/cos(30),$fn=6);}
module ar_D_2d(d=12,flat=5.5){intersection(){circle(d=d);translate([-20,-20])square([20+flat,40]);}}
module ar_socket(){translate([0,0,-4])linear_extrude(height=12)ar_hex_2d(ar_socket_af);}
module ar_lever_zero(){difference(){ci_local_lever_zero();ar_socket();}}
module ar_lever(u=ar_u){rotate([0,0,-ci_angle(u)])ar_lever_zero();}
module ar_bush_zero(){z=2-ar_length/2;difference(){
 union(){
  translate([0,0,z])linear_extrude(height=ar_edge,scale=ar_af/(ar_af-2*ar_edge))ar_hex_2d(ar_af-2*ar_edge);
  translate([0,0,z+ar_edge])linear_extrude(height=ar_length-2*ar_edge)ar_hex_2d();
  translate([0,0,z+ar_length-ar_edge])linear_extrude(height=ar_edge,scale=(ar_af-2*ar_edge)/ar_af)ar_hex_2d();
 }
 translate([0,0,z-.01])cylinder(h=ar_length+.02,d=ar_id);
 translate([0,0,z])cylinder(h=ar_bore_edge,d1=ar_id+2*ar_bore_edge,d2=ar_id);
 translate([0,0,z+ar_length-ar_bore_edge])cylinder(h=ar_bore_edge,d1=ar_id,d2=ar_id+2*ar_bore_edge);
}}
module ar_bush(u=ar_u){rotate([0,0,-ci_angle(u)])ar_bush_zero();}
module ar_thrust(){for(z=[-3.75,7.5])translate([0,0,z])difference(){
 cylinder(h=.25,d=16);translate([0,0,-.01])cylinder(h=.27,d=10);
}}
module ar_other_moving_hardware(u=ar_u){difference(){ci_local_moving_hardware(u);translate([0,0,-4])cylinder(h=12,d=12.1);}}
module ar_rotor(u=ar_u){
 color([.93,.57,.14])ar_lever(u);color([.9,.93,.94])ar_bush(u);color([.95,.85,.25])ar_thrust();
 rotate([0,0,-ci_angle(u)])ci_local_terminal_cap();ar_other_moving_hardware(u);
}
function ar_spec()=[
 ["coordinates","input local; wrap ci_to_cad() for feeder CAD"],
 ["status","isolated mechanical retention candidate; no adoption or machining order"],
 ["bush_material_requirement","unfilled POM-C, machined; grade/supplier unselected"],
 ["bush_AF",[11.97,12]], ["bush_ID",[8.20,8.25]], ["bush_L",[10.97,11]],
 ["bore_cylindricity_max",.02],["bore_to_hex_center_position_diameter_max",.05],
 ["end_parallelism_max",.02],["end_perpendicularity_to_bore_max",.03],
 ["outer_edge_break_max",.05],["bore_edge_break_max",.10],
 ["socket_AF_CAD",12.4],["socket_actual_acceptance_AF",[12.2,12.6]],
 ["washer_source","SWSPS16-10-.25 catalogue candidate; OD15.5..16/ID10..10.5/t.225..275"],
 ["axis_retention","existing two thrust washers; no extra cap/screw; requires assembled cheeks"],
 ["rotation_retention","hex form-fit to lever; not shaft antirotation"],
 ["axis_interface","through/shoulder axle independent; no old L27/M4 head inherited here"]
];
if(ar_part=="lever")ar_lever();
else if(ar_part=="bush")ar_bush();
else if(ar_part=="thrust-washers")ar_thrust();
else if(ar_part=="contract")echo(ar_spec());
else if(ar_part=="hex-profile")ar_hex_2d();
else if(ar_part=="D-profile")ar_D_2d();
else if(ar_part=="local-fit")intersection(){ar_lever();ar_bush();}
else ar_rotor();
