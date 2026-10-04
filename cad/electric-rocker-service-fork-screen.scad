// Split service fork candidate for the Y=65 rocker. Millimetres, X1C/PETG.
// Base retains the shell anchor and front cheek. Rear cheek approaches from
// +Y after the rocker pin enters the crosshead slot. A tongue carries the
// nominal X/Z shear alignment; two M3 bolts clamp captive nuts inserted from
// the mating face before the rear cheek closes it. Real bolt/nut fit, PETG
// joint strength and motor load remain unverified.
use <electric-rocker-pivot-mount-screen.scad>
use <electric-rocker-clamped-fork-screen.scad>
use <electric-rocker-pivot-joint-screen.scad>
use <electric-output-crosshead-screen.scad>
use <electric-end-switch-side-cap.scad>
use <electric-feeder-trigger-assembly.scad>
use <electric-home-switch-screen.scad>

sf_part = "probe"; // probe, base, rear, context
sf_probe = "base-fixed";
sf_t = 0;
sf_rear_offset_y = 0;
sf_rocker_offset_y = 0;
sf_shaft_offset_y = 0;
sf_nut_offset_y = 0;
sf_pivot_x = 85-sqrt(75*75-15*15);
sf_bolt_x = 15;
sf_bolt_z = [-14, 2];
sf_base_mating_y = 68;
sf_rear_foot_end_y = 76;
sf_tongue_x = [10,20];
sf_tongue_z = [-8,-4];
sf_tongue_end_y = 72;
sf_key_clearance = .3;

assert(sf_t>=0 && sf_t<=1);
assert(sf_rear_offset_y>=0 && sf_rear_offset_y<=25);
assert(sf_rocker_offset_y>=0 && sf_rocker_offset_y<=25);
assert(sf_shaft_offset_y>=0 && sf_shaft_offset_y<=25);
assert(sf_nut_offset_y>=0 && sf_nut_offset_y<=25);
assert(sf_bolt_z[1]-sf_bolt_z[0]>=16);

