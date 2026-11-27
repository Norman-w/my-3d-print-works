// Concrete external support candidate. Physical acceptance remains OPEN.
// Set feeder_support_library_mode=true before include for integration.
cam_library_mode = true;
include <cam-study.scad>

support_part = "assembly";
support_fraction = 0;
support_show_hardware = true;
support_show_body_reference = true;
support_show_tools = false;
support_exploded = false;
support_probe_fraction = 0; // for traversal probes
support_probe_kind = "motion"; // motion, remove_pins, lift_frame, extract_fingers

// Independent support parameters: all dimensions mm, not measured tolerances.
support_mount_x = 35.5;
support_mount_thickness = 8;
support_mount_y = -14;
support_mount_z = [-45,16];
support_radial_x0 = support_mount_x;
support_radial_x1 = 58;
support_radial_y0 = -10;
support_radial_y1 = 7.25;
support_radial_half_z = 7.5;
support_radial_clearance = 0.2;
support_axial_clearance = 0.2;
support_rail_x0 = 54;
support_rail_x1 = 58;
support_rail_y0 = 20;
support_rail_y1 = 24;
support_guide_x0 = 51.5;
support_guide_x1 = 67;
support_guide_y0 = 17.5;
support_guide_y_split = support_rail_y1+support_axial_clearance;
support_guide_y1 = 28;
support_guide_z0 = -35;
support_guide_z1 = 5;
support_cap_screw_x = 62.75;
support_cap_screw_z = [-29,-1];
support_stop_thickness = 4;
support_stop_x0 = support_rail_x0-1;
support_stop_x1 = support_rail_x1+1;
support_stop_y0 = support_rail_y0-1;
support_stop_y1 = support_rail_y1+1;
support_trigger_x = 76;
support_trigger_z = 24;
support_trigger_id = 18;
support_trigger_od = 26;
support_trigger_y0 = -4;
support_trigger_y1 = 2;
support_spring_x = -72;
support_spring_fixed_slot_z = [-37,-14];
support_spring_moving_z = cam_rail_z1-cam_bridge_width/2;
support_eps = 0.02;

assert(support_radial_x0>cam_body_r);
assert(support_radial_y1<cam_plate_y);
assert(support_guide_y0>cam_pin_shoulder_end_y+cam_pin_head_thickness);
assert(support_guide_x0>cam_rail_outer_r,
    "Axial guide blocks cam plate removal in +Y");
assert(support_guide_x0>finger_open_center_r+cam_follower_offset+cam_pin_head_d/2,
    "Axial guide obstructs follower screwdriver path");
assert(support_guide_z0>cam_rail_z0+cam_bridge_width+cam_stroke);
assert(support_guide_z1<cam_rail_z1-cam_bridge_width);

module support_y_hole(x,z,y0,length,d) {
    translate([x,y0,z]) rotate([-90,0,0]) cylinder(h=length,d=d,$fn=32);
}
module support_x_hole(y,z,x0,length,d) {
    translate([x0,y,z]) rotate([0,90,0]) cylinder(h=length,d=d,$fn=32);
}
module support_y_hex(x,z,y0,length,af) {
    translate([x,y0,z]) rotate([-90,0,0])
        rotate([0,0,30]) cylinder(h=length,d=af/cos(30),$fn=6);
}
module support_y_slot(x,z0,z1,y0,length,d) {
    hull() for(z=[z0,z1]) support_y_hole(x,z,y0,length,d);
}

