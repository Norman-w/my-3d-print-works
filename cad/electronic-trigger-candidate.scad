// Electronic finger trigger candidate on the ORIGINAL fixed beam, in mm.
// Pulling toward the grip is a negative rotation about the Y-axis.
// The switch and spring are catalog-based envelopes, not purchased hardware.
sh_library_mode = true;
include <feeder-support-harness.scad>
use <electric-feeder-assembly.scad>

et_part = "scene"; // scene, detail, mechanism, beam, lever, mount, switch, spring, probe
et_angle = 0; // 0 released, -8 degrees fully pulled
et_feed_t = 0;
et_probe = "lever-mount";
et_switch_shift = 0; // assembly calibration in X; nominal scene is zero
et_eps = 0.02;
et_pivot = [58, -52, -10];
// D2F-01FL30-D3 simulated roller lever: nominal OP is 9.5 mm from the
// housing bottom. Its exact free lever shape is only an illustration here;
// the real switch must be shifted in the slots to its own click.
// Raise the switch contact 4 mm for a larger released-to-click stroke while
// leaving the finger swing and spring seats unchanged. The case remains on
// the same fixed backplate; the real roller still requires click calibration.
et_switch_x = 43.988;
et_switch_z = -6.9;
et_switch_y = -55; // case seats on the fixed backplate when M2 screws are tightened
et_switch_case_depth_x = 6.5;
et_switch_case_depth_y = 5.8;
et_switch_actuator_op = 9.5;
et_switch_actuator_z_offset = 9.4; // drawing-based nominal contact station
et_switch_actuator_z = 2.5;
et_switch_marker_radius = 0.45;
// D3 solder tabs: three 2.2-mm-wide blades at 5.08-mm pitch, projecting
// 3.5 mm below the housing. Solid blades conservatively fill solder holes.
et_switch_terminal_length_x = 3.5;
et_switch_terminal_width_z = 2.2;
et_switch_terminal_thickness_y = 0.4;
et_switch_terminal_first_z_offset = 1.32;
et_switch_terminal_pitch_z = 5.08;
et_switch_op_tolerance = 1.0; // Omron L30 OP 9.5 +/-1.0 mm
et_switch_slot_x_min = 43.8;
et_switch_slot_x_max = 47.7; // 3.9 mm hole-center adjustment
et_switch_slot_d = 2.8; // M2 clearance plus catalog hole-pitch/FDM allowance
et_switch_hole_x_offset = 1.5; // mounting holes sit 1.5 mm above case bottom
et_switch_hole_z_offset = 3.15; // first hole from the 12.8 mm case edge
et_switch_cheek_start_x = 54.2;
// Two holes in the fixed PETG backplate accept one <=2.5-mm signal-wire
// cable tie. The tie carries cable pull into the beam, never into D3 tabs.
et_wire_tie_hole_x = [42.5, 48.5];
et_wire_tie_hole_z = -13.5;
et_wire_tie_hole_d = 3;
et_switch_ot_min = 0.5;
et_switch_md_max = 0.5;
et_switch_of_max = 0.3;
et_switch_click_calibration_angle = -7; // ~1 degree before hard stop
et_nose_x = 56.5;
et_nose_z = 2.5;
et_nose_d = 3;
// MISUMI WR4-15 catalog candidate: OD4, L15 +/-1.5, k0.3 +/-10% N/mm.
// The seat separation, rather than nominal free length, defines preload.
et_spring_od = 4;
et_spring_free = 15;
et_spring_length_tolerance = 1.5;
et_spring_k_nominal = 0.3;
et_spring_k_tolerance = 0.1;
et_spring_max_deflection_fraction = 0.6;
et_spring_catalog_max_load = 2.6;
et_spring_pocket_d = 5.2;
et_spring_center_y = -51;
et_spring_center_z = -33;
et_spring_fixed_seat_x = 64;
et_spring_moving_seat_x = 52.0;
et_backplate_front_y = -55;
et_paddle_back_y = -54.8;
et_paddle_relief_front_y = -55.3; // 0.5 mm gap away from both hard stops
et_pivot_cheek_back_y = -49;
et_pivot_spacer_length = 6;
// HIROSUGI CB-306-5E reference: nickel-plated brass, OD5 +/-0.05,
// ID3.2 +/-0.15, L6 +/-0.1. Not a purchased/verified component.
et_pivot_spacer_od = 5;
et_pivot_spacer_od_tolerance = 0.05;
et_pivot_spacer_id = 3.2;
et_pivot_spacer_length_tolerance = 0.1;
et_lever_pivot_bore_d = 5.2;
et_lever_pivot_width = 5.2;

