// Ø76 v4 / mm / X1C PETG candidate / print fan socket down, air +Z.
// Distributed-slope C2 contraction; thin non-mating wall, reinforced interfaces.
// Radial wall minimum is nominal 2.4mm, not a tested strength/airtightness claim.
// Fan enters +Z from z0. Unchanged Ø41 v5 cores enter/rotate -Z from Y end.
// Load: original v5 male tooth -> paired female groove -> shell -> bayonet roof.
// One continuous shell, no embedded supports or extra locking components.
// Flow-guide type is still pending; this is the smooth-shell candidate, not CFD.
include <fan-tee-v5-parameters.scad>
include <fan-tee-v5-thread.scad>

part="body";
$fn=192;
s4_eps=0.025;
s4_socket_id=76;
// Circumscribed bore: minimum across flats ID76; no added fit allowance.
s4_socket_r=s4_socket_id/2/cos(180/$fn);
s4_fan_face=24;
s4_blend_z0=26;
s4_blend_length=120;
s4_blend_z1=s4_blend_z0+s4_blend_length;
s4_body_h=244;
s4_collar_od=86;
s4_tube_od=50;
s4_spigot_od=50;
s4_spigot_id=44;
s4_spigot_l=25;
s4_spigot_z0=s4_body_h-s4_spigot_l;
s4_female_z0=s4_blend_z1;
s4_travel=20;
s4_female_z1=s4_female_z0+(v5_male_z1-v5_male_z0)+s4_travel;
s4_female_cut_z0=s4_female_z0-4;
s4_female_cut_z1=s4_female_z1+4;
s4_entry_z0=s4_female_z1-2;
s4_guide_z0=s4_female_z1+2;
s4_core_min_z=s4_female_z0-v5_male_z0;
s4_core_max_z=s4_core_min_z+s4_travel;
s4_straight_handoff_z=s4_guide_z0-v5_male_z0;
s4_lug_angles=[90,270];
s4_slot_inner_r=37.35;
s4_slot_outer_r=40.8;
s4_window_w=8.3;
s4_slot_half_angle=atan((s4_window_w/2)/s4_slot_inner_r);
s4_lock_deg=18;
s4_ramp=0.35;
s4_thin_wall=2.4;
s4_thread_shell_r=v5_female_major/2+s4_thin_wall;
s4_guide_r=s4_spigot_id/2+s4_thin_wall;

function s4_clamp(t)=max(0,min(1,t));
function s4_smooth(t)=let(u=s4_clamp(t)) u*u*u*(10+u*(-15+6*u));
// Integral of a cubic-smoothed slope ramp. C2 at all four joins.
// 42mm slope-up + 36mm uniform contraction + 42mm slope-down.
function s4_progress(t)=t<s4_ramp
    ? let(u=t/s4_ramp) s4_ramp*(u*u*u-u*u*u*u/2)/(1-s4_ramp)
    : t>1-s4_ramp ? 1-s4_progress(1-t) : (t-s4_ramp/2)/(1-s4_ramp);
function s4_contraction_r(z)=s4_socket_r+
    (v5_female_minor/2-s4_socket_r)*s4_progress(s4_clamp((z-s4_blend_z0)/s4_blend_length));
function s4_wall(z)=s4_thin_wall
    +(s4_collar_od/2-s4_socket_r-s4_thin_wall)*(1-s4_smooth((z-26)/60))
    +(s4_thread_shell_r-v5_female_minor/2-s4_thin_wall)*s4_smooth((z-98)/32);
function s4_bore_r(z)=z<1.2 ? s4_socket_r+1.2*(1.2-z)/(1.2+s4_eps)
    : z<=s4_blend_z0 ? s4_socket_r
    : z<=s4_blend_z1 ? s4_contraction_r(z)
    : z<=s4_entry_z0 ? v5_female_minor/2
    : z<s4_guide_z0 ? v5_female_minor/2+
        (s4_spigot_id-v5_female_minor)/2*(z-s4_entry_z0)/(s4_guide_z0-s4_entry_z0)
    : z<=s4_body_h-v5_tip_l ? s4_spigot_id/2
    : s4_spigot_id/2-v5_tip_radial_chamfer*(z-(s4_body_h-v5_tip_l))/v5_tip_l;
