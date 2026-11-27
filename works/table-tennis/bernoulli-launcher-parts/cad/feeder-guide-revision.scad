// Adjustable -Y gib candidate; physical setting and load acceptance OPEN.
// Wraps feeder_side_support_local(), not a copy of the original support.
// Initial reviewed base SHA256 is recorded in docs/feeder-guide-revision.md.
feeder_support_library_mode=true;
include <feeder-supports.scad>
use <feeder-body.scad>

revision_part="assembly"; // assembly,right_support,left_support,gib,keeper,probe,tools
revision_t=0.5;
revision_setting=0.90; // mm advance, [0,1]; not an as-printed tolerance
revision_probe="motion"; // motion,gib_remove,keeper_remove,tools,overtravel
revision_removal=0;
revision_show_body=true;
revision_show_hardware=true;
revision_exploded=false;
revision_x0=43.8;
revision_x1=57.8;
revision_pocket_clearance=0.2;
revision_contact_z0=2.1;
revision_contact_z1=4.1;
revision_front_retracted=-5.50;
// Integral datum lands restore the carrier centre to Y=0. The 0.2 mm
// proud face is backed by 0.8 mm overlap INTO the original front wall.
revision_datum_y=4.50;
revision_datum_embed=0.80;
revision_datum_z0=2.50;
revision_datum_z1=4.10;
revision_datum_lead=0.50;
revision_contact_depth=2.55;
revision_web_depth=3;
revision_travel=1;
revision_ear_x0=46;
revision_ear_x1=55;
revision_ear_z1=6.5;
revision_ear_depth=1;
revision_jack_x=51;
revision_keeper_bolt_z=10;
revision_keeper_boss_r=4.5;
revision_keeper_front_y=-13.5;
revision_keeper_back_y=-17.5;
revision_boss_front_y=-6;
revision_bias_y=0;
revision_eps=0.02;
// Carry the rear pocket past the radial housing end. An exactly coplanar
// computed end at X=58 left a sub-ULP sliver that collapsed in STL export.
// This is a cutter overrun, not a change to a working guide datum or rod hole.
revision_pocket_outer_x=support_radial_x1+revision_eps;

function revision_front(s)=revision_front_retracted+s;
function revision_rear(s)=revision_front(s)-revision_contact_depth-revision_web_depth;
function revision_ear_front(s)=revision_rear(s)+revision_ear_depth;
assert(revision_x0-revision_pocket_clearance>support_mount_x+support_mount_thickness,
    "Do not interrupt the original load-carrying mounting spine");
assert(revision_contact_z0>fastener_d/2,
    "Gib contact strips obstruct the follower thread tail");
assert(revision_datum_z0>cam_slot_d/2,
    "Datum lands obstruct the existing open-ended pin window");
assert(revision_datum_z1<=cam_carrier_axial/2+support_radial_clearance,
    "Datum land bounds must remain inside the original carrier channel");

module revision_datum_bands_local() {
    old_face=cam_carrier_width/2+support_radial_clearance;
    for(g=[0,-gate_spacing],sign=[-1,1])
        translate([0,0,g+(sign>0?revision_datum_z0:-revision_datum_z1)])
            linear_extrude(height=revision_datum_z1-revision_datum_z0)
                polygon([[revision_x0,old_face],
                    [revision_x0+revision_datum_lead,revision_datum_y],
                    [revision_x1-revision_datum_lead,revision_datum_y],
                    [revision_x1,old_face],
                    [revision_x1,old_face+revision_datum_embed],
                    [revision_x0,old_face+revision_datum_embed]]);
}

module revision_keeper_boss(z) {
    support_y_hole(revision_jack_x,z,revision_keeper_front_y,
        revision_boss_front_y-revision_keeper_front_y,2*revision_keeper_boss_r);
}

