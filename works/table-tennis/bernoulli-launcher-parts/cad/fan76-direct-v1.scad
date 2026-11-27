// Ø76 fan -> integral long adjustable nozzle -> measured Y socket.
// Five clean print targets: body, core15, core20, core25, core30.
// All review envelopes are explicitly non-printable evidence objects.
include <fan76-direct-v1-parameters.scad>
include <fan76-direct-v1-thread.scad>
part="body";
outlet_id=15;
adjust_z=f76_core_min_z;
$fn=f76_fn;

module f76_outer() {
    rotate_extrude() polygon(concat(
        [[0,0],[f76_collar_od/2,0],[f76_collar_od/2,f76_outer_taper_z0]],
        [for(i=[1:48]) [f76_blend(f76_collar_od/2,f76_tube_od/2,i/48),
            f76_outer_taper_z0+(f76_outer_taper_z1-f76_outer_taper_z0)*i/48]],
        [[f76_tube_od/2,f76_spigot_z0-2],
         [f76_spigot_od/2,f76_spigot_z0],
         [f76_spigot_od/2,f76_body_h-f76_spigot_chamfer_l],
         [f76_spigot_od/2-f76_spigot_chamfer_r,f76_body_h],
         [0,f76_body_h]]));
}
module f76_bore() {
    // Nominal fan face Z24 is a DATUM, not an added annular hard stop.
    // Socket R38.3 joins the reducer without a horizontal shoulder. The gentle
    // initial slope still clears fan OD76 at face Z24.5 (axial lug clearance).
    rotate_extrude() polygon(concat(
        [[0,-f76_eps],[f76_socket_id/2+f76_entry_chamfer,-f76_eps],
         [f76_socket_id/2,f76_entry_chamfer],[f76_socket_id/2,f76_face_z]],
        [for(i=[1:48]) [f76_blend(f76_socket_id/2,21.3,i/48),
            f76_face_z+(68-f76_face_z)*i/48]],
        [[f76_female_minor/2,f76_female_z0],
         [f76_female_minor/2,f76_female_z1],
         [f76_spigot_id/2,f76_guide_z0],
         [f76_spigot_id/2,f76_body_h+f76_eps],[0,f76_body_h+f76_eps]]));
}
module f76_sector(a0,a1,r0,r1,z0,z1) {
    n=64;
    translate([0,0,z0]) linear_extrude(height=z1-z0)
        polygon(concat([for(i=[0:n]) [r0*cos(a0+(a1-a0)*i/n),r0*sin(a0+(a1-a0)*i/n)]],
                       [for(i=[n:-1:0]) [r1*cos(a0+(a1-a0)*i/n),r1*sin(a0+(a1-a0)*i/n)]]));
}
module f76_bayonet_cut() {
    for(a=f76_lug_angles) {
        rotate([0,0,a]) translate([f76_slot_inner_r,-f76_lug_window_w/2,-f76_eps])
            cube([f76_fan_od/2+f76_lug_radial+0.6-f76_slot_inner_r,
                  f76_lug_window_w,f76_lug_z1+f76_lock_axial_clear+f76_eps]);
        // Include the entire tangential rectangle at BOTH ends of the turn.
        // Sweeping only the lug center angle (legacy sector) clips its corners.
        f76_sector(a-f76_slot_half_angle,a+f76_lock_deg+f76_slot_half_angle,
            f76_slot_inner_r,f76_slot_outer_r,
            f76_lug_z0-f76_lock_axial_clear,f76_lug_z1+f76_lock_axial_clear);
    }
}
module f76_body() {
    difference() { f76_outer(); f76_bore(); f76_female_groove(); f76_bayonet_cut(); }
}
module f76_core_shell(id) {
    // Same smooth inside/outside contraction, constant 2 mm radial wall.
    // Broad straight 108 mm guide precedes a 40 mm contraction and 12 mm lip.
    rotate_extrude() polygon(concat(
        [[f76_core_inlet_id/2,0],[f76_core_r,0],[f76_core_r,f76_core_mount_l]],
        [for(i=[1:48]) [f76_blend(f76_core_r,id/2+f76_core_wall,i/48),
            f76_core_mount_l+f76_core_taper_l*i/48]],
        [[id/2+f76_core_wall,f76_core_h],[id/2,f76_core_h],
         [id/2,f76_core_mount_l+f76_core_taper_l]],
        [for(i=[47:-1:0]) [f76_blend(f76_core_inlet_id/2,id/2,i/48),
            f76_core_mount_l+f76_core_taper_l*i/48]]));
}
module f76_grip_cuts(id) {
    for(a=[0,180]) rotate([0,0,a])
        translate([id/2+f76_core_wall-f76_grip_flat_depth,-30,f76_core_h-f76_grip_l])
            cube([10,60,f76_grip_l+f76_eps]);
}
module f76_core(id) {
    assert(len(search(id,f76_outlet_ids))>0);
    difference() { union() { f76_core_shell(id); f76_male_ridge(); } f76_grip_cuts(id); }
}
module f76_fan_envelope() {
    // Measured external rectangular lugs occupy r=38..40, never inside r38.
    // The -0.25 overlap below r38 is only a union root in the reference solid.
    union() {
        difference() { cylinder(d=f76_fan_od,h=f76_face_z);
            translate([0,0,-f76_eps]) cylinder(d=f76_fan_id,h=f76_face_z+2*f76_eps); }
        for(a=f76_lug_angles) rotate([0,0,a])
            translate([f76_fan_od/2-0.25,-f76_lug_tangent/2,f76_lug_z0])
                cube([f76_lug_radial+0.25,f76_lug_tangent,f76_lug_axial]);
    }
}
module f76_core_pose(id,z) {
    translate([0,0,z]) rotate([0,0,f76_core_angle(z)]) f76_core(id);
}
module f76_section() { intersection() { children(); translate([-100,0,-1]) cube([200,100,400]); } }
module f76_contract() {
    echo(fan76_contract=[
        ["units","mm"],["body_height",f76_body_h],["body_od",f76_collar_od],
        ["tube_od",f76_tube_od],["spigot_od",f76_spigot_od],["spigot_id",f76_spigot_id],
        ["spigot_z0",f76_spigot_z0],["spigot_length",f76_spigot_l],
        ["core_height",f76_core_h],["core_mount_l",f76_core_mount_l],
        ["core_taper_l",f76_core_taper_l],["core_exit_l",f76_core_exit_l],
        ["outlet_ids",f76_outlet_ids],["pitch",f76_pitch],["travel",f76_travel],
        ["adjust_turns",f76_travel/f76_pitch],["core_min_z",f76_core_min_z],
        ["core_max_z",f76_core_max_z],["straight_handoff_z",f76_straight_handoff_z],
        ["female_z0",f76_female_z0],["female_z1",f76_female_z1],
        ["female_cut_z0",f76_female_cut_z0],["female_cut_z1",f76_female_cut_z1],
        ["guide_z0",f76_guide_z0],["male_z0",f76_male_z0],["male_z1",f76_male_z1],
        ["male_full_z0",f76_male_full_z0],["male_full_z1",f76_male_full_z1],
        ["complete_turns_min",f76_full_turns(f76_core_min_z)],
        ["complete_turns_max",f76_full_turns(f76_core_max_z)],
        ["male_major",f76_male_major],["female_minor",f76_female_minor],
        ["female_major",f76_female_major],["thread_height",f76_thread_h],
        ["crest_width",f76_crest_w],["flank_deg",f76_flank_deg],
        ["root_embed",f76_root_embed],["shoulder_burial",f76_shoulder_burial],
        ["radial_clearance",f76_radial_clear],["axial_clearance",f76_axial_clear],
        ["profile_half",f76_profile_half],["female_min_web",f76_female_web],
        ["male_profile",f76_male_profile()],["female_profile",f76_female_profile()],
        ["protrusion_min",f76_protrusion_min],["protrusion_max",f76_protrusion_max],
        ["socket_id",f76_socket_id],["fan_od",f76_fan_od],["fan_id",f76_fan_id],
        ["face_z",f76_face_z],["lug_z0",f76_lug_z0],["lug_z1",f76_lug_z1],
        ["lock_deg",f76_lock_deg],["slot_roof_z",f76_lug_z1+f76_lock_axial_clear],
        ["slot_floor_z",f76_lug_z0-f76_lock_axial_clear],
        ["slot_outer_r",f76_slot_outer_r],["slot_half_angle",f76_slot_half_angle],
        ["fn",f76_fn],["steps_per_turn",f76_steps_turn]
    ]);
}

if(part=="body") f76_body();
else if(part=="core15") f76_core(15);
else if(part=="core20") f76_core(20);
else if(part=="core25") f76_core(25);
else if(part=="core30") f76_core(30);
else if(part=="review-fan-envelope") f76_fan_envelope();
else if(part=="review-male-ridge") f76_male_ridge();
else if(part=="review-female-groove") f76_female_groove();
else if(part=="body-section") f76_section() f76_body();
else if(part=="core-section") f76_section() f76_core(outlet_id);
else if(part=="assembly-section") {
    color([0.15,0.42,0.65]) f76_section() f76_body();
    color([0.92,0.52,0.12]) f76_section() f76_core_pose(outlet_id,adjust_z);
}
else if(part=="contract") f76_contract();
else assert(false,"Unknown fan76-direct-v1 part");
