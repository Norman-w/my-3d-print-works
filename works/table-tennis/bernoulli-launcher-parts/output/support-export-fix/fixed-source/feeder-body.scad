// Candidate feeder body. Interfaces and seal implementation remain unverified.
// Units mm; feed +Z. Export halves separately. No physical acceptance implied.
include <parameters.scad>

body_part = "assembly"; // assembly, positive_half, negative_half, section
body_show_reference = false;
body_eps = 0.02;
body_split_boss_x = 7;
body_split_boss_y = 40;
body_split_boss_r = 5;
body_split_bolt_z = [-72,-46,-10,16];
body_rib_thickness = 2.4;
body_rib_embed = 0.8;
body_port_width = 8;
body_port_length = 11;
body_spigot_bore = 45.4;
body_spigot_wall = (feed_socket_od-body_spigot_bore)/2;
body_inlet_start = guide_start_z-transition_length-feed_socket_length;
body_inlet_shoulder = guide_start_z-transition_length;
body_guide_end = guide_start_z+guide_length;
body_outlet_shoulder = body_guide_end+transition_length;
body_outlet_stop = 2;
body_outlet_end = body_outlet_shoulder+body_outlet_stop+y_stub_engagement;
body_outlet_socket_id = y_stub_od+2*interface_radial_clearance;
body_outlet_od = body_outlet_socket_id+2*body_wall;
body_outer_d = body_id+2*body_wall;
body_side_mount_x = 35.5;
body_side_mount_y = -14;
body_side_mount_z = [-45,16];
body_side_mount_size = 10;
body_side_mount_inner = 30.5;
body_side_mount_blind_end = 31.5;
body_side_seat_z = [0,-gate_spacing];
body_seal_state = "OPEN";

assert(body_spigot_wall>=1.8);
assert(body_spigot_bore>ball_max_d);
assert(body_split_boss_y+body_split_boss_r<=45);
assert(body_outlet_end-body_inlet_start<220,
    "Recheck the chosen upright printing envelope");
assert(body_port_length+4<transition_length);

module body_tube(z,h,od,id) {
    difference() {
        translate([0,0,z]) cylinder(h=h,d=od);
        translate([0,0,z-body_eps]) cylinder(h=h+2*body_eps,d=id);
    }
}

module body_taper(z,h,od1,od2,id1,id2) {
    difference() {
        translate([0,0,z]) cylinder(h=h,d1=od1,d2=od2);
        translate([0,0,z-body_eps])
            cylinder(h=h+2*body_eps,d1=id1,d2=id2);
    }
}

module body_outer_shell() {
    union() {
        body_tube(guide_start_z,guide_length,body_outer_d,body_id);
        body_taper(body_inlet_shoulder,transition_length,
            hose_od,body_outer_d,body_spigot_bore,body_id);
        body_tube(body_inlet_start,feed_socket_length,
            feed_socket_od,body_spigot_bore);
        // Shallow retention ridges, below nominal hose ID; clamp remains needed.
        for(z=[body_inlet_start+6,body_inlet_start+18])
            body_taper(z,1.5,feed_socket_od,feed_socket_od+0.4,
                body_spigot_bore,body_spigot_bore);
        body_taper(body_guide_end,transition_length,
            body_outer_d,body_outlet_od,body_id,body_spigot_bore);
        body_tube(body_outlet_shoulder,body_outlet_stop,
            body_outlet_od,body_spigot_bore);
        body_tube(body_outlet_shoulder+body_outlet_stop,y_stub_engagement,
            body_outlet_od,body_outlet_socket_id);
    }
}

module body_port(z,angle) {
    // Radial through-slot in the INNER taper only; never cut outer shell here.
    rotate([0,0,angle])
        hull() for(dz=[-(body_port_length-body_port_width)/2,
                       (body_port_length-body_port_width)/2])
            translate([10,0,z+dz]) rotate([0,90,0])
                cylinder(h=26,d=body_port_width,$fn=40);
}

module body_inner_guide() {
    difference() {
        union() {
            body_tube(guide_start_z,guide_length,guide_od,guide_id);
            body_taper(body_inlet_shoulder,transition_length,
                body_spigot_bore+4,guide_od,body_spigot_bore,guide_id);
            body_taper(body_guide_end,transition_length,
                guide_od,body_spigot_bore+4,guide_id,body_spigot_bore);
        }
        for(z=[body_inlet_shoulder+transition_length/2,
               body_guide_end+transition_length/2],a=[45,135,225,315])
            body_port(z,a);
        for(z=body_side_seat_z)
            translate([-60,0,z]) rotate([0,90,0])
                cylinder(h=120,r=finger_tip_radius+radial_print_clearance);
    }
}

