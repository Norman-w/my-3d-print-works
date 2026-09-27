// 3D constraint / assembly study only. NOT a finished printable mechanism.
// Standalone visualization excludes the concrete guide/retainer candidate in
// feeder-supports.scad. Seals, total error/load and spring choice remain OPEN.
// Ball travel +Z; front gate Z=0; rear gate Z=-gate_spacing.
// Fingers translate +/-X, removable follower pins point +Y, carriage moves +Z.
include <parameters.scad>

stroke_fraction = 0;         // [0:0.01:1]
study_part = "assembly";   // assembly, carriage, finger, pin, overlap
study_view = "assembled";  // assembled, installation, cam_only
show_body_envelope = true;
show_required_guides = true;
show_labels = true;
show_full_motion_envelope = false;

// Study-local additions. Merge into parameters.scad only after review.
cam_follower_offset = 20;
cam_pin_d = 4;
cam_pin_head_d = 7;
cam_pin_start_y = -5.25;
cam_pin_shoulder_start_y = 1.75;
cam_pin_shoulder_end_y = 13.75;
cam_pin_thread_d = 3;
cam_pin_head_thickness = 3;
cam_plate_y = 8;
cam_plate_thickness = 5;
cam_rail_inner_r = 36;
cam_rail_outer_r = 50;
cam_bridge_outer_r = 52;
cam_bridge_y = 48;
cam_bridge_thickness = 6;
cam_bridge_width = 6;
cam_end_margin = 16;
cam_carrier_inner_offset = 13;
cam_carrier_length = 15;
cam_carrier_width = 9;
cam_carrier_axial = 8;
cam_track_segments = 40;
cam_install_lift = 60;
cam_pin_extract = 22;
cam_probe_pin_radial_error = 0; // validation fault injection; keep ZERO in study

cam_eps = 0.02;
cam_slot_d = cam_pin_d + 2*radial_print_clearance;
cam_rail_z0 = -gate_spacing-cam_stroke-cam_end_margin;
cam_rail_z1 = cam_end_margin;
cam_closing_end = (1-gate_overlap_fraction)/2;
cam_opening_start = 1-cam_closing_end;
cam_body_r = body_id/2+body_wall;
cam_moving_outer_r = max(cam_bridge_outer_r,
    finger_open_center_r+cam_carrier_inner_offset+cam_carrier_length);
cam_moving_envelope = [2*cam_moving_outer_r,
    cam_bridge_y+cam_bridge_thickness-cam_pin_start_y,
    cam_rail_z1+cam_stroke-cam_rail_z0];
cam_guide_start_z = guide_start_z;
cam_guide_end_z = cam_guide_start_z+guide_length;
cam_u = cam_stroke*stroke_fraction;
cam_lift = study_view == "installation" ? cam_install_lift : 0;
cam_extract = study_view == "installation" ? cam_pin_extract : 0;

function cam_clamp(v, lo, hi) = min(hi, max(lo, v));
function cam_gate_r(rear,t) = rear
    ? finger_open_center_r-(finger_open_center_r-finger_closed_center_r)
        *cam_clamp(t/cam_closing_end,0,1)
    : finger_closed_center_r+(finger_open_center_r-finger_closed_center_r)
        *cam_clamp((t-cam_opening_start)/cam_closing_end,0,1);
function cam_gate_z(rear) = rear ? -gate_spacing : 0;
function cam_track_point(side,rear,t) =
    [side*(cam_gate_r(rear,t)+cam_follower_offset),
     cam_gate_z(rear)-cam_stroke*t];
function cam_track_global(side,rear,t) =
    [cam_track_point(side,rear,t)[0],cam_gate_z(rear)];

assert(stroke_fraction>=0 && stroke_fraction<=1);
assert(gate_overlap_fraction>0 && gate_overlap_fraction<1);
assert(cam_rail_inner_r>cam_body_r,
    "Cam rails intrude into the body envelope");
assert(cam_bridge_y>cam_body_r,
    "Cross bridges must pass outside the complete body");
assert(cam_plate_y>cam_carrier_width/2,
    "Cam plates collide with radial carriers");
assert(cam_pin_shoulder_end_y>cam_plate_y+cam_plate_thickness,
    "Follower shoulder does not pass through cam plate");
assert(cam_end_margin>cam_bridge_width+cam_pin_head_d/2,
    "Cross bridge blocks axial position of pin-removal path");
assert(gate_spacing>cam_stroke+cam_slot_d,
    "The front and rear closed slots lose their separating web");
assert(finger_closed_center_r+cam_follower_offset-cam_slot_d/2
    >cam_rail_inner_r);
assert(finger_open_center_r+cam_follower_offset+cam_slot_d/2
    <cam_rail_outer_r);

