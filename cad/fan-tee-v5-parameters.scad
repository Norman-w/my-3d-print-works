// v5 / mm / FDM PETG X1C 0.4. Five print targets: mother + 15/20/25/30 cores.
// Air +Z; fan inserts +Z from below; cores insert/rotate -Z from the Y end.
// No screws, lock rings, added stops or embedded support solids.
v5_fan_back_z = -18.5;
v5_fan_od = 41;
v5_fan_radial_clearance = 0.6;
v5_socket_id = 42.2;
v5_socket_od = 48;
v5_body_od = 50;
v5_fan_face_extra = 3;
v5_air_transition_end = 27;
v5_lug_d = 6;
v5_lug_radial_h = 3.4;
v5_lug_embed = 1.2;
v5_lug_z = -7.5;
v5_slot_axial_width = 7;
v5_slot_turn_width = 6.5;

// Preserve the physical tee mating envelope. Only its axial location changes.
v5_tee_measured_id = 50.2;
v5_tee_od = 50;
v5_tee_id = 44;
v5_tee_wall = 3;
v5_tee_l = 25;
v5_tee_z0 = 103;
v5_tee_z1 = v5_tee_z0+v5_tee_l; // 128
v5_tip_l = 0.8;
v5_tip_radial_chamfer = 0.35;

// Shared nozzle: stable straight mounting/guide section, then matching
// inner/outer conical slopes, then a straight exit. Same total/exit datum.
v5_core_od = 40;
v5_core_wall = 2;
v5_core_inlet_id = v5_core_od-2*v5_core_wall; // 36
v5_core_mount_l = 46;
v5_core_taper_l = 44;
v5_core_exit_l = 16;
v5_core_l = v5_core_mount_l+v5_core_taper_l+v5_core_exit_l; // 106
v5_outlet_ids = [15,20,25,30];

// Outward ridge with a finite flat crest. The exposed flank is 50 degrees
// to horizontal. Extend the fused root BELOW the core skin independently,
// instead of pulling the visible flank down when embedding it.
v5_pitch = 4;
v5_thread_h = 0.9;
v5_crest_w = 0.8;
v5_flank_angle_horizontal = 50;
v5_root_embed = 0.20;
v5_shoulder_burial = 0.05; // buried beyond cylinder faceting error
v5_core_r = v5_core_od/2;
v5_male_major = v5_core_od+2*v5_thread_h;
v5_root_half_at_surface = v5_crest_w/2+v5_thread_h*tan(v5_flank_angle_horizontal);
v5_profile_half = v5_crest_w/2+(v5_thread_h+v5_shoulder_burial)*tan(v5_flank_angle_horizontal);
v5_radial_clearance = 0.25;
v5_axial_clearance = 0.20; // per axial flank
v5_female_minor = 40.6;
v5_female_major = v5_male_major+2*v5_radial_clearance; // 42.3
v5_female_tip_web = v5_pitch-2*(v5_crest_w/2+v5_axial_clearance
    +(v5_female_major/2-v5_female_minor/2)*tan(v5_flank_angle_horizontal));

v5_male_z0 = 4;
v5_male_z1 = 28;
v5_runout_l = 1.5;
v5_runout_bury = 0.06;
v5_female_z0 = 38;
v5_female_z1 = 102;
v5_entry_cone_z0 = 100;
v5_phase = 0;
v5_core_seated_z = v5_female_z0-v5_male_z0; // 34
v5_work_travel = 40; // TEN TURNS; never confuse this with mother thread length
v5_core_extended_z = v5_core_seated_z+v5_work_travel; // 74
v5_exit_protrusion_min = v5_core_seated_z+v5_core_l-v5_tee_z1; // 12
v5_exit_protrusion_max = v5_exit_protrusion_min+v5_work_travel; // 52
v5_fn = 192;
v5_steps_per_turn = 128;

assert(v5_work_travel>=40 && v5_work_travel/v5_pitch==10);
assert(v5_tee_od==50 && v5_tee_id==44 && v5_tee_l==25);
assert(v5_core_l==106 && v5_exit_protrusion_min>=12);
assert(v5_male_z1+2<=v5_core_mount_l);
assert(v5_root_embed>v5_shoulder_burial);
assert(2*(v5_profile_half+v5_axial_clearance)<v5_pitch);
assert(v5_female_tip_web>=0.75);
assert((v5_body_od-v5_female_major)/2>=3);
assert(v5_female_minor>v5_core_od && v5_female_minor<v5_male_major);
assert(v5_tee_id-2*v5_tip_radial_chamfer>v5_female_major);
assert(v5_female_z1<v5_tee_z0 && v5_entry_cone_z0<v5_female_z1);
assert(v5_lug_d+0.5<=min(v5_slot_axial_width,v5_slot_turn_width));
