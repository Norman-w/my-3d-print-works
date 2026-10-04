// Outlet connection candidate: one continuous stepped split collar.
// Printable implementation is two serviceable half-shells joined by one M3 pair.
// Adhesive/sealant is non-structural; module load and hose drag still need a bracket.
// Units mm. Preserve the existing feeder and X=0 seam hard stops.
include <parameters.scad>
use <feeder-seam-candidate.scad>

interface_part="section";
if_eps=0.02;
if_socket_start=guide_start_z+guide_length+transition_length+2;
if_socket_end=if_socket_start+y_stub_engagement;
if_socket_id=y_stub_od+2*interface_radial_clearance;
if_socket_od=if_socket_id+2*body_wall;
if_shoulder_t=1.5;
if_shoulder_od=50.0;
if_tube_start=if_socket_start+if_shoulder_t;
if_tube_end=135; // display only: actual stock is marked and cut at assembly.
if_liner_od=47.6;
if_liner_id=45.4; // explicit contract with feeder body's current exit bore.
if_liner_end=99;

// One-piece stepped collar envelope. These are radial clearances, not squeeze.
if_collar_start=50;
if_collar_transition_start=if_socket_end;
if_collar_transition_end=73;
if_collar_end=103;
if_collar_module_clearance=0.25;
if_collar_tube_clearance=0.25;
if_collar_wall=3.0;
if_collar_split_gap=0.4;
// Keep the single screw pair close to the tube-side transition, at +3.5 mm.
if_collar_bolt_z=if_collar_transition_end+3.5;
if_collar_ear_width=14;
if_collar_ear_depth=7;
if_collar_ear_height=10;
if_collar_head_depth=2.4;
if_collar_head_d=6.0;
if_collar_bolt_nominal_d=3.0;
if_collar_hardware_overhang=4;
if_fn=144;

if_collar_inner_socket_d=if_socket_od+2*if_collar_module_clearance;
if_collar_inner_tube_d=barrel_od+2*if_collar_tube_clearance;
if_collar_outer_socket_d=if_collar_inner_socket_d+2*if_collar_wall;
if_collar_outer_tube_d=if_collar_inner_tube_d+2*if_collar_wall;
if_collar_bolt_x=if_collar_outer_socket_d/2+2.5;

assert(if_shoulder_od>barrel_id && if_shoulder_od<if_socket_id);
assert(if_liner_od<barrel_id && if_liner_id>guide_id);
assert(if_liner_end>=if_collar_bolt_z);
assert(if_socket_end-if_tube_start>0);
assert(if_collar_start<if_collar_transition_start);
assert(if_collar_transition_start<if_collar_transition_end);
assert(if_collar_transition_end<if_collar_end);
assert(if_collar_module_clearance>0 && if_collar_tube_clearance>0);
assert(if_collar_wall>=2.4);
assert(if_collar_split_gap>=0.2 && if_collar_split_gap<1.0);
assert(if_collar_bolt_z>if_collar_transition_end && if_collar_bolt_z<if_collar_end);
assert(if_collar_ear_width>if_collar_head_d);
assert(if_collar_ear_depth>nut_depth);

module if_ring(z,h,od,id) {
    difference() {
        translate([0,0,z]) cylinder(h=h,d=od,$fn=if_fn);
        translate([0,0,z-if_eps]) cylinder(h=h+2*if_eps,d=id,$fn=if_fn);
    }
}

module if_liner() {
    union() {
        if_ring(if_socket_start,if_shoulder_t,if_shoulder_od,if_liner_id);
        if_ring(if_tube_start-if_eps,if_liner_end-if_tube_start+if_eps,
            if_liner_od,if_liner_id);
    }
}

module if_tube(z=if_tube_start) {
    if_ring(z,if_tube_end-if_tube_start,barrel_od,barrel_id);
}