echo("CAM SUBASSEMBLY ONLY: see feeder-supports for guide/retainer candidate; physical validation OPEN");
echo("stroke_mm",cam_u,"rear_tip_r",cam_gate_r(true,stroke_fraction),
    "front_tip_r",cam_gate_r(false,stroke_fraction));
echo("moving members full-stroke envelope XYZ, excluding body/labels/guides",
    cam_moving_envelope);
echo("background body XYZ",[2*cam_body_r,2*cam_body_r,guide_length],
    "background Z range",[cam_guide_start_z,cam_guide_end_z]);

module cam_y_cylinder(p,y0,length,d) {
    translate([p[0],y0,p[1]]) rotate([-90,0,0])
        cylinder(h=length,d=d,$fn=32);
}

// These are genuinely closed, through-thickness 3D slots. Their centre lines
// are the INVERSE of the carriage translation: local Z = fixed gate Z - u.
module cam_slot(side,rear) {
    for(i=[0:cam_track_segments-1]) hull() {
        cam_y_cylinder(cam_track_point(side,rear,i/cam_track_segments),
            cam_plate_y-cam_eps,cam_plate_thickness+2*cam_eps,cam_slot_d);
        cam_y_cylinder(cam_track_point(side,rear,(i+1)/cam_track_segments),
            cam_plate_y-cam_eps,cam_plate_thickness+2*cam_eps,cam_slot_d);
    }
}

module cam_carriage_local() {
    difference() {
        union() {
            for(side=[-1,1]) {
                translate([side==1?cam_rail_inner_r:-cam_rail_outer_r,
                    cam_plate_y,cam_rail_z0])
                    cube([cam_rail_outer_r-cam_rail_inner_r,
                        cam_plate_thickness,cam_rail_z1-cam_rail_z0]);
                for(z=[cam_rail_z0,cam_rail_z1-cam_bridge_width])
                    translate([side==1?cam_rail_outer_r-3:-cam_bridge_outer_r,
                        cam_plate_y,z])
                        cube([cam_bridge_outer_r-cam_rail_outer_r+3,
                            cam_bridge_y+cam_bridge_thickness-cam_plate_y,
                            cam_bridge_width]);
            }
            for(z=[cam_rail_z0,cam_rail_z1-cam_bridge_width])
                translate([-cam_bridge_outer_r,cam_bridge_y,z])
                    cube([2*cam_bridge_outer_r,cam_bridge_thickness,
                        cam_bridge_width]);
        }
        for(side=[-1,1],rear=[false,true]) cam_slot(side,rear);
    }
}

module cam_carriage(t=stroke_fraction,lift=cam_lift) {
    translate([0,lift,cam_stroke*t]) cam_carriage_local();
}

// A separate rigid carrier is necessary for EACH tip. Its outer rectangular
// portion prevents rotation only when a real fixed radial guide is added.
module cam_finger_local() {
    difference() {
        union() {
            sphere(r=finger_tip_radius,$fn=40);
            rotate([0,90,0]) cylinder(h=cam_carrier_inner_offset+1,
                r=finger_tip_radius,$fn=32);
            translate([cam_carrier_inner_offset,-cam_carrier_width/2,
                -cam_carrier_axial/2])
                cube([cam_carrier_length,cam_carrier_width,cam_carrier_axial]);
        }
        // Shoulder seats on this real step, not on the moving cam plate.
        cam_y_cylinder([cam_follower_offset,0],cam_pin_shoulder_start_y,
            cam_carrier_width/2-cam_pin_shoulder_start_y+cam_eps,
            cam_pin_d+2*radial_print_clearance);
        cam_y_cylinder([cam_follower_offset,0],-cam_carrier_width/2-cam_eps,
            cam_carrier_width/2+cam_pin_shoulder_start_y+2*cam_eps,fastener_d);
        translate([cam_follower_offset,-cam_carrier_width/2-cam_eps,0])
            rotate([-90,0,0]) cylinder(h=nut_depth+cam_eps,
                d=nut_af/cos(30),$fn=6);
    }
}

module cam_finger(side,rear,t=stroke_fraction) {
    translate([side*cam_gate_r(rear,t),0,cam_gate_z(rear)])
        scale([side,1,1]) cam_finger_local();
}

// norelem 07534-04X12 envelope: shoulder D4/L12, M3 thread L7,
// head D7/H3. Thread/hex socket are represented by their clearance envelope.
module cam_pin_local() {
    cam_y_cylinder([0,0],cam_pin_start_y,
        cam_pin_shoulder_start_y-cam_pin_start_y,cam_pin_thread_d);
    cam_y_cylinder([0,0],cam_pin_shoulder_start_y,
        cam_pin_shoulder_end_y-cam_pin_shoulder_start_y,cam_pin_d);
    cam_y_cylinder([0,0],cam_pin_shoulder_end_y,
        cam_pin_head_thickness,cam_pin_head_d);
}

