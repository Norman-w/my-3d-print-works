// E-clip candidate BENCH access only. No ring/tool deformation model.
use <../candidate.scad>
use <../../current-axis-through-candidate/candidate.scad>
use <../../current-axis-retention-review/candidate.scad>
use <../../../cad/cable-trigger-input.scad>
$fn=72;
function eb_k()=1/cos(180/72);
module eb_fixed(){other_fixed_metal();}
module eb_preassembly(){ec_plastics();ar_rotor(0);eb_fixed();ci_local_cable(0);}
module eb_pin_seated_outer(){
 // q0: Lmax30.1 + engineering Nmax6, maxD8/headD16/T2.1.
 translate([0,0,-22.1])cylinder(h=36.1,d=8*eb_k());
 translate([0,0,11.5])cylinder(h=2.5,d=9*eb_k());
 translate([0,0,14])cylinder(h=2.1,d=16*eb_k());
}
module eb_pin_insertion(){
 // Continuous translation s0..60 of each enclosing primitive.
 translate([0,0,-22.1])cylinder(h=96.1,d=8*eb_k());
 translate([0,0,11.5])cylinder(h=62.5,d=9*eb_k());
 translate([0,0,14])cylinder(h=62.1,d=16*eb_k());
}
module eb_washer_sweep(){ec_ring(-76,64,15*eb_k(),8.4);}
module eb_tail_stack_max(){ec_ring(-15.6,3.6,15*eb_k(),8.4);}
module eb_empty_side_corridor(){
 // FREE-SPACE REQUEST only: stop outside the full shaft, not at its centre.
 // X[-60,-4.2],Y[-12,12],Z[-18.1,-15.7]. No clip or tool identity attached.
 translate([-60,-12,-18.1])cube([55.8,24,2.4]);
}
module eb_corridor_positive(){
 // Move endpoint into unrelieved conservative shaft to prove interference
 // detector responds. This is not an actual ring installation model.
 translate([.6,0,0])eb_empty_side_corridor();
}
