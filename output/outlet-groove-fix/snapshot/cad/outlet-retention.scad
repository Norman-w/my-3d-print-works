// Candidate outlet retention, millimetres; +Z is ball travel.
// Capture flange carries module-side retention. PC side is friction clamping.
// No tube crush, torque, load, air-tightness or print acceptance is implied.
include <parameters.scad>
use <feeder-body.scad>

or_part="assembly";
or_closure=0; // display open. Each pipe-clamp half may move inward up to 0.4.
or_service=0;
or_service_positive=true;
or_angle=0;
or_eps=0.02;
or_fn=96;
or_socket_z0=44;
or_socket_z1=69;
or_socket_id=50.5;
or_socket_od=56.5;
or_flange_z0=44;
or_flange_z1=48;
or_flange_od=64;
or_flange_flat_y=30;
or_capture_z0=40;
or_capture_z1=53;
or_capture_od=72;
or_capture_id=57;
or_recess_z0=43.7;
or_recess_z1=48.3;
or_recess_d=64.6;
or_recess_flat_y=30.3;
or_pipe_z0=45.5;
or_pipe_z1=135;
or_liner_shoulder_od=50;
or_liner_od=47.6;
or_liner_id=44.4;
or_liner_end=118;
or_liner_leadin=6;
or_clamp_z0=90;
or_clamp_z1=114;
or_clamp_od=64;
or_clamp_id=50.6;
or_split_cut=0.5;
or_stop_gap_half=0.4;
or_ear_outer_x=14;
or_closure_y=55;
or_closure_z=[47,102];
or_rod_y=45;
or_rod_z0=30;
or_rod_z1=130;
or_rod_slot_d=4.6;
or_rod_slot_x_length=6.2;
or_washer_od=12;
or_washer_t=0.8;
or_m4_af=7;
or_m4_nut_h=3.2;
or_m4_pocket_af=7.4;
or_m4_pocket_h=3.6;
or_band_z0=54;
or_band_z1=89;
or_band_work_od=64;
$fn=96;

module or_ring(z0,z1,od,id) {
    difference() {
        translate([0,0,z0]) cylinder(h=z1-z0,d=od);
        translate([0,0,z0-or_eps]) cylinder(h=z1-z0+2*or_eps,d=id);
    }
}
module or_x_cylinder(x,y,z,h,d,fn=or_fn) {
    translate([x,y,z]) rotate([0,90,0]) cylinder(h=h,d=d,$fn=fn);
}
module or_x_hex(x,y,z,h,af) { or_x_cylinder(x,y,z,h,af/cos(30),6); }
module or_halfspace(positive=true,start=0) {
    translate([positive?start:-120,-90,20]) cube([120-start,180,140]);
}

