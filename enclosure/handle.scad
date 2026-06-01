// SmartPaddle Handle — Butterfly FL profile, internal cavities
// Prints upright with support, Bambu X1C, PLA, 0.16mm layers

include <parameters.scad>

// t=0 at blade end (+Z), t=1 at butt (-Z) — FL: neck → waist → flare
function fl_width(t) =
    let(
        waist_t = 0.28,
        w0 = handle_neck_w * 0.98
    )
    t <= waist_t
        ? handle_neck_w * (1 - 0.05 * sin(t / waist_t * 90))
        : w0 + (handle_butt_w - w0) * (3 * pow((t - waist_t) / (1 - waist_t), 2) - 2 * pow((t - waist_t) / (1 - waist_t), 3));

module rounded_rect_2d(w, h, r) {
    rr = min(r, w / 2 - 0.1, h / 2 - 0.1);
    minkowski() {
        square([w - 2 * rr, h - 2 * rr], center = true);
        circle(r = rr, $fn = 24);
    }
}

module handle_outer() {
    steps = 48;
    for (i = [0:steps - 1]) {
        t = i / steps;
        z = handle_length / 2 - t * handle_length;
        w = fl_width(t);
        translate([0, 0, z - handle_length / steps / 2])
            linear_extrude(height = handle_length / steps + 0.02, convexity = 4)
                rounded_rect_2d(w, handle_thickness, handle_corner_r);
    }
}

module handle_body() {
    difference() {
        handle_outer();

        // PCB cavity
        translate([0, pcb_y_offset, pcb_cavity_l / 2 - handle_length / 2 + blade_neck_l])
            cube([pcb_cavity_w, pcb_cavity_h, pcb_cavity_l], center = true);

        // Battery cavity (below PCB, toward handle bottom)
        translate([0, battery_y_offset, -handle_length / 2 + battery_cavity_l / 2 + 10])
            cube([battery_cavity_w, battery_cavity_h, battery_cavity_l], center = true);

        // USB-C opening
        translate([0, 0, handle_length / 2 - blade_neck_l - pcb_cavity_l / 2 + 5])
            cube([usb_cutout_w, usb_cutout_h, 10], center = true);

        // Ventilation slots (near charging IC)
        for (i = [0:vent_count - 1]) {
            translate([0, -handle_thickness / 4, handle_length / 2 - blade_neck_l - 15 - i * 6])
                cube([vent_slot_w, 10, vent_slot_l], center = true);
        }

        // PCB mounting bosses (M2)
        boss_offset_l = pcb_cavity_l / 2 - 8;
        boss_offset_w = pcb_cavity_w / 2 - 4;

        for (z = [-1, 1]) {
            for (x = [-1, 1]) {
                translate([x * boss_offset_w, 0, z * boss_offset_l])
                    cylinder(d = boss_diameter, h = 20, center = true);
            }
        }

        // Wire channel to blade (for piezo sensor wires)
        translate([0, pcb_y_offset, handle_length / 2])
            cube([6, 4, 10], center = true);
    }
}

handle_body();