// Right-hand fixed chair. Left chair is a whole-part mirror, not separately
// mirrored holes/ribs. Carrier channels are open through +/-X for assembly.
module feeder_side_support_local() {
    difference() {
        union() {
            for(z=[0,-gate_spacing])
                translate([support_radial_x0,support_radial_y0,
                    z-support_radial_half_z])
                    cube([support_radial_x1-support_radial_x0,
                        support_radial_y1-support_radial_y0,
                        2*support_radial_half_z]);
            translate([support_mount_x,support_mount_y-5,support_mount_z[0]-5])
                cube([support_mount_thickness,10,
                    support_mount_z[1]-support_mount_z[0]+10]);
            // Back plate connects the radial housings to the outboard rail.
            translate([support_radial_x0,support_radial_y0,
                -gate_spacing-support_radial_half_z])
                cube([support_guide_x1-support_radial_x0,
                    support_radial_y0*-1-cam_carrier_width/2-support_radial_clearance,
                    gate_spacing+2*support_radial_half_z]);
            // Mount spine overlaps the back plate by a full millimetre.
            translate([support_mount_x,support_mount_y,
                -gate_spacing-support_radial_half_z])
                cube([support_mount_thickness,5,
                    gate_spacing+2*support_radial_half_z]);
            translate([support_guide_x1-4,support_radial_y0,
                -gate_spacing-support_radial_half_z])
                cube([4,support_guide_y_split-support_radial_y0,
                    gate_spacing+2*support_radial_half_z]);
            translate([support_guide_x0,support_guide_y0,support_guide_z0])
                cube([support_guide_x1-support_guide_x0,
                    support_guide_y_split-support_guide_y0,
                    support_guide_z1-support_guide_z0]);
        }
        for(z=[0,-gate_spacing]) {
            translate([support_radial_x0-support_eps,
                -cam_carrier_width/2-support_radial_clearance,
                z-cam_carrier_axial/2-support_radial_clearance])
                cube([support_guide_x1-support_radial_x0+2*support_eps,
                    cam_carrier_width+2*support_radial_clearance,
                    cam_carrier_axial+2*support_radial_clearance]);
            // Open-ended front window allows pin insertion and later carrier
            // extraction using the loosely fitted screw as a pull handle.
            translate([finger_closed_center_r+cam_follower_offset-cam_slot_d/2,
                cam_carrier_width/2,z-cam_slot_d/2])
                cube([support_radial_x1-(finger_closed_center_r+cam_follower_offset)
                    +cam_slot_d/2+support_eps,20,cam_slot_d]);
            translate([finger_closed_center_r+cam_follower_offset-fastener_d/2,
                support_radial_y0-support_eps,z-fastener_d/2])
                cube([finger_open_center_r-finger_closed_center_r+fastener_d,
                    8,fastener_d]);
        }
        // Open +Y channel; a separate bolted keeper closes it after drop-in.
        translate([support_rail_x0-support_axial_clearance,
            support_rail_y0-support_axial_clearance,support_guide_z0-support_eps])
            cube([support_rail_x1-support_rail_x0+2*support_axial_clearance,
                20,support_guide_z1-support_guide_z0+2*support_eps]);
        for(z=support_mount_z)
            support_x_hole(support_mount_y,z,support_mount_x-support_eps,
                support_mount_thickness+2*support_eps,fastener_d);
        for(z=support_cap_screw_z) {
            support_y_hole(support_cap_screw_x,z,16,15,fastener_d);
            support_y_hex(support_cap_screw_x,z,18,nut_depth,nut_af);
            // Nut enters axially from -Z; two hex flanks retain its rotation.
            translate([support_cap_screw_x-nut_af/2,18,support_guide_z0-support_eps])
                cube([nut_af,nut_depth,
                    z-support_guide_z0+support_eps]);
        }
    }
}

module feeder_guide_cap_local() {
    difference() {
        translate([support_guide_x0,support_guide_y_split,support_guide_z0])
            cube([support_guide_x1-support_guide_x0,
                support_guide_y1-support_guide_y_split,
                support_guide_z1-support_guide_z0]);
        for(z=support_cap_screw_z)
            support_y_hole(support_cap_screw_x,z,
                support_guide_y_split-support_eps,10,fastener_d);
    }
}

module feeder_spring_fixed_interface() {
    difference() {
        union() {
            translate([-76,11.4,-42]) cube([13,6.6,33]);
            translate([-67,11.4,-23]) cube([4,12.8,14]);
        }
        support_y_slot(support_spring_x,support_spring_fixed_slot_z[0],
            support_spring_fixed_slot_z[1],11,9,fastener_d);
        // Captive sliding M3 nut; hook/stud stack and spring remain unselected.
        translate([support_spring_x-nut_af/2,11.4-support_eps,-40])
            cube([nut_af,2.6+support_eps,29]);
    }
}

