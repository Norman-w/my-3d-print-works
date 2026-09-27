// Independent inlet clamp candidate. mm, +Z ball feed. No frozen host changed.
// Soft liner and smooth hose are nominal reference envelopes, NOT purchased parts.
include <parameters.scad>
use <launcher-final-assembly.scad>
use <feeder-support-harness.scad>
use <feeder-return-spring.scad>

ir_part="assembly";
ir_probe="neighbors";
ir_closure=0;
ir_t=0;
ir_service=0;
ir_fault=0;
ir_z0=-123;
ir_z1=-101;
ir_z=-112;
ir_id=61;
ir_od=73;
ir_split=1.2;
ir_travel=2;
ir_pad_t=3; // Undeformed display ONLY; no hardness/force assumption.
ir_ear_x=43;
ir_key_x=10.5;
ir_key_z=-142;
ir_key_w=2.6;
ir_key_h=21.2;
ir_key_depth=5.8;
ir_eps=.02;
$fn=72;
assert(ir_closure>=0&&ir_closure<=ir_travel);
assert(ir_z0>=-126&&ir_z1<=-98);
assert(abs(2*ir_split-ir_travel-.4)<1e-9);

module ir_box(x0,x1,y0,y1,z0,z1){translate([x0,y0,z0])cube([x1-x0,y1-y0,z1-z0]);}
module ir_ycyl(x,z,y0,h,d,fn=72){translate([x,y0,z])rotate([-90,0,0])cylinder(h=h,d=d,$fn=fn);}
module ir_yhex(x,z,y0,h,af){translate([x,y0,z])rotate([-90,0,0])rotate([0,0,30])cylinder(h=h,d=af/cos(30),$fn=6);}
module ir_ring(od,id,z0=ir_z0,z1=ir_z1){difference(){translate([0,0,z0])cylinder(h=z1-z0,d=od);translate([0,0,z0-ir_eps])cylinder(h=z1-z0+2*ir_eps,d=id);}}
module ir_half(positive=false){ir_box(-100,100,positive?ir_split:-100,positive?100:-ir_split,-180,0);}
module ir_collar_blank(){union(){
 intersection(){ir_ring(ir_od,ir_id);ir_half(false);}
 for(s=[-1,1])hull(){
  translate([s*30,-6,ir_z])cube([8,8,ir_z1-ir_z0],center=true);
  translate([s*ir_ear_x,-6.6,ir_z])cube([12,10.8,ir_z1-ir_z0],center=true);
 }
}}
module ir_collar_rear(){difference(){
 ir_collar_blank();
 translate([0,0,ir_z0-ir_eps])cylinder(h=ir_z1-ir_z0+2*ir_eps,d=ir_id);
 for(x=[-ir_ear_x,ir_ear_x]){
  ir_ycyl(x,ir_z,-20,45,4.5);
  // Axial -Y insertion: actual M4 AF7 x3.2 sits against Y=-8.4.
  ir_yhex(x,ir_z,-12-ir_eps,3.6+ir_eps,7.4);
 }
}}
module ir_front_raw(){difference(){
 mirror([0,1,0])ir_collar_blank();
 translate([0,0,ir_z0-ir_eps])cylinder(h=ir_z1-ir_z0+2*ir_eps,d=ir_id);
 for(x=[-ir_ear_x,ir_ear_x])ir_ycyl(x,ir_z,-20,45,4.5);
}}
module ir_front(closure=ir_closure){translate([0,-closure,0])ir_front_raw();}
module ir_anchor_blank(){union(){
 ir_box(-28,28,-48,-42,-156,-128);
 for(x=[-ir_key_x,ir_key_x])ir_box(x-ir_key_w/2,x+ir_key_w/2,
  -48-ir_key_depth,-47.8,ir_key_z-ir_key_h/2,ir_key_z+ir_key_h/2);
}}
module ir_anchor_cuts(){
 for(x=[-ir_key_x,ir_key_x])ir_ycyl(x,ir_key_z,-60,30,2.9);
 // Replacement SINGLE-LAYER textile paths; old slots now carry the keys.
 for(x=[-20.5,20.5])ir_box(x-1.5,x+1.5,-49,-41,-153,-131);
}
module ir_rear(){difference(){union(){
 ir_collar_rear();ir_anchor_blank();
 for(x=[-ir_key_x,ir_key_x])hull(){
  ir_box(x-4,x+4,-39,-32,-121,-105);
  ir_box(x-4,x+4,-48,-42,-150,-134);
 }
}ir_anchor_cuts();}}
module ir_backplate(){difference(){
 ir_box(-14,14,-57,-54,-156,-128);
 for(x=[-ir_key_x,ir_key_x])ir_ycyl(x,ir_key_z,-58,5,2.9);
}}
module ir_printed(closure=ir_closure){ir_rear();ir_front(closure);ir_backplate();}
module ir_washer(x,z,y,od,id,t){difference(){ir_ycyl(x,z,y,t,od);ir_ycyl(x,z,y-ir_eps,t+2*ir_eps,id);}}
module ir_nut(x,z,y,af,h,d){difference(){ir_yhex(x,z,y,h,af);ir_ycyl(x,z,y-ir_eps,h+2*ir_eps,d);}}
module ir_m4_nuts(){for(x=[-ir_ear_x,ir_ear_x])ir_nut(x,ir_z,-11.6,7,3.2,4);}
module ir_clamp_hardware(closure=ir_closure){
 ir_m4_nuts();
 for(x=[-ir_ear_x,ir_ear_x]){
  ir_ycyl(x,ir_z,12.8-closure-30,30,4);
  difference(){ir_ycyl(x,ir_z,12.8-closure,4,7);ir_yhex(x,ir_z,14.8-closure,2.1,3);}
  ir_washer(x,ir_z,12-closure,12,4.3,.8);
 }
}
// M2.5 hardware envelope requirements; commercial SKU not yet frozen.
module ir_anchor_hardware(){for(x=[-ir_key_x,ir_key_x]){
 ir_ycyl(x,ir_key_z,-57.5,20,2.5);
 difference(){ir_ycyl(x,ir_key_z,-60.5,3,5);ir_yhex(x,ir_key_z,-60.6,1.6,2);}
 ir_washer(x,ir_key_z,-57.5,6,2.7,.5);
 ir_washer(x,ir_key_z,-42,6,2.7,.5);
 ir_nut(x,ir_key_z,-41.5,5,2,2.5);
}}
module ir_hardware(closure=ir_closure){ir_clamp_hardware(closure);ir_anchor_hardware();}
module ir_hose_reference(){ir_ring(hose_od,hose_id,-166,-98);}
module ir_pad_reference(front=false,closure=ir_closure){translate([0,front?-closure:0,0])intersection(){ir_ring(ir_id,ir_id-2*ir_pad_t);ir_half(front);}}
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