module revision_side_support_local() {
    difference() {
        union() {
            feeder_side_support_local();
            revision_datum_bands_local();
            for(g=[0,-gate_spacing],dz=[-revision_keeper_bolt_z,revision_keeper_bolt_z])
                revision_keeper_boss(g+dz);
        }
        for(g=[0,-gate_spacing]) {
            // Only the outboard part of the rear bearing face is replaced.
            translate([revision_x0-revision_pocket_clearance,-14,
                g-revision_contact_z1-revision_pocket_clearance])
                cube([revision_pocket_outer_x-(revision_x0-revision_pocket_clearance),
                    14-cam_carrier_width/2-support_radial_clearance+revision_eps,
                    2*(revision_contact_z1+revision_pocket_clearance)]);
            // Closed +Y ends of these ear pockets form the advance hard stop.
            for(sign=[-1,1])
                translate([revision_ear_x0-revision_pocket_clearance,-14,
                    g+(sign>0?revision_contact_z1:
                    -revision_ear_z1-revision_pocket_clearance)])
                    cube([revision_ear_x1-revision_ear_x0+2*revision_pocket_clearance,
                        14+revision_ear_front(revision_travel),
                        revision_ear_z1-revision_contact_z1+revision_pocket_clearance]);
            // A pull lip is exposed on the outboard edge after backing off.
            translate([revision_x1-revision_eps,-14,g-2.2])
                cube([62.7-revision_x1+revision_eps,14+revision_ear_front(revision_travel),4.4]);
            for(dz=[-revision_keeper_bolt_z,revision_keeper_bolt_z]) {
                support_y_hole(revision_jack_x,g+dz,revision_keeper_front_y-revision_eps,
                    9,fastener_d);
                support_y_hex(revision_jack_x,g+dz,
                    revision_boss_front_y-nut_depth,nut_depth+revision_eps,nut_af);
            }
        }
    }
}

module revision_gib_local(s=revision_setting) {
    f=revision_front(s);r=revision_rear(s);
    union() {
        translate([revision_x0,r,-revision_contact_z1])
            cube([revision_x1-revision_x0,revision_web_depth,2*revision_contact_z1]);
        for(sign=[-1,1]) {
            translate([revision_x0,f-revision_contact_depth,
                sign>0?revision_contact_z0:-revision_contact_z1])
                cube([revision_x1-revision_x0,revision_contact_depth,
                    revision_contact_z1-revision_contact_z0]);
            translate([revision_ear_x0,r,
                sign>0?revision_contact_z1:-revision_ear_z1])
                cube([revision_ear_x1-revision_ear_x0,revision_ear_depth,
                    revision_ear_z1-revision_contact_z1]);
        }
        translate([revision_x1-revision_eps,r,-2])
            cube([62.5-revision_x1+revision_eps,revision_ear_depth,4]);
    }
}

module revision_keeper_local() {
    difference() {
        union() {
            translate([43.8,revision_keeper_back_y,-14])
                cube([16.2,revision_keeper_front_y-revision_keeper_back_y,28]);
            // Rear stroke stops retract with the removable keeper.
            for(sign=[-1,1])
                translate([revision_ear_x0,revision_keeper_front_y,
                    sign>0?revision_contact_z1:-revision_ear_z1])
                    cube([revision_ear_x1-revision_ear_x0,
                        revision_rear(0)-revision_keeper_front_y,
                        revision_ear_z1-revision_contact_z1]);
        }
        for(z=[-revision_keeper_bolt_z,0,revision_keeper_bolt_z])
            support_y_hole(revision_jack_x,z,revision_keeper_back_y-revision_eps,8,fastener_d);
        support_y_hex(revision_jack_x,0,revision_keeper_front_y-nut_depth,
            nut_depth+revision_eps,nut_af);
    }
}

module revision_m3_nut(x,z,y) {
    difference(){support_y_hex(x,z,y,2.4,5.5);
        support_y_hole(x,z,y-revision_eps,2.4+2*revision_eps,3);}
}
module revision_hardware_local(g=0,s=revision_setting) {
    // Jack M3x16: flat end bears on replaceable printed gib web.
    under=revision_rear(s)-16;
    support_y_hole(revision_jack_x,g,under,16,3);
    support_y_hole(revision_jack_x,g,under-3,3,5.5);
    revision_m3_nut(revision_jack_x,g,revision_keeper_front_y-nut_depth);
    revision_m3_nut(revision_jack_x,g,revision_keeper_back_y-0.5-2.4);
    support_y_hole(revision_jack_x,g,revision_keeper_back_y-0.5,0.5,7);
    for(dz=[-revision_keeper_bolt_z,revision_keeper_bolt_z]) {
        // Keeper M3x12 + .5 washer; nut is seated in fixed boss.
        support_y_hole(revision_jack_x,g+dz,revision_keeper_back_y-.5,12,3);
        support_y_hole(revision_jack_x,g+dz,revision_keeper_back_y-3.5,3,5.5);
        support_y_hole(revision_jack_x,g+dz,revision_keeper_back_y-.5,.5,7);
        revision_m3_nut(revision_jack_x,g+dz,revision_boss_front_y-nut_depth);
    }
}

