// v5 matched set. All five STL targets are clean solids without supports.
// Print Z-up, fan end down on mother; large inlet down on every nozzle.
include <fan-tee-v5-parameters.scad>
include <fan-tee-v5-thread.scad>
part="mother";
core_id=15;
core_offset=0;
$fn=v5_fn;

module v5_outer() {
    rotate_extrude() polygon([
        [0,v5_fan_back_z],[v5_socket_od/2,v5_fan_back_z],
        [v5_body_od/2,v5_fan_back_z+30],
        [v5_body_od/2,v5_tee_z0],[v5_tee_od/2,v5_tee_z1-v5_tip_l],
        [v5_tee_od/2-v5_tip_radial_chamfer,v5_tee_z1],[0,v5_tee_z1]]);
}
module v5_bore() {
    rotate_extrude() polygon([
        [0,v5_fan_back_z-1],[v5_socket_id/2+0.3,v5_fan_back_z-1],
        [v5_socket_id/2+0.3,v5_fan_back_z],
        [v5_socket_id/2,v5_fan_back_z+1],[v5_socket_id/2,v5_fan_face_extra],
        [v5_female_minor/2,v5_air_transition_end],
        [v5_female_minor/2,v5_entry_cone_z0],[v5_tee_id/2,v5_tee_z0],
        [v5_tee_id/2,v5_tee_z1-v5_tip_l],
        [v5_tee_id/2-v5_tip_radial_chamfer,v5_tee_z1],
        [v5_tee_id/2-v5_tip_radial_chamfer,v5_tee_z1+1],[0,v5_tee_z1+1]]);
}
module v5_shell() { difference() {v5_outer();v5_bore();v5_female_groove();} }
module v5_lugs() {
    for(a=[0,180]) rotate([0,0,a])
        translate([v5_socket_id/2-v5_lug_radial_h,0,v5_lug_z])
        rotate([0,90,0]) cylinder(h=v5_lug_radial_h+v5_lug_embed,d=v5_lug_d,$fn=96);
}
module v5_mother() { union() {v5_shell();v5_lugs();} }

module v5_core_body(id) {
    assert(id>=15 && id<=30);
    rotate_extrude() polygon([
        [v5_core_inlet_id/2,0],[v5_core_od/2,0],
        [v5_core_od/2,v5_core_mount_l],
        [id/2+v5_core_wall,v5_core_mount_l+v5_core_taper_l],
        [id/2+v5_core_wall,v5_core_l],[id/2,v5_core_l],
        [id/2,v5_core_mount_l+v5_core_taper_l],
        [v5_core_inlet_id/2,v5_core_mount_l]]);
}
module v5_core(id) { union() {v5_core_body(id);v5_male_ridge();} }
module v5_installed_core(id=core_id,offset=core_offset) {
    assert(offset>=0 && offset<=v5_work_travel);
    translate([0,0,v5_core_seated_z+offset])
        rotate([0,0,360*offset/v5_pitch]) v5_core(id);
}
module v5_half() { translate([-60,0,-20]) cube([120,60,230]); }

if(part=="mother") v5_mother();
else if(part=="nozzle15") v5_core(15);
else if(part=="nozzle20") v5_core(20);
else if(part=="nozzle25") v5_core(25);
else if(part=="nozzle30") v5_core(30);
else if(part=="review-lugs") v5_lugs();
else if(part=="review-shell") v5_shell();
else if(part=="review-lug-roots") intersection() {v5_shell();v5_lugs();}
else if(part=="review-male-ridge") v5_male_ridge();
else if(part=="review-female-groove") v5_female_groove();
else if(part=="mother-section") intersection(){v5_mother();v5_half();}
else if(part=="core-section") intersection(){v5_core(core_id);v5_half();}
else if(part=="assembly-section") {
    color("SteelBlue") intersection(){v5_mother();v5_half();}
    color("Orange") intersection(){v5_installed_core();v5_half();}
}
else if(part=="contract") echo(v5_parameters=[
    ["fan_back_z",v5_fan_back_z],["fan_od",v5_fan_od],
    ["socket_id",v5_socket_id],["socket_od",v5_socket_od],["body_od",v5_body_od],
    ["fan_face_extra",v5_fan_face_extra],["air_transition_end",v5_air_transition_end],
    ["fan_radial_clearance",v5_fan_radial_clearance],
    ["lug_d",v5_lug_d],["lug_radial_h",v5_lug_radial_h],
    ["lug_embed",v5_lug_embed],["lug_z",v5_lug_z],
    ["tee_od",v5_tee_od],["tee_id",v5_tee_id],["tee_wall",v5_tee_wall],
    ["tee_z0",v5_tee_z0],["tee_z1",v5_tee_z1],["tee_l",v5_tee_l],
    ["tip_l",v5_tip_l],["tip_radial_chamfer",v5_tip_radial_chamfer],
    ["core_od",v5_core_od],["core_wall",v5_core_wall],["core_inlet_id",v5_core_inlet_id],
    ["core_mount_l",v5_core_mount_l],["core_taper_l",v5_core_taper_l],
    ["core_exit_l",v5_core_exit_l],["core_l",v5_core_l],["outlet_ids",v5_outlet_ids],
    ["pitch",v5_pitch],["thread_h",v5_thread_h],["crest_w",v5_crest_w],
    ["flank_angle_horizontal",v5_flank_angle_horizontal],["root_embed",v5_root_embed],
    ["shoulder_burial",v5_shoulder_burial],["profile_half",v5_profile_half],
    ["root_half_at_surface",v5_root_half_at_surface],
    ["male_major",v5_male_major],["female_minor",v5_female_minor],["female_major",v5_female_major],
    ["radial_clearance",v5_radial_clearance],["axial_clearance",v5_axial_clearance],
    ["female_tip_web",v5_female_tip_web],
    ["male_z0",v5_male_z0],["male_z1",v5_male_z1],["runout_l",v5_runout_l],
    ["runout_bury",v5_runout_bury],["female_z0",v5_female_z0],["female_z1",v5_female_z1],
    ["entry_cone_z0",v5_entry_cone_z0],["phase",v5_phase],
    ["core_seated_z",v5_core_seated_z],["core_extended_z",v5_core_extended_z],
    ["work_travel",v5_work_travel],["exit_protrusion_min",v5_exit_protrusion_min],
    ["exit_protrusion_max",v5_exit_protrusion_max],
    ["fn",v5_fn],["steps_per_turn",v5_steps_per_turn],
    ["male_profile",v5_male_profile()],["female_profile",v5_female_profile()]
]);
else assert(false,"Unknown v5 part selector");
