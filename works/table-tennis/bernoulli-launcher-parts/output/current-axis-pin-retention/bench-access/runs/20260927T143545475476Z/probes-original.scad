// Bench-only continuous insertion envelopes. No production geometry changed.
// Explicit ci_origin override must be supplied by runner; $fn=72 is deliberate.
use <../candidate.scad>
use <../../current-axis-through-candidate/candidate.scad>
use <../../current-axis-retention-review/candidate.scad>
use <../../../cad/cable-trigger-input.scad>
$fn=72;
function bench_k()=1/cos(180/72);
module bench_fixed(){other_fixed_metal();}
module bench_preassembly(){pin_plastics();ar_rotor(0);bench_fixed();ci_local_cable(0);}
module bench_pin_seated_outer(){
 translate([0,0,-21])cylinder(h=35,d=7.95*bench_k());
 translate([0,0,11.5])cylinder(h=2.5,d=9*bench_k());
 translate([0,0,14])cylinder(h=3,d=14*bench_k());
}
module bench_pin_insertion(){
 // Exact continuous +Z translation sweep of each coaxial envelope primitive,
 // s in[0,60]. Start at s60, move toward s0; do not hull an annular part.
 translate([0,0,-21])cylinder(h=95,d=7.95*bench_k());
 translate([0,0,11.5])cylinder(h=62.5,d=9*bench_k());
 translate([0,0,14])cylinder(h=63,d=14*bench_k());
}
module bench_tail_washer_sweep(){
 // First/second can be carried individually. All allowed thicknesses and
 // their matched stop positions are enclosed in this annular swept tube.
 pin_ring(-75.6,63.6,15*bench_k(),8.4);
}
module bench_tail_washers_max_stack(){pin_ring(-15.6,3.6,15*bench_k(),8.4);}
module bench_x_tube(z,d=1.8){
 translate([-40,0,z])rotate([0,90,0])cylinder(h=52,d=d*bench_k());
}
module bench_cotter_straight_sweep(){
 // Rigid straight-leg sweep ONLY, centred on the actual transverse hole.
 // E30, q0 and D-hole[2,2.5] give centre Z[-17.25,-17].
 hull(){bench_x_tube(-17.25);bench_x_tube(-17);}
}
module bench_min_hole_pin(){difference(){
 bench_pin_seated_outer();
 translate([-10,0,-17])rotate([0,90,0])cylinder(h=20,d=2);
}}
