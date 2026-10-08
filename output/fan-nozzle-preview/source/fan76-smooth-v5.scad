// Ø76 v5 / mm / X1C PETG candidate / print fan socket down, air +Z.
// C3 contraction with smoothed curvature ramps; thinner non-mating wall.
// Radial wall minimum is nominal 2.0mm, not a tested strength/airtightness claim.
// Fan enters +Z from z0. Unchanged Ø41 v5 cores enter/rotate -Z from Y end.
// Load: original v5 male tooth -> paired female groove -> shell -> bayonet roof.
// One continuous shell, no embedded supports or extra locking components.
// Flow-guide type is still pending; this is the smooth-shell candidate, not CFD.
include <fan-tee-v5-parameters.scad>
include <fan-tee-v5-thread.scad>

part="body";
$fn=192;
s5_eps=0.025;
s5_socket_id=76;
// Circumscribed bore: minimum across flats ID76; no added fit allowance.
s5_socket_r=s5_socket_id/2/cos(180/$fn);
s5_fan_face=24;
s5_blend_z0=26;
s5_blend_length=124;
s5_blend_z1=s5_blend_z0+s5_blend_length;
s5_body_h=248;
s5_collar_od=86;
s5_tube_od=50;
s5_spigot_od=50;
s5_spigot_id=44;
s5_spigot_l=25;
s5_spigot_z0=s5_body_h-s5_spigot_l;
s5_female_z0=s5_blend_z1;
s5_travel=20;
s5_female_z1=s5_female_z0+(v5_male_z1-v5_male_z0)+s5_travel;
s5_female_cut_z0=s5_female_z0-4;
s5_female_cut_z1=s5_female_z1+4;
s5_entry_z0=s5_female_z1-2;
s5_guide_z0=s5_female_z1+2;
s5_core_min_z=s5_female_z0-v5_male_z0;
s5_core_max_z=s5_core_min_z+s5_travel;
s5_straight_handoff_z=s5_guide_z0-v5_male_z0;
s5_lug_angles=[90,270];
s5_slot_inner_r=37.35;
s5_slot_outer_r=40.8;
s5_window_w=8.3;
s5_slot_half_angle=atan((s5_window_w/2)/s5_slot_inner_r);
s5_lock_deg=18;
s5_ramp=34/s5_blend_length;
s5_curvature_ramp=0.15;
s5_thin_wall=2.0;
s5_thread_root_wall=2.4;
s5_guide_wall=2.0;
s5_wall_fade_length=60;
s5_wall_rise_z0=104;
s5_wall_rise_length=36;
s5_thread_shell_r=v5_female_major/2+s5_thread_root_wall;
s5_guide_r=s5_spigot_id/2+s5_guide_wall;

function s5_clamp(t)=max(0,min(1,t));
function s5_smooth(t)=let(u=s5_clamp(t)) u*u*u*(10+u*(-15+6*u));
// Twice-integrated curvature ramp: C3 at every contraction join.
// 34mm slope-up + 56mm uniform contraction + 34mm slope-down.
// Curvature is eased over the first/last 15% of each 34mm ramp.
function s5_ramp_integral(u,b=s5_curvature_ramp)=u<b
    ? let(v=u/b) b*b*(v*v*v*v/4-v*v*v*v*v/10)/(1-b)
    : u>1-b ? u-0.5+s5_ramp_integral(1-u,b)
    : (u*u/2-b*u/2+3*b*b/20)/(1-b);
function s5_progress(t,a=s5_ramp)=t<a
    ? a*s5_ramp_integral(t/a)/(1-a)
    : t>1-a ? 1-s5_progress(1-t,a) : (t-a/2)/(1-a);
function s5_contraction_r(z)=s5_socket_r+
    (v5_female_minor/2-s5_socket_r)*s5_progress(s5_clamp((z-s5_blend_z0)/s5_blend_length));
function s5_wall(z)=s5_thin_wall
    +(s5_collar_od/2-s5_socket_r-s5_thin_wall)*(1-s5_progress(s5_clamp((z-s5_blend_z0)/s5_wall_fade_length),0.3))
    +(s5_thread_shell_r-v5_female_minor/2-s5_thin_wall)*s5_progress(s5_clamp((z-s5_wall_rise_z0)/s5_wall_rise_length),0.3);
function s5_bore_r(z)=z<1.2 ? s5_socket_r+1.2*(1.2-z)/(1.2+s5_eps)
    : z<=s5_blend_z0 ? s5_socket_r
    : z<=s5_blend_z1 ? s5_contraction_r(z)
    : z<=s5_entry_z0 ? v5_female_minor/2
    : z<s5_guide_z0 ? v5_female_minor/2+
        (s5_spigot_id-v5_female_minor)/2*(z-s5_entry_z0)/(s5_guide_z0-s5_entry_z0)
    : z<=s5_body_h-v5_tip_l ? s5_spigot_id/2
    : s5_spigot_id/2-v5_tip_radial_chamfer*(z-(s5_body_h-v5_tip_l))/v5_tip_l;
