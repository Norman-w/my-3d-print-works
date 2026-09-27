// Isolated fastening revision of the L27 floating axle. Not adopted.
use <../candidate.scad>
use <../../../cad/cable-trigger-input.scad>
$fn=72;
part="section";
input_u=0;

module locking_axis(L=27,q=0,tw=1.1,bolt_L=40,nut_h=5){
 lo=1-L/2+q;hi=1+L/2+q;
 ring(lo,L,8,4.3);
 ring(lo-tw,tw,12,4.3);ring(hi,tw,12,4.3);
 ci_zbolt(0,0,hi+tw,bolt_L,4,7,4,3);
 // DIN985 outer envelope, insert at distal (-Z) end; not a thread CAD.
 difference(){ci_zhex(0,0,lo-tw-nut_h,nut_h,7);
  translate([0,0,lo-tw-nut_h-.02])cylinder(h=nut_h+.04,d=4.1);}
}
module locking_sweep(){
 // Continuous coaxial envelope. L=26.98..27.02, washers=.9..1.1,
 // full legal float in external span 26. Bolt L=39..41 is a DESIGN
 // acceptance window, not a supplier-published length tolerance.
 ring(-13.02,28.04,8,4.3);
 ring(-14.12,2.12,12,4.3);ring(14,2.12,12,4.3);
 translate([0,0,-26.1])cylinder(h=42.22,d=4);
 translate([0,0,14.9])cylinder(h=5.22,d=7);
 ring(-19.12,6.22,7/cos(30),4.1);
}
module local_other_metal(){other_fixed_metal();thrust();
 ci_from_cad()ci_mount_hardware_cad();}
module rotating_parts(){ci_local_lever(input_u);ci_local_moving_hardware(input_u);
 rotate([0,0,-ci_angle(input_u)])ci_local_terminal_cap();}
module external_overlap_candidates(){
 // Frozen t=0 scene; each selected part is FIXED. review.py verifies
 // source/STL identity and independently rebuilds the broad phase.
 import("../../cable-scene-export/20260927T091627124663Z/feeder__beam-grip.stl");
 import("../../cable-scene-export/20260927T091627124663Z/feeder__cable-housing.stl");
 import("../../cable-scene-export/20260927T091627124663Z/feeder__cable-core-route.stl");
}
if(part=="plastic-probe")intersection(){locking_sweep();plastics();}
else if(part=="metal-probe")intersection(){locking_sweep();local_other_metal();}
else if(part=="rotor-probe")intersection(){locking_sweep();rotating_parts();}
else if(part=="external-probe")intersection(){ci_to_cad()locking_sweep();external_overlap_candidates();}
else if(part=="external-nominal-witness")intersection(){ci_to_cad()locking_axis();external_overlap_candidates();}
else if(part=="short-positive")intersection(){locking_axis(25.9);plastics();}
else if(part=="axis")locking_axis();
else if(part=="section"){
 color([.13,.48,.72])clip()plastics();
 color([.94,.57,.15])clip()ci_local_lever(input_u);
 color([.78,.8,.83])clip()locking_axis();
 color([.3,.31,.34])clip()ci_local_moving_hardware(input_u);
 color([.95,.85,.35])clip()thrust();
}