function s4_outer_r(z)=z<=s4_blend_z0 ? s4_collar_od/2
    : z<=s4_blend_z1 ? s4_contraction_r(z)+s4_wall(z)
    : z<=s4_guide_z0 ? s4_thread_shell_r+
        (s4_guide_r-s4_thread_shell_r)*s4_smooth((z-(s4_guide_z0-18))/18)
    : z<=s4_spigot_z0 ? s4_guide_r+
        (s4_spigot_od/2-s4_guide_r)*s4_smooth((z-(s4_spigot_z0-16))/16)
    : z<=s4_body_h-v5_tip_l ? s4_spigot_od/2
    : s4_spigot_od/2-v5_tip_radial_chamfer*(z-(s4_body_h-v5_tip_l))/v5_tip_l;
function s4_angle(z)=360*(z+v5_male_z0-s4_female_z0)/v5_pitch;
function s4_turns(z)=floor((min(z+v5_male_z1-v5_runout_l,s4_entry_z0)
    -max(z+v5_male_z0+v5_runout_l,s4_female_z0)-2*v5_profile_half)/v5_pitch);

assert(s4_socket_id==76 && s4_spigot_od==50);
assert(s4_female_z1-s4_female_z0==44 && s4_travel==20 && v5_pitch==4);
assert(s4_turns(s4_core_min_z)>=4 && s4_turns(s4_core_max_z)>=4);
assert(s4_thread_shell_r-v5_female_major/2>=2.39999);
assert(s4_spigot_id-2*v5_tip_radial_chamfer>v5_male_major);
assert(s4_guide_z0<s4_spigot_z0-16);
assert(s4_core_min_z+v5_core_l-s4_body_h==4);
assert(s4_core_max_z+v5_core_l-s4_body_h==24);
assert(s4_body_h<=245);
for(z=[26:0.25:s4_body_h])
    assert(s4_outer_r(z)-s4_bore_r(z)>=s4_thin_wall-0.00001);

