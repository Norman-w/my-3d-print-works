// Isolated candidate. Invoke with -D 'ci_origin=[75,-85,5]'.
// The four mounting holes and mating faces remain in their original CAD coordinates.
use <../../cad/cable-trigger-input.scad>
use <../current-axis-through-candidate/candidate.scad>
use <../current-axis-retention-review/candidate.scad>
use <../current-axis-centering-washer/candidate.scad>
$fn=72;
part="section";
input_u=0;
module offset_body(){body();}
module offset_cover(){difference(){cover();
 // Published D8 shoulder screw head-root envelope: max D8.7 x 2.5.
 // This is a root relief, not a recessed screw-head seat.
 translate([0,0,11.3])cylinder(h=3,d=9.2);
}}
module offset_plastics(){offset_body();offset_cover();}
module cup_washer(lo,p=.525,T=3){cw_washer(shoulder_z=lo,p=p,T=T);}
module offset_axis(L=27,p=.525,T=3,q=0){
 hi=1+(L-p)/2+q;lo=hi-L;
 translate([0,0,lo])cylinder(h=L,d=7.995);
 // Conservative maximum root profile, actual manufacturer profile is rounded.
 translate([0,0,hi-2.5])cylinder(h=2.5,d=8.7);
 difference(){translate([0,0,hi])cylinder(h=6,d=13);
  ci_zhex(0,0,hi+3,3.02,5);}
 translate([0,0,lo-12])cylinder(h=12,d=6);
 // Additional proposed supply envelope, not a published supplier guarantee.
 translate([0,0,lo-.5])cylinder(h=.5,d=6.6);
 cup_washer(lo,p,T);
 difference(){ci_zhex(0,0,lo+p-T-6,6,10);
  translate([0,0,lo+p-T-6.02])cylinder(h=6.04,d=6.1);}
}
module offset_axis_sweep(){
 // Coaxial all-float envelope, L26.95..27.05, p.50..55, T2.95..3.05.
 // External circles circumscribed, internal cuts inscribed.
 k=1/cos(180/72);
 translate([0,0,-13.05])cylinder(h=27.6,d=7.995*k);
 translate([0,0,11.5])cylinder(h=3.05,d=8.7*k);
 translate([0,0,14])cylinder(h=6.75,d=13.2*k);
 translate([0,0,-25.55])cylinder(h=13.05,d=6*k);
 translate([0,0,-13.55])cylinder(h=1.05,d=6.6*k);
 ring(-15.60,3.60,12*k,6.4);
 ring(-21.60,6.65,10/cos(30)*k,6.1);
}
module offset_fixed_metal(){other_fixed_metal();ci_from_cad()ci_mount_hardware_cad();}
module offset_assembly(){
 color([.13,.48,.72])offset_plastics();
 ar_rotor(input_u);
 color([.74,.77,.82]){offset_axis();offset_fixed_metal();}
 color([.25,.27,.29])ci_local_cable(input_u);
}
if(part=="body")ci_to_cad()offset_body();
else if(part=="cover")ci_to_cad()offset_cover();
else if(part=="axis")ci_to_cad()offset_axis();
else if(part=="assembly")ci_to_cad()offset_assembly();
else if(part=="local-assembly")offset_assembly();
else if(part=="plastic-probe")intersection(){offset_axis_sweep();offset_plastics();}
else if(part=="metal-probe")intersection(){offset_axis_sweep();offset_fixed_metal();}
else if(part=="rotor-probe")intersection(){offset_axis_sweep();ar_rotor(input_u);}
else if(part=="rotor-plastic-probe")intersection(){offset_plastics();ar_rotor(input_u);}
else if(part=="body-metal-probe")intersection(){offset_body();offset_fixed_metal();}
else if(part=="mount-missing-probe")difference(){ci_mount_cad();ci_to_cad()offset_body();}
else if(part=="short-positive")intersection(){offset_axis(26);offset_plastics();}
else if(part=="unrelieved-root-positive")intersection(){offset_axis();cover();}
else if(part=="section")intersection(){offset_assembly();translate([-19,-.001,-30])cube([38,90,59]);}
