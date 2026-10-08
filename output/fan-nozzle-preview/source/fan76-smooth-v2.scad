// Ø76 v2 / mm / X1C PETG candidate / print fan socket down, air +Z.
// Single continuous shell; no embedded supports, screws or invented turbine.
// Fan enters +Z from z0. Existing Ø41 v5 cores enter/rotate -Z from Y end.
// Load: original v5 male tooth -> paired female groove -> shell -> bayonet roof.
// Exact v5 core geometry is imported from the frozen delivery by the exporter.
// The requested flow-guide type remains a separate user decision, not a claim
// that a static vane adds pressure or that this unsimulated flow is laminar.
include <fan-tee-v5-parameters.scad>
include <fan-tee-v5-thread.scad>

part="body";
$fn=192;
s2_eps=0.025;
s2_socket_id=76;
// Circumscribed socket polygon: minimum across flats is exactly nominal ID76.
// This is tessellation compensation, NOT the former 0.6mm diametral allowance.
s2_socket_r=s2_socket_id/2/cos(180/$fn);
s2_fan_face=24;
s2_blend_z0=26; // beyond fan face +0.5mm axial play, no premature shoulder
s2_blend_length=80;
s2_blend_z1=s2_blend_z0+s2_blend_length;
s2_body_h=184;
s2_collar_od=86;
s2_tube_od=50;
s2_spigot_od=50;
s2_spigot_id=44;
s2_spigot_l=25;
s2_spigot_z0=s2_body_h-s2_spigot_l;
s2_female_z0=s2_blend_z1;
s2_travel=32;
s2_female_z1=s2_female_z0+(v5_male_z1-v5_male_z0)+s2_travel;
s2_female_cut_z0=s2_female_z0-4;
s2_female_cut_z1=s2_female_z1+4;
s2_entry_z0=s2_female_z1-2;
s2_guide_z0=s2_female_z1+2;
s2_core_min_z=s2_female_z0-v5_male_z0;
s2_core_max_z=s2_core_min_z+s2_travel;
s2_straight_handoff_z=s2_guide_z0-v5_male_z0;
s2_lug_angles=[90,270];
s2_slot_inner_r=37.35;
s2_slot_outer_r=40.8;
s2_window_w=8.3;
s2_slot_half_angle=atan((s2_window_w/2)/s2_slot_inner_r);
s2_lock_deg=18;

function s2_smooth(t)=t*t*t*(10+t*(-15+6*t));
function s2_lerp(a,b,t)=a+(b-a)*s2_smooth(t);
function s2_angle(z)=360*(z+v5_male_z0-s2_female_z0)/v5_pitch;
function s2_turns(z)=floor((min(z+v5_male_z1-v5_runout_l,s2_entry_z0)
    -max(z+v5_male_z0+v5_runout_l,s2_female_z0)-2*v5_profile_half)/v5_pitch);

assert(s2_socket_id==76 && s2_spigot_od==50);
assert(s2_female_z1-s2_female_z0==56 && s2_travel==32 && v5_pitch==4);
assert(s2_turns(s2_core_min_z)>=3 && s2_turns(s2_core_max_z)>=3);
assert((s2_tube_od-v5_female_major)/2>=3);
assert(s2_spigot_id-2*v5_tip_radial_chamfer>v5_male_major);
assert(s2_guide_z0<s2_body_h-v5_tip_l);