module revision_fixed(include_keepers=true,include_caps=true) {
    for(side=[-1,1])scale([side,1,1]) {
        revision_side_support_local();
        if(include_caps)feeder_guide_cap_local();
        if(include_keepers)for(g=[0,-gate_spacing])translate([0,0,g])revision_keeper_local();
    }
    feeder_spring_fixed_interface();
}
module revision_gibs(s=revision_setting,remove=0) {
    for(side=[-1,1],g=[0,-gate_spacing])
        scale([side,1,1])translate([0,-remove,g])revision_gib_local(s);
}
module revision_followers(t=revision_t) {
    translate([0,revision_bias_y,0])for(side=[-1,1],rear=[false,true]) {
        cam_finger(side,rear,t);cam_pin(side,rear,t,0);cam_follower_nut(side,rear,t);
    }
}
module revision_tools() {
    for(side=[-1,1],g=[0,-gate_spacing])scale([side,1,1]) {
        for(z=[g-revision_keeper_bolt_z,g,g+revision_keeper_bolt_z])
            support_y_hole(revision_jack_x,z,-60,
                (z==g?revision_rear(revision_setting)-19:revision_keeper_back_y-3.5)+60,4);
        // Small open-end wrench swing envelope for the external M3 locknut.
        support_y_hole(revision_jack_x,g,revision_keeper_back_y-3.1,2.8,9);
        // Outward handle corridor; an actual wrench still needs trial fitting.
        translate([revision_jack_x,revision_keeper_back_y-3.1,g-3])
            cube([45,2.8,6]);
    }
}
module revision_assembly() {
    if(revision_show_body)color([.6,.65,.68,.18])feeder_body_full();
    color([.72,.72,.76])revision_fixed(!revision_exploded);
    if(revision_exploded)for(side=[-1,1],g=[0,-gate_spacing])
        color([.7,.7,.75])scale([side,1,1])translate([0,-26,g])revision_keeper_local();
    color([1,.65,.15])revision_gibs(revision_setting,revision_exploded?12:0);
    color([.1,.45,.8])feeder_carriage(revision_t);
    color([.15,.65,.35])revision_followers();
    if(revision_show_hardware&&!revision_exploded)color([.3,.3,.32]) {
        for(side=[-1,1],g=[0,-gate_spacing])scale([side,1,1])revision_hardware_local(g);
        feeder_cap_hardware();feeder_mount_hardware();
    }
}

