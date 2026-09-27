// Independent inlet review harness against archived old-33 composition.
// Never imported by the current final assembly. The pure library has no
// dependency on this harness or any la_* assembly.
include <inlet-retention-final.scad>
use <review-launcher-baseline33.scad>
use <feeder-support-harness.scad>
use <feeder-return-spring.scad>
ir_part="assembly";
ir_probe="neighbors";
ir_t=0;
ir_fault=0;

module ir_neighbors(t=ir_t){la_fixed();la_moving(t);rs_spring(t,true);}
module ir_host_without_beam(){difference(){la_fixed();sh_beam();sh_bolts();}}
module ir_sweep_y(travel){
 // Exact directional extrusion with a stated conservative +/-0.001 X/Z pad.
 // Unlike hull(children), this retains concavities not swept by translation.
 minkowski(){children();translate([-.001,min(0,travel),-.001])cube([.002,abs(travel),.002]);}
}
module ir_clamp_drivers(closure=ir_closure){for(x=[-ir_ear_x,ir_ear_x])ir_ycyl(x,ir_z,16.9-closure,55,4);}
module ir_anchor_drivers(){for(x=[-ir_key_x,ir_key_x])ir_ycyl(x,ir_key_z,-105,44.4,2.5);}
module ir_front_spanners(){for(x=[-ir_key_x,ir_key_x])difference(){
 ir_box(x-5,x+5,-41.4,-39.2,-190,-138);
 ir_box(x-2.6,x+2.6,-41.5,-39.1,-190.1,-139);
}}
module ir_m4_nut_feed(){for(x=[-ir_ear_x,ir_ear_x])ir_yhex(x,ir_z,-45,36.6,7);}
module ir_m25_nut_feed(){for(x=[-ir_key_x,ir_key_x])ir_yhex(x,ir_key_z,-41.5,22,5);}
module ir_strap_feed(){for(x=[-20.5,20.5])ir_box(x-.75,x+.75,-65,-34,-152,-132);}
module ir_clip(){intersection(){children();ir_box(-120,120,-120,90,-175,-80);}}
module ir_show(section=false){
 color([.63,.7,.75,.55])ir_clip(){la_fixed();}
 color([.12,.4,.56])ir_rear();color([.96,.61,.18])ir_front();color([.19,.52,.60])ir_backplate();
 color([.3,.32,.35])ir_hardware();
 color([.8,.2,.46,.4]){ir_pad_reference();ir_pad_reference(true);}
 color([.52,.65,.75,.2])ir_hose_reference();
}
module ir_probe_geometry(){
 if(ir_probe=="neighbors")intersection(){ir_printed();ir_neighbors();}
 else if(ir_probe=="new_hardware_fit")intersection(){ir_hardware();ir_printed();}
 else if(ir_probe=="new_hardware_neighbors")intersection(){ir_hardware();ir_neighbors();}
 else if(ir_probe=="halves")intersection(){ir_front();ir_rear();}
 else if(ir_probe=="overclosure_control")intersection(){ir_front_raw();translate([0,2.1,0])ir_rear();}
 else if(ir_probe=="hard_hose")intersection(){ir_printed();ir_hose_reference();}
 else if(ir_probe=="soft_overlap")intersection(){ir_pad_reference(true);ir_hose_reference();}
 else if(ir_probe=="key_insert_bench")intersection(){ir_sweep_y(35)ir_rear();sh_beam();}
 else if(ir_probe=="backplate_insert_bench")intersection(){ir_sweep_y(-35)ir_backplate();union(){sh_beam();ir_rear();}}
 else if(ir_probe=="front_remove")intersection(){ir_sweep_y(65)ir_front();union(){ir_rear();ir_backplate();ir_hose_reference();ir_neighbors();}}
 else if(ir_probe=="beam_install")intersection(){ir_sweep_y(-65){ir_rear();ir_backplate();ir_anchor_hardware();ir_m4_nuts();sh_beam();}union(){ir_host_without_beam();ir_hose_reference();}}
 else if(ir_probe=="wrong_rear_install_control")intersection(){ir_sweep_y(-65)ir_rear();sh_beam();}
 else if(ir_probe=="key_end_control")intersection(){translate([0,0,ir_fault])ir_rear();sh_beam();}
 else if(ir_probe=="clamp_driver")intersection(){ir_clamp_drivers();union(){ir_printed();ir_neighbors();ir_hardware();}}
 else if(ir_probe=="anchor_driver")intersection(){ir_anchor_drivers();union(){ir_printed();ir_neighbors();ir_hardware();}}
 else if(ir_probe=="anchor_spanner")intersection(){ir_front_spanners();union(){ir_printed();ir_neighbors();ir_hardware();ir_hose_reference();}}
 else if(ir_probe=="m4_nut_insert")intersection(){ir_m4_nut_feed();union(){ir_rear();ir_backplate();ir_neighbors();}}
 else if(ir_probe=="m25_nut_insert_bench")intersection(){ir_m25_nut_feed();union(){ir_rear();ir_backplate();sh_beam();}}
 else if(ir_probe=="m25_nut_hose_control")intersection(){ir_m25_nut_feed();ir_hose_reference();}
 else if(ir_probe=="strap_feed")intersection(){ir_strap_feed();union(){ir_printed();ir_neighbors();ir_hardware();ir_hose_reference();}}
 else if(ir_probe=="ball_path")intersection(){ir_printed();translate([0,0,-160])cylinder(h=70,d=41.5);}
 else assert(false,"Unknown inlet probe");
}
if(ir_part=="rear")ir_rear();
else if(ir_part=="front")ir_front_raw();
else if(ir_part=="backplate")ir_backplate();
else if(ir_part=="hardware")ir_hardware();
else if(ir_part=="pads") {ir_pad_reference();ir_pad_reference(true);}
else if(ir_part=="probe")ir_probe_geometry();
else if(ir_part=="section")intersection(){ir_show();ir_box(0,110,-110,80,-175,-80);}
else if(ir_part=="exploded"){
 color([.2,.5,.6])ir_rear();color([1,.6,.2])translate([0,45,0])ir_front();
 color([.2,.5,.6])translate([0,-25,0])ir_backplate();color([.65,.7,.75,.3])ir_clip()sh_beam();
 color([.8,.2,.46,.4]){ir_pad_reference();translate([0,45,0])ir_pad_reference(true);}
}else ir_show();
