// Isolated standard-clevis-pin candidate, NOT production CAD.
// Invoke with -D 'ci_origin=[75,-85,5]' and explicit $fn=72 in wrappers.
// AMPG PIN301M8X35: E is under-head to NEAR EDGE of cross-hole.
// Both HRDW-M8-A2 washers are at the REAR; no washer under the pin head.
use <../../cad/cable-trigger-input.scad>
use <../current-axis-offset-candidate/candidate.scad>
use <../current-axis-retention-review/candidate.scad>
$fn=72;
pin_part="section";
pin_u=0;
pin_q=.525;
module pin_body(){offset_body();}
module pin_cover(){offset_cover();}
module pin_plastics(){pin_body();pin_cover();}
module pin_ring(z,h,od,id){difference(){
 translate([0,0,z])cylinder(h=h,d=od);
 translate([0,0,z-.01])cylinder(h=h+.02,d=id);
}}
module pin_clevis(q=pin_q){
 head=14+q;hole_z=head-30-2.25/2;
 difference(){union(){
  translate([0,0,head-35])cylinder(h=35,d=7.925);
  translate([0,0,head])cylinder(h=2.81,d=13.81);
 }
 translate([-8,0,hole_z])rotate([0,90,0])cylinder(h=16,d=2.25);
 }
}
module pin_rear_washers(){for(z=[-15.2,-13.6])pin_ring(z,1.6,15,8.5);}

// Explicit DISPLAY of the proposed split-pin installation, not supplier CAD.
// Eye and both splayed legs stay in the plane normal to the main axle.
// No claim that a freely hand-bent part automatically meets this envelope.
module pin_path(points,diam=.875){for(i=[0:len(points)-2])hull(){
 translate(points[i])sphere(d=diam,$fn=24);
 translate(points[i+1])sphere(d=diam,$fn=24);
}}
module pin_cotter_display(q=pin_q){
 z=14+q-31.125;
 translate([0,0,z]){
  for(s=[-1,1])pin_path([[-4.35,s*.4375,0],[4.4,s*.4375,0],
   [5.1,s*1.15,0],[5.1,s*(s>0?7:5.5),0]]);
  pin_path([for(i=[0:24])let(a=90+180*i/24)
   [-5.9+1.55*cos(a),1.55*sin(a),0]]);
  pin_path([[-5.9,1.55,0],[-4.35,.4375,0]]);
  pin_path([[-5.9,-1.55,0],[-4.35,-.4375,0]]);
 }
}

// CONDITIONAL geometry envelope:
// E=30 and L=35 held nominal (their supplier tolerances are still unknown).
// Pin D7.90..7.95; head D13.62..14/H2.62..3; hole D2..2.5;
// cotter straight leg D1.7..1.8; rear washers t1.4..1.8 each.
// Capture span ranges E-sum(t)..E+Dhole-Dcotter-sum(t), because the
// cotter can move inside its hole. Thus conservative g is 0.4..2.0.
// OD15 washers held nominal. Shaft/washer registration coaxial, no tilt.
module pin_axis_envelope(){
 k=1/cos(180/72);
 translate([0,0,-21])cylinder(h=37,d=7.95*k);
 // PROPOSED head-root acceptance envelope, NOT AMPG published geometry:
 // no more than D9.0 over 2.5mm under the head, matching available relief.
 translate([0,0,11.5])cylinder(h=4.5,d=9.0*k);
 translate([0,0,14])cylinder(h=5,d=14*k);
 pin_ring(-17.6,5.6,15*k,8.4);
}
module pin_cotter_envelope(){
 // Additional installed-shape REQUIREMENT, not catalogue tolerance:
 // ALL installed material, including transverse play, is within R24 of
 // the main shaft axis and within +/-1 of the straight cotter-leg centre
 // plane. That plane is perpendicular to the main shaft. Not merely a
 // thickness constraint about an unrelated eye centre.
 // Hole centre -17.25..-15, plus cotter in-hole axial play +/-0.4,
 // plus installed material +/-1: resulting Z -18.65..-13.6.
 translate([0,0,-18.65])cylinder(h=5.05,r=24/cos(180/72));
}
module pin_assembly(){
 color([.13,.48,.72])pin_plastics();ar_rotor(pin_u);
 color([.73,.76,.81]){pin_clevis();pin_rear_washers();offset_fixed_metal();}
 color([.94,.38,.12])pin_cotter_display();
 color([.25,.27,.29])ci_local_cable(pin_u);
}
if(pin_part=="clevis")ci_to_cad()pin_clevis();
else if(pin_part=="axis-envelope")ci_to_cad()pin_axis_envelope();
else if(pin_part=="cotter-envelope")ci_to_cad()pin_cotter_envelope();
else if(pin_part=="assembly")ci_to_cad()pin_assembly();
else if(pin_part=="local-assembly")pin_assembly();
else if(pin_part=="section")intersection(){pin_assembly();
 translate([-28,-.001,-30])cube([56,100,55]);}
else if(pin_part=="axis-plastic-probe")intersection(){pin_axis_envelope();pin_plastics();}
else if(pin_part=="cotter-plastic-probe")intersection(){pin_cotter_envelope();pin_plastics();}
else if(pin_part=="axis-metal-probe")intersection(){pin_axis_envelope();offset_fixed_metal();}
else if(pin_part=="cotter-metal-probe")intersection(){pin_cotter_envelope();offset_fixed_metal();}
else if(pin_part=="axis-rotor-probe")intersection(){pin_axis_envelope();ar_rotor(pin_u);}
else if(pin_part=="cotter-rotor-probe")intersection(){pin_cotter_envelope();ar_rotor(pin_u);}
else if(pin_part=="short-negative-control")intersection(){
 // Nominal E25, centred D2.25 hole with D1.75 cotter: forcing two rear
 // washers between the cotter and the housing penetrates the housing.
 pin_ring(14-25-2.25/2+1.75/2,3.2,15,8.4);pin_plastics();}