assert(sh_grip_x == 76 && sh_grip_y == -52 && sh_grip_r == 11,
       "Trigger mount must be reviewed if the beam grip changes");
assert(et_angle <= 1 && et_angle >= -9.1); // +1/-9 deliberately probe stops
assert(et_feed_t >= 0 && et_feed_t <= 1);

module et_box(x0,x1,y0,y1,z0,z1) {
    translate([x0,y0,z0]) cube([x1-x0,y1-y0,z1-z0]);
}
module et_y_cyl(x,z,y0,h,d) {
    translate([x,y0,z]) rotate([-90,0,0]) cylinder(h=h,d=d,$fn=64);
}
module et_x_cyl(y,z,x0,h,d) {
    translate([x0,y,z]) rotate([0,90,0]) cylinder(h=h,d=d,$fn=64);
}
module et_pull(a=et_angle) {
    translate(et_pivot) rotate([0,a,0]) translate(-et_pivot) children();
}
function et_rotated_x(x,z,a) = et_pivot[0]
    +(x-et_pivot[0])*cos(a)+(z-et_pivot[2])*sin(a);

// The four-mm back plate joins the fixed 22-mm grip over a broad area.
// A six-mm gap between cheeks takes a six-mm metal pivot sleeve, so screw
// tightening cannot squeeze the printed lever. The front and rear finger
// stops carry the user's force; the switch lever is not a stop.
module et_backplate() {
    difference() {
        et_box(39,70,-59,et_backplate_front_y,-39,7);
        // Shave only the lower sweep area. The pivot zone stays at Y=-55,
        // preserving the six-mm span between the two fixed cheeks.
        et_box(46,59.35,et_paddle_relief_front_y,
               et_backplate_front_y+et_eps,-39,-28);
    }
}
module et_mount_blank() {
    union() {
        et_backplate();
        et_box(et_switch_cheek_start_x,63,et_pivot_cheek_back_y,-45,-16,-4);
        et_box(61,70,et_pivot_cheek_back_y,-45,-15,-6);
        et_box(43,46,-57,-47,-38,-28); // released stop
        et_box(59.35,66,-57,-47,-38,-28); // pulled stop/spring seat
    }
}
module et_mount() {
    difference() {
        et_mount_blank();
        // Open the finger window while leaving a four-mm rim and a lower
        // crossbar that carry the released stop back to the grip.
        et_box(47,59,-60,-54.8,-35,-18);
        et_y_cyl(et_pivot[0],et_pivot[2],-60,16,3.4);
        // Two M2 slots allow calibration against the real switch click.
        for(z=[et_switch_z+et_switch_hole_z_offset,
               et_switch_z+et_switch_hole_z_offset+6.5]) hull()
            for(x=[et_switch_slot_x_min,et_switch_slot_x_max])
            et_y_cyl(x,z,-60,6,et_switch_slot_d);
        // Fixed pocket stops before the original grip starts near X=65.
        et_x_cyl(et_spring_center_y,et_spring_center_z,59.1,
                 et_spring_fixed_seat_x-59.1,et_spring_pocket_d);
        for(z=[-17,-22]) et_y_cyl(46.5,z,-60,6,2.4);
    }
}
module et_beam_without_wire_relief() { union() { sh_beam(); et_mount(); } }
module et_wire_tie_holes() {
    for(x=et_wire_tie_hole_x)
        et_y_cyl(x,et_wire_tie_hole_z,-59.1,4.2,et_wire_tie_hole_d);
}
module et_beam() {
    difference() {
        et_beam_without_wire_relief();
        et_wire_tie_holes();
    }
}

