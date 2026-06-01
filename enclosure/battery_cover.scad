// SmartPaddle Battery Cover — snap-fit at FL handle butt
// Prints flat on build plate, Bambu X1C, PLA, 0.16mm layers

include <parameters.scad>

module rounded_rect_2d(w, h, r) {
    rr = min(r, w / 2 - 0.1, h / 2 - 0.1);
    minkowski() {
        square([w - 2 * rr, h - 2 * rr], center = true);
        circle(r = rr, $fn = 24);
    }
}

module battery_cover() {
    cover_h = battery_cavity_h + wall_thickness * 1.5;
    cover_w = handle_butt_w - wall_thickness * 2;
    cover_t = handle_thickness - wall_thickness * 2;

    difference() {
        union() {
            linear_extrude(height = cover_h, center = true, convexity = 4)
                rounded_rect_2d(cover_w + cover_lip_w * 2, cover_t + cover_lip_w * 2, handle_corner_r);

            // Snap-fit lips
            for (z = [-1, 1]) {
                translate([0, 0, z * (cover_h / 2 + cover_lip_h / 2)])
                    linear_extrude(height = cover_lip_h, convexity = 4)
                        rounded_rect_2d(cover_w + cover_lip_w * 2, cover_t + cover_lip_w * 2, handle_corner_r);
            }
        }

        // Hollow interior
        translate([0, 0, 0])
            cube([cover_w, cover_t, handle_length], center = true);

        // Fingernail groove for opening
        translate([0, cover_t / 2 + 1, wall_thickness / 2])
            sphere(r = cover_fingernail_r, $fn = 32);

        // Ventilation slots match handle
        for (i = [0:vent_count - 1]) {
            translate([0, 0, -battery_cavity_l / 4 + i * 6])
                cube([vent_slot_w, 15, vent_slot_l], center = true);
        }
    }
}

battery_cover();
