// Replaceable right Y-guide cap with two adjustable endpoint-switch saddles.
// This is a nominal CAD candidate, not a released print or proven BY141 fit.
// The original guide datum, jack pockets, hard-stop faces and M3 axes remain.
use <feeder-frame-y-guide.scad>
use <electric-feeder-trigger-assembly.scad>
use <electric-feeder-assembly.scad>
use <electric-home-switch-screen.scad>
use <electric-full-stroke-switch-screen.scad>

es_part = "probe"; // probe, cap, home-tab, full-tab, context
es_probe = "cap-other-fixed";
es_t = 0;
es_switch_shift_z = 0; // catalogue OP setup sweep, -0.8..+0.8 mm
es_switch_x = 68;
es_switch_y = 42;
es_lug_x = [66,81];
es_lug_y = [36.5,42];
es_lug_home_z = [-3,7];
es_lug_full_z = [-37,-27];
es_mount_x = [es_switch_x+3.15,es_switch_x+9.65];
es_home_mount_z = 1.95;
es_full_mount_z = -31.95;
es_slot_adjust = .8;
es_slot_d = 2.25;
es_nut_pocket_x = 4.8;
es_nut_pocket_z = 5.8;
es_nut_pocket_y = [36.5,39.25];
es_motor_x = 85;
es_motor_y = 70; // seller-envelope corridor; drive joint is still unresolved
es_motor_d = 29;

assert(es_t>=0 && es_t<=1);
assert(es_switch_shift_z>=-es_slot_adjust && es_switch_shift_z<=es_slot_adjust);
assert(es_mount_x[1]+es_nut_pocket_x/2 < es_lug_x[1]);