module et_lever_blank() {
    union() {
        et_y_cyl(58,-10,-54.6,et_lever_pivot_width,9.4);
        hull() {
            et_y_cyl(58,-10,-54.6,et_lever_pivot_width,8.8);
            et_y_cyl(51,-33,-54.6,et_lever_pivot_width,8);
        }
        // Centered 7.6-mm paddle leaves 1.2 mm per side of the 5.2-mm bore.
        // It stays clear of the fixed back plate behind it.
        et_y_cyl(51,-33,et_paddle_back_y,7.6,10);
        // This upper nose moves toward -X when the finger pulls toward +X.
        // Keep its root narrower than the pivot boss so the moving tongue
        // clears the D2F case at the positive end of OP calibration.
        hull() {
            et_y_cyl(58,-10,-54.6,et_lever_pivot_width,6);
            et_y_cyl(et_nose_x,et_nose_z,-54.6,et_lever_pivot_width,et_nose_d);
        }
    }
}
module et_lever_unposed() {
    difference() {
        et_lever_blank();
        et_y_cyl(58,-10,-55,6,et_lever_pivot_bore_d);
        // Deeper moving seat leaves preload even at the short catalog limit.
        et_x_cyl(et_spring_center_y,et_spring_center_z,et_spring_moving_seat_x,
                 56.45-et_spring_moving_seat_x,et_spring_pocket_d);
    }
}
module et_lever(a=et_angle) { et_pull(a) et_lever_unposed(); }

