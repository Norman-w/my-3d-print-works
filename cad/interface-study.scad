// Packaging study ONLY. No released seals, clamps, liner or support bracket.
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
if_boot_start=50;
if_boot_transition_end=73;
if_boot_end=103;
if_boot_wall=2; // unselected elastomer envelope, NOT a squeeze specification.
if_band_width=9; // envelope only; no catalog part has been selected.
if_band_t=0.6;
if_band_z=[59,90];
if_fn=144;

assert(if_shoulder_od>barrel_id && if_shoulder_od<if_socket_id);
assert(if_liner_od<barrel_id && if_liner_id>guide_id);
assert(if_liner_end>=if_band_z[1]+if_band_width/2);
assert(if_socket_end-if_tube_start>0);

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

module if_boot() {
    // Closed STEP envelope over the existing outside diameters. Zero squeeze.
    difference() {
        union() {
            translate([0,0,if_boot_start]) cylinder(h=if_socket_end-if_boot_start,
                d=if_socket_od+2*if_boot_wall,$fn=if_fn);
            translate([0,0,if_socket_end]) cylinder(h=if_boot_transition_end-if_socket_end,
                d1=if_socket_od+2*if_boot_wall,d2=barrel_od+2*if_boot_wall,$fn=if_fn);
            translate([0,0,if_boot_transition_end]) cylinder(h=if_boot_end-if_boot_transition_end,
                d=barrel_od+2*if_boot_wall,$fn=if_fn);
        }
        translate([0,0,if_boot_start-if_eps]) cylinder(h=if_socket_end-if_boot_start+if_eps,
            d=if_socket_od,$fn=if_fn);
        translate([0,0,if_socket_end-if_eps]) cylinder(h=if_boot_transition_end-if_socket_end+2*if_eps,
            d1=if_socket_od,d2=barrel_od,$fn=if_fn);
        translate([0,0,if_boot_transition_end]) cylinder(h=if_boot_end-if_boot_transition_end+if_eps,
            d=barrel_od,$fn=if_fn);
    }
}

module if_bands() {
    // Bands only. Screw housings/tools are OMITTED and still require selection.
    for(i=[0,1]) let(d=(i==0?if_socket_od:barrel_od)+2*if_boot_wall)
        if_ring(if_band_z[i]-if_band_width/2,if_band_width,d+2*if_band_t,d);
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
            color([0.28,0.58,0.38]) if_boot();
            color([0.48,0.49,0.53]) if_bands();
        }
        translate([section?0:-60,-60,29]) cube([120,120,110]);
    }
}

if(interface_part=="section") if_assembly(true);
else if(interface_part=="assembly") if_assembly();
else if(interface_part=="liner") if_liner();
else if(interface_part=="boot-envelope") if_boot();
else if(interface_part=="liner-body") intersection() { if_liner(); if_body(); }
else if(interface_part=="liner-tube") intersection() { if_liner(); if_tube(); }
else if(interface_part=="boot-body-tube") intersection() { if_boot(); union(){if_body();if_tube();} }
else if(interface_part=="boot-offset-control") intersection() {
    translate([0.2,0,0]) if_boot(); union(){if_body();if_tube();}
}
else if(interface_part=="liner-upstream-stop") intersection() {translate([0,0,-0.2]) if_liner();if_body();}
else if(interface_part=="liner-downstream-stop") intersection() {translate([0,0,0.2]) if_liner();if_tube();}
else if(interface_part=="tube-assembly-sweep") intersection() {
    // Constant OD50 / ID48 tube swept from +Z20 to its seated position.
    if_ring(if_tube_start,if_tube_end-if_tube_start+20,barrel_od,barrel_id);
    union(){if_liner();if_body();}
}
else if(interface_part=="ballway") intersection() {
    translate([0,0,if_socket_start-if_eps]) cylinder(h=if_tube_end-if_socket_start+2*if_eps,d=41.5,$fn=if_fn);
    union(){if_liner();if_tube();if_boot();if_bands();if_body();}
}
else assert(false,"Unknown interface study selector");

echo("INTERFACE_STUDY_ONLY: no clamp housing, bracket, seal compression or strength proof");
echo("interface_dims",[
    ["socket_start",if_socket_start],["socket_end",if_socket_end],
    ["socket_id",if_socket_id],["socket_od",if_socket_od],
    ["tube_id",barrel_id],["tube_od",barrel_od],["polygon_fn",if_fn],
    ["tube_start",if_tube_start],["tube_engagement",if_socket_end-if_tube_start],
    ["tube_end_display_only",if_tube_end],
    ["liner_id",if_liner_id],["liner_od",if_liner_od],
    ["liner_end",if_liner_end],["shoulder_od",if_shoulder_od],["shoulder_t",if_shoulder_t],
    ["band_z",if_band_z],["band_width",if_band_width],
    ["boot_start",if_boot_start],["boot_end",if_boot_end],
    ["boot_transition_end",if_boot_transition_end],["boot_wall_envelope",if_boot_wall]
]);