module sf_box(x0,x1,y0,y1,z0,z1){
    translate([x0,y0,z0])cube([x1-x0,y1-y0,z1-z0]);
}
module sf_anchor_holes(){
    for(z=[-10,16]){
        pm_xcyl(6.9,14.1,40,z,3.5);
        pm_xcyl(10.8,14.1,40,z,6.2);
    }
}
module sf_front_cheek_holes(){
    pm_ycyl(57.9,61.1,sf_pivot_x,25,6.4);
    sf_box(sf_pivot_x-.6,sf_pivot_x+.6,57.9,61.1,28,42.1);
    pm_xcyl(1,24.1,59.5,36.5,2.25);
    cf_nut_trap(59.5);
}
module sf_rear_cheek_holes(){
    pm_ycyl(68.9,73.1,sf_pivot_x,25,6.4);
    sf_box(sf_pivot_x-.6,sf_pivot_x+.6,68.9,73.1,28,42.1);
    pm_xcyl(1,24.1,71,36.5,2.25);
    cf_nut_trap(71);
}
module sf_foot_bolt_holes(y0,y1){
    for(z=sf_bolt_z)pm_ycyl(y0,y1,sf_bolt_x,z,3.4);
}
module sf_nut_pockets(){
    // M3 AF5.5 candidate with 0.3 mm nominal across-flats allowance.
    for(z=sf_bolt_z)
        translate([sf_bolt_x,65.2,z])rotate([-90,0,0])
            cylinder(h=2.9,d=5.8/cos(30),$fn=6);
}
module sf_nuts(){
    for(z=sf_bolt_z)
        translate([sf_bolt_x,65.4,z])rotate([-90,0,0])
            cylinder(h=2.4,d=5.5/cos(30),$fn=6);
}
module sf_base(){difference(){
    union(){
        pm_anchor_web();
        sf_box(7,10,40,68,-18,-7);
        sf_box(7,10,58,61,-14,17);
        pm_cheek(58,61);
        cf_pad_pair(58,61);
        sf_box(7,23,61,sf_base_mating_y,-21,8);
        sf_box(sf_tongue_x[0],sf_tongue_x[1],sf_base_mating_y,
               sf_tongue_end_y,sf_tongue_z[0],sf_tongue_z[1]);
    }
    sf_anchor_holes();
    sf_front_cheek_holes();
    sf_foot_bolt_holes(60.9,sf_base_mating_y+.1);
    sf_nut_pockets();
}}
module sf_rear(){difference(){
    union(){
        sf_box(7,23,sf_base_mating_y,sf_rear_foot_end_y,-21,8);
        sf_box(7,13,69,73,8,17);
        pm_cheek(69,73);
        cf_pad_pair(69,73);
    }
    sf_rear_cheek_holes();
    sf_foot_bolt_holes(sf_base_mating_y-.1,sf_rear_foot_end_y+.1);
    // Pocket opens at the Y=68 mating face; the key enters along -Y.
    sf_box(sf_tongue_x[0]-sf_key_clearance,
           sf_tongue_x[1]+sf_key_clearance,
           sf_base_mating_y-.1,
           sf_tongue_end_y+sf_key_clearance,
           sf_tongue_z[0]-sf_key_clearance,
           sf_tongue_z[1]+sf_key_clearance);
}}
module sf_m3_hardware(){
    for(z=sf_bolt_z){
        pm_ycyl(64,76,sf_bolt_x,z,3);
        pm_ycyl(76,79,sf_bolt_x,z,6); // head/washer envelope
    }
    sf_nuts();
}
module sf_m3_tools(){
    for(z=sf_bolt_z)pm_ycyl(79,110,sf_bolt_x,z,5);
}
module sf_nuts_shifted(){translate([0,sf_nut_offset_y,0])sf_nuts();}
module sf_rocker(){translate([0,sf_rocker_offset_y,0])pj_rocker();}
module sf_rear_shifted(){translate([0,sf_rear_offset_y,0])sf_rear();}
module sf_shaft_shifted(){translate([0,sf_shaft_offset_y,0])cf_shaft();}
module sf_fixed(){ss_other_fixed();ss_cap();}
module sf_other_hardware(){hs_selected_hardware(sf_t);ss_switch_fasteners();}
module sf_probe_geometry(){
    if(sf_probe=="base-fixed")intersection(){sf_base();sf_fixed();}
    else if(sf_probe=="base-carriage")intersection(){sf_base();oc_carriage();}
    else if(sf_probe=="base-hardware")intersection(){sf_base();sf_other_hardware();}
    else if(sf_probe=="base-motor")intersection(){sf_base();ss_motor_envelope();}
    else if(sf_probe=="base-bushing")intersection(){sf_base();pj_bushing();}
    else if(sf_probe=="rear-fixed")intersection(){sf_rear();sf_fixed();}
    else if(sf_probe=="rear-carriage")intersection(){sf_rear();oc_carriage();}
    else if(sf_probe=="rear-hardware")intersection(){sf_rear();sf_other_hardware();}
    else if(sf_probe=="rear-motor")intersection(){sf_rear();ss_motor_envelope();}
    else if(sf_probe=="rear-bushing")intersection(){sf_rear();pj_bushing();}
    else if(sf_probe=="base-rear")intersection(){sf_base();sf_rear();}
    else if(sf_probe=="anchor-original-minus-base")intersection(){
        difference(){cf_bracket();sf_base();}
        sf_box(0,25,34,46,-21,42);
    }
    else if(sf_probe=="anchor-base-minus-original")intersection(){
        difference(){sf_base();cf_bracket();}
        sf_box(0,25,34,46,-21,42);
    }
    else if(sf_probe=="base-rocker-insertion")intersection(){sf_base();sf_rocker();}
    else if(sf_probe=="rocker-crosshead-insertion")intersection(){sf_rocker();oc_carriage();}
    else if(sf_probe=="rear-rocker-insertion")intersection(){sf_rear_shifted();pj_rocker();}
    else if(sf_probe=="rear-base-insertion")intersection(){sf_rear_shifted();sf_base();}
    else if(sf_probe=="rear-carriage-insertion")intersection(){sf_rear_shifted();oc_carriage();}
    else if(sf_probe=="rear-fixed-insertion")intersection(){sf_rear_shifted();sf_fixed();}
    else if(sf_probe=="shaft-assembly-insertion")intersection(){
        sf_shaft_shifted();
        union(){sf_base();sf_rear();pj_rocker();pj_bushing();oc_carriage();sf_fixed();}
    }
    else if(sf_probe=="m3-hardware-fixed")intersection(){sf_m3_hardware();sf_fixed();}
    else if(sf_probe=="m3-hardware-moving")intersection(){sf_m3_hardware();oc_carriage();}
    else if(sf_probe=="m3-hardware-rocker")intersection(){sf_m3_hardware();pj_rocker();}
    else if(sf_probe=="m3-hardware-base")intersection(){sf_m3_hardware();sf_base();}
    else if(sf_probe=="m3-hardware-rear")intersection(){sf_m3_hardware();sf_rear();}
    else if(sf_probe=="m3-tools-fixed")intersection(){sf_m3_tools();sf_fixed();}
    else if(sf_probe=="m3-tools-moving")intersection(){sf_m3_tools();oc_carriage();}
    else if(sf_probe=="m3-tools-motor")intersection(){sf_m3_tools();ss_motor_envelope();}
    else if(sf_probe=="nut-base-insertion")intersection(){sf_nuts_shifted();sf_base();}
    else if(sf_probe=="nut-fixed-insertion")intersection(){sf_nuts_shifted();sf_fixed();}
    else if(sf_probe=="nut-carriage-insertion")intersection(){sf_nuts_shifted();oc_carriage();}
    else if(sf_probe=="nut-rocker-insertion")intersection(){sf_nuts_shifted();pj_rocker();}
    else if(sf_probe=="key-contact-control")intersection(){
        sf_base();sf_box(9.9,20.1,67.9,72.1,-8.1,-3.9);
    }
    else if(sf_probe=="base-self-control")intersection(){sf_base();sf_base();}
    else assert(false,"Unknown service fork probe");
}

if(sf_part=="probe")sf_probe_geometry();
else if(sf_part=="base")sf_base();
else if(sf_part=="rear")sf_rear();
else if(sf_part=="context"){
    color([.70,.74,.78,.18])sf_fixed();
    color([.94,.53,.16,.55])oc_carriage();
    color([.12,.53,.83])sf_base();
    color([.19,.70,.88])sf_rear_shifted();
    color([.19,.70,.39])sf_rocker();
    if(sf_rear_offset_y==0)color([.65,.67,.70])sf_m3_hardware();
    color([.95,.18,.15,.10])ss_motor_envelope();
}
else assert(false,"Unknown service fork part");
