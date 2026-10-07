// v4: ONLY "connector" is a printable deliverable. All other selectors are
// review/reference solids. Clean model: NO embedded supports or enforcers.
// Load path: each radial disc -> 1.2 mm fused root -> continuous socket wall
// -> continuous body -> 25 mm tee insertion section. Not a strength rating.
include <fan-tee-v4-parameters.scad>
include <fan-tee-v4-thread.scad>
part="connector";
core_offset=0;
$fn=v4_fn;

module v4_outer() {
    // A single axial polygon avoids coplanar stacked cylinders/edge-only joins.
    rotate_extrude() polygon([
        [0,v4_fan_back_z],[v4_socket_od/2,v4_fan_back_z],
        [v4_body_od/2,v4_fan_back_z+30],
        [v4_body_od/2,v4_tee_z0-4],[v4_tee_od/2,v4_tee_z0],
        [v4_tee_od/2,v4_tee_z1-v4_tip_l],
        [v4_tee_od/2-v4_tip_radial_chamfer,v4_tee_z1],[0,v4_tee_z1]]);
}

module v4_bore() {
    // Fan face allowance and long smooth inlet contraction are preserved.
    // Entry from the tee has no under-size smooth funnel before the groove.
    rotate_extrude() polygon([
        [0,v4_fan_back_z-1],[v4_socket_id/2+0.3,v4_fan_back_z-1],
        [v4_socket_id/2+0.3,v4_fan_back_z],
        [v4_socket_id/2,v4_fan_back_z+1],
        [v4_socket_id/2,v4_fan_face_extra],
        [v4_female_minor/2,v4_air_transition_end],
        [v4_female_minor/2,v4_entry_cone_z0],
        [v4_tee_id/2,v4_tee_z0],
        [v4_tee_id/2,v4_tee_z1-v4_tip_l],
        [v4_tee_id/2-v4_tip_radial_chamfer,v4_tee_z1],
        [v4_tee_id/2-v4_tip_radial_chamfer,v4_tee_z1+1],[0,v4_tee_z1+1]]);
}

module v4_shell() { difference() {v4_outer(); v4_bore(); v4_female_groove();} }
module v4_lugs() {
    for(a=[0,180]) rotate([0,0,a])
        translate([v4_socket_id/2-v4_lug_radial_h,0,v4_lug_z])
        rotate([0,90,0]) cylinder(h=v4_lug_radial_h+v4_lug_embed,d=v4_lug_d,$fn=96);
}
module v4_connector() { union() {v4_shell();v4_lugs();} }

// These modules are verification-only. The existing core is not redesigned
// or included in the one-connector print plate.
module v4_reference_core(id=36) {
    difference() {
        union() {cylinder(h=v4_core_l,d=v4_core_od);v4_reference_male_ridge();}
        rotate_extrude() polygon([[0,-1],[v4_core_inlet_id/2,-1],
            [v4_core_inlet_id/2,v4_core_mount_l],
            [id/2,v4_core_mount_l+v4_core_taper_l],[id/2,v4_core_l+1],[0,v4_core_l+1]]);
    }
}
module v4_installed_reference() {
    translate([0,0,v4_core_seated_z+core_offset])
        rotate([0,0,360*core_offset/v4_pitch]) v4_reference_core();
}
module v4_half() { translate([-60,0,-20]) cube([120,60,140]); }

if(part=="connector") v4_connector();
else if(part=="review-shell") v4_shell();
else if(part=="review-lugs") v4_lugs();
else if(part=="review-root-intersection") intersection() {v4_shell();v4_lugs();}
else if(part=="review-female-groove") v4_female_groove();
else if(part=="reference-core36") v4_reference_core();
else if(part=="connector-section") intersection(){v4_connector();v4_half();}
else if(part=="section") {
    color("SteelBlue") intersection(){v4_connector();v4_half();}
    color("Orange") intersection(){v4_installed_reference();v4_half();}
}
else if(part=="contract") echo(v4_parameters=[
    ["tee_measured_id",v4_tee_measured_id],["tee_radial_clearance",v4_tee_radial_clearance],
    ["tee_od",v4_tee_od],["tee_id",v4_tee_id],["wall",v4_wall],
    ["tee_z0",v4_tee_z0],["tee_z1",v4_tee_z1],
    ["tip_l",v4_tip_l],["tip_radial_chamfer",v4_tip_radial_chamfer],
    ["body_od",v4_body_od],["socket_id",v4_socket_id],["socket_od",v4_socket_od],
    ["fan_od",v4_fan_od],["fan_back_z",v4_fan_back_z],
    ["fan_radial_clearance",v4_fan_radial_clearance],["fan_face_extra",v4_fan_face_extra],
    ["air_transition_end",v4_air_transition_end],
    ["lug_d",v4_lug_d],["lug_radial_h",v4_lug_radial_h],
    ["lug_embed",v4_lug_embed],["lug_z",v4_lug_z],
    ["slot_axial_width",v4_slot_axial_width],["slot_turn_width",v4_slot_turn_width],
    ["core_od",v4_core_od],["core_l",v4_core_l],["core_inlet_id",v4_core_inlet_id],
    ["pitch",v4_pitch],["thread_h",v4_thread_h],["male_major",v4_male_major],
    ["root_w",v4_root_w],["crest_w",v4_crest_w],["root_embed",v4_root_embed],
    ["radial_clearance",v4_radial_clearance],["axial_clearance",v4_axial_clearance],
    ["female_minor",v4_female_minor],["female_major",v4_female_major],
    ["male_z0",v4_male_z0],["male_z1",v4_male_z1],
    ["female_z0",v4_female_z0],["female_z1",v4_female_z1],
    ["core_seated_z",v4_core_seated_z],["entry_cone_z0",v4_entry_cone_z0],
    ["phase",v4_phase],["roof_angle_horizontal",v4_roof_angle_horizontal],
    ["groove_r0",v4_groove_r0],["groove_r1",v4_groove_r1],
    ["groove_top_outer",v4_groove_top_outer],["groove_top_root",v4_groove_top_root],
    ["female_tip_web",v4_female_tip_web],
    ["steps_per_turn",v4_steps_per_turn],["fn",v4_fn],
    ["female_profile",v4_female_profile()],["male_profile",v4_reference_male_profile()]
]);
else assert(false,"Unknown selector; only connector is the print target");