module if_collar_outer_profile() {
    union() {
        translate([0,0,if_collar_start])
            cylinder(h=if_collar_transition_start-if_collar_start,
                d=if_collar_outer_socket_d,$fn=if_fn);
        translate([0,0,if_collar_transition_start])
            cylinder(h=if_collar_transition_end-if_collar_transition_start,
                d1=if_collar_outer_socket_d,d2=if_collar_outer_tube_d,$fn=if_fn);
        translate([0,0,if_collar_transition_end])
            cylinder(h=if_collar_end-if_collar_transition_end,
                d=if_collar_outer_tube_d,$fn=if_fn);
    }
}

module if_collar_inner_profile() {
    // Extend each cutter slightly past the profile joins so the bore is open.
    union() {
        translate([0,0,if_collar_start-if_eps])
            cylinder(h=if_collar_transition_start-if_collar_start+2*if_eps,
                d=if_collar_inner_socket_d,$fn=if_fn);
        translate([0,0,if_collar_transition_start-if_eps])
            cylinder(h=if_collar_transition_end-if_collar_transition_start+2*if_eps,
                d1=if_collar_inner_socket_d,d2=if_collar_inner_tube_d,$fn=if_fn);
        translate([0,0,if_collar_transition_end-if_eps])
            cylinder(h=if_collar_end-if_collar_transition_end+2*if_eps,
                d=if_collar_inner_tube_d,$fn=if_fn);
    }
}

module if_collar_shell() {
    difference() {
        if_collar_outer_profile();
        if_collar_inner_profile();
    }
}

module if_collar_halfspace(positive=true) {
    translate([-100,positive?if_collar_split_gap/2:-100,if_collar_start-if_eps])
        cube([200,positive?100:100-if_collar_split_gap/2,
            if_collar_end-if_collar_start+2*if_eps]);
}

module if_y_cylinder(x,y,z,h,d) {
    translate([x,y,z]) rotate([90,0,0])
        cylinder(h=h,d=d,center=true,$fn=if_fn);
}

module if_y_hex(x,y,z,h,af) {
    translate([x,y,z]) rotate([90,0,0])
        cylinder(h=h,r=af/sqrt(3),center=true,$fn=6);
}

module if_collar_ear(positive=true,x=0) {
    translate([x-if_collar_ear_width/2,
        positive?if_collar_split_gap/2:-if_collar_split_gap/2-if_collar_ear_depth,
        if_collar_bolt_z-if_collar_ear_height/2])
        cube([if_collar_ear_width,if_collar_ear_depth,if_collar_ear_height]);
}

module if_collar_fastener_cuts(positive=true) {
    for(x=[-if_collar_bolt_x,if_collar_bolt_x]) {
        // One shared clearance hole passes through both halves.
        if_y_cylinder(x,0,if_collar_bolt_z,
            2*(if_collar_ear_depth+if_collar_split_gap/2+if_eps),fastener_d);
        if(positive)
            if_y_cylinder(x,
                if_collar_split_gap/2+if_collar_ear_depth-if_collar_head_depth/2,
                if_collar_bolt_z,if_collar_head_depth+if_eps,if_collar_head_d);
        else
            if_y_hex(x,
                -if_collar_split_gap/2-if_collar_ear_depth+nut_depth/2,
                if_collar_bolt_z,nut_depth+if_eps,nut_af);
    }
}

module if_collar_half(positive=true) {
    difference() {
        union() {
            intersection() {
                if_collar_shell();
                if_collar_halfspace(positive);
            }
            for(x=[-if_collar_bolt_x,if_collar_bolt_x]) if_collar_ear(positive,x);
        }
        if_collar_fastener_cuts(positive);
    }
}

module if_collar() {
    // The continuous stepped profile is split only for printing and service.
    union() {
        if_collar_half(false);
        if_collar_half(true);
    }
}

module if_collar_hardware() {
    // Reference M3 hardware; exact supplier head style and torque are open.
    for(x=[-if_collar_bolt_x,if_collar_bolt_x]) {
        if_y_cylinder(x,0,if_collar_bolt_z,
            2*(if_collar_ear_depth+if_collar_split_gap/2+if_collar_hardware_overhang),
            if_collar_bolt_nominal_d);
        if_y_cylinder(x,
            if_collar_split_gap/2+if_collar_ear_depth+if_collar_head_depth/2,
            if_collar_bolt_z,if_collar_head_depth,if_collar_head_d);
        if_y_hex(x,
            -if_collar_split_gap/2-if_collar_ear_depth-nut_depth/2,
            if_collar_bolt_z,nut_depth,nut_af);
    }
}

