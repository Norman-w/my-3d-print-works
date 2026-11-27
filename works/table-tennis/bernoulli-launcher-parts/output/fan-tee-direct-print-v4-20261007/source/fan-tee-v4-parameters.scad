// v4 mechanical contract, millimetres. Air +Z; fan enters from -Z;
// existing outward-ridge nozzle core enters from +Z toward -Z.
// FDM / X1C / PETG candidate. Only the outer connector is a print target.
// The measured tee bore is approximate; shrinkage, ovality and slot depth
// remain physical first-article gates, not digitally verified dimensions.
v4_tee_measured_id = 50.2;
v4_tee_radial_clearance = 0.10;
v4_wall = 3;
v4_tee_od = v4_tee_measured_id - 2*v4_tee_radial_clearance; // exactly 50
v4_tee_id = v4_tee_od - 2*v4_wall; // 44
v4_tee_z0 = 55;
v4_tee_z1 = 80;
v4_tip_l = 0.8;
v4_tip_radial_chamfer = 0.35;
v4_body_od = 50;
v4_fan_od = 41;
v4_fan_radial_clearance = 0.60;
v4_socket_id = v4_fan_od + 2*v4_fan_radial_clearance;
v4_socket_od = 48;
v4_fan_back_z = -18.5;
v4_fan_face_extra = 3; // retained provisional face allowance, not a measured stop
v4_air_transition_end = 27;
v4_slot_axial_width = 7;
v4_slot_turn_width = 6.5;
v4_slot_side_clearance = 0.25;
v4_lug_d = 6; // do NOT enlarge the disc diameter to increase radial capture
v4_lug_radial_h = 3.4; // 2.4 + 1, inward projection from socket bore
v4_lug_embed = 1.2; // root fusion stays unchanged
v4_lug_z = -7.5; // -7 - 0.5, toward fan / -Z

// Existing core interface: unchanged dimensions and anchored screw lead.
// This profile is retained for compatibility checks, NOT as a new print job.
v4_core_od = 40;
v4_core_l = 45;
v4_core_inlet_id = 38;
v4_core_mount_l = 22;
v4_core_taper_l = 15;
v4_pitch = 4;
v4_thread_h = 0.9;
v4_male_major = v4_core_od + 2*v4_thread_h;
v4_root_w = 2.88;
v4_crest_w = 1.12;
v4_root_embed = 0.2;
v4_radial_clearance = 0.25;
v4_axial_clearance = 0.20;
v4_female_minor = 40.6;
v4_female_major = v4_male_major + 2*v4_radial_clearance;
v4_male_z0 = 4;
v4_male_z1 = 20;
v4_female_z0 = 38;
v4_female_z1 = 54;
v4_core_seated_z = v4_female_z0-v4_male_z0;
v4_entry_cone_z0 = 52;
v4_phase = 0;

// Female-only roof relief: the original male and the lower groove flank
// stay intact. Raise the groove roof near the minor bore so the remaining
// female down-facing flank is 50 deg to horizontal in axial section.
// This ONLY removes material from the old groove envelope; compatibility
// and remaining ridge width must still pass final-mesh tests.
v4_roof_angle_horizontal = 50;
v4_groove_r0 = v4_core_od/2-v4_root_embed+v4_radial_clearance;
v4_groove_r1 = v4_female_major/2;
v4_groove_top_outer = v4_crest_w/2+v4_axial_clearance;
v4_groove_top_root = v4_groove_top_outer
    +(v4_groove_r1-v4_groove_r0)*tan(v4_roof_angle_horizontal);
v4_groove_top_at_minor = v4_groove_top_outer
    +(v4_groove_r1-v4_female_minor/2)*tan(v4_roof_angle_horizontal);
v4_old_flank_slope = (v4_root_w-v4_crest_w)/2
    /(v4_thread_h+v4_root_embed);
v4_groove_bottom_depth_at_minor = v4_root_w/2+v4_axial_clearance
    -(v4_female_minor/2-v4_groove_r0)*v4_old_flank_slope;
v4_female_tip_web = v4_pitch-v4_groove_top_at_minor
    -v4_groove_bottom_depth_at_minor;
v4_steps_per_turn = 128;
v4_fn = 192;
v4_eps = 0.01;

assert(abs(v4_tee_od-50)<1e-8 && v4_tee_id==44);
assert(v4_wall==3 && v4_tip_l<0.05*(v4_tee_z1-v4_tee_z0));
assert(v4_tee_od<=v4_body_od && v4_tee_id>v4_female_major);
assert(v4_socket_od-v4_socket_id>=4);
assert(v4_fan_face_extra>=2 && v4_air_transition_end-v4_fan_face_extra>=20);
assert(v4_lug_d+2*v4_slot_side_clearance<=min(v4_slot_axial_width,v4_slot_turn_width));
assert(v4_lug_embed>=1 && v4_lug_embed<(v4_socket_od-v4_socket_id)/2);
assert(v4_lug_radial_h>v4_fan_radial_clearance && v4_lug_d==6);
assert(v4_female_minor>v4_core_od && v4_female_minor<v4_male_major);
assert((v4_body_od-v4_female_major)/2>=v4_wall);
assert(v4_female_z1<v4_tee_z0 && v4_root_w+2*v4_axial_clearance<v4_pitch);
assert(tan(v4_roof_angle_horizontal)>v4_old_flank_slope);
assert(v4_groove_top_root+v4_root_w/2+v4_axial_clearance<v4_pitch);
assert(v4_female_tip_web>=0.70, "Female ridge too thin: do not hide this by enlarging the bore");