function s5_outer_r(z)=z<=s5_blend_z0 ? s5_collar_od/2
    : z<=s5_blend_z1 ? s5_contraction_r(z)+s5_wall(z)
    : z<=s5_guide_z0 ? s5_thread_shell_r+
        (s5_guide_r-s5_thread_shell_r)*s5_smooth((z-(s5_guide_z0-18))/18)
    : z<=s5_spigot_z0 ? s5_guide_r+
        (s5_spigot_od/2-s5_guide_r)*s5_smooth((z-(s5_spigot_z0-16))/16)
    : z<=s5_body_h-v5_tip_l ? s5_spigot_od/2
    : s5_spigot_od/2-v5_tip_radial_chamfer*(z-(s5_body_h-v5_tip_l))/v5_tip_l;
function s5_angle(z)=360*(z+v5_male_z0-s5_female_z0)/v5_pitch;
function s5_turns(z)=floor((min(z+v5_male_z1-v5_runout_l,s5_entry_z0)
    -max(z+v5_male_z0+v5_runout_l,s5_female_z0)-2*v5_profile_half)/v5_pitch);

assert(s5_socket_id==76 && s5_spigot_od==50);
assert(s5_female_z1-s5_female_z0==44 && s5_travel==20 && v5_pitch==4);
assert(s5_turns(s5_core_min_z)>=4 && s5_turns(s5_core_max_z)>=4);
assert(s5_thread_shell_r-v5_female_major/2>=2.39999);
assert(s5_spigot_id-2*v5_tip_radial_chamfer>v5_male_major);
assert(s5_guide_z0<s5_spigot_z0-16);
assert(s5_core_min_z+v5_core_l-s5_body_h==4);
assert(s5_core_max_z+v5_core_l-s5_body_h==24);
// Local frozen X1C preset has 250mm printable height; reserve 2mm.
assert(s5_body_h<=248);
for(z=[26:0.25:s5_body_h])
    assert(s5_outer_r(z)-s5_bore_r(z)>=s5_thin_wall-0.00001);

