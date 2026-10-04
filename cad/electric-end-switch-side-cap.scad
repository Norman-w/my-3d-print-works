// Side-bolted endpoint switch cap: M2 adjustment tools enter from +X, away
// from the seller-gallery motor envelope. This is an unreleased CAD candidate.
// Original right Y-guide cap's M3 axes, jack geometry and stop faces remain.
use <feeder-frame-y-guide.scad>
use <electric-feeder-trigger-assembly.scad>
use <electric-feeder-assembly.scad>
use <electric-home-switch-screen.scad>
use <electric-full-stroke-switch-screen.scad>

ss_part = "probe"; // probe, cap, carriage, home-tab, full-tab, context
ss_probe = "cap-other-fixed";
ss_t = 0;
ss_show_motor = true;
// Catalogue OP tolerance and the earlier click-window calculation require
// only these asymmetric case shifts, with 0.1 mm each-end mounting allowance.
// Larger upward excursions would put the switch housing into the moving tab.
ss_home_shift_z = 0; // -0.75..+0.15 mm
ss_full_shift_z = 0; // -0.15..+0.75 mm (mirrored home)
ss_case_x = 70;
ss_case_y = 35;
ss_case_x_end = ss_case_x+5.8;
ss_case_y_end = ss_case_y+12.8;
ss_mount_y = [ss_case_y+3.15,ss_case_y+9.65];
ss_home_mount_z = 1.95;
ss_full_mount_z = -31.95;
ss_home_adjust = [-.75,.15];
ss_full_adjust = [-.15,.75];
ss_nut_half_z = 2.35; // M2 AF4 hex corners: 4.62 mm across, plus allowance
ss_motor_x = 85;
ss_motor_y = 63;
ss_motor_d = 29;

assert(ss_t>=0 && ss_t<=1);
assert(ss_home_shift_z>=ss_home_adjust[0] && ss_home_shift_z<=ss_home_adjust[1]);
assert(ss_full_shift_z>=ss_full_adjust[0] && ss_full_shift_z<=ss_full_adjust[1]);

module ss_box(x0,x1,y0,y1,z0,z1){
    translate([x0,y0,z0]) cube([x1-x0,y1-y0,z1-z0]);
}
module ss_reflect(){translate([0,0,-30]) scale([1,1,-1]) children();}
module ss_spine(){
    // x=66 avoids the old OD7 washers at x<=66.25 only after the notch below.
    // Keep the load path in the removable cap's +X exterior, not its guide.
    ss_box(66.4,70,32,39,-35,5);
}
module ss_saddles(){
    ss_box(66.4,70,33,49,-3,5.4);
    ss_box(66.4,70,33,49,-35.4,-27);
}
module ss_blank(){ss_spine();ss_saddles();}
module ss_slot(y,z,adjust){
    hull() for(dz=adjust)
        translate([66.3,y,z+dz]) rotate([0,90,0])
            cylinder(h=3.8,d=2.25,$fn=48);
}
module ss_nut_pocket(y,z,adjust){
    // Rear-loaded M2 sliding nut trap. It remains a hardware footprint until
    // an actual nut, bolt length and service sequence are physically checked.
    ss_box(66.3,68.2,y-2.4,y+2.4,
           z+adjust[0]-ss_nut_half_z,z+adjust[1]+ss_nut_half_z);
}
module ss_cuts(){
    for(y=ss_mount_y){
        ss_slot(y,ss_home_mount_z,ss_home_adjust);
        ss_nut_pocket(y,ss_home_mount_z,ss_home_adjust);
        ss_slot(y,ss_full_mount_z,ss_full_adjust);
        ss_nut_pocket(y,ss_full_mount_z,ss_full_adjust);
    }
}
module ss_cap(){difference(){
    union(){yg_at(1) yg_cap_local();ss_blank();}
    ss_cuts();
}}
module ss_added_only(){difference(){ss_cap();yg_at(1) yg_cap_local();}}

