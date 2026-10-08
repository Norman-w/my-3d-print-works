// Ø76 v3 / mm / X1C PETG candidate / print fan socket down, air +Z.
// Longer C2 contraction and shallow default tip, not a rescaled v2 mesh.
// Fan enters +Z from z0. Unchanged Ø41 v5 cores enter/rotate -Z from Y end.
// Load: original v5 male tooth -> paired female groove -> shell -> bayonet roof.
// One continuous shell, no embedded supports or extra locking components.
// Flow-guide type is still pending; this is the smooth-shell candidate, not CFD.
include <fan-tee-v5-parameters.scad>
include <fan-tee-v5-thread.scad>

part="body";
$fn=192;
s3_eps=0.025;
s3_socket_id=76;
// Circumscribed bore: minimum across flats ID76; no added fit allowance.
s3_socket_r=s3_socket_id/2/cos(180/$fn);
s3_fan_face=24;
s3_blend_z0=26;
s3_blend_length=110;
s3_blend_z1=s3_blend_z0+s3_blend_length;
s3_body_h=234;
s3_collar_od=86;
s3_tube_od=50;
s3_spigot_od=50;
s3_spigot_id=44;
s3_spigot_l=25;
s3_spigot_z0=s3_body_h-s3_spigot_l;
s3_female_z0=s3_blend_z1;
s3_travel=20;
s3_female_z1=s3_female_z0+(v5_male_z1-v5_male_z0)+s3_travel;
s3_female_cut_z0=s3_female_z0-4;
s3_female_cut_z1=s3_female_z1+4;
s3_entry_z0=s3_female_z1-2;
s3_guide_z0=s3_female_z1+2;
s3_core_min_z=s3_female_z0-v5_male_z0;
s3_core_max_z=s3_core_min_z+s3_travel;
s3_straight_handoff_z=s3_guide_z0-v5_male_z0;
s3_lug_angles=[90,270];
s3_slot_inner_r=37.35;
s3_slot_outer_r=40.8;
s3_window_w=8.3;
s3_slot_half_angle=atan((s3_window_w/2)/s3_slot_inner_r);
s3_lock_deg=18;

function s3_smooth(t)=t*t*t*(10+t*(-15+6*t));
function s3_lerp(a,b,t)=a+(b-a)*s3_smooth(t);
function s3_angle(z)=360*(z+v5_male_z0-s3_female_z0)/v5_pitch;
function s3_turns(z)=floor((min(z+v5_male_z1-v5_runout_l,s3_entry_z0)
    -max(z+v5_male_z0+v5_runout_l,s3_female_z0)-2*v5_profile_half)/v5_pitch);

assert(s3_socket_id==76 && s3_spigot_od==50);
assert(s3_female_z1-s3_female_z0==44 && s3_travel==20 && v5_pitch==4);
assert(s3_turns(s3_core_min_z)>=4 && s3_turns(s3_core_max_z)>=4);
assert((s3_tube_od-v5_female_major)/2>=3);
assert(s3_spigot_id-2*v5_tip_radial_chamfer>v5_male_major);
assert(s3_guide_z0<s3_body_h-v5_tip_l);
assert(s3_core_min_z+v5_core_l-s3_body_h==4);
assert(s3_core_max_z+v5_core_l-s3_body_h==24);
assert(s3_body_h<=245);