module s5_outer() {
    rotate_extrude() polygon(concat([[0,0]],
        [for(z=[0:0.5:s5_body_h-v5_tip_l]) [s5_outer_r(z),z]],
        [[s5_outer_r(s5_body_h-v5_tip_l),s5_body_h-v5_tip_l],
         [s5_outer_r(s5_body_h),s5_body_h],[0,s5_body_h]]));
}
module s5_bore() {
    rotate_extrude() polygon(concat(
        [[0,-s5_eps],[s5_socket_r+1.2,-s5_eps],
         [s5_socket_r,1.2],[s5_socket_r,s5_blend_z0]],
        [for(i=[1:240]) [s5_contraction_r(s5_blend_z0+s5_blend_length*i/240),
            s5_blend_z0+s5_blend_length*i/240]],
        [[v5_female_minor/2,s5_entry_z0],[s5_spigot_id/2,s5_guide_z0],
         [s5_spigot_id/2,s5_body_h-v5_tip_l],
         [s5_spigot_id/2-v5_tip_radial_chamfer,s5_body_h],
         [s5_spigot_id/2-v5_tip_radial_chamfer,s5_body_h+s5_eps],
         [0,s5_body_h+s5_eps]]));
}
module s5_profile_samples() {
    echo(fan76_profile_samples=[for(z=[0:0.25:s5_body_h])
        [z,s5_bore_r(z),s5_outer_r(z)]]);
}
module s5_female_groove() {
    // Original paired v5 r-z tooth/groove, P4 and clearances are unchanged.
    v5_profile_helix(s5_female_cut_z0,s5_female_cut_z1,s5_female_z0,
        v5_pitch,v5_female_profile(),v5_phase,v5_steps_per_turn);
}
module s5_sector(a0,a1,r0,r1,z0,z1) {
    translate([0,0,z0]) linear_extrude(height=z1-z0)
        polygon(concat([for(i=[0:64]) [r0*cos(a0+(a1-a0)*i/64),r0*sin(a0+(a1-a0)*i/64)]],
                       [for(i=[64:-1:0]) [r1*cos(a0+(a1-a0)*i/64),r1*sin(a0+(a1-a0)*i/64)]]));
}
module s5_bayonet_cut() {
    for(a=s5_lug_angles) {
        rotate([0,0,a]) translate([s5_slot_inner_r,-s5_window_w/2,-s5_eps])
            cube([40.6-s5_slot_inner_r,s5_window_w,21.5+s5_eps]);
        s5_sector(a-s5_slot_half_angle,a+s5_lock_deg+s5_slot_half_angle,
                  s5_slot_inner_r,s5_slot_outer_r,12.5,21.5);
    }
}
module s5_body() { difference() {s5_outer();s5_bore();s5_female_groove();s5_bayonet_cut();} }
module s5_fan_reference() {
    union() {
        difference() {cylinder(d=76,h=s5_fan_face);
            translate([0,0,-s5_eps]) cylinder(d=71,h=s5_fan_face+2*s5_eps);}
        for(a=s5_lug_angles) rotate([0,0,a]) translate([37.75,-3.75,13]) cube([2.25,7.5,8]);
    }
}
module s5_section() {intersection(){children();translate([-100,0,-1]) cube([200,100,350]);}}
module s5_contract() {
    echo(fan76_smooth_contract=[
        ["units","mm"],["body_height",s5_body_h],["body_od",s5_collar_od],
        ["tube_od",s5_tube_od],["spigot_od",s5_spigot_od],["spigot_id",s5_spigot_id],
        ["spigot_z0",s5_spigot_z0],["spigot_length",s5_spigot_l],
        ["socket_id",s5_socket_id],["socket_polygon_circumdiameter",2*s5_socket_r],
        ["fan_od",76],["fan_id",71],["face_z",s5_fan_face],
        ["blend_z0",s5_blend_z0],["blend_z1",s5_blend_z1],["blend_length",s5_blend_length],
        ["blend_polynomial","C3 twice-integrated eased curvature / constant slope / mirrored ramp"],
        ["curve_ramp_fraction",s5_ramp],["curve_curvature_ramp_fraction",s5_curvature_ramp],
        ["thin_wall_radial_nominal",s5_thin_wall],["thread_root_wall",s5_thread_root_wall],
        ["guide_wall",s5_guide_wall],["wall_fade_length",s5_wall_fade_length],
        ["wall_rise_z0",s5_wall_rise_z0],["wall_rise_length",s5_wall_rise_length],
        ["thread_shell_od",2*s5_thread_shell_r],["guide_od",2*s5_guide_r],
        ["peak_inner_wall_angle_to_axis_deg",atan((s5_socket_r-v5_female_minor/2)/(s5_blend_length*(1-s5_ramp)))],
        ["design_height_budget",248],["slicer_height_limit",250],
        ["female_z0",s5_female_z0],["female_z1",s5_female_z1],
        ["female_length",s5_female_z1-s5_female_z0],
        ["female_cut_z0",s5_female_cut_z0],["female_cut_z1",s5_female_cut_z1],
        ["entry_z0",s5_entry_z0],["guide_z0",s5_guide_z0],
        ["straight_handoff_z",s5_straight_handoff_z],
        ["core_min_z",s5_core_min_z],["core_max_z",s5_core_max_z],
        ["travel",s5_travel],["pitch",v5_pitch],["core_height",v5_core_l],
        ["male_z0",v5_male_z0],["male_z1",v5_male_z1],
        ["complete_turns_min",s5_turns(s5_core_min_z)],
        ["complete_turns_max",s5_turns(s5_core_max_z)],
        ["male_major",v5_male_major],["female_minor",v5_female_minor],["female_major",v5_female_major],
        ["male_profile",v5_male_profile()],["female_profile",v5_female_profile()],
        ["outlet_ids",v5_outlet_ids],
        ["protrusion_min",s5_core_min_z+v5_core_l-s5_body_h],
        ["protrusion_max",s5_core_max_z+v5_core_l-s5_body_h],
        ["default_travel",0],["protrusion_datum","body spigot end, NOT Y mouth"],
        ["core_source_release","fan-tee-narrow-nozzles-v5-20261007"],
        ["slot_floor_z",12.5],["slot_roof_z",21.5],["slot_outer_r",s5_slot_outer_r],
        ["lock_deg",s5_lock_deg],["flow_guide_status","AWAITING_USER_CHOICE"],
        ["fn",$fn],["steps_per_turn",v5_steps_per_turn]
    ]);
}
if(part=="body") s5_body();
else if(part=="body-section") s5_section() s5_body();
else if(part=="review-fan-envelope") s5_fan_reference();
else if(part=="review-female-groove") s5_female_groove();
else if(part=="profile-samples") s5_profile_samples();
else if(part=="contract") s5_contract();
else assert(false,"v5 generates only the shell; reuse byte-identical Ø41 v5 cores");