// Rotate the catalogue D2F from X-long to Y-long. Its plunger becomes
// (x=72.9,y=36.2); the through-hole centres become y=38.15 and y=44.65.
// This still uses the conservative terminal slab from the earlier screen.
module ss_rotate(){
    translate([ss_case_x+47.8,ss_case_y-58.5,0])
        rotate([0,0,90]) children();
}
module ss_home_switch(dz=ss_home_shift_z){
    translate([0,0,dz]) ss_rotate() hs_non_actuating_envelope();
}
module ss_full_switch(dz=ss_full_shift_z){
    translate([0,0,dz]) ss_rotate() fs_switch();
}
module ss_switch_cases(){
    translate([0,0,ss_home_shift_z]) ss_rotate(){hs_case();hs_solder_clearance();}
    translate([0,0,ss_full_shift_z]) ss_rotate(){fs_case();fs_terminals();}
}
module ss_switches(){ss_home_switch();ss_full_switch();}
module ss_operating_markers(){
    ss_rotate() hs_nominal_operating_marker();
    ss_rotate() ss_reflect() hs_nominal_operating_marker();
}
module ss_home_tab(t=ss_t){
    // L route passes the old fixed boss at x=63..74,y=23.5..28. The 0.4 mm
    // nominal saddle gap is not a manufactured clearance claim.
    translate([0,0,20*t]) union(){
        ss_box(54,59,23.5,37.8,5.8,9);
        ss_box(54,74.2,34.5,37.8,5.8,9);
    }
}
module ss_full_tab(t=ss_t){
    translate([0,0,20*(t-1)]) ss_reflect() ss_home_tab(0);
}
module ss_tabs(t=ss_t){ss_home_tab(t);ss_full_tab(t);}
module ss_carriage(t=ss_t){
    // Both tabs are integral additions to the one existing printed frame.
    ed_carriage(t);ss_tabs(t);
}
module ss_motor_envelope(){
    translate([ss_motor_x,ss_motor_y,-91])
        cylinder(h=129,d=ss_motor_d,$fn=96);
}
module ss_switch_adjustment_tools(){
    // Ø4 straight screwdriver shaft, from both M2 heads to outside the motor.
    for(y=ss_mount_y){
        for(z=[ss_home_mount_z+ss_home_shift_z,
               ss_full_mount_z+ss_full_shift_z])
            translate([78.1,y,z]) rotate([0,90,0])
                cylinder(h=45,d=4,$fn=48);
    }
}
module ss_one_M2_screw(y,z){
    // M2x10 reaches 0.7 mm beyond a DIN439 M2 thin nut and clears the M3 head.
    translate([66.3,y,z]) rotate([0,90,0])
        cylinder(h=10,d=2,$fn=48);
    translate([75.8,y,z]) rotate([0,90,0])
        cylinder(h=.5,d=4.2,$fn=48); // face washer reference
    translate([76.3,y,z]) rotate([0,90,0])
        cylinder(h=1.8,d=3.8,$fn=48); // M2 head reference
    translate([67,y,z]) rotate([0,90,0])
        rotate([0,0,30]) cylinder(h=1.2,d=4/cos(30),$fn=6);
}
module ss_switch_fasteners(){
    for(y=ss_mount_y){
        ss_one_M2_screw(y,ss_home_mount_z+ss_home_shift_z);
        ss_one_M2_screw(y,ss_full_mount_z+ss_full_shift_z);
    }
}
module ss_other_fixed(){difference(){
    it_fixed_printed();yg_at(1) yg_cap_local();
}}
module ss_probe_geometry(){
    if(ss_probe=="cap-other-fixed") intersection(){
        ss_added_only();ss_other_fixed();
    }
    else if(ss_probe=="cap-moving") intersection(){
        ss_cap();it_moving_printed(ss_t,0);
    }
    else if(ss_probe=="cap-hardware") intersection(){
        ss_added_only();hs_selected_hardware(ss_t);
    }
    else if(ss_probe=="cap-service-tools") intersection(){
        ss_added_only();
        for(z=[-29,-1]) yg_local_tools(z,false);
        for(z=[-30.5,.5]) yg_local_tools(z,true);
    }
    else if(ss_probe=="cap-motor") intersection(){
        ss_cap();ss_motor_envelope();
    }
    else if(ss_probe=="cap-motor-removal") intersection(){
        translate([0,25*ss_t,0]) ss_cap();ss_motor_envelope();
    }
    else if(ss_probe=="switch-cap") intersection(){
        ss_switches();ss_cap();
    }
    else if(ss_probe=="switch-selected") intersection(){
        ss_switches();it_fixed_printed();it_moving_printed(ss_t,0);
    }
    else if(ss_probe=="switch-hardware") intersection(){
        ss_switches();hs_selected_hardware(ss_t);
    }
    else if(ss_probe=="switch-motor") intersection(){
        ss_switches();ss_motor_envelope();
    }
    else if(ss_probe=="switch-tool-motor") intersection(){
        ss_switch_adjustment_tools();ss_motor_envelope();
    }
    else if(ss_probe=="switch-tool-selected") intersection(){
        ss_switch_adjustment_tools();it_fixed_printed();it_moving_printed(ss_t,0);
    }
    else if(ss_probe=="fasteners-cap") intersection(){
        ss_switch_fasteners();ss_cap();
    }
    else if(ss_probe=="fasteners-selected") intersection(){
        ss_switch_fasteners();it_fixed_printed();it_moving_printed(ss_t,0);
    }
    else if(ss_probe=="fasteners-hardware") intersection(){
        ss_switch_fasteners();hs_selected_hardware(ss_t);
    }
    else if(ss_probe=="fasteners-motor") intersection(){
        ss_switch_fasteners();ss_motor_envelope();
    }
    else if(ss_probe=="fasteners-tab") intersection(){
        ss_switch_fasteners();ss_tabs(ss_t);
    }
    else if(ss_probe=="tab-fixed") intersection(){
        ss_tabs(ss_t);it_fixed_printed();
    }
    else if(ss_probe=="tab-other-moving") difference(){
        intersection(){ss_tabs(ss_t);it_moving_printed(ss_t,0);}
        ed_carriage(ss_t);
    }
    else if(ss_probe=="tab-hardware") intersection(){
        ss_tabs(ss_t);hs_selected_hardware(ss_t);
    }
    else if(ss_probe=="tab-cap") intersection(){
        ss_tabs(ss_t);ss_cap();
    }
    else if(ss_probe=="tab-switch-case") intersection(){
        ss_tabs(ss_t);ss_switch_cases();
    }
    else if(ss_probe=="nominal-contact-control") intersection(){
        ss_tabs(ss_t);ss_operating_markers();
    }
    else if(ss_probe=="tab-root-control") intersection(){
        ss_tabs(ss_t);ed_carriage(ss_t);
    }
    else if(ss_probe=="mount-slot-control") intersection(){
        ss_cap();ss_slot(ss_mount_y[0],ss_home_mount_z,ss_home_adjust);
    }
    else if(ss_probe=="old-cap-preserved") difference(){
        yg_at(1) yg_cap_local();ss_cap();
    }
    else if(ss_probe=="old-carriage-preserved") difference(){
        ed_carriage(ss_t);ss_carriage(ss_t);
    }
    else if(ss_probe=="cap-self-control") intersection(){ss_cap();ss_cap();}
    else assert(false,"Unknown side-cap probe");
}

if(ss_part=="probe") ss_probe_geometry();
else if(ss_part=="cap") ss_cap();
else if(ss_part=="carriage") ss_carriage();
else if(ss_part=="home-tab") ss_home_tab();
else if(ss_part=="full-tab") ss_full_tab();
else if(ss_part=="context") {
    // Replace the old cap in this scene; do not overlay two installed caps.
    color([.70,.74,.77,.40]) ss_other_fixed();
    color([.94,.55,.17,.70]) it_moving_printed(ss_t,0);
    color([.62,.65,.68,.75]) hs_selected_hardware(ss_t);
    color([.12,.50,.78]) ss_cap();
    color([.10,.12,.14]) ss_switches();
    color([.82,.83,.85]) ss_switch_fasteners();
    color([.99,.74,.11]) ss_tabs(ss_t);
    if(ss_show_motor) color([.90,.18,.15,.25]) ss_motor_envelope();
}
else assert(false,"Unknown side-cap part");