module s3_outer() {
    rotate_extrude() polygon(concat(
        [[0,0],[s3_collar_od/2,0],[s3_collar_od/2,s3_blend_z0]],
        [for(i=[1:220]) [s3_lerp(s3_collar_od/2,s3_tube_od/2,i/220),
            s3_blend_z0+s3_blend_length*i/220]],
        [[s3_spigot_od/2,s3_body_h-v5_tip_l],
         [s3_spigot_od/2-v5_tip_radial_chamfer,s3_body_h],[0,s3_body_h]]));
}
module s3_bore() {
    rotate_extrude() polygon(concat(
        [[0,-s3_eps],[s3_socket_r+1.2,-s3_eps],
         [s3_socket_r,1.2],[s3_socket_r,s3_blend_z0]],
        [for(i=[1:220]) [s3_lerp(s3_socket_r,v5_female_minor/2,i/220),
            s3_blend_z0+s3_blend_length*i/220]],
        [[v5_female_minor/2,s3_entry_z0],[s3_spigot_id/2,s3_guide_z0],
         [s3_spigot_id/2,s3_body_h-v5_tip_l],
         [s3_spigot_id/2-v5_tip_radial_chamfer,s3_body_h],
         [s3_spigot_id/2-v5_tip_radial_chamfer,s3_body_h+s3_eps],
         [0,s3_body_h+s3_eps]]));
}
module s3_female_groove() {
    // Original paired v5 r-z tooth/groove, P4 and clearances are unchanged.
    v5_profile_helix(s3_female_cut_z0,s3_female_cut_z1,s3_female_z0,
        v5_pitch,v5_female_profile(),v5_phase,v5_steps_per_turn);
}
module s3_sector(a0,a1,r0,r1,z0,z1) {
    translate([0,0,z0]) linear_extrude(height=z1-z0)
        polygon(concat([for(i=[0:64]) [r0*cos(a0+(a1-a0)*i/64),r0*sin(a0+(a1-a0)*i/64)]],
                       [for(i=[64:-1:0]) [r1*cos(a0+(a1-a0)*i/64),r1*sin(a0+(a1-a0)*i/64)]]));
}
module s3_bayonet_cut() {
    for(a=s3_lug_angles) {
        rotate([0,0,a]) translate([s3_slot_inner_r,-s3_window_w/2,-s3_eps])
            cube([40.6-s3_slot_inner_r,s3_window_w,21.5+s3_eps]);
        s3_sector(a-s3_slot_half_angle,a+s3_lock_deg+s3_slot_half_angle,
                  s3_slot_inner_r,s3_slot_outer_r,12.5,21.5);
    }
}
module s3_body() { difference() {s3_outer();s3_bore();s3_female_groove();s3_bayonet_cut();} }
module s3_fan_reference() {
    union() {
        difference() {cylinder(d=76,h=s3_fan_face);
            translate([0,0,-s3_eps]) cylinder(d=71,h=s3_fan_face+2*s3_eps);}
        for(a=s3_lug_angles) rotate([0,0,a]) translate([37.75,-3.75,13]) cube([2.25,7.5,8]);
    }
}
module s3_section() {intersection(){children();translate([-100,0,-1]) cube([200,100,350]);}}
module s3_contract() {
    echo(fan76_smooth_contract=[
        ["units","mm"],["body_height",s3_body_h],["body_od",s3_collar_od],
        ["tube_od",s3_tube_od],["spigot_od",s3_spigot_od],["spigot_id",s3_spigot_id],
        ["spigot_z0",s3_spigot_z0],["spigot_length",s3_spigot_l],
        ["socket_id",s3_socket_id],["socket_polygon_circumdiameter",2*s3_socket_r],
        ["fan_od",76],["fan_id",71],["face_z",s3_fan_face],
        ["blend_z0",s3_blend_z0],["blend_z1",s3_blend_z1],["blend_length",s3_blend_length],
        ["blend_polynomial","10t3-15t4+6t5"],
        ["peak_inner_wall_angle_to_axis_deg",atan(1.875*(s3_socket_r-v5_female_minor/2)/s3_blend_length)],
        ["female_z0",s3_female_z0],["female_z1",s3_female_z1],
        ["female_length",s3_female_z1-s3_female_z0],
        ["female_cut_z0",s3_female_cut_z0],["female_cut_z1",s3_female_cut_z1],
        ["entry_z0",s3_entry_z0],["guide_z0",s3_guide_z0],
        ["straight_handoff_z",s3_straight_handoff_z],
        ["core_min_z",s3_core_min_z],["core_max_z",s3_core_max_z],
        ["travel",s3_travel],["pitch",v5_pitch],["core_height",v5_core_l],
        ["male_z0",v5_male_z0],["male_z1",v5_male_z1],
        ["complete_turns_min",s3_turns(s3_core_min_z)],
        ["complete_turns_max",s3_turns(s3_core_max_z)],
        ["male_major",v5_male_major],["female_minor",v5_female_minor],["female_major",v5_female_major],
        ["male_profile",v5_male_profile()],["female_profile",v5_female_profile()],
        ["outlet_ids",v5_outlet_ids],
        ["protrusion_min",s3_core_min_z+v5_core_l-s3_body_h],
        ["protrusion_max",s3_core_max_z+v5_core_l-s3_body_h],
        ["default_travel",0],["protrusion_datum","body spigot end, NOT Y mouth"],
        ["core_source_release","fan-tee-narrow-nozzles-v5-20261007"],
        ["slot_floor_z",12.5],["slot_roof_z",21.5],["slot_outer_r",s3_slot_outer_r],
        ["lock_deg",s3_lock_deg],["flow_guide_status","AWAITING_USER_CHOICE"],
        ["fn",$fn],["steps_per_turn",v5_steps_per_turn]
    ]);
}
if(part=="body") s3_body();
else if(part=="body-section") s3_section() s3_body();
else if(part=="review-fan-envelope") s3_fan_reference();
else if(part=="review-female-groove") s3_female_groove();
else if(part=="contract") s3_contract();
else assert(false,"v3 generates only the shell; reuse byte-identical Ø41 v5 cores");