module es_box(x0,x1,y0,y1,z0,z1){
    translate([x0,y0,z0]) cube([x1-x0,y1-y0,z1-z0]);
}
module es_reflect(){translate([0,0,-30]) scale([1,1,-1]) children();}
module es_spine(){
    // 40 mm overlap into the old removable cap; 0.15 mm clear of the nominal
    // OD7 washer at x=62.75 (maximum X=66.25).
    es_box(66.4,69,32,39,-35,5);
}
module es_lugs(){
    es_box(es_lug_x[0],es_lug_x[1],es_lug_y[0],es_lug_y[1],
           es_lug_home_z[0],es_lug_home_z[1]);
    es_box(es_lug_x[0],es_lug_x[1],es_lug_y[0],es_lug_y[1],
           es_lug_full_z[0],es_lug_full_z[1]);
}
module es_extra_blank(){es_spine();es_lugs();}
module es_mount_slot(x,z){
    hull() for(dz=[-es_slot_adjust,es_slot_adjust])
        translate([x,es_lug_y[0]-.1,z+dz]) rotate([-90,0,0])
            cylinder(h=es_lug_y[1]-es_lug_y[0]+.2,
                     d=es_slot_d,$fn=48);
}
module es_nut_pocket(x,z){
    // Rear-loading sliding M2 nut capture. Exact nut and bolt are still open.
    es_box(x-es_nut_pocket_x/2,x+es_nut_pocket_x/2,
           es_nut_pocket_y[0]-.1,es_nut_pocket_y[1],
           z-es_nut_pocket_z/2,z+es_nut_pocket_z/2);
}
module es_switch_cuts(){
    for(x=es_mount_x,z=[es_home_mount_z,es_full_mount_z]){
        es_mount_slot(x,z); es_nut_pocket(x,z);
    }
}
module es_cap(){
    difference(){
        union(){yg_at(1) yg_cap_local();es_extra_blank();}
        es_switch_cuts();
    }
}
module es_added_only(){difference(){es_cap();yg_at(1) yg_cap_local();}}
module es_home_switch(dz=es_switch_shift_z){
    translate([es_switch_x-58.5,es_switch_y-42,dz]) hs_non_actuating_envelope();
}
module es_full_switch(dz=es_switch_shift_z){
    translate([es_switch_x-58.5,es_switch_y-42,dz]) fs_switch();
}
module es_home_tab(t=es_t){
    // L route stays inboard of the switch saddle until its final finger at Y43.
    translate([0,0,20*t]) union(){
        es_box(54,59,23.5,44,5.8,9);
        es_box(54,es_switch_x+2.8,43,46.5,5.8,9);
    }
}
module es_full_tab(t=es_t){
    translate([0,0,20*(t-1)]) es_reflect() es_home_tab(0);
}
module es_motor_envelope(){
    // Seller-gallery overbound, not the selected SKU's real motor geometry.
    translate([es_motor_x,es_motor_y,-91]) cylinder(h=129,d=es_motor_d,$fn=96);
}
module es_switch_adjustment_tool(){
    // Ø4 straight screwdriver access from the exposed +Y face of each M2
    // switch fastener. Tool reach is screened, not a precise handle envelope.
    for(x=es_mount_x,z=[es_home_mount_z,es_full_mount_z])
        translate([x,47.8,z]) rotate([-90,0,0])
            cylinder(h=50,d=4,$fn=48);
}
module es_other_fixed(){
    difference(){it_fixed_printed();yg_at(1) yg_cap_local();}
}
module es_switches(){es_home_switch();es_full_switch();}
module es_tabs(t=es_t){es_home_tab(t);es_full_tab(t);}
module es_probe_geometry(){
    if(es_probe=="cap-other-fixed") intersection(){
        es_added_only();es_other_fixed();
    }
    else if(es_probe=="cap-moving") intersection(){
        es_cap();it_moving_printed(es_t,0);
    }
    else if(es_probe=="cap-hardware") intersection(){
        es_added_only();hs_selected_hardware(es_t);
    }
    else if(es_probe=="cap-motor-envelope") intersection(){
        es_added_only();es_motor_envelope();
    }
    else if(es_probe=="switch-cap") intersection(){
        es_switches();es_cap();
    }
    else if(es_probe=="switch-selected") intersection(){
        es_switches();it_fixed_printed();it_moving_printed(es_t,0);
    }
    else if(es_probe=="switch-hardware") intersection(){
        es_switches();hs_selected_hardware(es_t);
    }
    else if(es_probe=="switch-motor-envelope") intersection(){
        es_switches();es_motor_envelope();
    }
    else if(es_probe=="switch-tool-motor") intersection(){
        es_switch_adjustment_tool();es_motor_envelope();
    }
    else if(es_probe=="cap-service-tools") intersection(){
        es_added_only();
        for(z=[-29,-1]) yg_local_tools(z,false);
        for(z=[-30.5,.5]) yg_local_tools(z,true);
    }
    else if(es_probe=="tab-fixed") intersection(){
        es_tabs(es_t);it_fixed_printed();
    }
    else if(es_probe=="tab-other-moving") difference(){
        intersection(){es_tabs(es_t);it_moving_printed(es_t,0);}
        ed_carriage(es_t);
    }
    else if(es_probe=="tab-hardware") intersection(){
        es_tabs(es_t);hs_selected_hardware(es_t);
    }
    else if(es_probe=="tab-cap") intersection(){
        es_tabs(es_t);es_cap();
    }
    else if(es_probe=="tab-root-control") intersection(){
        es_tabs(es_t);ed_carriage(es_t);
    }
    else if(es_probe=="mount-slot-control") intersection(){
        es_cap();es_mount_slot(es_mount_x[0],es_home_mount_z);
    }
    else if(es_probe=="cap-self-control") intersection(){es_cap();es_cap();}
    else assert(false,"Unknown endpoint-cap probe");
}

if(es_part=="probe") es_probe_geometry();
else if(es_part=="cap") es_cap();
else if(es_part=="home-tab") es_home_tab();
else if(es_part=="full-tab") es_full_tab();
else if(es_part=="context") {
    color([.70,.74,.77,.42]) it_assembly(es_t,0);
    color([.12,.50,.78]) es_cap();
    color([.10,.12,.14]) es_switches();
    color([.99,.74,.11]) es_tabs(es_t);
    color([.90,.18,.15,.25]) es_motor_envelope();
}
else assert(false,"Unknown endpoint-cap part");