module cam_pin(side,rear,t=stroke_fraction,extract=cam_extract) {
    translate([side*(cam_gate_r(rear,t)+cam_follower_offset
        +cam_probe_pin_radial_error),
        extract,cam_gate_z(rear)]) cam_pin_local();
}

module cam_follower_nut(side,rear,t=stroke_fraction) {
    translate([side*(cam_gate_r(rear,t)+cam_follower_offset),
        -cam_carrier_width/2+0.1,cam_gate_z(rear)])
        rotate([-90,0,0]) difference() {
            cylinder(h=2.4,d=5.5/cos(30),$fn=6);
            translate([0,0,-cam_eps]) cylinder(h=2.4+2*cam_eps,d=3,$fn=32);
        }
}

module cam_body_proxy() {
    difference() {
        translate([0,0,cam_guide_start_z])
            cylinder(h=guide_length,r=cam_body_r,$fn=80);
        translate([0,0,cam_guide_start_z-cam_eps])
            cylinder(h=guide_length+2*cam_eps,d=body_id,$fn=80);
        // Required slider openings are oversized proxies, not seals/bearings.
        for(z=[0,-gate_spacing])
            translate([-70,-cam_carrier_width/2-radial_print_clearance,
                z-cam_carrier_axial/2-radial_print_clearance])
                cube([140,cam_carrier_width+2*radial_print_clearance,
                    cam_carrier_axial+2*radial_print_clearance]);
    }
}

module cam_liner_proxy() {
    difference() {
        translate([0,0,cam_guide_start_z])
            cylinder(h=guide_length,d=guide_od,$fn=80);
        translate([0,0,cam_guide_start_z-cam_eps])
            cylinder(h=guide_length+2*cam_eps,d=guide_id,$fn=80);
        for(z=[0,-gate_spacing])
            translate([-guide_od,0,z]) rotate([0,90,0])
                cylinder(h=2*guide_od,
                    r=finger_tip_radius+radial_print_clearance,$fn=32);
    }
}

module cam_required_guides() {
    // Red translucent BLOCKS are reservation volumes, deliberately not
    // modelled as completed bearings. They must not be exported as parts.
    for(side=[-1,1],rear=[false,true])
        translate([side==1?cam_body_r:-cam_body_r-12,-6,
            cam_gate_z(rear)-6]) cube([12,12,12]);
    // Two outboard longitudinal guide envelopes, also unresolved.
    for(side=[-1,1])
        translate([side==1?cam_body_r:-cam_body_r-3,17,cam_guide_start_z])
            cube([3,7,guide_length]);
}

module cam_label(message,at,size=4) {
    translate(at) rotate([90,0,0]) linear_extrude(height=0.2)
        text(message,size=size,halign="center",font="Liberation Sans");
}

module cam_annotations() {
    color([0.65,0.03,0.03]) {
        cam_label("RESEARCH - NOT PRINT READY",[0,-42,44],4);
        cam_label("RED: GUIDES OMITTED IN THIS VIEW",[0,-42,37],3);
        cam_label("SEALS / ERROR BUDGET / SPRING: OPEN",[0,-42,30],3);
        if(study_view=="installation")
            cam_label("REMOVE 4 PINS +Y, THEN LIFT FRAME +Y",[0,-42,23],3);
    }
}

module cam_assembly() {
    if(study_view!="cam_only") {
        if(show_body_envelope) {
            color([0.68,0.72,0.76,0.20]) cam_body_proxy();
            color([0.20,0.72,0.82,0.18]) cam_liner_proxy();
        }
        for(side=[-1,1],rear=[false,true]) {
            color(rear?[0.15,0.65,0.42]:[0.95,0.40,0.10])
                cam_finger(side,rear);
            color([0.35,0.38,0.42]) cam_pin(side,rear);
        }
        if(show_required_guides)
            color([1,0.06,0.05,0.18]) cam_required_guides();
    }
    color([0.12,0.47,0.80]) cam_carriage();
    if(show_full_motion_envelope)
        color([0.8,0.15,0.8,0.09])
            translate([-cam_moving_outer_r,cam_pin_start_y,cam_rail_z0])
                cube(cam_moving_envelope);
    if(show_labels) cam_annotations();
}

if(is_undef(cam_library_mode) || !cam_library_mode) {
if(study_part=="assembly") cam_assembly();
else if(study_part=="carriage") cam_carriage_local();
else if(study_part=="finger") cam_finger_local();
else if(study_part=="pin") cam_pin_local();
else if(study_part=="overlap") {
    // In assembled view, a nonempty solid means a real cam/follower collision.
    // Intentional bearing reservation volumes and labels are excluded.
    intersection() {
        cam_carriage();
        union() for(side=[-1,1],rear=[false,true]) {
            cam_pin(side,rear);
            cam_finger(side,rear);
        }
    }
}
else assert(false,"Unknown study_part");
}