module revision_probe_geometry() {
    if(revision_probe=="motion")union() {
        intersection(){union(){revision_fixed();revision_gibs();feeder_body_full();}
            union(){feeder_carriage(revision_t);revision_followers();}}
        intersection(){feeder_carriage(revision_t);revision_followers();}
    }
    else if(revision_probe=="gib_remove")intersection(){
        union(){revision_fixed(false);feeder_body_full();revision_followers();}
        revision_gibs(0,revision_removal*25);}
    else if(revision_probe=="keeper_remove")intersection(){
        union(){revision_fixed(false);revision_gibs();feeder_body_full();}
        union()for(side=[-1,1],g=[0,-gate_spacing])
            scale([side,1,1])translate([0,-revision_removal*25,g])revision_keeper_local();}
    else if(revision_probe=="tools")intersection(){
        union(){revision_fixed();revision_gibs();feeder_body_full();feeder_carriage(revision_t);revision_followers();}
        revision_tools();}
    else if(revision_probe=="gib_fit")intersection(){revision_fixed();revision_gibs();}
    else if(revision_probe=="hardware")intersection(){
        union(){revision_fixed();revision_gibs();feeder_body_full();feeder_carriage(revision_t);revision_followers();}
        union()for(side=[-1,1],g=[0,-gate_spacing])scale([side,1,1])revision_hardware_local(g);}
    else if(revision_probe=="overtravel")intersection(){revision_fixed();revision_gibs(revision_travel+.1);}
    else if(revision_probe=="overtravel_back")intersection(){revision_fixed();revision_gibs(-.1);}
    else if(revision_probe=="datum_embed")intersection(){
        revision_datum_bands_local();feeder_side_support_local();}
    // Convex hull is deliberately only tested against the NEW datum bands:
    // it is a superset of every pure-radial carrier pose, including holes.
    // Using this hull against the whole body would fill the rod/carrier
    // transition and could introduce spurious collisions.
    else if(revision_probe=="datum_sweep")intersection(){
        union()for(side=[-1,1])scale([side,1,1])revision_datum_bands_local();
        union()for(side=[-1,1],rear=[false,true])hull()
            for(t=[0,1],dy=[revision_front(revision_setting)+cam_carrier_width/2,
                revision_datum_y-cam_carrier_width/2])
                translate([0,dy,0])cam_finger(side,rear,t);}
    else if(revision_probe=="datum_intrusion_control")intersection(){
        union()for(side=[-1,1])scale([side,1,1])revision_datum_bands_local();
        translate([0,.1,0])revision_followers();}
    else if(revision_probe=="remove_pins")intersection(){
        union(){revision_fixed();revision_gibs();feeder_body_full();feeder_carriage(revision_t);
            for(side=[-1,1],rear=[false,true])cam_finger(side,rear,revision_t);}
        union()for(side=[-1,1],rear=[false,true])cam_pin(side,rear,revision_t,22*revision_removal);}
    else if(revision_probe=="lift_frame")intersection(){
        union(){revision_fixed(true,false);revision_gibs();feeder_body_full();
            for(side=[-1,1],rear=[false,true])cam_finger(side,rear,revision_t);}
        feeder_carriage(revision_t,60*revision_removal);}
    else if(revision_probe=="extract_fingers")intersection(){
        union(){revision_fixed(true,false);revision_gibs(0);feeder_body_full();}
        union()for(side=[-1,1],rear=[false,true])translate([side*35*revision_removal,0,0])
            cam_finger(side,rear,revision_t);}
    else assert(false,"unknown revision probe");
}

module revision_dimensions() {
    echo("REVISION_DIMENSIONS",[
        ["datum_y",revision_datum_y],
        ["datum_embed",revision_datum_embed],
        ["datum_back_y",cam_carrier_width/2+support_radial_clearance+revision_datum_embed],
        ["datum_z0",revision_datum_z0],["datum_z1",revision_datum_z1],
        ["datum_lead",revision_datum_lead],
        ["datum_x0",revision_x0],["datum_x1",revision_x1],
        ["old_datum_y",cam_carrier_width/2+support_radial_clearance],
        ["front_wall_outer_y",support_radial_y1],
        ["pin_window_half_z",cam_slot_d/2],
        ["retracted_y",revision_front(0)],["advanced_y",revision_front(revision_travel)],
        ["setting",revision_setting],["display_gib_y",revision_front(revision_setting)],
        ["carrier_width",cam_carrier_width],["carrier_half_z",cam_carrier_axial/2],
        ["display_carrier_y",revision_bias_y],
        ["rod_radius",finger_tip_radius],["sidehole_radius",finger_tip_radius+radial_print_clearance],
        ["closed_carrier_x1",finger_closed_center_r+cam_carrier_inner_offset+cam_carrier_length],
        ["open_carrier_x1",finger_open_center_r+cam_carrier_inner_offset+cam_carrier_length]
    ]);
}

if(is_undef(revision_library_mode)||!revision_library_mode) {
    if(revision_part=="assembly")revision_assembly();
    else if(revision_part=="right_support")revision_side_support_local();
    else if(revision_part=="left_support")union(){mirror([1,0,0])revision_side_support_local();feeder_spring_fixed_interface();}
    else if(revision_part=="gib")revision_gib_local(0);
    else if(revision_part=="keeper")revision_keeper_local();
    else if(revision_part=="probe")revision_probe_geometry();
    else if(revision_part=="tools")revision_tools();
    else if(revision_part=="dimensions")revision_dimensions();
    else assert(false,"unknown revision_part");
}
