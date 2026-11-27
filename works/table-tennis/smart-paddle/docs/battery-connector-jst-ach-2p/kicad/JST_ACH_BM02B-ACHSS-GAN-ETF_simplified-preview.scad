// Simplified visual model for JST BM02B-ACHSS-GAN-ETF (ACH, 2P).
//
// Evidence: JST eACH official datasheet archived one directory above.
// External envelope used here: 4.2 mm x 4.3 mm x 1.4 mm.
// The internal cavity is illustrative. This file and its generated STL are
// PREVIEW ONLY: do not use them for tolerance, collision, or manufacturing
// decisions. JST's official STEP requires a license form and was not fetched.

$fn = 48;

body_w = 4.2;
body_d = 4.3;
body_h = 1.4;
body_y0 = -2.0;

module housing() {
    difference() {
        // Official outside envelope, aligned to the KiCad footprint F.Fab.
        translate([-body_w / 2, body_y0, 0])
            cube([body_w, body_d, body_h]);

        // Illustrative top-entry cavity; intentionally not dimension evidence.
        translate([-1.38, -1.43, 0.55])
            cube([2.76, 2.72, 1.0]);

        // Front keying opening and the two contact-entry channels.
        translate([-0.48, body_y0 - 0.01, 0.72])
            cube([0.96, 0.72, 0.78]);
        for (x = [-0.6, 0.6])
            translate([x - 0.19, -1.58, 0.48])
                cube([0.38, 1.36, 1.0]);
    }
}

module latch_details() {
    // Small exterior shoulders make the connector direction readable in 3D.
    for (x = [-1.76, 1.46])
        translate([x, 1.72, 0.18])
            cube([0.30, 0.58, 0.72]);

    // Pin-1 corner mark; visual only.
    translate([-1.91, -1.80, 1.38])
        cylinder(h = 0.04, d = 0.22);
}

color([0.94, 0.91, 0.76]) {
    union() {
        housing();
        latch_details();
    }
}