module body_ribs() {
    // Two load paths connect both sleeve halves to the outside shell.
    for(sign=[-1,1])
        translate([-body_rib_thickness/2,
            sign==1?guide_od/2-body_rib_embed:-body_id/2-body_rib_embed,guide_start_z])
            cube([body_rib_thickness,(body_id-guide_od)/2+2*body_rib_embed,
                guide_length]);
}

module body_split_bosses() {
    for(y=[-body_split_boss_y,body_split_boss_y],z=body_split_bolt_z)
        hull() {
            translate([-body_split_boss_x,y,z]) rotate([0,90,0])
                cylinder(h=2*body_split_boss_x,r=body_split_boss_r,$fn=40);
            // Inboard foot joins the shell instead of a tangent-only contact.
            translate([-body_split_boss_x,y>0?30:-34,z-6])
                cube([2*body_split_boss_x,4,4]);
        }
}

module body_mount_bosses() {
    for(side=[-1,1]) {
        for(z=body_side_mount_z)
            translate([side==1?body_side_mount_inner:-body_side_mount_x,
                body_side_mount_y-body_side_mount_size/2,z-body_side_mount_size/2])
                cube([body_side_mount_x-body_side_mount_inner,
                    body_side_mount_size,body_side_mount_size]);
        for(z=body_side_seat_z)
            translate([side==1?31.5:-body_side_mount_x,-10,z-9])
                cube([body_side_mount_x-31.5,19,18]);
    }
}

module body_split_fastener_cuts() {
    for(y=[-body_split_boss_y,body_split_boss_y],z=body_split_bolt_z) {
        translate([-10,y,z]) rotate([0,90,0])
            cylinder(h=20,d=fastener_d);
        // Head and captive nut enter from the two exterior X faces.
        translate([body_split_boss_x-3.2,y,z]) rotate([0,90,0])
            cylinder(h=3.2+body_eps,d=6.2,$fn=40);
        translate([-body_split_boss_x-body_eps,y,z]) rotate([0,90,0])
            cylinder(h=nut_depth+body_eps,r=nut_af/sqrt(3),$fn=6);
    }
}

module body_side_cuts() {
    for(side=[-1,1]) {
        for(z=body_side_mount_z) {
            translate([side*(body_side_mount_x-nut_depth/2),body_side_mount_y,z])
                rotate([0,90,0])
                    cylinder(h=nut_depth+2*body_eps,r=nut_af/sqrt(3),$fn=6,center=true);
            translate([side*(body_side_mount_blind_end+body_side_mount_x)/2,
                body_side_mount_y,z]) rotate([0,90,0])
                cylinder(h=body_side_mount_x-body_side_mount_blind_end+2*body_eps,
                    d=fastener_d,center=true);
        }
        for(z=body_side_seat_z) {
            translate([side==1?33.5:-60,-4.75,z-4.25])
                cube([26.5,9.5,8.5]);
            translate([side==1?23.5:-33.5,0,z]) rotate([0,90,0])
                cylinder(h=10,r=finger_tip_radius+radial_print_clearance);
        }
    }
}

module feeder_body_full() {
    difference() {
        union() {
            body_outer_shell();
            body_inner_guide();
            body_ribs();
            body_split_bosses();
            body_mount_bosses();
        }
        body_split_fastener_cuts();
        body_side_cuts();
    }
}

module feeder_body_half(positive=true) {
    intersection() {
        feeder_body_full();
        translate([positive?0:-100,-100,body_inlet_start-1])
            cube([100,200,body_outlet_end-body_inlet_start+2]);
    }
}

echo("CANDIDATE: seam sealing, actual Y interface and physical airflow remain OPEN");
echo("body Z envelope",body_inlet_start,body_outlet_end);
echo("inner guide cylindrical domain",guide_start_z,body_guide_end);
if(body_part=="assembly") color([0.66,0.70,0.73]) feeder_body_full();
else if(body_part=="positive_half") feeder_body_half(true);
else if(body_part=="negative_half") feeder_body_half(false);
else if(body_part=="section") color([0.66,0.70,0.73]) feeder_body_half(true);
else assert(false,"Unknown feeder body part");
