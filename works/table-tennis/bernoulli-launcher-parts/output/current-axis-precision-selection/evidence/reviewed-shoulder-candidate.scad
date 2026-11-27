// Recessed precision-shoulder candidate; no production CAD modifications.
use <../current-axis-through-candidate/candidate.scad>
use <../../cad/cable-trigger-input.scad>
$fn=72;
part="section";
input_u=0;
module recessed_cover(){difference(){cover();
 translate([0,0,11.5])cylinder(h=4,d=13.8);
}}
module shoulder_plastics(){body();recessed_cover();}
module shoulder_axis(L=24.5,q=0,tw=1.6,F=12,nh=6){
 // q=0 is centered in a 23.5 mm capture span, not the old 26 mm span.
 lo=(-.5-L)/2+q;hi=(-.5+L)/2+q;
 translate([0,0,lo])cylinder(h=L,d=7.995);
 difference(){translate([0,0,hi])cylinder(h=6,d=13);
  ci_zhex(0,0,hi+3,3.02,5);}
 translate([0,0,lo-F])cylinder(h=F,d=6);
 ring(lo-tw,tw,12,6.4);
 difference(){ci_zhex(0,0,lo-tw-nh,nh,10);
  translate([0,0,lo-tw-nh-.02])cylinder(h=nh+.04,d=6.1);}
}
module shoulder_sweep(){
 // L24.45..24.55 supplier shoulder tolerance; full .95..1.05 float.
 // Head D<=13.2/H<=6.2 and F11.5..12.5 are DESIGN acceptance windows,
 // because the source only publishes nominal head dimensions and F.
 // Circumscribe every external circular envelope. The unexpanded inner
 // polygonal cuts remove LESS than the true circular bore, conservatively.
 k=1/cos(180/72);
 translate([0,0,-13.05])cylinder(h=25.6,d=7.995*k);
 translate([0,0,11.5])cylinder(h=7.25,d=13.2*k);
 translate([0,0,-25.55])cylinder(h=13.55,d=6*k);
 ring(-14.85,2.85,12*k,6.4);
 ring(-20.85,7.45,10/cos(30)*k,6.1);
}
module other_input_metal(){other_fixed_metal();thrust();ci_from_cad()ci_mount_hardware_cad();}
module rotor(){ci_local_lever(input_u);ci_local_moving_hardware(input_u);
 rotate([0,0,-ci_angle(input_u)])ci_local_terminal_cap();}
module static_route(){
 import("../cable-scene-export/20260927T091627124663Z/feeder__cable-housing.stl");
 import("../cable-scene-export/20260927T091627124663Z/feeder__cable-core-route.stl");
}
if(part=="plastic-probe")intersection(){shoulder_sweep();shoulder_plastics();}
else if(part=="metal-probe")intersection(){shoulder_sweep();other_input_metal();}
else if(part=="rotor-probe")intersection(){shoulder_sweep();rotor();}
else if(part=="external-probe")intersection(){ci_to_cad()shoulder_sweep();static_route();}
else if(part=="short-positive")intersection(){shoulder_axis(23.4);shoulder_plastics();}
else if(part=="cover")recessed_cover();
else if(part=="axis")shoulder_axis();
else if(part=="section"){
 color([.13,.48,.72])clip()shoulder_plastics();
 color([.94,.57,.15])clip()ci_local_lever(input_u);
 color([.78,.8,.83])clip()shoulder_axis();
 color([.3,.31,.34])clip()ci_local_moving_hardware(input_u);
 color([.95,.85,.35])clip()thrust();
}
