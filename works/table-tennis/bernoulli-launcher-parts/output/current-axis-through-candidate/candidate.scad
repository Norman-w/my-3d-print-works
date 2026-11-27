// Isolated design candidate. Not adopted into the production CAD or print set.
use <../../cad/cable-trigger-input.scad>
$fn=72;
part="section";
tube_length=27;
axis_offset=0;
input_u=0;
washer_t=1.1;

module ring(z,h,od,id){difference(){
 translate([0,0,z])cylinder(h=h,d=od);
 translate([0,0,z-.02])cylinder(h=h+.04,d=id);
}}
module body(){difference(){ci_local_body();
 translate([0,0,-13])cylinder(h=28,d=8.3);
}}
module cover(){difference(){ci_local_cover();
 translate([0,0,7])cylinder(h=8,d=8.3);
}}
module other_fixed_metal(){difference(){ci_local_fixed_hardware(0);
 translate([0,0,-25])cylinder(h=50,d=16.2);
}}
module thrust(){for(z=[-3.75,7.5])ring(z,.25,16,8.4);}
module actual_axis(L=tube_length,q=axis_offset,t=washer_t){
 lo=1-L/2+q;hi=1+L/2+q;
 ring(lo,L,8,4.3);
 ring(lo-t,t,12,4.3);ring(hi,t,12,4.3);
 ci_zbolt(0,0,hi+t,35,4,7,4,3);
 difference(){ci_zhex(0,0,lo-t-3.2,3.2,7);
  translate([0,0,lo-t-3.3])cylinder(h=3.4,d=4.1);}
}
module axis_sweep(){
 // Exact Z-interval outer envelopes for L=26.98..27.02, centered external
 // faces -12/14, all legal axial float, and washer t=.9..1.1.
 // Radial registration, bolt length and nut-height tolerances are NOT covered.
 ring(-13.02,28.04,8,4.3);
 ring(-14.12,2.12,12,4.3);
 ring(14,2.12,12,4.3);
 translate([0,0,-20.1])cylinder(h=36.22,d=4);
 // Conservative socket fill in the cap head.
 translate([0,0,14.9])cylinder(h=5.22,d=7);
 ring(-17.32,4.42,7/cos(30),4.1); // complete rotation envelope of hex nut
}
module plastics(){body();cover();}
module clip(){intersection(){
 children();
 // Native section through the axis; this is actual candidate geometry.
 translate([-18,-.001,-24])cube([36,30,49]);
}}
module section(){
 color([.13,.48,.72])clip()body();color([.13,.48,.72])clip()cover();
 color([.94,.57,.15])clip()ci_local_lever(input_u);
 color([.78,.8,.83])clip()actual_axis();
 color([.3,.31,.34])clip()ci_local_moving_hardware(input_u);
 color([.95,.85,.35])clip()thrust();
}
if(part=="body")body();
else if(part=="cover")cover();
else if(part=="plastic-probe")intersection(){axis_sweep();plastics();}
else if(part=="metal-probe")intersection(){axis_sweep();union(){other_fixed_metal();thrust();}}
else if(part=="rotor-probe")intersection(){axis_sweep();
 union(){ci_local_lever(0);ci_local_moving_hardware(0);}}
else if(part=="short-positive")intersection(){actual_axis(25.9,0,1.1);plastics();}
else if(part=="section")section();
else if(part=="assembly"){
 plastics();other_fixed_metal();thrust();actual_axis();
 ci_local_lever(input_u);ci_local_moving_hardware(input_u);}