module if_body() {
    union() { seam_candidate_half(false); seam_candidate_half(true); }
}

module if_body_outlet() {
    intersection() { if_body(); translate([-50,-50,30]) cube([100,100,110]); }
}

module if_assembly(section=false) {
    intersection() {
        union() {
            color([0.70,0.78,0.84]) if_body_outlet();
            color([0.20,0.62,0.80]) if_tube();
            color([0.95,0.60,0.20]) if_liner();
            color([0.28,0.58,0.38]) if_collar();
            color([0.48,0.49,0.53]) if_collar_hardware();
        }
        translate([section?0:-60,-60,29]) cube([120,120,110]);
    }
}

if(interface_part=="section") if_assembly(true);
else if(interface_part=="assembly") if_assembly();
else if(interface_part=="collar") if_collar();
else if(interface_part=="collar-positive") if_collar_half(true);
else if(interface_part=="collar-negative") if_collar_half(false);
else if(interface_part=="collar-shell") if_collar_shell();
else if(interface_part=="collar-hardware") if_collar_hardware();
else if(interface_part=="liner") if_liner();
else if(interface_part=="liner-body") intersection() { if_liner(); if_body(); }
else if(interface_part=="liner-tube") intersection() { if_liner(); if_tube(); }
else if(interface_part=="collar-body-tube") intersection() {
    if_collar(); union(){if_body();if_tube();}
}
else if(interface_part=="collar-offset-control") intersection() {
    translate([0.6,0,0]) if_collar(); union(){if_body();if_tube();}
}
else if(interface_part=="liner-upstream-stop") intersection() {
    translate([0,0,-0.2]) if_liner();if_body();
}
else if(interface_part=="liner-downstream-stop") intersection() {
    translate([0,0,0.2]) if_liner();if_tube();
}
else if(interface_part=="tube-assembly-sweep") intersection() {
    // Constant OD50 / ID48 tube swept from +Z20 to its seated position.
    if_ring(if_tube_start,if_tube_end-if_tube_start+20,barrel_od,barrel_id);
    union(){if_liner();if_body();}
}
else if(interface_part=="ballway") intersection() {
    translate([0,0,if_socket_start-if_eps])
        cylinder(h=if_tube_end-if_socket_start+2*if_eps,d=41.5,$fn=if_fn);
    union(){if_liner();if_tube();if_collar();if_body();}
}
else assert(false,"Unknown interface study selector");

echo("INTERFACE_STUDY_ONLY: one-piece stepped split collar candidate; sealant, support and physical strength remain OPEN");
echo("interface_dims",[
    ["socket_start",if_socket_start],["socket_end",if_socket_end],
    ["socket_id",if_socket_id],["socket_od",if_socket_od],
    ["tube_id",barrel_id],["tube_od",barrel_od],["polygon_fn",if_fn],
    ["tube_start",if_tube_start],["tube_engagement",if_socket_end-if_tube_start],
    ["tube_end_display_only",if_tube_end],
    ["liner_id",if_liner_id],["liner_od",if_liner_od],
    ["liner_end",if_liner_end],["shoulder_od",if_shoulder_od],["shoulder_t",if_shoulder_t],
    ["collar_start",if_collar_start],["collar_end",if_collar_end],
    ["collar_transition",[if_collar_transition_start,if_collar_transition_end]],
    ["collar_inner_socket_d",if_collar_inner_socket_d],
    ["collar_inner_tube_d",if_collar_inner_tube_d],
    ["collar_wall",if_collar_wall], ["collar_split_gap",if_collar_split_gap],
    ["collar_bolt_count",2], ["collar_bolt_z",if_collar_bolt_z],
    ["collar_bolt_x",[-if_collar_bolt_x,if_collar_bolt_x]],
    ["collar_clearance_hole_d",fastener_d], ["collar_nut_af",nut_af]
]);