module s4_outer() {
    rotate_extrude() polygon(concat([[0,0]],
        [for(z=[0:0.5:s4_body_h-v5_tip_l]) [s4_outer_r(z),z]],
        [[s4_outer_r(s4_body_h-v5_tip_l),s4_body_h-v5_tip_l],
         [s4_outer_r(s4_body_h),s4_body_h],[0,s4_body_h]]));
}
module s4_bore() {
    rotate_extrude() polygon(concat(
        [[0,-s4_eps],[s4_socket_r+1.2,-s4_eps],
         [s4_socket_r,1.2],[s4_socket_r,s4_blend_z0]],
        [for(i=[1:240]) [s4_contraction_r(s4_blend_z0+s4_blend_length*i/240),
            s4_blend_z0+s4_blend_length*i/240]],
        [[v5_female_minor/2,s4_entry_z0],[s4_spigot_id/2,s4_guide_z0],
         [s4_spigot_id/2,s4_body_h-v5_tip_l],
         [s4_spigot_id/2-v5_tip_radial_chamfer,s4_body_h],
         [s4_spigot_id/2-v5_tip_radial_chamfer,s4_body_h+s4_eps],
         [0,s4_body_h+s4_eps]]));
}
module s4_profile_samples() {
    echo(fan76_profile_samples=[for(z=[0:0.25:s4_body_h])
        [z,s4_bore_r(z),s4_outer_r(z)]]);
}
module s4_female_groove() {
    // Original paired v5 r-z tooth/groove, P4 and clearances are unchanged.
    v5_profile_helix(s4_female_cut_z0,s4_female_cut_z1,s4_female_z0,
        v5_pitch,v5_female_profile(),v5_phase,v5_steps_per_turn);
}
module s4_sector(a0,a1,r0,r1,z0,z1) {
    translate([0,0,z0]) linear_extrude(height=z1-z0)
        polygon(concat([for(i=[0:64]) [r0*cos(a0+(a1-a0)*i/64),r0*sin(a0+(a1-a0)*i/64)]],
                       [for(i=[64:-1:0]) [r1*cos(a0+(a1-a0)*i/64),r1*sin(a0+(a1-a0)*i/64)]]));
}
module s4_bayonet_cut() {
    for(a=s4_lug_angles) {
        rotate([0,0,a]) translate([s4_slot_inner_r,-s4_window_w/2,-s4_eps])
            cube([40.6-s4_slot_inner_r,s4_window_w,21.5+s4_eps]);
        s4_sector(a-s4_slot_half_angle,a+s4_lock_deg+s4_slot_half_angle,
                  s4_slot_inner_r,s4_slot_outer_r,12.5,21.5);
    }
}
module s4_body() { difference() {s4_outer();s4_bore();s4_female_groove();s4_bayonet_cut();} }
module s4_fan_reference() {
    union() {
        difference() {cylinder(d=76,h=s4_fan_face);
            translate([0,0,-s4_eps]) cylinder(d=71,h=s4_fan_face+2*s4_eps);}
        for(a=s4_lug_angles) rotate([0,0,a]) translate([37.75,-3.75,13]) cube([2.25,7.5,8]);
    }
}
module s4_section() {intersection(){children();translate([-100,0,-1]) cube([200,100,350]);}}
module s4_contract() {
    echo(fan76_smooth_contract=[
        ["units","mm"],["body_height",s4_body_h],["body_od",s4_collar_od],
        ["tube_od",s4_tube_od],["spigot_od",s4_spigot_od],["spigot_id",s4_spigot_id],
        ["spigot_z0",s4_spigot_z0],["spigot_length",s4_spigot_l],
        ["socket_id",s4_socket_id],["socket_polygon_circumdiameter",2*s4_socket_r],
        ["fan_od",76],["fan_id",71],["face_z",s4_fan_face],
        ["blend_z0",s4_blend_z0],["blend_z1",s4_blend_z1],["blend_length",s4_blend_length],
        ["blend_polynomial","integrated cubic slope ramp / constant slope / mirrored ramp"],
        ["curve_ramp_fraction",s4_ramp],["thin_wall_radial_nominal",s4_thin_wall],
        ["thread_shell_od",2*s4_thread_shell_r],["guide_od",2*s4_guide_r],
        ["peak_inner_wall_angle_to_axis_deg",atan((s4_socket_r-v5_female_minor/2)/(s4_blend_length*(1-s4_ramp)))],
        ["female_z0",s4_female_z0],["female_z1",s4_female_z1],
        ["female_length",s4_female_z1-s4_female_z0],
        ["female_cut_z0",s4_female_cut_z0],["female_cut_z1",s4_female_cut_z1],
        ["entry_z0",s4_entry_z0],["guide_z0",s4_guide_z0],
        ["straight_handoff_z",s4_straight_handoff_z],
        ["core_min_z",s4_core_min_z],["core_max_z",s4_core_max_z],
        ["travel",s4_travel],["pitch",v5_pitch],["core_height",v5_core_l],
        ["male_z0",v5_male_z0],["male_z1",v5_male_z1],
        ["complete_turns_min",s4_turns(s4_core_min_z)],
        ["complete_turns_max",s4_turns(s4_core_max_z)],
        ["male_major",v5_male_major],["female_minor",v5_female_minor],["female_major",v5_female_major],
        ["male_profile",v5_male_profile()],["female_profile",v5_female_profile()],
        ["outlet_ids",v5_outlet_ids],
        ["protrusion_min",s4_core_min_z+v5_core_l-s4_body_h],
        ["protrusion_max",s4_core_max_z+v5_core_l-s4_body_h],
        ["default_travel",0],["protrusion_datum","body spigot end, NOT Y mouth"],
        ["core_source_release","fan-tee-narrow-nozzles-v5-20261007"],
        ["slot_floor_z",12.5],["slot_roof_z",21.5],["slot_outer_r",s4_slot_outer_r],
        ["lock_deg",s4_lock_deg],["flow_guide_status","AWAITING_USER_CHOICE"],
        ["fn",$fn],["steps_per_turn",v5_steps_per_turn]
    ]);
}
if(part=="body") s4_body();
else if(part=="body-section") s4_section() s4_body();
else if(part=="review-fan-envelope") s4_fan_reference();
else if(part=="review-female-groove") s4_female_groove();
else if(part=="profile-samples") s4_profile_samples();
else if(part=="contract") s4_contract();
else assert(false,"v4 generates only the shell; reuse byte-identical Ø41 v5 cores");