// D2F's 12.8 x 6.5 x 5.8 body and solid D3 solder-tab proxies. The actual
// spring lever, solder joints and wire bending room still need verification.
module et_switch_body() {
    et_box(et_switch_x+et_switch_shift,
           et_switch_x+et_switch_shift+et_switch_case_depth_x,
           et_switch_y,et_switch_y+et_switch_case_depth_y,
           et_switch_z,et_switch_z+12.8);
}
module et_switch_terminals() {
    for(i=[0:2]) let(zc=et_switch_z+et_switch_terminal_first_z_offset
                            +i*et_switch_terminal_pitch_z)
        et_box(et_switch_x+et_switch_shift-et_switch_terminal_length_x,
               et_switch_x+et_switch_shift,
               et_switch_y+et_switch_case_depth_y/2-et_switch_terminal_thickness_y/2,
               et_switch_y+et_switch_case_depth_y/2+et_switch_terminal_thickness_y/2,
               zc-et_switch_terminal_width_z/2,zc+et_switch_terminal_width_z/2);
}
module et_switch_actuation_target() {
    // A tiny reference target at nominal OP, not the free-position envelope.
    et_x_cyl(-52,et_switch_actuator_z,
             et_switch_x+et_switch_shift+et_switch_actuator_op
             -et_switch_marker_radius,
             et_switch_marker_radius,2*et_switch_marker_radius);
}
module et_switch_illustrative_lever() {
    // Catalog drawing silhouette for explaining the contact path only.
    color([.70,.73,.76]) hull() {
        et_y_cyl(et_switch_x+et_switch_shift+et_switch_case_depth_x-.3,
                 et_switch_z+1,-53.5,3,.4);
        et_y_cyl(et_switch_x+et_switch_shift+et_switch_actuator_op-.5,
                 et_switch_actuator_z,-53.5,3,.4);
    }
}
module et_switch_reference() {
    color([.09,.10,.12]) et_switch_body();
    color([.68,.70,.72]) et_switch_terminals();
    et_switch_illustrative_lever();
    color([.75,.19,.14]) et_switch_actuation_target();
}
module et_spring_reference(a=et_angle) {
    // A transparent cylinder is the installed-length envelope, not a coil.
    color([.89,.70,.13,.65])
        et_x_cyl(et_spring_center_y,et_spring_center_z,
                 et_rotated_x(et_spring_moving_seat_x,et_spring_center_z,a),
                 et_spring_fixed_seat_x
                 -et_rotated_x(et_spring_moving_seat_x,et_spring_center_z,a),
                 et_spring_od);
}
module et_pivot_reference() {
    color([.67,.70,.73]) {
        difference() {
            et_y_cyl(58,-10,et_backplate_front_y,
                     et_pivot_spacer_length,et_pivot_spacer_od);
            et_y_cyl(58,-10,-55.1,6.2,et_pivot_spacer_id);
        }
        et_y_cyl(58,-10,-59.4,18,3);
        et_y_cyl(58,-10,-61,1.6,5.5);
    }
}
module et_scene(a=et_angle) {
    ed_assembly(); // current electric structural preview still owns the beam
    color([.18,.45,.68]) et_mount();
    color([.97,.40,.11]) et_lever(a);
    et_switch_reference();
    et_pivot_reference();
    et_spring_reference(a);
}
module et_detail(a=et_angle) {
    color([.18,.45,.68,.28]) et_beam();
    color([.97,.40,.11]) et_lever(a);
    et_switch_reference();
    et_pivot_reference();
    et_spring_reference(a);
}
module et_mechanism(a=et_angle) {
    color([.18,.45,.68,.42]) et_mount();
    color([.97,.40,.11]) et_lever(a);
    et_switch_reference();
    et_pivot_reference();
    et_spring_reference(a);
}
module et_probe_geometry() {
    if(et_probe=="lever-mount") intersection(){ et_lever(); et_mount(); }
    else if(et_probe=="lever-switch-body") intersection(){
        et_lever(); et_switch_body();
    }
    else if(et_probe=="lever-switch-actuation-target") intersection(){
        et_lever(); et_switch_actuation_target();
    }
    else if(et_probe=="lever-beam") intersection(){
        et_lever(); sh_beam();
    }
    else if(et_probe=="switch-beam") intersection(){
        et_switch_body(); sh_beam();
    }
    else if(et_probe=="switch-terminals-fixed") intersection(){
        et_switch_terminals(); ed_fixed_printed();
    }
    else if(et_probe=="switch-terminals-moving") intersection(){
        et_switch_terminals(); ed_moving_printed(et_feed_t);
    }
    else if(et_probe=="mount-other-fixed") intersection(){
        et_mount(); difference(){ ed_fixed_printed(); sh_beam(); }
    }
    else if(et_probe=="mount-moving") intersection(){
        et_mount(); ed_moving_printed(et_feed_t);
    }
    else if(et_probe=="lever-moving") intersection(){
        et_lever(); ed_moving_printed(et_feed_t);
    }
    else if(et_probe=="lever-original-hardware") intersection(){
        et_lever(); union(){ ed_fixed_hardware(); ed_moving_hardware(et_feed_t); }
    }
    else if(et_probe=="switch-other-fixed") intersection(){
        et_switch_body(); difference(){ ed_fixed_printed(); sh_beam(); }
    }
    else assert(false,"Unknown trigger probe");
}

if(et_part=="scene") et_scene();
else if(et_part=="detail") et_detail();
else if(et_part=="mechanism") et_mechanism();
else if(et_part=="beam") et_beam();
else if(et_part=="lever") et_lever_unposed();
else if(et_part=="mount") et_mount();
else if(et_part=="switch") et_switch_reference();
else if(et_part=="spring") et_spring_reference();
else if(et_part=="probe") et_probe_geometry();
else assert(false,"Unknown electronic trigger candidate part");