module s2_outer() {
    rotate_extrude() polygon(concat(
        [[0,0],[s2_collar_od/2,0],[s2_collar_od/2,s2_blend_z0]],
        [for(i=[1:160]) [s2_lerp(s2_collar_od/2,s2_tube_od/2,i/160),
            s2_blend_z0+s2_blend_length*i/160]],
        [[s2_spigot_od/2,s2_body_h-v5_tip_l],
         [s2_spigot_od/2-v5_tip_radial_chamfer,s2_body_h],[0,s2_body_h]]));
}
module s2_bore() {
    rotate_extrude() polygon(concat(
        [[0,-s2_eps],[s2_socket_r+1.2,-s2_eps],
         [s2_socket_r,1.2],[s2_socket_r,s2_blend_z0]],
        [for(i=[1:160]) [s2_lerp(s2_socket_r,v5_female_minor/2,i/160),
            s2_blend_z0+s2_blend_length*i/160]],
        [[v5_female_minor/2,s2_entry_z0],[s2_spigot_id/2,s2_guide_z0],
         [s2_spigot_id/2,s2_body_h-v5_tip_l],
         [s2_spigot_id/2-v5_tip_radial_chamfer,s2_body_h],
         [s2_spigot_id/2-v5_tip_radial_chamfer,s2_body_h+s2_eps],
         [0,s2_body_h+s2_eps]]));
}
module s2_female_groove() {
    // Reuse original v5's precise r-z profile, P4, radial/axial clearances.
    // Extended ends keep the entry groove continuous through both lead-ins.
    v5_profile_helix(s2_female_cut_z0,s2_female_cut_z1,s2_female_z0,
        v5_pitch,v5_female_profile(),v5_phase,v5_steps_per_turn);
}
module s2_sector(a0,a1,r0,r1,z0,z1) {
    translate([0,0,z0]) linear_extrude(height=z1-z0)
        polygon(concat([for(i=[0:64]) [r0*cos(a0+(a1-a0)*i/64),r0*sin(a0+(a1-a0)*i/64)]],
                       [for(i=[64:-1:0]) [r1*cos(a0+(a1-a0)*i/64),r1*sin(a0+(a1-a0)*i/64)]]));
}
module s2_bayonet_cut() {
    for(a=s2_lug_angles) {
        rotate([0,0,a]) translate([s2_slot_inner_r,-s2_window_w/2,-s2_eps])
            cube([40.6-s2_slot_inner_r,s2_window_w,21.5+s2_eps]);
        s2_sector(a-s2_slot_half_angle,a+s2_lock_deg+s2_slot_half_angle,
                  s2_slot_inner_r,s2_slot_outer_r,12.5,21.5);
    }
}
module s2_body() { difference() {s2_outer();s2_bore();s2_female_groove();s2_bayonet_cut();} }
module s2_fan_reference() {
    union() {
        difference() {cylinder(d=76,h=s2_fan_face);
            translate([0,0,-s2_eps]) cylinder(d=71,h=s2_fan_face+2*s2_eps);}
        for(a=s2_lug_angles) rotate([0,0,a]) translate([37.75,-3.75,13]) cube([2.25,7.5,8]);
    }
}
module s2_section() {intersection(){children();translate([-100,0,-1]) cube([200,100,300]);}}
module s2_contract() {
    echo(fan76_smooth_contract=[
        ["units","mm"],["body_height",s2_body_h],["body_od",s2_collar_od],
        ["tube_od",s2_tube_od],["spigot_od",s2_spigot_od],["spigot_id",s2_spigot_id],
        ["spigot_z0",s2_spigot_z0],["spigot_length",s2_spigot_l],
        ["socket_id",s2_socket_id],["socket_polygon_circumdiameter",2*s2_socket_r],
        ["fan_od",76],["fan_id",71],["face_z",s2_fan_face],
        ["blend_z0",s2_blend_z0],["blend_z1",s2_blend_z1],["blend_length",s2_blend_length],
        ["blend_polynomial","10t3-15t4+6t5"],
        ["peak_inner_wall_angle_to_axis_deg",atan(1.875*(s2_socket_r-v5_female_minor/2)/s2_blend_length)],
        ["female_z0",s2_female_z0],["female_z1",s2_female_z1],
        ["female_length",s2_female_z1-s2_female_z0],
        ["female_cut_z0",s2_female_cut_z0],["female_cut_z1",s2_female_cut_z1],
        ["entry_z0",s2_entry_z0],["guide_z0",s2_guide_z0],
        ["straight_handoff_z",s2_straight_handoff_z],
        ["core_min_z",s2_core_min_z],["core_max_z",s2_core_max_z],
        ["travel",s2_travel],["pitch",v5_pitch],["core_height",v5_core_l],
        ["male_z0",v5_male_z0],["male_z1",v5_male_z1],
        ["complete_turns_min",s2_turns(s2_core_min_z)],
        ["complete_turns_max",s2_turns(s2_core_max_z)],
        ["male_major",v5_male_major],["female_minor",v5_female_minor],["female_major",v5_female_major],
        ["male_profile",v5_male_profile()],["female_profile",v5_female_profile()],
        ["outlet_ids",v5_outlet_ids],
        ["protrusion_min",s2_core_min_z+v5_core_l-s2_body_h],
        ["protrusion_max",s2_core_max_z+v5_core_l-s2_body_h],
        ["core_source_release","fan-tee-narrow-nozzles-v5-20261007"],
        ["slot_floor_z",12.5],["slot_roof_z",21.5],["slot_outer_r",s2_slot_outer_r],
        ["lock_deg",s2_lock_deg],["flow_guide_status","AWAITING_USER_CHOICE"],
        ["fn",$fn],["steps_per_turn",v5_steps_per_turn]
    ]);
}
if(part=="body") s2_body();
else if(part=="body-section") s2_section() s2_body();
else if(part=="review-fan-envelope") s2_fan_reference();
else if(part=="review-female-groove") s2_female_groove();
else if(part=="contract") s2_contract();
else assert(false,"v2 only generates the shell; copy the frozen Ø41 v5 cores byte-for-byte");