// Public additive host interface; union with the corresponding source half.
// The ring includes the original wall so that it is a volume union, not tangent.
module or_host_additions(positive=true) {
    intersection() {
        or_ring(or_flange_z0,or_flange_z1,or_flange_od,or_socket_id);
        translate([-40,-or_flange_flat_y,or_flange_z0-or_eps]) cube([80,2*or_flange_flat_y,or_flange_z1-or_flange_z0+2*or_eps]);
        or_halfspace(positive);
    }
}
module or_host_reference() {
    union() {
        intersection() { feeder_body_full(); translate([-60,-70,35]) cube([120,140,40]); }
        or_host_additions(true); or_host_additions(false);
    }
}
module or_pipe() { or_ring(or_pipe_z0,or_pipe_z1,barrel_od,barrel_id); }
module or_liner() {
    // One revolved closed profile avoids near-coincident Boolean seams at the
    // two C0.2 lead-out chamfers; local end wall remains 1.2 mm.
    rotate_extrude() polygon([
        [or_liner_shoulder_od/2,or_socket_z0],
        [or_liner_shoulder_od/2,or_pipe_z0],
        [or_liner_od/2,or_pipe_z0],
        [or_liner_od/2,or_liner_end-0.2],
        [or_liner_od/2-0.2,or_liner_end],
        [or_liner_id/2+0.2,or_liner_end],
        [or_liner_id/2,or_liner_end-0.2],
        [or_liner_id/2,or_socket_z0+or_liner_leadin],
        [45.4/2,or_socket_z0]
    ]);
}
module or_lug_blank(z0,z1) {
    // Continuous spokes overlap the annulus over a real area. The bore is cut
    // afterwards, preserving the correct mating circle through all root webs.
    for(sx=[-1,1],sy=[-1,1]) scale([sx,sy,1]) hull() {
        translate([0,34,z0]) cube([or_ear_outer_x,29,z1-z0]);
        translate([10,23,z0]) cube([16,13,z1-z0]);
    }
}
module or_rod_slot(y,z0,z1) {
    hull() for(x=[-(or_rod_slot_x_length-or_rod_slot_d)/2,(or_rod_slot_x_length-or_rod_slot_d)/2])
        translate([x,y,z0-or_eps]) cylinder(h=z1-z0+2*or_eps,d=or_rod_slot_d);
}
module or_split_bolt_cuts(z) {
    for(y=[-or_closure_y,or_closure_y]) {
        or_x_cylinder(-20,y,z,40,4.5);
        // Spotfaces remove the diagonal spoke outside the true ear face.
        // They also provide entry for the head washer and negative-X nut.
        or_x_cylinder(or_ear_outer_x,y,z,30,12.6);
        or_x_cylinder(-44,y,z,44-or_ear_outer_x,12.6);
        // M4 nut enters from -X; recess is open, no hidden insertion slot.
        or_x_hex(-or_ear_outer_x-or_eps,y,z,or_m4_pocket_h+or_eps,or_m4_pocket_af);
    }
}
module or_capture_blank() {
    difference() {
        union() {
            translate([0,0,or_capture_z0]) cylinder(h=or_capture_z1-or_capture_z0,d=or_capture_od);
            or_lug_blank(or_capture_z0,or_capture_z1);
        }
        translate([0,0,or_capture_z0-or_eps]) cylinder(h=or_capture_z1-or_capture_z0+2*or_eps,d=or_capture_id);
        // The existing host still tapers at Z40..42: open the lower mouth.
        translate([0,0,or_capture_z0-or_eps]) cylinder(h=or_recess_z0-or_capture_z0+or_eps,d1=60.5,d2=or_capture_id);
        intersection() {
            translate([0,0,or_recess_z0]) cylinder(h=or_recess_z1-or_recess_z0,d=or_recess_d);
            translate([-40,-or_recess_flat_y,or_recess_z0-or_eps]) cube([80,2*or_recess_flat_y,or_recess_z1-or_recess_z0+2*or_eps]);
        }
        for(y=[-or_rod_y,or_rod_y]) or_rod_slot(y,or_capture_z0,or_capture_z1);
        or_split_bolt_cuts(or_closure_z[0]);
    }
}
module or_capture_half(positive=true) {
    intersection() { or_capture_blank(); or_halfspace(positive); }
}
module or_clamp_half_raw(positive=true) {
    difference() {
        union() {
            intersection() {
                or_ring(or_clamp_z0,or_clamp_z1,or_clamp_od,or_clamp_id);
                or_halfspace(positive,or_split_cut);
            }
            intersection() {
                difference() {
                    or_lug_blank(or_clamp_z0,or_clamp_z1);
                    translate([0,0,or_clamp_z0-or_eps]) cylinder(h=or_clamp_z1-or_clamp_z0+2*or_eps,d=or_clamp_id);
                }
                or_halfspace(positive,or_stop_gap_half);
            }
        }
        for(y=[-or_rod_y,or_rod_y]) or_rod_slot(y,or_clamp_z0,or_clamp_z1);
        or_split_bolt_cuts(or_closure_z[1]);
    }
}
module or_pipe_clamp_half(positive=true,closure=or_closure) {
    translate([positive?-closure:closure,0,0]) or_clamp_half_raw(positive);
}
module or_capture() { or_capture_half(true); or_capture_half(false); }
module or_pipe_clamp() { or_pipe_clamp_half(true); or_pipe_clamp_half(false); }
module or_washer_z(z,y) { translate([0,y,z]) difference() { cylinder(h=or_washer_t,d=or_washer_od); translate([0,0,-or_eps]) cylinder(h=or_washer_t+2*or_eps,d=4.3); } }
module or_nut_z(z,y) { translate([0,y,z]) difference() { cylinder(h=or_m4_nut_h,d=or_m4_af/cos(30),$fn=6); translate([0,0,-or_eps]) cylinder(h=or_m4_nut_h+2*or_eps,d=4); } }
module or_nut_x(x,y,z) { difference() { or_x_hex(x,y,z,or_m4_nut_h,or_m4_af); or_x_cylinder(x-or_eps,y,z,or_m4_nut_h+2*or_eps,4); } }
module or_rod_hardware() {
    for(y=[-or_rod_y,or_rod_y]) {
        translate([0,y,or_rod_z0]) cylinder(h=or_rod_z1-or_rod_z0,d=4);
        for(z=[or_capture_z0-or_washer_t,or_capture_z1,or_clamp_z0-or_washer_t,or_clamp_z1]) or_washer_z(z,y);
        for(z=[or_capture_z0-or_washer_t-or_m4_nut_h,or_capture_z1+or_washer_t,
               or_clamp_z0-or_washer_t-or_m4_nut_h,or_clamp_z1+or_washer_t]) or_nut_z(z,y);
    }
}
module or_split_hardware() {
    for(k=[0,1],y=[-or_closure_y,or_closure_y]) {
        c=k==1?or_closure:0;
        z=or_closure_z[k];
        face=or_ear_outer_x-c;
        // M4x30; washer under screw head; captured nut on negative-X side.
        or_x_cylinder(face+or_washer_t-30,y,z,30,4);
        or_x_cylinder(face+or_washer_t,y,z,4,7);
        difference() { or_x_cylinder(face,y,z,or_washer_t,or_washer_od); or_x_cylinder(face-or_eps,y,z,or_washer_t+2*or_eps,4.3); }
        or_nut_x(-face+0.2,y,z);
    }
}
module or_hardware() { or_rod_hardware(); or_split_hardware(); }
module or_printed() { or_host_reference(); or_capture(); or_pipe_clamp(); or_liner(); }
module or_band_envelope() { or_ring(or_band_z0,or_band_z1,or_band_work_od,barrel_od); }
module or_tools() {
    for(z=or_closure_z,y=[-or_closure_y,or_closure_y])
        or_x_cylinder(or_ear_outer_x+or_washer_t+4.1,y,z,35,8);
    // OD14 thin-wall socket envelope for M4 rod nuts; only approaches from
    // the exposed rod ends. Inner nuts are fitted before the rods enter seats.
    for(y=[-or_rod_y,or_rod_y]) {
        translate([0,y,20]) cylinder(h=or_capture_z0-or_washer_t-or_m4_nut_h-20,d=14);
        translate([0,y,or_clamp_z1+or_washer_t+or_m4_nut_h]) cylinder(h=23,d=14);
    }
    // Candidate 7 mm open-end spanner approach to the two inner nut levels:
    // 14 mm envelope width / 3 mm thickness, coming from the outer +/-Y side.
    for(s=[-1,1],z=[or_capture_z1+or_washer_t+or_m4_nut_h/2,
                     or_clamp_z0-or_washer_t-or_m4_nut_h/2])
        translate([-7,s>0?or_rod_y-7:-or_rod_y-45,z-1.5]) cube([14,52,3]);
}
module or_section_clip() {
    intersection() {
        children();
        // X=1 slice avoids the open clamp's central split, exposing its wall.
        if(or_part=="axial-slice") translate([0.8,-90,30]) cube([0.4,180,110]);
        else translate([-100,-90,30]) cube([100,180,110]);
    }
}
module or_assembly(section=false) {
    color([0.35,0.55,0.72]) if(section) or_section_clip() or_host_reference(); else or_host_reference();
    color([0.95,0.59,0.18]) if(section) or_section_clip() or_capture(); else or_capture();
    color([0.4,0.7,0.85,0.35]) if(section) or_section_clip() or_pipe(); else or_pipe();
    color([0.25,0.67,0.5]) if(section) or_section_clip() or_liner(); else or_liner();
    color([0.85,0.49,0.18]) if(section) or_section_clip() or_pipe_clamp(); else or_pipe_clamp();
    color([0.25,0.27,0.3]) if(section) or_section_clip() or_hardware(); else or_hardware();
}

