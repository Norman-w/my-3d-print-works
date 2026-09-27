// Candidate only: no measured spring load, friction or physical acceptance.
// Axis Z = launch direction; +X = floating pad service side; +Y completes frame.
include <spin-parameters.scad>
part = "assembly";
float_shift = 0;
preload_shift = 0;
bore_d = spin_guide_id;
probe_ball_d = ball_max_d;
show_reference_ball = false;
service_shift = 0;
$fn = 72;

module cyl_x(x,y,z,h,d,fn=72) {
    translate([x,y,z]) rotate([0,90,0]) cylinder(h=h,d=d,$fn=fn);
}
module hole_x(x,y,z,h,d) { cyl_x(x,y,z,h,d); }
module hex_x(x,y,z,h,af) { cyl_x(x,y,z,h,af/cos(30),6); }
module hole_y(x,y,z,h,d) {
    translate([x,y,z]) rotate([-90,0,0]) cylinder(h=h,d=d);
}
module bore() {
    translate([0,0,-barrel_engagement-sh_eps]) cylinder(h=barrel_engagement+sh_eps,d=barrel_od+2*interface_radial_clearance);
    translate([0,0,-sh_eps]) cylinder(h=transition_length+2*sh_eps,d1=barrel_id,d2=bore_d);
    translate([0,0,transition_length]) cylinder(h=sh_body_length-transition_length+sh_eps,d=bore_d);
}
module body() {
    difference() {
        union() {
            translate([0,0,-barrel_engagement]) cylinder(h=sh_body_length+barrel_engagement,d=sh_body_od);
            // Collar ears; M4 load returns through the full collar wall.
            for(s=[-1,1]) translate([-40,s<0?-7:sh_socket_slit/2,-22])
                cube([16,7-sh_socket_slit/2,18]);
            // Open service tower, side webs rooted in the cylindrical shell.
            for(s=[-1,1]) {
                translate([23,s<0?-20:16,20]) cube([32,4,49]);
                translate([23,s<0?-20:sh_carrier_width/2+sh_side_clearance,23.7])
                    cube([10,20-sh_carrier_width/2-sh_side_clearance,41.6]);
                // Inward ledges stop rigid carriage before it enters the bore.
                translate([21.5,s<0?-11.6:10,26]) cube([sh_carrier_front_x-21.5,1.6,34]);
            }
            for(z=[20,65.3]) translate([22,-20,z]) cube([33,40,3.7]);
            for(y=[-18,18],z=[27,61]) cyl_x(47,y,z,8,10);
        }
        bore();
        // Radial service aperture and free space for the full carriage.
        translate([16,-sh_carrier_width/2-sh_side_clearance,23.7])
            cube([45,sh_carrier_width+2*sh_side_clearance,41.6]);
        // Restore the inward ledges after this cavity subtraction.
        translate([-40,-sh_socket_slit/2,-barrel_engagement-sh_eps])
            cube([40,sh_socket_slit,barrel_engagement-1]);
        hole_y(-34,-9,-13,18,4.5);
        hole_y(-34,5,-13,4,8.5);
        translate([-34,-7.1,-13]) rotate([-90,0,0]) cylinder(h=3.4,d=7.1/cos(30),$fn=6);
        // Opposing insert mounts from -X; its flange seats on a machined plane.
        translate([-40,-11.2,17]) cube([12.5,22.4,52]);
        translate([-40,-8.3,25.7]) cube([24,16.6,34.6]);
        for(z=[20,66]) {
            hole_x(-32,0,z,9,3.4);
            hex_x(-27.52,0,z,2.7,5.8);
        }
        // Cover nut pockets open from +X before the cover is fitted.
        for(y=[-18,18],z=[27,61]) {
            hole_x(47,y,z,10,3.4);
            hex_x(49,y,z,2.7,5.8);
            translate([49,y<0?-25:y,z-3.4]) cube([2.7,7,6.8]);
        }
    }
    // Stops and ledges re-added after cavity subtraction, only outside the
    // 41.5 mm rigid corridor. This is checked with real CSG intersections.
    for(s=[-1,1]) translate([21.5,s<0?-11.6:10,26])
        cube([sh_carrier_front_x-21.5,1.6,34]);
}
module dovetail_section(clearance=0) {
    polygon([[sh_carrier_front_x-sh_eps,-2-clearance],
             [sh_carrier_front_x+4.2,-3-clearance],
             [sh_carrier_front_x+4.2,3+clearance],
             [sh_carrier_front_x-sh_eps,2+clearance]]);
}
module carriage() {
    difference() {
        union() {
            translate([sh_carrier_front_x,-sh_carrier_width/2,sh_carrier_z0])
                cube([sh_carrier_thickness,sh_carrier_width,sh_carrier_z1-sh_carrier_z0]);
            for(z=sh_guide_pin_z) {
                cyl_x(sh_carrier_back_x,0,z,4,8);
                cyl_x(sh_carrier_back_x,0,z,sh_guide_pin_length,sh_guide_pin_d);
            }
            cyl_x(sh_carrier_back_x,0,sh_spring_axis_z,1,sh_spring_pilot_d);
        }
        translate([0,0,26]) linear_extrude(height=36.1) dovetail_section(0.25);
        // M3 nuts inserted sideways before carriage enters the body.
        for(y=[-7,7]) {
            translate([26.75,y,55]) cylinder(h=8,d=3.4);
            translate([26.75,y,56.8]) cylinder(h=2.7,d=5.8/cos(30),$fn=6);
            translate([23.4,y<0?-11.1:7,56.8]) cube([6.7,4.1,2.7]);
        }
    }
}
module pad() {
    // Entire part is compliant. Material/hardness is an open input.
    // Keel inserts axially from +Z; no rigid piece enters the working face.
    union() {
        translate([0,-spin_pad_width/2,sh_pad_z0]) rotate([-90,0,0])
            linear_extrude(height=spin_pad_width)
                polygon([[sh_carrier_front_x-sh_pad_ramp_end_thickness,0],
                         [sh_pad_face_x,-sh_pad_ramp],
                         [sh_pad_face_x,-sh_pad_ramp-spin_pad_length],
                         [sh_carrier_front_x-sh_pad_ramp_end_thickness,-sh_pad_total_length],
                         [sh_carrier_front_x,-sh_pad_total_length],[sh_carrier_front_x,0]]);
        translate([0,0,26.2]) linear_extrude(height=35.6) dovetail_section(0);
    }
}
module pad_keeper() {
    difference() {
        translate([sh_carrier_front_x,-sh_carrier_width/2,62]) cube([sh_carrier_thickness,sh_carrier_width,3]);
        for(y=[-7,7]) {
            translate([26.75,y,61.9]) cylinder(h=3.2,d=3.4);
            translate([26.75,y,63.2]) cylinder(h=1.82,d1=3.4,d2=6.5);
        }
    }
}
module opposite_guide() {
    difference() {
        union() {
            translate([-31,-11,17.2]) cube([3.5,22,51.6]);
            translate([-27.5,-8,26]) cube([12,16,34]);
        }
        translate([0,0,15]) cylinder(h=56,d=bore_d);
        for(z=[20,66]) hole_x(-32,0,z,6,3.4);
    }
}
module cover() {
    difference() {
        union() {
            translate([55,-20,20]) cube([4,40,49]);
            for(y=[-18,18],z=[27,61]) cyl_x(55,y,z,4,10);
            // Outer seat stop; separate cage permits axial seat assembly.
            cyl_x(50.5,0,sh_spring_axis_z,4.5,12);
            // M4 nut reacts on this outer boss, not a thin pocket lip.
            cyl_x(59,0,sh_spring_axis_z,6,14);
            // Outward stops belong to the removable cover. Removing the cover
            // removes these stops, so the carriage can be inserted/extracted.
            for(y=[-9,9],z=[32,54])
                cyl_x(sh_carrier_back_x+sh_float_travel,y,z,55-sh_carrier_back_x-sh_float_travel+0.1,6);
        }
        for(y=[-18,18],z=[27,61]) hole_x(54.9,y,z,4.2,3.4);
        for(y=[-11,11]) hole_x(54.9,y,sh_spring_axis_z,4.2,3.4);
        for(z=sh_guide_pin_z) hole_x(54.9,0,z,4.2,sh_guide_pin_d+0.5);
        hole_x(49,0,sh_spring_axis_z,18,4.5);
        hex_x(55.7,0,sh_spring_axis_z,3.3,7.1);
        translate([55.7,0,sh_spring_axis_z-4.1]) cube([3.3,21,8.2]);
    }
}
module spring_cage() {
    difference() {
        union() {
            cyl_x(sh_spring_guide_front_x,0,sh_spring_axis_z,18,sh_spring_guide_od);
            for(y=[-11,11]) translate([48,y-3,40]) cube([7,6,6]);
        }
        hole_x(36.9,0,sh_spring_axis_z,6.6,11);
        hole_x(43.5,0,sh_spring_axis_z,11.6,sh_spring_guide_id);
        for(y=[-11,11]) {
            hole_x(47.9,y,sh_spring_axis_z,7.3,3.4);
            hex_x(49,y,sh_spring_axis_z,2.7,5.8);
            translate([49,y<0?-15:y,sh_spring_axis_z-3.4]) cube([2.7,4,6.8]);
        }
    }
}
module spring_seat() {
    union() {
        cyl_x(sh_spring_seat_front_x,0,sh_spring_axis_z,sh_spring_seat_thickness,sh_spring_seat_d);
        cyl_x(sh_spring_seat_front_x-1,0,sh_spring_axis_z,1.02,sh_spring_pilot_d);
    }
}
module hard_fixed() { body(); opposite_guide(); cover(); spring_cage(); }
module moving_hard() { translate([float_shift,0,0]) { carriage(); pad_keeper(); } }
module hard_all() { hard_fixed(); moving_hard(); translate([-preload_shift,0,0]) spring_seat(); }
module hardware_reference() {
    // Nominal fastener envelopes, no threads. Actual purchased heads remain to measure.
    for(y=[-18,18],z=[27,61]) { cyl_x(47,y,z,12,3); cyl_x(59,y,z,3,5.5); }
    for(y=[-11,11]) { cyl_x(47,y,43,12,3); cyl_x(59,y,43,3,5.5); }
    for(z=[20,66]) { cyl_x(-31,0,z,8,3); cyl_x(-34,0,z,3,5.5); }
    hole_y(-34,-11,-13,16,4); hole_y(-34,5,-13,4,7);
    cyl_x(50.5-preload_shift,0,43,25,4);
    cyl_x(75.5-preload_shift,0,43,6,14);
    translate([float_shift,0,0]) for(y=[-7,7]) {
        translate([26.75,y,55]) cylinder(h=8.3,d=3);
        translate([26.75,y,63.3]) cylinder(h=1.7,d1=3,d2=6);
    }
}
module assembly() {
    color([0.25,0.49,0.67]) body();
    color([0.8,0.85,0.86]) opposite_guide();
    color([0.97,0.63,0.18]) moving_hard();
    color([0.29,0.72,0.53]) translate([float_shift,0,0]) pad();
    color([0.34,0.41,0.47]) cover();
    color([0.65,0.72,0.75]) spring_cage();
    color([0.83,0.45,0.2]) translate([-preload_shift,0,0]) spring_seat();
    color([0.18,0.21,0.23]) hardware_reference();
    if(show_reference_ball) color([1,1,1,0.35])
        translate([(probe_ball_d-bore_d)/2,0,43]) sphere(d=probe_ball_d);
}
if(part=="body") body();
else if(part=="carriage") carriage();
else if(part=="pad") pad();
else if(part=="pad-keeper") pad_keeper();
else if(part=="opposite-guide") opposite_guide();
else if(part=="cover") cover();
else if(part=="spring-cage") spring_cage();
else if(part=="spring-seat") spring_seat();
else if(part=="hard-corridor") intersection() {
    hard_all(); translate([0,0,-barrel_engagement]) cylinder(h=sh_body_length+barrel_engagement,d=sh_clearance_probe_d);
}
else if(part=="slide-collision") intersection() { moving_hard(); hard_fixed(); }
else if(part=="seat-collision") intersection() { translate([-preload_shift,0,0]) spring_seat(); hard_fixed(); }
else if(part=="pad-hard-collision") intersection() { pad(); carriage(); }
else if(part=="cover-removal-collision") intersection() {
    translate([service_shift,0,0]) { cover(); spring_cage(); spring_seat(); }
    union() { body(); opposite_guide(); moving_hard(); }
}
else if(part=="carriage-removal-collision") intersection() {
    translate([service_shift,0,0]) { carriage(); pad_keeper(); pad(); }
    union() { body(); opposite_guide(); }
}
else if(part=="fixed-parts-collision") union() {
    intersection() { body(); opposite_guide(); }
    intersection() { body(); cover(); }
    intersection() { body(); spring_cage(); }
    intersection() { cover(); spring_cage(); }
}
else if(part=="hardware-interference") intersection() { hardware_reference(); hard_all(); }
else if(part=="tool-access") intersection() {
    hard_all();
    union() {
        for(y=[-18,18],z=[27,61]) cyl_x(59.1,y,z,35,6);
        for(y=[-11,11]) cyl_x(59.1,y,43,35,6);
        cyl_x(65.1,0,43,30,12);
        for(z=[20,66]) cyl_x(-65,0,z,33.9,6);
        hole_y(-34,9.1,-13,25,8);
    }
}
else if(part=="soft-ball-overlap") intersection() {
    translate([float_shift,0,0]) pad();
    translate([(probe_ball_d-bore_d)/2,0,43]) sphere(d=probe_ball_d);
}
else if(part=="section") intersection() { assembly(); translate([-40,-40,-26]) cube([115,40,104]); }
else if(part=="exploded") {
    color([0.25,0.49,0.67]) body();
    translate([-17,0,0]) color("silver") opposite_guide();
    translate([25,0,0]) { color("orange") carriage(); color("seagreen") pad(); translate([0,0,12]) pad_keeper(); }
    translate([50,0,0]) { color("grey") cover(); spring_cage(); color("orange") spring_seat(); }
}
else assembly();