module feeder_support_fixed(include_caps=true) {
    for(side=[-1,1]) scale([side,1,1]) {
        feeder_side_support_local();
        if(include_caps) feeder_guide_cap_local();
    }
    feeder_spring_fixed_interface();
}

module feeder_carriage_features_local() {
    for(side=[-1,1]) scale([side,1,1]) {
        translate([support_rail_x0,support_rail_y0,cam_rail_z0])
            cube([support_rail_x1-support_rail_x0,
                support_rail_y1-support_rail_y0,cam_rail_z1-cam_rail_z0]);
        for(z=[cam_rail_z0,cam_rail_z1-cam_bridge_width])
            translate([cam_rail_outer_r-3,support_rail_y0,z])
                cube([support_rail_x1-(cam_rail_outer_r-3),
                    support_rail_y1-support_rail_y0,cam_bridge_width]);
        // Positive shoulders locate both stroke endpoints on the fixed seat.
        for(z=[support_guide_z0-cam_stroke-support_stop_thickness,
            support_guide_z1])
            translate([support_stop_x0,support_stop_y0,z])
                cube([support_stop_x1-support_stop_x0,
                    support_stop_y1-support_stop_y0,support_stop_thickness]);
    }
    // Direct 20 mm mechanical trigger: closed finger loop integral to carriage.
    translate([support_rail_x1,support_rail_y0,cam_rail_z1-cam_bridge_width])
        cube([support_trigger_x+3-support_rail_x1,4,cam_bridge_width]);
    translate([support_trigger_x-3,support_trigger_y0,
        cam_rail_z1-cam_bridge_width])
        cube([6,support_rail_y1-support_trigger_y0,cam_bridge_width]);
    translate([support_trigger_x,support_trigger_y0,support_trigger_z])
        rotate([-90,0,0]) difference() {
            cylinder(h=support_trigger_y1-support_trigger_y0,
                d=support_trigger_od,$fn=72);
            translate([0,0,-support_eps])
                cylinder(h=support_trigger_y1-support_trigger_y0+2*support_eps,
                    d=support_trigger_id,$fn=72);
        }
    difference() {
        translate([-76,support_rail_y0,cam_rail_z1-cam_bridge_width])
            cube([24,4,cam_bridge_width]);
        support_y_hole(support_spring_x,support_spring_moving_z,19,6,fastener_d);
    }
}

module feeder_carriage(t=support_fraction,lift=0) {
    translate([0,lift,cam_stroke*t]) union() {
        cam_carriage_local();
        feeder_carriage_features_local();
    }
}

module feeder_support_moving(t=support_fraction,lift=0,extract=0) {
    feeder_carriage(t,lift);
    for(side=[-1,1],rear=[false,true]) {
        cam_finger(side,rear,t);
        cam_pin(side,rear,t,extract);
        cam_follower_nut(side,rear,t);
    }
}

module feeder_cap_hardware() {
    for(side=[-1,1],z=support_cap_screw_z) scale([side,1,1]) {
        // M3x12 screw + 0.5 washer; start at 16.5, head underside 28.5.
        support_y_hole(support_cap_screw_x,z,16.5,12,3);
        support_y_hole(support_cap_screw_x,z,28,0.5,7);
        support_y_hole(support_cap_screw_x,z,28.5,3,5.5);
        difference() {
            support_y_hex(support_cap_screw_x,z,18.1,2.4,5.5);
            support_y_hole(support_cap_screw_x,z,18,3,3);
        }
    }
}

module feeder_mount_hardware() {
    for(side=[-1,1],z=support_mount_z) scale([side,1,1]) {
        support_x_hole(support_mount_y,z,32,12,3);
        support_x_hole(support_mount_y,z,43.5,0.5,7);
        support_x_hole(support_mount_y,z,44,3,5.5);
    }
}

