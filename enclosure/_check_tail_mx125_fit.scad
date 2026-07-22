// AUTO: MX1.25 正反 5P vs 拍柄 — check_tail_mx125_shell_fit.py
include <parameters.scad>
include <bezier_profile.scad>
USE_BEZIER_PROFILES = true;

module conn_bbox(z0, z1, c) {
    color(c, 0.85)
        translate([0.000, -97.200, (z0 + z1) / 2])
            cube([11.400, 5.000, z1 - z0], center = true);
}

conn_bbox(0.400, 3.900, "red");
conn_bbox(-3.900, -0.400, "orange");
