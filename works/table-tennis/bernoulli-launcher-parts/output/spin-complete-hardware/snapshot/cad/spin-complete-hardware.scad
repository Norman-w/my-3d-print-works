// Complete NOMINAL METAL / TOOL references; never print these as fasteners.
// Threads are associated by dimensions, not helical contact/strength models.
include <spin-parameters.scad>
use <spin-head.scad>

sch_part="assembly";
sch_opaque=false;
sch_group="all";
sch_float=0;
sch_preload=0;
sch_held=false;
sch_delta=0;
sch_angle=0;
sch_tool_x=65.05;
sch_eps=.02;
$fn=72;

module sch_x_cyl(x,y,z,h,d,n=72){translate([x,y,z])rotate([0,90,0])cylinder(h=h,d=d,$fn=n);}
module sch_x_nut(x,y,z,d=3,af=5.5,h=2.4){difference(){
    sch_x_cyl(x,y,z,h,af/cos(30),6);
    sch_x_cyl(x-.02,y,z,h+.04,d+.2);
}}
module sch_x_bolt(under,y,z,length,d=3,head_d=5.5,head_h=3){
    sch_x_cyl(under-length,y,z,length,d);
    sch_x_cyl(under,y,z,head_h,head_d);
}
module sch_cover_hardware(){for(y=[-18,18],z=[27,61]){
    sch_x_bolt(59,y,z,12);sch_x_nut(49.3,y,z);
}}
module sch_cage_hardware(){for(y=[-11,11]){
    sch_x_bolt(59,y,43,12);sch_x_nut(49.3,y,43);
}}
module sch_guide_hardware(){for(z=[20,66]){
    mirror([1,0,0])sch_x_bolt(31+sh_opposite_washer_t,0,z,sh_opposite_screw_length);
    sch_x_nut(sh_opposite_nut_x,0,z);
    difference(){sch_x_cyl(-31-sh_opposite_washer_t,0,z,sh_opposite_washer_t,7);
        sch_x_cyl(-31-sh_opposite_washer_t-.02,0,z,sh_opposite_washer_t+.04,3.2);}
}}
module sch_keeper_hardware(f=sch_float){translate([f,0,0])for(y=[-7,7]){
    // DIN 7991, total length includes head; true nominal 90-degree cone.
    translate([26.75,y,sh_keeper_head_top-10])cylinder(h=8.5,d=3);
    translate([26.75,y,sh_keeper_head_top-1.7])cylinder(h=1.7,d1=2.6,d2=6);
    translate([26.75,y,57.1])difference(){
        cylinder(h=2.4,d=5.5/cos(30),$fn=6);
        translate([0,0,-.02])cylinder(h=2.44,d=3.2);
    }
}}
module sch_pull_hardware(f=sch_float){translate([f,0,0]){
    sch_x_bolt(sh_pull_cap_x+sh_pull_cap_length,0,sh_pull_z,45);
    sch_x_nut(sh_pull_nut_x+.3,0,sh_pull_z);
}}
module sch_latch_hardware(held=sch_held){
    sch_x_nut(sh_latch_nut_x+.3,0,sh_latch_bolt_z);
    if(held){
        sch_x_bolt(sh_latch_bolt_seat_x+sh_latch_washer_t,0,sh_latch_bolt_z,16);
        difference(){sch_x_cyl(sh_latch_bolt_seat_x,0,sh_latch_bolt_z,sh_latch_washer_t,7);
            sch_x_cyl(sh_latch_bolt_seat_x-.02,0,sh_latch_bolt_z,sh_latch_washer_t+.04,3.2);}
    }
}
module sch_clamp_hardware(){
    translate([-34,0,-13])rotate([0,0,90]){
        sch_x_bolt(5,0,0,16,4,7,4);
        rotate([90,0,0])sch_x_nut(-6.9,0,0,4,7,3.2);
    }
}
module sch_preload_hardware(p=sch_preload,locknut=true){
    tip=sh_spring_seat_front_x+sh_spring_seat_thickness-p;
    sch_x_cyl(tip,0,43,25,4);
    // ELESA+GANTER DIN464-M4-25: D16, shoulder D8, h9.5, k3.5.
    sch_x_cyl(tip+25,0,43,6,8);
    sch_x_cyl(tip+31,0,43,3.5,16);
    sch_x_nut(55.8,0,43,4,7,3.2);
    if(locknut)sch_x_nut(65,0,43,4,7,3.2);
}
module sch_hardware(group=sch_group,f=sch_float,p=sch_preload,held=sch_held){
    if(group=="all"||group=="cover")sch_cover_hardware();
    if(group=="all"||group=="cage")sch_cage_hardware();
    if(group=="all"||group=="guide")sch_guide_hardware();
    if(group=="all"||group=="keeper")sch_keeper_hardware(f);
    if(group=="all"||group=="pull")sch_pull_hardware(f);
    if(group=="all"||group=="latch")sch_latch_hardware(held);
    if(group=="all"||group=="clamp")sch_clamp_hardware();
    if(group=="all"||group=="preload")sch_preload_hardware(p);
}
module sch_printed(f=sch_float,p=sch_preload,held=sch_held){
    body();opposite_guide();cover();spring_cage();
    translate([f,0,0]){carriage();pad_keeper();pad();pull_cap();}
    translate([-p,0,0])spring_seat();
    if(held)hold_fork();
}
module sch_nut_feeds(group=sch_group){
    if(group=="cover")for(y=[-18,18],z=[27,61])hull()for(d=[0,y<0?-20:20])
        sch_x_nut(49.3,y+d,z);
    if(group=="cage")for(y=[-11,11])hull()for(d=[0,y<0?-20:20])
        sch_x_nut(49.3,y+d,43);
    if(group=="guide")for(z=[20,66])hull()for(d=[0,24])
        sch_x_nut(sh_opposite_nut_x,d,z);
    if(group=="keeper")for(y=[-7,7])hull()for(d=[0,y<0?-15:15])
        translate([26.75,y+d,57.1])cylinder(h=2.4,d=5.5/cos(30),$fn=6);
    if(group=="pull")hull()for(d=[0,16])sch_x_nut(sh_pull_nut_x+.3,0,57+d);
    if(group=="latch")hull()for(d=[0,16])sch_x_nut(sh_latch_nut_x+.3,0,69+d);
    if(group=="clamp")translate([-34,0,-13])rotate([0,0,90])hull()for(d=[0,-20])
        rotate([90,0,0])sch_x_nut(-6.9+d,0,0,4,7,3.2);
    if(group=="preload")hull()for(d=[0,30])sch_x_nut(55.8,d,43,4,7,3.2);
}
module sch_feed_host(group=sch_group){
    if(group=="cover"||group=="guide"||group=="clamp")body();
    if(group=="cage")spring_cage();
    if(group=="keeper"||group=="pull")carriage();
    if(group=="latch"||group=="preload")cover();
}
module sch_drivers(group=sch_group){
    if(group=="cover")for(y=[-18,18],z=[27,61])sch_x_cyl(62.05,y,z,45,4);
    if(group=="cage")for(y=[-11,11])sch_x_cyl(62.05,y,43,45,4);
    if(group=="guide")for(z=[20,66])sch_x_cyl(-80,0,z,45.45,4);
    if(group=="pull")sch_x_cyl(sh_pull_cap_x+sh_pull_cap_length+sch_float+3.05,0,57,45,4);
    if(group=="latch"&&sch_held)sch_x_cyl(74.05+sh_latch_washer_t,0,69,45,4);
    if(group=="clamp")translate([-34,0,-13])rotate([0,0,90])sch_x_cyl(9.05,0,0,45,5);
    if(group=="keeper")translate([sch_float,0,0])for(y=[-7,7])
        translate([26.75,y,65.05])cylinder(h=45,d=4);
}
module sch_lock_wrench(){
    // Conditional service envelope based on GEDORE red R09100070 catalogue:
    // 7 mm open end, head width15.5, thickness3.7, overall length105.
    // Solid envelope is intentionally conservative, not supplier tool CAD.
    translate([sch_tool_x,0,43])rotate([sch_angle,0,0])difference(){
        union(){sch_x_cyl(0,0,0,3.7,15.5);
            translate([0,-105,-7.75])cube([3.7,105,15.5]);}
        sch_x_cyl(-.02,0,0,3.74,7.2/cos(30),6);
        translate([-.02,0,-3.6])cube([3.74,12,7.2]);
    }
}
module sch_guide_subassembly(){opposite_guide();sch_guide_hardware();}
module sch_spring(f=sch_float,p=sch_preload){difference(){
    sch_x_cyl(sh_carrier_back_x+f,0,43,sh_spring_seat_front_x-p-sh_carrier_back_x-f,sh_spring_candidate_od);
    sch_x_cyl(sh_carrier_back_x+f-.02,0,43,sh_spring_seat_front_x-p-sh_carrier_back_x-f+.04,
        sh_spring_candidate_od-2*sh_spring_candidate_wire);
}}
module sch_show(){
    color([.33,.53,.65,sch_opaque?1:.6])sch_printed();
    color([.19,.20,.23])sch_hardware("all");
    color([.68,.48,.22,.6])sch_spring();
}
if(sch_part=="assembly")sch_show();
else if(sch_part=="hardware")sch_hardware();
else if(sch_part=="spring")sch_spring();
else if(sch_part=="fit")intersection(){sch_hardware();sch_printed();}
else if(sch_part=="nut-feed")intersection(){sch_nut_feeds();sch_feed_host();}
else if(sch_part=="wrong-preload-sequence")intersection(){sch_nut_feeds("preload");sch_cage_hardware();}
else if(sch_part=="driver")intersection(){sch_drivers();union(){sch_printed();sch_hardware("all");}}
else if(sch_part=="keeper-driver")intersection(){sch_drivers("keeper");union(){carriage();pad_keeper();pad();sch_keeper_hardware(0);}}
else if(sch_part=="wrench")intersection(){sch_lock_wrench();union(){
    sch_printed();
    for(g=["cover","cage","guide","keeper","pull","latch","clamp"])sch_hardware(g);
    sch_preload_hardware(sch_preload,false); // Intended driven nut omitted.
}}
else if(sch_part=="wrench-view"){sch_show();color([.85,.23,.16,.6])sch_lock_wrench();}
else if(sch_part=="guide-withdrawal")intersection(){body();translate([sch_delta,0,0])sch_guide_subassembly();}
else if(sch_part=="guide-bearing")intersection(){body();for(z=[20,66])
    difference(){sch_x_cyl(sh_opposite_nut_x-.01,0,z,.01,5.5/cos(30),6);
        sch_x_cyl(sh_opposite_nut_x-.02,0,z,.03,3.2);}}
else if(sch_part=="guide-withdrawal-view"){
    color([.33,.53,.65,.4])body();
    color([.9,.45,.1])translate([sch_delta,0,0])sch_guide_subassembly();
}
else if(sch_part=="fault")intersection(){sch_printed();translate([0,1,0])sch_hardware("cover");}
else assert(false,"Unknown spin complete hardware part");