module feeder_follower_tools(t=support_fraction) {
    for(side=[-1,1],rear=[false,true])
        support_y_hole(side*(cam_gate_r(rear,t)+cam_follower_offset),
            cam_gate_z(rear),cam_pin_shoulder_end_y+cam_pin_head_thickness,
            65,4); // 2mm hex bit plus access envelope, not a purchased tool
}

module feeder_support_reference_body() {
    color([0.6,0.65,0.68,0.15]) cam_body_proxy();
    color([0.3,0.7,0.78,0.12]) cam_liner_proxy();
}

module feeder_assembly() {
    if(support_show_body_reference) feeder_support_reference_body();
    color([0.72,0.73,0.76]) feeder_support_fixed(!support_exploded);
    if(support_exploded) for(side=[-1,1])
        color([0.7,0.7,0.74]) translate([0,35,0]) scale([side,1,1])
            feeder_guide_cap_local();
    color([0.10,0.46,0.80]) feeder_carriage(support_fraction,
        support_exploded?18:0);
    for(side=[-1,1],rear=[false,true]) {
        color(rear?[0.15,0.65,0.42]:[0.95,0.4,0.1])
            cam_finger(side,rear,support_fraction);
        if(support_show_hardware) color([0.28,0.3,0.34]) {
            cam_pin(side,rear,support_fraction,support_exploded?22:0);
            cam_follower_nut(side,rear,support_fraction);
        }
    }
    if(support_show_hardware && !support_exploded) color([0.28,0.3,0.34]) {
        feeder_cap_hardware();
        feeder_mount_hardware();
    }
    if(support_show_tools) color([0.95,0.8,0.1,0.35])
        feeder_follower_tools();
}

// Actual geometry probes, with positive-control cases provided by Python.
module feeder_motion_intersection(t=support_fraction) {
    union() {
        intersection() {
            feeder_support_fixed();
            feeder_support_moving(t);
        }
        intersection() {
            feeder_carriage(t);
            union() for(side=[-1,1],rear=[false,true]) {
                cam_finger(side,rear,t);
                cam_pin(side,rear,t,0);
                cam_follower_nut(side,rear,t);
            }
        }
    }
}

module feeder_traversal_probe() {
    if(support_probe_kind=="motion") feeder_motion_intersection();
    else if(support_probe_kind=="remove_pins") intersection() {
        union() {
            feeder_support_fixed();
            feeder_carriage(support_fraction);
            for(side=[-1,1],rear=[false,true]) cam_finger(side,rear,support_fraction);
        }
        union() for(side=[-1,1],rear=[false,true])
            cam_pin(side,rear,support_fraction,22*support_probe_fraction);
    }
    else if(support_probe_kind=="lift_frame") intersection() {
        union() {
            feeder_support_fixed(false);
            for(side=[-1,1],rear=[false,true]) cam_finger(side,rear,support_fraction);
        }
        feeder_carriage(support_fraction,60*support_probe_fraction);
    }
    else if(support_probe_kind=="extract_fingers") intersection() {
        feeder_support_fixed(false);
        union() for(side=[-1,1],rear=[false,true])
            translate([side*35*support_probe_fraction,0,0])
                cam_finger(side,rear,support_fraction);
    }
    else assert(false,"Unknown support_probe_kind");
}

if(is_undef(feeder_support_library_mode) || !feeder_support_library_mode) {
    if(support_part=="assembly") feeder_assembly();
    else if(support_part=="right_support") feeder_side_support_local();
    else if(support_part=="left_support") union() {
        mirror([1,0,0]) feeder_side_support_local();
        feeder_spring_fixed_interface();
    }
    else if(support_part=="cap") feeder_guide_cap_local();
    else if(support_part=="carriage") feeder_carriage(0);
    else if(support_part=="finger") cam_finger_local();
    else if(support_part=="spring_interface") feeder_spring_fixed_interface();
    else if(support_part=="probe") feeder_traversal_probe();
    else if(support_part=="tool_probe") intersection() {
        union() {feeder_support_fixed();feeder_carriage(support_fraction);}
        feeder_follower_tools();
    }
    else assert(false,"Unknown support_part");
}
