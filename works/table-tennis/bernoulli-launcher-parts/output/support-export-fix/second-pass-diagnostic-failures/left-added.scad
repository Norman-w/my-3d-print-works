module old(){cg_library_mode=true;
// Independent right-master X guide candidate. Units mm; X1C/.4/PETG.
// Reuses the existing carrier Y gibs, cam carriage and seam-body candidates.
// Not adopted into the root assembly; no physical/tolerance release implied.
revision_library_mode=true;
// Adjustable -Y gib candidate; physical setting and load acceptance OPEN.
// Wraps feeder_side_support_local(), not a copy of the original support.
// Initial reviewed base SHA256 is recorded in docs/feeder-guide-revision.md.
feeder_support_library_mode=true;
// Concrete external support candidate. Physical acceptance remains OPEN.
// Set feeder_support_library_mode=true before include for integration.
cam_library_mode = true;
// 3D constraint / assembly study only. NOT a finished printable mechanism.
// Standalone visualization excludes the concrete guide/retainer candidate in
// feeder-supports.scad. Seals, total error/load and spring choice remain OPEN.
// Ball travel +Z; front gate Z=0; rear gate Z=-gate_spacing.
// Fingers translate +/-X, removable follower pins point +Y, carriage moves +Z.
// 单位：mm。用户提供的接口尺寸与待实测的样机候选参数明确分开。
// 该文件是几何尺寸的唯一来源；修改后必须重新校核并导出。

// 用户提供；未以实物量规复核。
barrel_id = 48;
barrel_od = 50;
hose_id = 50;
hose_od = 55;

// 以下是工程校核包络，不是对用户实际球径的声明。
ball_min_d = 40;
ball_max_d = 41;
guide_id = 42.5;
guide_od = 47;
guide_start_z = -80;
guide_length = 104;
transition_length = 18;
feed_socket_od = 49.4;
feed_socket_length = 28;
y_stub_od = 50;
y_stub_engagement = 25;
barrel_engagement = 25;
interface_radial_clearance = 0.25;

// 待运动校核的双挡指候选几何。
finger_tip_radius = 2.5;
finger_closed_center_r = 21;
finger_open_center_r = 26;
gate_spacing = 28.5;
gate_overlap_fraction = 0.20;
cam_stroke = 20;
guide_clearance_budget = 0.25;
// 容纳槽/销孔名义游隙后的设计包络；并非实测的制造或受力误差。
gate_position_budget = 1.0;

// 外壳、旁通与可拆装接口。
body_id = 64;
body_wall = 3;
body_flange = 9;
split_gasket_thickness = 1;
fastener_d = 3.4;
nut_af = 5.8;
nut_depth = 2.6;
radial_print_clearance = 0.25;
axial_print_clearance = 0.3;

// 摩擦头候选；零接触位置不能被宣传为已验证的无旋球。
spin_guide_id = 42.5;
spin_body_wall = 3;
spin_pad_width = 12;
spin_pad_length = 22;
spin_pad_thickness = 1;
spin_adjustment_travel = 2.5;
spin_contact_length = 30;
spin_angle = 0;

$fn = 72;


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
// The outer connecting column starts below the axial guide. Nut insertion must
// clear that lower lip as well as the guide itself.
support_nut_entry_z = -gate_spacing-support_radial_half_z-support_eps;

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
            translate([support_cap_screw_x-nut_af/2,18,support_nut_entry_z])
                cube([nut_af,nut_depth,
                    z-support_nut_entry_z]);
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
        // The integral spring rib must not refill the axial cap-nut channel.
        // Preserve the lower 6.6 mm-deep load path (Y=11.4..18); clear the
        // same Y=18..20.6 insertion band used by the left fixed guide.
        translate([-support_cap_screw_x-nut_af/2,18,support_nut_entry_z])
            cube([nut_af,nut_depth,max(support_cap_screw_z)-support_nut_entry_z]);
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
                cube([revision_x1-revision_x0+2*revision_pocket_clearance,
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

use <feeder-seam-candidate.scad>

cg_part="assembly"; // assembly,section,right_support,gib,cover,probe,dimensions
cg_t=.5;
cg_setting=.9; // advance [0,1]; parallel display, NOT measured printing error
cg_probe="motion";
cg_remove=0;
cg_fault_x=0;
cg_gib_dz=0; // rigid axial float; ear pocket bounds it to +/- .2 nominally
cg_witness_matrix=[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]];
cg_show_body=true;
cg_show_hardware=true;
cg_eps=.02;

// ONE X master on the right. The left guide's original .2 side gaps remain.
cg_datum_x=support_rail_x0;
cg_datum_embed=.8;
cg_contact_y0=21;
cg_contact_y1=support_rail_y1;
cg_contact_z=[[support_guide_z0,support_cap_screw_z[0]-3.1],
              [support_cap_screw_z[1]+3.1,support_guide_z1]];
cg_travel=1;
cg_front_retracted=support_rail_x1+cg_travel;
cg_tooth_length=9.4;
cg_spine_thickness=3;
cg_pocket_gap=.2;
cg_end_recess=.4; // both moving ends stay behind FIXED guide stop planes
cg_jack_y=(cg_contact_y0+cg_contact_y1)/2;
cg_jack_z=[for(b=cg_contact_z)(b[0]+b[1])/2];
cg_case_x0=support_guide_x1-1;
cg_case_face_x=75;
cg_case_y0=10.5;
cg_case_y1=28;
cg_case_z0=support_guide_z0-4;
cg_case_z1=support_guide_z1+4;
cg_cover_thickness=5.5;
cg_cover_outer_x=cg_case_face_x+cg_cover_thickness;
cg_mount_y=15;
cg_mount_z=[-24,-6];
cg_mount_nut_x=68;
cg_ear_z0=-18;
cg_ear_z1=-12;
cg_ear_y0=cg_contact_y1;
cg_ear_y1=cg_contact_y1+2;
cg_ear_x_length=1;
cg_jack_length=16;
cg_mount_length=16;
cg_mount_tip_clearance=1.5;
cg_bolt_d=3;
cg_bolt_hole=fastener_d;
cg_head_d=5.5;
cg_head_h=3;
cg_washer_d=7;
cg_washer_h=.5;
cg_nut_af=5.5;
cg_nut_h=2.4;

function cg_front(s)=cg_front_retracted-s;
function cg_spine(s)=cg_front(s)+cg_tooth_length;
function cg_back(s)=cg_spine(s)+cg_spine_thickness;
function cg_gap(s)=cg_front(s)-support_rail_x1;
function cg_jack_head_x(s)=cg_back(s)+cg_jack_length;
assert(cg_setting>=0&&cg_setting<=cg_travel);
assert(cg_end_recess>cg_pocket_gap,"End recess must exceed ear axial float");
assert(cg_contact_y0-cg_pocket_gap>18+nut_depth,
    "Keep the original guide-cap nut entry corridor completely open");
assert(cg_spine(cg_travel)-cg_pocket_gap>support_guide_x1,
    "The long gib spine must stay outside the original fixed wall");
assert(cg_case_z1<cam_rail_z1-cam_bridge_width,
    "New top must clear the unshifted trigger cross member");
assert(cg_mount_nut_x>support_guide_x1,
    "New nut feed slots must not cut original cap nut channels");

module cg_box(x0,x1,y0,y1,z0,z1){translate([x0,y0,z0])cube([x1-x0,y1-y0,z1-z0]);}
module cg_x_hole(x,y,z,length,d){support_x_hole(y,z,x,length,d);}
module cg_x_hex(x,y,z,length,af){
    translate([x,y,z])rotate([0,90,0])rotate([0,0,30])
        cylinder(h=length,d=af/cos(30),$fn=6);
}
module cg_nut(x,y,z){difference(){
    cg_x_hex(x,y,z,cg_nut_h,cg_nut_af);
    cg_x_hole(x-cg_eps,y,z,cg_nut_h+2*cg_eps,3.2);
}}
module cg_washer(x,y,z){difference(){
    cg_x_hole(x,y,z,cg_washer_h,cg_washer_d);
    cg_x_hole(x-cg_eps,y,z,cg_washer_h+2*cg_eps,3.2);
}}

// The datum is integral, with .8 mm overlap into the OLD inner wall.
// Its long exposed face can be dressed with the +Y cap removed. Dressing
// changes the datum: measure/re-enter that offset; never call it self-centering.
module cg_datum(){
    cg_box(cg_datum_x-support_axial_clearance-cg_datum_embed,cg_datum_x,
        cg_contact_y0,cg_contact_y1,support_guide_z0,support_guide_z1);
}
module cg_case_blank(){
    cg_box(cg_case_x0,cg_case_face_x,cg_case_y0,cg_case_y1,
        cg_case_z0,cg_case_z1);
}
module cg_case_cuts(){
    // Do not merge the original +Y removable cap into the fixed support.
    cg_box(cg_case_x0-cg_eps,support_guide_x1+cg_eps,
        support_guide_y_split-cg_eps,cg_case_y1+cg_eps,
        support_guide_z0-cg_eps,support_guide_z1+cg_eps);
    // Only two windows pass through the original outboard wall.
    for(b=cg_contact_z)
        cg_box(support_rail_x1-cg_pocket_gap,cg_case_face_x+cg_eps,
            cg_contact_y0-cg_pocket_gap,cg_contact_y1+cg_pocket_gap,
            b[0]-cg_pocket_gap,b[1]+cg_pocket_gap);
    // Continuous spine is wholly outside the original wall.
    cg_box(cg_spine(cg_travel)-cg_pocket_gap,cg_case_face_x+cg_eps,
        cg_contact_y0-cg_pocket_gap,cg_contact_y1+cg_pocket_gap,
        support_guide_z0-cg_pocket_gap,support_guide_z1+cg_pocket_gap);
    // Ear pocket: its inner X wall is the positive advance stop.
    cg_box(cg_spine(cg_travel),cg_case_face_x+cg_eps,
        cg_ear_y0-cg_pocket_gap,cg_ear_y1+cg_pocket_gap,
        cg_ear_z0-cg_pocket_gap,cg_ear_z1+cg_pocket_gap);
    for(z=cg_mount_z){
        cg_x_hole(cg_cover_outer_x+.5-cg_mount_length-cg_mount_tip_clearance,cg_mount_y,z,
            cg_mount_length+cg_mount_tip_clearance+cg_eps,cg_bolt_hole);
        // Nut loads against the +X pocket floor; feed from +Y BEFORE gib.
        cg_x_hex(cg_mount_nut_x,cg_mount_y,z,nut_depth,nut_af);
        cg_box(cg_mount_nut_x,cg_mount_nut_x+nut_depth,
            cg_mount_y,cg_case_y1+cg_eps,z-nut_af/2,z+nut_af/2);
    }
}
module cg_right_support(){difference(){
    union(){revision_side_support_local();cg_datum();cg_case_blank();}
    cg_case_cuts();
}}

module cg_gib(s=cg_setting,dz=cg_gib_dz,recess=cg_end_recess){translate([0,0,dz])union(){
    cg_box(cg_spine(s),cg_back(s),cg_contact_y0,cg_contact_y1,
        support_guide_z0+recess,support_guide_z1-recess);
    for(b=cg_contact_z)
        cg_box(cg_front(s),cg_spine(s)+cg_eps,cg_contact_y0,cg_contact_y1,
            max(b[0],support_guide_z0+recess),min(b[1],support_guide_z1-recess));
    cg_box(cg_spine(s),cg_spine(s)+cg_ear_x_length,
        cg_ear_y0-cg_eps,cg_ear_y1,cg_ear_z0,cg_ear_z1);
}}
module cg_cover(){difference(){union(){
    cg_box(cg_case_face_x,cg_cover_outer_x,cg_case_y0,cg_case_y1,
        cg_case_z0,cg_case_z1);
    // Back stop leaves with the cover, so the gib can be pulled out +X.
    cg_box(cg_spine(0)+cg_ear_x_length,cg_case_face_x+cg_eps,
        cg_ear_y0,cg_ear_y1,cg_ear_z0,cg_ear_z1);
}
    for(z=cg_mount_z)cg_x_hole(cg_case_face_x-cg_eps,cg_mount_y,z,
        cg_cover_thickness+2*cg_eps,cg_bolt_hole);
    for(z=cg_jack_z){
        cg_x_hole(cg_case_face_x-cg_eps,cg_jack_y,z,
            cg_cover_thickness+2*cg_eps,cg_bolt_hole);
        // Insert nuts from the loose cover's -X face; 2.9 mm bearing web.
        cg_x_hex(cg_case_face_x-cg_eps,cg_jack_y,z,nut_depth+cg_eps,nut_af);
    }
}}
module cg_new_hardware(s=cg_setting,skip_z=undef){
    for(z=cg_mount_z)if(is_undef(skip_z)||z!=skip_z){
        under=cg_cover_outer_x+cg_washer_h;
        cg_x_hole(under-cg_mount_length,cg_mount_y,z,cg_mount_length,cg_bolt_d);
        cg_x_hole(under,cg_mount_y,z,cg_head_h,cg_head_d);
        cg_washer(cg_cover_outer_x,cg_mount_y,z);
        cg_nut(cg_mount_nut_x+nut_depth-cg_nut_h,cg_mount_y,z);
    }
    for(z=cg_jack_z)if(is_undef(skip_z)||z!=skip_z){
        cg_x_hole(cg_back(s),cg_jack_y,z,cg_jack_length,cg_bolt_d);
        cg_x_hole(cg_jack_head_x(s),cg_jack_y,z,cg_head_h,cg_head_d);
        cg_nut(cg_case_face_x+nut_depth-cg_nut_h,cg_jack_y,z);
        cg_washer(cg_cover_outer_x,cg_jack_y,z);
        cg_nut(cg_cover_outer_x+cg_washer_h,cg_jack_y,z);
    }
}
module cg_fixed(include_new_cover=true,include_y_caps=true){
    cg_right_support();
    mirror([1,0,0])revision_side_support_local();
    if(include_y_caps)for(side=[-1,1])scale([side,1,1])feeder_guide_cap_local();
    for(side=[-1,1],g=[0,-gate_spacing])
        scale([side,1,1])translate([0,0,g])revision_keeper_local();
    feeder_spring_fixed_interface();
    if(include_new_cover)cg_cover();
}
module cg_body(){seam_candidate_half(false);seam_candidate_half(true);seam_pins();}
module cg_old_hardware(include_caps=true){
    if(include_caps)feeder_cap_hardware();
    feeder_mount_hardware();
    for(side=[-1,1],g=[0,-gate_spacing])scale([side,1,1])revision_hardware_local(g,.9);
}
module cg_moving(t=cg_t){feeder_carriage(t);revision_followers(t);}
module cg_station_tools(z,s=cg_setting,jack=true){
    if(!jack)cg_x_hole(cg_cover_outer_x+.5+cg_head_h,cg_mount_y,z,40,4);
    else{
        cg_x_hole(cg_jack_head_x(s)+cg_head_h,cg_jack_y,z,40,4);
        // 5.5 open wrench outer envelope, with handle directed +Y.
        cg_x_hole(cg_cover_outer_x+.5,cg_jack_y,z,2.8,9);
        cg_box(cg_cover_outer_x+.5,cg_cover_outer_x+3.3,
            cg_jack_y,cg_jack_y+35,z-3,z+3);
    }
}
module cg_tools(s=cg_setting){
    for(z=cg_mount_z)cg_station_tools(z,s,false);
    for(z=cg_jack_z)cg_station_tools(z,s,true);
}
// Exact swept primitives of the unmodified RIGHT rail + its endpoint stops.
// These are the only moving members able to touch the new bearing faces.
module cg_rail_sweep(dx=0){translate([dx,0,0]){
    cg_box(support_rail_x0,support_rail_x1,support_rail_y0,support_rail_y1,
        cam_rail_z0,cam_rail_z1+cam_stroke);
    for(z=[support_guide_z0-cam_stroke-support_stop_thickness,support_guide_z1])
        cg_box(support_stop_x0,support_stop_x1,support_stop_y0,support_stop_y1,
            z,z+support_stop_thickness+cam_stroke);
}}
module cg_new_contact_solids(s=cg_setting){cg_datum();cg_gib(s);}
module cg_new_only_fixed(){difference(){cg_right_support();revision_side_support_local();}cg_cover();}

module cg_probe_geometry(){
    if(cg_probe=="motion")intersection(){
        union(){cg_fixed();cg_gib();revision_gibs();cg_body();cg_old_hardware();cg_new_hardware();}
        cg_moving();}
    else if(cg_probe=="cam_followers")intersection(){feeder_carriage(cg_t);revision_followers(cg_t);}
    else if(cg_probe=="hardware")intersection(){
        union(){cg_fixed();cg_gib();revision_gibs();cg_body();cg_moving();cg_old_hardware();}
        cg_new_hardware();}
    else if(cg_probe=="old_hardware")intersection(){
        cg_new_only_fixed();cg_old_hardware();}
    else if(cg_probe=="tools")union(){intersection(){
        union(){cg_fixed();cg_gib();revision_gibs();cg_body();cg_moving();cg_old_hardware();}
        cg_tools();}
        for(z=cg_mount_z)intersection(){cg_new_hardware(skip_z=z);cg_station_tools(z,jack=false);}
        for(z=cg_jack_z)intersection(){cg_new_hardware(skip_z=z);cg_station_tools(z,jack=true);}
    }
    else if(cg_probe=="old_tools")intersection(){cg_new_only_fixed();union(){revision_tools();feeder_follower_tools(cg_t);}}
    else if(cg_probe=="gib_fit")intersection(){cg_fixed();cg_gib();}
    else if(cg_probe=="legacy_gib_endpoint")intersection(){
        cg_gib(dz=cg_gib_dz,recess=0);feeder_carriage(cg_t);}
    else if(cg_probe=="fixed_stop_bearing")intersection(){
        // Exact rectangular subset of the FIXED datum's stop-bearing face.
        // 0.01 mm inside the plane makes area measurable as volume/.01.
        cg_datum();
        z=(cg_t==0?support_guide_z1-.01:support_guide_z0);
        cg_box(support_stop_x0+cg_fault_x,support_stop_x1+cg_fault_x,
            support_stop_y0,support_stop_y1,z,z+.01);}
    else if(cg_probe=="sweep")intersection(){cg_new_contact_solids();cg_rail_sweep(cg_fault_x);}
    else if(cg_probe=="old_witness")intersection(){
        cg_new_contact_solids();multmatrix(cg_witness_matrix)feeder_carriage(cg_t);}
    else if(cg_probe=="gib_remove")intersection(){
        union(){cg_fixed(false);revision_gibs();cg_body();cg_moving();cg_old_hardware();}
        translate([cg_remove,0,0])cg_gib(0);}
    else if(cg_probe=="cover_remove")intersection(){
        union(){cg_fixed(false);cg_gib(0);revision_gibs();cg_body();cg_moving();cg_old_hardware();}
        translate([cg_remove,0,0])cg_cover();}
    else if(cg_probe=="lift_frame")intersection(){
        union(){cg_fixed(true,false);cg_gib(0);revision_gibs();cg_body();
            for(side=[-1,1],rear=[false,true])cam_finger(side,rear,cg_t);}
        feeder_carriage(cg_t,cg_remove);}
    else if(cg_probe=="mount_nut_insert")intersection(){
        cg_right_support();
        for(z=cg_mount_z)hull()for(dy=[0,25])
            cg_x_hex(cg_mount_nut_x+nut_depth-cg_nut_h,cg_mount_y+dy,z,cg_nut_h,cg_nut_af);}
    else if(cg_probe=="jack_nut_insert")intersection(){
        cg_cover();
        for(z=cg_jack_z)hull()for(dx=[0,-10])
            cg_x_hex(cg_case_face_x+nut_depth-cg_nut_h+dx,cg_jack_y,z,cg_nut_h,cg_nut_af);}
    else if(cg_probe=="old_nut_insert")intersection(){
        cg_right_support();
        for(z=support_cap_screw_z)hull()for(from=[support_nut_entry_z-4,z])
            support_y_hex(support_cap_screw_x,from,18.1,2.4,5.5);}
    else if(cg_probe=="advance_stop")intersection(){cg_fixed();cg_gib(cg_travel+.1);}
    else if(cg_probe=="retract_stop")intersection(){cg_fixed();cg_gib(-.1);}
    else if(cg_probe=="datum_embed")intersection(){cg_datum();revision_side_support_local();}
    else if(cg_probe=="case_embed")intersection(){
        difference(){cg_case_blank();cg_case_cuts();}revision_side_support_local();}
    else if(cg_probe=="bad_nut_sequence")intersection(){
        cg_gib();for(z=cg_mount_z)hull()for(dy=[0,25])
            cg_x_hex(cg_mount_nut_x+nut_depth-cg_nut_h,cg_mount_y+dy,z,cg_nut_h,cg_nut_af);}
    else assert(false,"Unknown cg_probe");
}
module cg_display(section=false){
    if(cg_show_body)color([.6,.68,.75]){
        if(section)seam_candidate_half(false);else cg_body();
    }
    color([.70,.72,.76])cg_fixed();
    color([.95,.63,.12]){cg_gib();revision_gibs();}
    color([.12,.43,.78])feeder_carriage(cg_t);
    color([.15,.65,.39])revision_followers(cg_t);
    if(cg_show_hardware)color([.28,.29,.31]){cg_old_hardware();cg_new_hardware();}
}
module cg_working_section(){
    // Local horizontal XY section through the upper bearing and jack axis.
    // Color outside each boolean preserves the mechanical interfaces in F6.
    module clip(){intersection(){children();
        cg_box(48,94,16,31,cg_jack_z[1]-.65,cg_jack_z[1]+.65);}}
    color([.70,.72,.76])clip()cg_fixed();
    color([.95,.63,.12])clip()cg_gib();
    color([.12,.43,.78])clip()feeder_carriage(cg_t);
    if(cg_show_hardware)color([.28,.29,.31])clip()cg_new_hardware();
}
module cg_dimensions(){echo("CG_DIMENSIONS",[
    ["datum_x",cg_datum_x],["rail_x0",support_rail_x0],["rail_x1",support_rail_x1],
    ["old_half_gap",support_axial_clearance],["contact_y",[cg_contact_y0,cg_contact_y1]],
    ["contact_z",cg_contact_z],["front_x",cg_front(cg_setting)],["setting",cg_setting],
    ["travel",cg_travel],["parallel_x_interval",[0,cg_gap(cg_setting)]],
    ["gib_end_recess",cg_end_recess],["gib_axial_float_limit",cg_pocket_gap],
    ["worst_axial_end_clearance",cg_end_recess-cg_pocket_gap],
    ["active_contact_z",[for(b=cg_contact_z)
        [max(b[0],support_guide_z0+cg_end_recess),min(b[1],support_guide_z1-cg_end_recess)]]],
    ["known_gib_limit_planes",[[0,cg_spine(cg_travel)],
        [2,cg_ear_z0-cg_pocket_gap],[2,cg_ear_z1+cg_pocket_gap],
        [2,cg_contact_z[0][1]+cg_pocket_gap],[2,cg_contact_z[1][0]-cg_pocket_gap]]],
    ["stroke",cam_stroke],["spine_front_min",cg_spine(cg_travel)],
    ["datum_overlap",cg_datum_embed],["nut_channel_y_max",18+nut_depth],
    ["new_pocket_y_min",cg_contact_y0-cg_pocket_gap],
    ["jack_z",cg_jack_z],["jack_y",cg_jack_y],["mount_z",cg_mount_z],
    ["nut_bearing_web",cg_cover_thickness-nut_depth],
    ["mount_tip_clearance",cg_mount_tip_clearance],
    ["max_new_hardware_x",cg_jack_head_x(0)+cg_head_h],
    ["guide_z",[support_guide_z0,support_guide_z1]]]);}

if(is_undef(cg_library_mode)||!cg_library_mode){
    if(cg_part=="assembly")cg_display();
    else if(cg_part=="section")cg_working_section();
    else if(cg_part=="right_support")cg_right_support();
    else if(cg_part=="gib")cg_gib(0);
    else if(cg_part=="cover")cg_cover();
    else if(cg_part=="probe")cg_probe_geometry();
    else if(cg_part=="dimensions")cg_dimensions();
    else assert(false,"Unknown cg_part");
}

union(){mirror([1,0,0])revision_side_support_local();feeder_spring_fixed_interface();}
}
module revised(){cg_library_mode=true;
// Independent right-master X guide candidate. Units mm; X1C/.4/PETG.
// Reuses the existing carrier Y gibs, cam carriage and seam-body candidates.
// Not adopted into the root assembly; no physical/tolerance release implied.
revision_library_mode=true;
// Adjustable -Y gib candidate; physical setting and load acceptance OPEN.
// Wraps feeder_side_support_local(), not a copy of the original support.
// Initial reviewed base SHA256 is recorded in docs/feeder-guide-revision.md.
feeder_support_library_mode=true;
// Concrete external support candidate. Physical acceptance remains OPEN.
// Set feeder_support_library_mode=true before include for integration.
cam_library_mode = true;
// 3D constraint / assembly study only. NOT a finished printable mechanism.
// Standalone visualization excludes the concrete guide/retainer candidate in
// feeder-supports.scad. Seals, total error/load and spring choice remain OPEN.
// Ball travel +Z; front gate Z=0; rear gate Z=-gate_spacing.
// Fingers translate +/-X, removable follower pins point +Y, carriage moves +Z.
// 单位：mm。用户提供的接口尺寸与待实测的样机候选参数明确分开。
// 该文件是几何尺寸的唯一来源；修改后必须重新校核并导出。

// 用户提供；未以实物量规复核。
barrel_id = 48;
barrel_od = 50;
hose_id = 50;
hose_od = 55;

// 以下是工程校核包络，不是对用户实际球径的声明。
ball_min_d = 40;
ball_max_d = 41;
guide_id = 42.5;
guide_od = 47;
guide_start_z = -80;
guide_length = 104;
transition_length = 18;
feed_socket_od = 49.4;
feed_socket_length = 28;
y_stub_od = 50;
y_stub_engagement = 25;
barrel_engagement = 25;
interface_radial_clearance = 0.25;

// 待运动校核的双挡指候选几何。
finger_tip_radius = 2.5;
finger_closed_center_r = 21;
finger_open_center_r = 26;
gate_spacing = 28.5;
gate_overlap_fraction = 0.20;
cam_stroke = 20;
guide_clearance_budget = 0.25;
// 容纳槽/销孔名义游隙后的设计包络；并非实测的制造或受力误差。
gate_position_budget = 1.0;

// 外壳、旁通与可拆装接口。
body_id = 64;
body_wall = 3;
body_flange = 9;
split_gasket_thickness = 1;
fastener_d = 3.4;
nut_af = 5.8;
nut_depth = 2.6;
radial_print_clearance = 0.25;
axial_print_clearance = 0.3;

// 摩擦头候选；零接触位置不能被宣传为已验证的无旋球。
spin_guide_id = 42.5;
spin_body_wall = 3;
spin_pad_width = 12;
spin_pad_length = 22;
spin_pad_thickness = 1;
spin_adjustment_travel = 2.5;
spin_contact_length = 30;
spin_angle = 0;

$fn = 72;


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
// The outer connecting column starts below the axial guide. Nut insertion must
// clear that lower lip as well as the guide itself.
support_nut_entry_z = -gate_spacing-support_radial_half_z-support_eps;

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
            translate([support_cap_screw_x-nut_af/2,18,support_nut_entry_z])
                cube([nut_af,nut_depth,
                    z-support_nut_entry_z]);
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
        // The integral spring rib must not refill the axial cap-nut channel.
        // Preserve the lower 6.6 mm-deep load path (Y=11.4..18); clear the
        // same Y=18..20.6 insertion band used by the left fixed guide.
        translate([-support_cap_screw_x-nut_af/2,18,support_nut_entry_z])
            cube([nut_af,nut_depth,max(support_cap_screw_z)-support_nut_entry_z]);
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

use <feeder-seam-candidate.scad>

cg_part="assembly"; // assembly,section,right_support,gib,cover,probe,dimensions
cg_t=.5;
cg_setting=.9; // advance [0,1]; parallel display, NOT measured printing error
cg_probe="motion";
cg_remove=0;
cg_fault_x=0;
cg_gib_dz=0; // rigid axial float; ear pocket bounds it to +/- .2 nominally
cg_witness_matrix=[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]];
cg_show_body=true;
cg_show_hardware=true;
cg_eps=.02;

// ONE X master on the right. The left guide's original .2 side gaps remain.
cg_datum_x=support_rail_x0;
cg_datum_embed=.8;
cg_contact_y0=21;
cg_contact_y1=support_rail_y1;
cg_contact_z=[[support_guide_z0,support_cap_screw_z[0]-3.1],
              [support_cap_screw_z[1]+3.1,support_guide_z1]];
cg_travel=1;
cg_front_retracted=support_rail_x1+cg_travel;
cg_tooth_length=9.4;
cg_spine_thickness=3;
cg_pocket_gap=.2;
cg_end_recess=.4; // both moving ends stay behind FIXED guide stop planes
cg_jack_y=(cg_contact_y0+cg_contact_y1)/2;
cg_jack_z=[for(b=cg_contact_z)(b[0]+b[1])/2];
cg_case_x0=support_guide_x1-1;
cg_case_face_x=75;
cg_case_y0=10.5;
cg_case_y1=28;
cg_case_z0=support_guide_z0-4;
cg_case_z1=support_guide_z1+4;
cg_cover_thickness=5.5;
cg_cover_outer_x=cg_case_face_x+cg_cover_thickness;
cg_mount_y=15;
cg_mount_z=[-24,-6];
cg_mount_nut_x=68;
cg_ear_z0=-18;
cg_ear_z1=-12;
cg_ear_y0=cg_contact_y1;
cg_ear_y1=cg_contact_y1+2;
cg_ear_x_length=1;
cg_jack_length=16;
cg_mount_length=16;
cg_mount_tip_clearance=1.5;
cg_bolt_d=3;
cg_bolt_hole=fastener_d;
cg_head_d=5.5;
cg_head_h=3;
cg_washer_d=7;
cg_washer_h=.5;
cg_nut_af=5.5;
cg_nut_h=2.4;

function cg_front(s)=cg_front_retracted-s;
function cg_spine(s)=cg_front(s)+cg_tooth_length;
function cg_back(s)=cg_spine(s)+cg_spine_thickness;
function cg_gap(s)=cg_front(s)-support_rail_x1;
function cg_jack_head_x(s)=cg_back(s)+cg_jack_length;
assert(cg_setting>=0&&cg_setting<=cg_travel);
assert(cg_end_recess>cg_pocket_gap,"End recess must exceed ear axial float");
assert(cg_contact_y0-cg_pocket_gap>18+nut_depth,
    "Keep the original guide-cap nut entry corridor completely open");
assert(cg_spine(cg_travel)-cg_pocket_gap>support_guide_x1,
    "The long gib spine must stay outside the original fixed wall");
assert(cg_case_z1<cam_rail_z1-cam_bridge_width,
    "New top must clear the unshifted trigger cross member");
assert(cg_mount_nut_x>support_guide_x1,
    "New nut feed slots must not cut original cap nut channels");

module cg_box(x0,x1,y0,y1,z0,z1){translate([x0,y0,z0])cube([x1-x0,y1-y0,z1-z0]);}
module cg_x_hole(x,y,z,length,d){support_x_hole(y,z,x,length,d);}
module cg_x_hex(x,y,z,length,af){
    translate([x,y,z])rotate([0,90,0])rotate([0,0,30])
        cylinder(h=length,d=af/cos(30),$fn=6);
}
module cg_nut(x,y,z){difference(){
    cg_x_hex(x,y,z,cg_nut_h,cg_nut_af);
    cg_x_hole(x-cg_eps,y,z,cg_nut_h+2*cg_eps,3.2);
}}
module cg_washer(x,y,z){difference(){
    cg_x_hole(x,y,z,cg_washer_h,cg_washer_d);
    cg_x_hole(x-cg_eps,y,z,cg_washer_h+2*cg_eps,3.2);
}}

// The datum is integral, with .8 mm overlap into the OLD inner wall.
// Its long exposed face can be dressed with the +Y cap removed. Dressing
// changes the datum: measure/re-enter that offset; never call it self-centering.
module cg_datum(){
    cg_box(cg_datum_x-support_axial_clearance-cg_datum_embed,cg_datum_x,
        cg_contact_y0,cg_contact_y1,support_guide_z0,support_guide_z1);
}
module cg_case_blank(){
    cg_box(cg_case_x0,cg_case_face_x,cg_case_y0,cg_case_y1,
        cg_case_z0,cg_case_z1);
}
module cg_case_cuts(){
    // Do not merge the original +Y removable cap into the fixed support.
    cg_box(cg_case_x0-cg_eps,support_guide_x1+cg_eps,
        support_guide_y_split-cg_eps,cg_case_y1+cg_eps,
        support_guide_z0-cg_eps,support_guide_z1+cg_eps);
    // Only two windows pass through the original outboard wall.
    for(b=cg_contact_z)
        cg_box(support_rail_x1-cg_pocket_gap,cg_case_face_x+cg_eps,
            cg_contact_y0-cg_pocket_gap,cg_contact_y1+cg_pocket_gap,
            b[0]-cg_pocket_gap,b[1]+cg_pocket_gap);
    // Continuous spine is wholly outside the original wall.
    cg_box(cg_spine(cg_travel)-cg_pocket_gap,cg_case_face_x+cg_eps,
        cg_contact_y0-cg_pocket_gap,cg_contact_y1+cg_pocket_gap,
        support_guide_z0-cg_pocket_gap,support_guide_z1+cg_pocket_gap);
    // Ear pocket: its inner X wall is the positive advance stop.
    cg_box(cg_spine(cg_travel),cg_case_face_x+cg_eps,
        cg_ear_y0-cg_pocket_gap,cg_ear_y1+cg_pocket_gap,
        cg_ear_z0-cg_pocket_gap,cg_ear_z1+cg_pocket_gap);
    for(z=cg_mount_z){
        cg_x_hole(cg_cover_outer_x+.5-cg_mount_length-cg_mount_tip_clearance,cg_mount_y,z,
            cg_mount_length+cg_mount_tip_clearance+cg_eps,cg_bolt_hole);
        // Nut loads against the +X pocket floor; feed from +Y BEFORE gib.
        cg_x_hex(cg_mount_nut_x,cg_mount_y,z,nut_depth,nut_af);
        cg_box(cg_mount_nut_x,cg_mount_nut_x+nut_depth,
            cg_mount_y,cg_case_y1+cg_eps,z-nut_af/2,z+nut_af/2);
    }
}
module cg_right_support(){difference(){
    union(){revision_side_support_local();cg_datum();cg_case_blank();}
    cg_case_cuts();
}}

module cg_gib(s=cg_setting,dz=cg_gib_dz,recess=cg_end_recess){translate([0,0,dz])union(){
    cg_box(cg_spine(s),cg_back(s),cg_contact_y0,cg_contact_y1,
        support_guide_z0+recess,support_guide_z1-recess);
    for(b=cg_contact_z)
        cg_box(cg_front(s),cg_spine(s)+cg_eps,cg_contact_y0,cg_contact_y1,
            max(b[0],support_guide_z0+recess),min(b[1],support_guide_z1-recess));
    cg_box(cg_spine(s),cg_spine(s)+cg_ear_x_length,
        cg_ear_y0-cg_eps,cg_ear_y1,cg_ear_z0,cg_ear_z1);
}}
module cg_cover(){difference(){union(){
    cg_box(cg_case_face_x,cg_cover_outer_x,cg_case_y0,cg_case_y1,
        cg_case_z0,cg_case_z1);
    // Back stop leaves with the cover, so the gib can be pulled out +X.
    cg_box(cg_spine(0)+cg_ear_x_length,cg_case_face_x+cg_eps,
        cg_ear_y0,cg_ear_y1,cg_ear_z0,cg_ear_z1);
}
    for(z=cg_mount_z)cg_x_hole(cg_case_face_x-cg_eps,cg_mount_y,z,
        cg_cover_thickness+2*cg_eps,cg_bolt_hole);
    for(z=cg_jack_z){
        cg_x_hole(cg_case_face_x-cg_eps,cg_jack_y,z,
            cg_cover_thickness+2*cg_eps,cg_bolt_hole);
        // Insert nuts from the loose cover's -X face; 2.9 mm bearing web.
        cg_x_hex(cg_case_face_x-cg_eps,cg_jack_y,z,nut_depth+cg_eps,nut_af);
    }
}}
module cg_new_hardware(s=cg_setting,skip_z=undef){
    for(z=cg_mount_z)if(is_undef(skip_z)||z!=skip_z){
        under=cg_cover_outer_x+cg_washer_h;
        cg_x_hole(under-cg_mount_length,cg_mount_y,z,cg_mount_length,cg_bolt_d);
        cg_x_hole(under,cg_mount_y,z,cg_head_h,cg_head_d);
        cg_washer(cg_cover_outer_x,cg_mount_y,z);
        cg_nut(cg_mount_nut_x+nut_depth-cg_nut_h,cg_mount_y,z);
    }
    for(z=cg_jack_z)if(is_undef(skip_z)||z!=skip_z){
        cg_x_hole(cg_back(s),cg_jack_y,z,cg_jack_length,cg_bolt_d);
        cg_x_hole(cg_jack_head_x(s),cg_jack_y,z,cg_head_h,cg_head_d);
        cg_nut(cg_case_face_x+nut_depth-cg_nut_h,cg_jack_y,z);
        cg_washer(cg_cover_outer_x,cg_jack_y,z);
        cg_nut(cg_cover_outer_x+cg_washer_h,cg_jack_y,z);
    }
}
module cg_fixed(include_new_cover=true,include_y_caps=true){
    cg_right_support();
    mirror([1,0,0])revision_side_support_local();
    if(include_y_caps)for(side=[-1,1])scale([side,1,1])feeder_guide_cap_local();
    for(side=[-1,1],g=[0,-gate_spacing])
        scale([side,1,1])translate([0,0,g])revision_keeper_local();
    feeder_spring_fixed_interface();
    if(include_new_cover)cg_cover();
}
module cg_body(){seam_candidate_half(false);seam_candidate_half(true);seam_pins();}
module cg_old_hardware(include_caps=true){
    if(include_caps)feeder_cap_hardware();
    feeder_mount_hardware();
    for(side=[-1,1],g=[0,-gate_spacing])scale([side,1,1])revision_hardware_local(g,.9);
}
module cg_moving(t=cg_t){feeder_carriage(t);revision_followers(t);}
module cg_station_tools(z,s=cg_setting,jack=true){
    if(!jack)cg_x_hole(cg_cover_outer_x+.5+cg_head_h,cg_mount_y,z,40,4);
    else{
        cg_x_hole(cg_jack_head_x(s)+cg_head_h,cg_jack_y,z,40,4);
        // 5.5 open wrench outer envelope, with handle directed +Y.
        cg_x_hole(cg_cover_outer_x+.5,cg_jack_y,z,2.8,9);
        cg_box(cg_cover_outer_x+.5,cg_cover_outer_x+3.3,
            cg_jack_y,cg_jack_y+35,z-3,z+3);
    }
}
module cg_tools(s=cg_setting){
    for(z=cg_mount_z)cg_station_tools(z,s,false);
    for(z=cg_jack_z)cg_station_tools(z,s,true);
}
// Exact swept primitives of the unmodified RIGHT rail + its endpoint stops.
// These are the only moving members able to touch the new bearing faces.
module cg_rail_sweep(dx=0){translate([dx,0,0]){
    cg_box(support_rail_x0,support_rail_x1,support_rail_y0,support_rail_y1,
        cam_rail_z0,cam_rail_z1+cam_stroke);
    for(z=[support_guide_z0-cam_stroke-support_stop_thickness,support_guide_z1])
        cg_box(support_stop_x0,support_stop_x1,support_stop_y0,support_stop_y1,
            z,z+support_stop_thickness+cam_stroke);
}}
module cg_new_contact_solids(s=cg_setting){cg_datum();cg_gib(s);}
module cg_new_only_fixed(){difference(){cg_right_support();revision_side_support_local();}cg_cover();}

module cg_probe_geometry(){
    if(cg_probe=="motion")intersection(){
        union(){cg_fixed();cg_gib();revision_gibs();cg_body();cg_old_hardware();cg_new_hardware();}
        cg_moving();}
    else if(cg_probe=="cam_followers")intersection(){feeder_carriage(cg_t);revision_followers(cg_t);}
    else if(cg_probe=="hardware")intersection(){
        union(){cg_fixed();cg_gib();revision_gibs();cg_body();cg_moving();cg_old_hardware();}
        cg_new_hardware();}
    else if(cg_probe=="old_hardware")intersection(){
        cg_new_only_fixed();cg_old_hardware();}
    else if(cg_probe=="tools")union(){intersection(){
        union(){cg_fixed();cg_gib();revision_gibs();cg_body();cg_moving();cg_old_hardware();}
        cg_tools();}
        for(z=cg_mount_z)intersection(){cg_new_hardware(skip_z=z);cg_station_tools(z,jack=false);}
        for(z=cg_jack_z)intersection(){cg_new_hardware(skip_z=z);cg_station_tools(z,jack=true);}
    }
    else if(cg_probe=="old_tools")intersection(){cg_new_only_fixed();union(){revision_tools();feeder_follower_tools(cg_t);}}
    else if(cg_probe=="gib_fit")intersection(){cg_fixed();cg_gib();}
    else if(cg_probe=="legacy_gib_endpoint")intersection(){
        cg_gib(dz=cg_gib_dz,recess=0);feeder_carriage(cg_t);}
    else if(cg_probe=="fixed_stop_bearing")intersection(){
        // Exact rectangular subset of the FIXED datum's stop-bearing face.
        // 0.01 mm inside the plane makes area measurable as volume/.01.
        cg_datum();
        z=(cg_t==0?support_guide_z1-.01:support_guide_z0);
        cg_box(support_stop_x0+cg_fault_x,support_stop_x1+cg_fault_x,
            support_stop_y0,support_stop_y1,z,z+.01);}
    else if(cg_probe=="sweep")intersection(){cg_new_contact_solids();cg_rail_sweep(cg_fault_x);}
    else if(cg_probe=="old_witness")intersection(){
        cg_new_contact_solids();multmatrix(cg_witness_matrix)feeder_carriage(cg_t);}
    else if(cg_probe=="gib_remove")intersection(){
        union(){cg_fixed(false);revision_gibs();cg_body();cg_moving();cg_old_hardware();}
        translate([cg_remove,0,0])cg_gib(0);}
    else if(cg_probe=="cover_remove")intersection(){
        union(){cg_fixed(false);cg_gib(0);revision_gibs();cg_body();cg_moving();cg_old_hardware();}
        translate([cg_remove,0,0])cg_cover();}
    else if(cg_probe=="lift_frame")intersection(){
        union(){cg_fixed(true,false);cg_gib(0);revision_gibs();cg_body();
            for(side=[-1,1],rear=[false,true])cam_finger(side,rear,cg_t);}
        feeder_carriage(cg_t,cg_remove);}
    else if(cg_probe=="mount_nut_insert")intersection(){
        cg_right_support();
        for(z=cg_mount_z)hull()for(dy=[0,25])
            cg_x_hex(cg_mount_nut_x+nut_depth-cg_nut_h,cg_mount_y+dy,z,cg_nut_h,cg_nut_af);}
    else if(cg_probe=="jack_nut_insert")intersection(){
        cg_cover();
        for(z=cg_jack_z)hull()for(dx=[0,-10])
            cg_x_hex(cg_case_face_x+nut_depth-cg_nut_h+dx,cg_jack_y,z,cg_nut_h,cg_nut_af);}
    else if(cg_probe=="old_nut_insert")intersection(){
        cg_right_support();
        for(z=support_cap_screw_z)hull()for(from=[support_nut_entry_z-4,z])
            support_y_hex(support_cap_screw_x,from,18.1,2.4,5.5);}
    else if(cg_probe=="advance_stop")intersection(){cg_fixed();cg_gib(cg_travel+.1);}
    else if(cg_probe=="retract_stop")intersection(){cg_fixed();cg_gib(-.1);}
    else if(cg_probe=="datum_embed")intersection(){cg_datum();revision_side_support_local();}
    else if(cg_probe=="case_embed")intersection(){
        difference(){cg_case_blank();cg_case_cuts();}revision_side_support_local();}
    else if(cg_probe=="bad_nut_sequence")intersection(){
        cg_gib();for(z=cg_mount_z)hull()for(dy=[0,25])
            cg_x_hex(cg_mount_nut_x+nut_depth-cg_nut_h,cg_mount_y+dy,z,cg_nut_h,cg_nut_af);}
    else assert(false,"Unknown cg_probe");
}
module cg_display(section=false){
    if(cg_show_body)color([.6,.68,.75]){
        if(section)seam_candidate_half(false);else cg_body();
    }
    color([.70,.72,.76])cg_fixed();
    color([.95,.63,.12]){cg_gib();revision_gibs();}
    color([.12,.43,.78])feeder_carriage(cg_t);
    color([.15,.65,.39])revision_followers(cg_t);
    if(cg_show_hardware)color([.28,.29,.31]){cg_old_hardware();cg_new_hardware();}
}
module cg_working_section(){
    // Local horizontal XY section through the upper bearing and jack axis.
    // Color outside each boolean preserves the mechanical interfaces in F6.
    module clip(){intersection(){children();
        cg_box(48,94,16,31,cg_jack_z[1]-.65,cg_jack_z[1]+.65);}}
    color([.70,.72,.76])clip()cg_fixed();
    color([.95,.63,.12])clip()cg_gib();
    color([.12,.43,.78])clip()feeder_carriage(cg_t);
    if(cg_show_hardware)color([.28,.29,.31])clip()cg_new_hardware();
}
module cg_dimensions(){echo("CG_DIMENSIONS",[
    ["datum_x",cg_datum_x],["rail_x0",support_rail_x0],["rail_x1",support_rail_x1],
    ["old_half_gap",support_axial_clearance],["contact_y",[cg_contact_y0,cg_contact_y1]],
    ["contact_z",cg_contact_z],["front_x",cg_front(cg_setting)],["setting",cg_setting],
    ["travel",cg_travel],["parallel_x_interval",[0,cg_gap(cg_setting)]],
    ["gib_end_recess",cg_end_recess],["gib_axial_float_limit",cg_pocket_gap],
    ["worst_axial_end_clearance",cg_end_recess-cg_pocket_gap],
    ["active_contact_z",[for(b=cg_contact_z)
        [max(b[0],support_guide_z0+cg_end_recess),min(b[1],support_guide_z1-cg_end_recess)]]],
    ["known_gib_limit_planes",[[0,cg_spine(cg_travel)],
        [2,cg_ear_z0-cg_pocket_gap],[2,cg_ear_z1+cg_pocket_gap],
        [2,cg_contact_z[0][1]+cg_pocket_gap],[2,cg_contact_z[1][0]-cg_pocket_gap]]],
    ["stroke",cam_stroke],["spine_front_min",cg_spine(cg_travel)],
    ["datum_overlap",cg_datum_embed],["nut_channel_y_max",18+nut_depth],
    ["new_pocket_y_min",cg_contact_y0-cg_pocket_gap],
    ["jack_z",cg_jack_z],["jack_y",cg_jack_y],["mount_z",cg_mount_z],
    ["nut_bearing_web",cg_cover_thickness-nut_depth],
    ["mount_tip_clearance",cg_mount_tip_clearance],
    ["max_new_hardware_x",cg_jack_head_x(0)+cg_head_h],
    ["guide_z",[support_guide_z0,support_guide_z1]]]);}

if(is_undef(cg_library_mode)||!cg_library_mode){
    if(cg_part=="assembly")cg_display();
    else if(cg_part=="section")cg_working_section();
    else if(cg_part=="right_support")cg_right_support();
    else if(cg_part=="gib")cg_gib(0);
    else if(cg_part=="cover")cg_cover();
    else if(cg_part=="probe")cg_probe_geometry();
    else if(cg_part=="dimensions")cg_dimensions();
    else assert(false,"Unknown cg_part");
}

union(){mirror([1,0,0])revision_side_support_local();feeder_spring_fixed_interface();}
}
difference(){revised();old();}