if(or_part=="capture-positive") or_capture_half(true);
else if(or_part=="capture-negative") or_capture_half(false);
else if(or_part=="pipe-clamp-positive") or_clamp_half_raw(true);
else if(or_part=="pipe-clamp-negative") or_clamp_half_raw(false);
else if(or_part=="liner") or_liner();
else if(or_part=="host-flange-positive") or_host_additions(true);
else if(or_part=="host-positive") intersection() { or_host_reference(); or_halfspace(true); }
else if(or_part=="capture-host-collision") intersection() { or_capture(); or_host_reference(); }
else if(or_part=="capture-halves-collision") intersection() { or_capture_half(true); or_capture_half(false); }
else if(or_part=="clamp-halves-collision") intersection() { or_pipe_clamp_half(true); or_pipe_clamp_half(false); }
else if(or_part=="clamp-pipe-contact") intersection() { or_pipe_clamp(); or_pipe(); }
else if(or_part=="liner-host-pipe-collision") intersection() { or_liner(); union() { or_host_reference(); or_pipe(); } }
else if(or_part=="hardware-collision") intersection() { or_hardware(); or_printed(); }
else if(or_part=="crossed-hardware") intersection() { or_rod_hardware(); or_split_hardware(); }
else if(or_part=="tools-collision") intersection() { or_tools(); or_printed(); }
else if(or_part=="ballway-collision") intersection() { or_printed(); translate([0,0,40]) cylinder(h=80,d=41.5); }
else if(or_part=="seal-access-collision") intersection() { or_band_envelope(); union() { or_capture(); or_pipe_clamp(); or_hardware(); } }
else if(or_part=="capture-removal") intersection() { translate([or_service_positive?or_service:-or_service,0,0]) or_capture_half(or_service_positive); union() { or_host_reference(); or_capture_half(!or_service_positive); or_rod_hardware(); } }
else if(or_part=="pipe-clamp-removal") intersection() { translate([or_service_positive?or_service:-or_service,0,0]) or_pipe_clamp_half(or_service_positive); union() {or_pipe();or_rod_hardware();} }
else if(or_part=="liner-insertion") intersection() { translate([0,0,or_service]) or_liner(); or_host_reference(); }
else if(or_part=="pipe-insertion") intersection() { translate([0,0,or_service]) or_pipe(); union() { or_liner();or_host_reference(); } }
else if(or_part=="nut-insertion") intersection() {
    union() { or_capture();or_pipe_clamp(); }
    for(z=or_closure_z,y=[-or_closure_y,or_closure_y]) hull() {
        or_x_hex(-or_ear_outer_x+0.2,y,z,or_m4_nut_h,or_m4_af);
        or_x_hex(-or_ear_outer_x-20,y,z,or_m4_nut_h,or_m4_af);
    }
}
else if(or_part=="flange-stop") intersection() { translate([0,0,or_service]) or_capture(); or_host_reference(); }
else if(or_part=="flange-rotation") intersection() { or_capture(); rotate([0,0,or_angle]) or_host_reference(); }
else if(or_part=="old-collar-band-control") intersection() { or_band_envelope(); or_ring(50,55,72,57); }
else if(or_part=="old-rod-axis-control") intersection() { or_capture(); translate([0,-10,0]) or_rod_hardware(); }
else if(or_part=="section") or_assembly(true);
else if(or_part=="axial-slice") or_assembly(true);
else if(or_part=="exploded") {
    color("steelblue") or_host_reference(); color("seagreen") or_liner();
    for(s=[-1,1]) translate([s*42,0,0]) {
        color("orange") or_capture_half(s==1);
        color("coral") or_clamp_half_raw(s==1);
    }
    color([0.3,0.7,0.8,0.3]) or_pipe();
}
else or_assembly();
