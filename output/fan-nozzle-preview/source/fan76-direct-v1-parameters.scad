// FAN76 DIRECT v1 / mm. FDM, upright +Z, X1C 256 bed.
// Material is a PETG candidate, not a sliced or physically accepted process.
// Air +Z. Fan enters +Z from z=0; cartridge enters -Z from z=222.
// Mechanical load: core tooth -> mother tooth -> continuous tube -> collar
// -> two EXTERNAL rectangular fan lugs. No locking screw/ring or support solids.
f76_eps = 0.025;
f76_fn = 192;
f76_steps_turn = 128;
f76_fan_od = 76;
f76_fan_id = 71;
f76_socket_id = 76.6;
f76_collar_od = 86;
f76_collar_h = 30;
f76_face_z = 24;
f76_entry_chamfer = 1.2;
f76_lug_axial = 8;
f76_lug_tangent = 7.5;
f76_lug_radial = 2;
f76_lug_from_face = 3;
f76_lug_angles = [90,270];
f76_lug_z0 = f76_face_z-f76_lug_from_face-f76_lug_axial; // 13
f76_lug_z1 = f76_face_z-f76_lug_from_face; // 21
f76_lug_window_w = f76_lug_tangent+0.8;
f76_lock_deg = 18;
f76_lock_axial_clear = 0.5;
f76_lock_radial_clear = 0.8;
f76_slot_inner_r = f76_socket_id/2-0.65;
f76_slot_outer_r = f76_socket_id/2+f76_lug_radial+f76_lock_radial_clear;
f76_slot_half_angle = atan((f76_lug_window_w/2)/f76_slot_inner_r);

f76_body_h = 222;
f76_tube_od = 54;
f76_outer_taper_z0 = 30;
f76_outer_taper_z1 = 70;
f76_y_measured_id = 50.2; // Approximate measured value, no physical-fit claim.
f76_spigot_od = 50;
f76_spigot_id = 44;
f76_spigot_l = 25;
f76_spigot_z0 = f76_body_h-f76_spigot_l; // 197
f76_spigot_chamfer_l = 0.8;
f76_spigot_chamfer_r = 0.35; // Only the last 0.8 mm; not a full-length taper.

// Paired flat-topped outward ridge: same profile intent as independent Ø41 v5.
// The six-point root embeds independently; the exposed 50 degree flank does
// NOT become shallower when root_embed is increased.
f76_pitch = 4;
f76_thread_h = 0.9;
f76_crest_w = 0.8;
f76_flank_deg = 50; // To horizontal, +Z print orientation.
f76_root_embed = 0.20;
f76_shoulder_burial = 0.05;
f76_runout_bury = 0.06;
f76_radial_clear = 0.25;
f76_axial_clear = 0.20; // Each flank.
f76_core_od = 40;
f76_core_r = f76_core_od/2;
f76_male_major = f76_core_od+2*f76_thread_h; // 41.8
f76_female_minor = 40.6;
f76_female_major = f76_male_major+2*f76_radial_clear; // 42.3
f76_profile_half = f76_crest_w/2+
    (f76_thread_h+f76_shoulder_burial)*tan(f76_flank_deg);
f76_female_web = f76_pitch-2*(f76_crest_w/2+f76_axial_clear+
    (f76_female_major/2-f76_female_minor/2)*tan(f76_flank_deg));

f76_female_z0 = 70;
f76_female_z1 = 182; // Fully developed mother thread, 112 mm.
f76_female_cut_z0 = 66; // Extended into the open inlet transition.
f76_female_cut_z1 = 186; // Extended beyond the outlet guide bevel.
f76_guide_z0 = 184; // ID44 all the way to z=222.
f76_male_z0 = 4;
f76_male_z1 = 28;
f76_runout_l = 2;
f76_male_full_z0 = f76_male_z0+f76_runout_l; // 6
f76_male_full_z1 = f76_male_z1-f76_runout_l; // 26
f76_core_min_z = 70;
f76_travel = 80;
f76_core_max_z = f76_core_min_z+f76_travel; // 150
f76_straight_handoff_z = f76_guide_z0-f76_male_z0; // 180

f76_core_wall = 2;
f76_core_inlet_id = f76_core_od-2*f76_core_wall; // 36
f76_core_mount_l = 108;
f76_core_taper_l = 40;
f76_core_exit_l = 12;
f76_core_h = f76_core_mount_l+f76_core_taper_l+f76_core_exit_l; // 160
f76_outlet_ids = [15,20,25,30];
f76_grip_l = 8;
f76_grip_flat_depth = 0.5; // Two shallow external flats, no airflow crossbar.
f76_protrusion_min = f76_core_min_z+f76_core_h-f76_body_h; // 8
f76_protrusion_max = f76_protrusion_min+f76_travel; // 88

function f76_smooth(t) = t*t*(3-2*t);
function f76_blend(a,b,t) = a+(b-a)*f76_smooth(t);
function f76_core_angle(z) = 360*(z+f76_male_z0-f76_female_z0)/f76_pitch;
function f76_full_turns(z) = floor((
    min(z+f76_male_full_z1,f76_female_z1)-
    max(z+f76_male_full_z0,f76_female_z0)-2*f76_profile_half)/f76_pitch);

assert(f76_pitch==4 && f76_travel==80 && f76_travel/f76_pitch==20);
assert(f76_body_h<=245 && f76_core_h<=245);
assert(f76_spigot_od==50 && f76_spigot_id==44 && f76_spigot_l==25);
assert(f76_protrusion_min>=8);
assert(f76_full_turns(f76_core_min_z)>=3 && f76_full_turns(f76_core_max_z)>=3);
assert(f76_root_embed>f76_shoulder_burial);
assert(2*(f76_profile_half+f76_axial_clear)<f76_pitch);
assert(f76_female_web>=0.75);
assert(f76_female_minor>f76_core_od && f76_female_minor<f76_male_major);
assert(f76_spigot_id>f76_female_major);
assert((f76_tube_od-f76_female_major)/2>=3);
assert(f76_collar_od/2-f76_slot_outer_r>=1.89);
