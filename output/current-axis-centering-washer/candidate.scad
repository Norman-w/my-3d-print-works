// CW-01 machined centering cup washer. Isolated design requirement, NOT bought.
// Units mm; input-local Z. shoulder_z is the actual tail shoulder face.
// Cup opens toward +Z (shoulder/head); nut is on -Z side.
// Nominal input-local shape spans shoulder_z-2.475 .. shoulder_z+.525.
$fn=180;
cw_part="washer";
cw_e=.05;

module cw_washer(shoulder_z=0,p=.525,T=3,od=12,pilot_d=8.03,
                 relief_d=6.85,relief_depth=.625,bore_d=6.45){
 assert(T-p-relief_depth>=1.75-1e-9,"Do not silently thin the load web");
 translate([0,0,shoulder_z])difference(){
  translate([0,0,p-T])cylinder(h=T,d=od);
  translate([0,0,0])cylinder(h=p+.01,d=pilot_d);
  translate([0,0,-relief_depth])cylinder(h=relief_depth+.01,d=relief_d);
  translate([0,0,p-T-.01])cylinder(h=T+.02,d=bore_d);
 }
}
// Explicit worst root envelope consumed from the CONDITIONAL supplier contract.
// The .032 axial growth encloses .02 face error plus 3.3*sin(.2deg).
// Radial offset is tested
// separately from the pilot: it already includes fit, coaxiality and tilt.
module cw_tail_envelope(e=cw_e){translate([e,0,0]){
 translate([0,0,-.532])cylinder(h=.532,d=6.6/cos(.2)/cos(180/180));
 translate([0,0,-12.5])cylinder(h=12,d=6/cos(.2)/cos(180/180));
}}
module cw_section(){intersection(){cw_washer();translate([-7,-.001,-4])cube([14,8,6]);}}
function cw_spec()=[
 ["status","ISOLATED_MACHINING_REQUIREMENT_NOT_RELEASED"],
 ["material_request","Machined SUS304, not heat/strength/torque qualified"],
 ["coordinate","+Z toward shoulder; z=0 actual shoulder seating face"],
 ["OD",[11.95,12.00]],["overall_T",[2.95,3.05]],
 ["pilot_ID",[8.02,8.04]],["pilot_depth_p",[.50,.55]],
 ["relief_finished_opening_ID",[6.80,6.88]],["relief_depth_from_seat",[.60,.65]],
 ["through_ID",[6.40,6.50]],
 ["position_diameter_to_pilot_axis_A_max",.02],
 ["seat_B_flatness_max",.005],["seat_B_perpendicularity_to_A_max",.005],
 ["mouth_C_flatness_max",.005],["mouth_C_parallelism_to_B_max",.01],
 ["nut_face_D_flatness_max",.005],["nut_face_D_parallelism_to_B_max",.01],
 ["edge_limit_pilot_mouth_and_floor_R_max",.05],
 ["root_hole_edge_break_included_in_6_88_finished_aperture",true],
 ["paired_seated_axis_tilt_max_deg",.2],
 ["total_radial_budget_max",.05],
 ["effective_captured_span","shoulder_L - p; NOT shoulder_L"],
 ["shoulder_to_nut_seat_thickness","T - p"]
];
if(cw_part=="washer")cw_washer();
else if(cw_part=="section")cw_section();
else if(cw_part=="contract")echo(cw_spec());
else if(cw_part=="root-clearance")intersection(){
 cw_washer(p=.55,T=2.95,pilot_d=8.02,relief_d=6.8,relief_depth=.60,bore_d=6.4);
 cw_tail_envelope(.05);
}
else if(cw_part=="eccentric-positive")intersection(){
 cw_washer(p=.55,T=2.95,pilot_d=8.02,relief_d=6.8,relief_depth=.60,bore_d=6.4);
 cw_tail_envelope(.2);
}
