// Independent X1C/PETG geometry screen: tapered lower web carries the fork
// beam around the shell's lower M3 screw root. The two shell screw channels
// remain untouched. This is not a force-rated or selected printable part.
use <electric-rocker-service-fork-reinforcement-screen.scad>
use <electric-rocker-service-fork-screen.scad>
use <electric-output-crosshead-screen.scad>
use <electric-end-switch-side-cap.scad>

rg_part = "probe"; // probe, base, added, context
rg_probe = "fixed";
rg_offset_x = 0; // assembly insertion screen only
oc_t = 0;

module rg_box(x0,x1,y0,y1,z0,z1) {
    translate([x0,y0,z0]) cube([x1-x0,y1-y0,z1-z0]);
}
module rg_root_web() {
    difference() {
        hull() {
            rg_box(8,14,37.5,38,-17,-14);
            rg_box(8,14,39,41,-22,-14);
            rg_box(8,14,44,46,-18,-14);
        }
        sf_anchor_holes();
    }
}
module rg_base() { union() { rf_base(); rg_root_web(); } }
module rg_added() { difference() { rg_root_web(); rf_base(); } }

module rg_probe_geometry() {
    if (rg_probe=="fixed") intersection() { rg_added(); sf_fixed(); }
    else if (rg_probe=="insertion-fixed") intersection() {
        translate([rg_offset_x,0,0]) rg_added(); sf_fixed();
    }
    else if (rg_probe=="moving") intersection() { rg_added(); oc_carriage(); }
    else if (rg_probe=="insertion-margin") intersection() {
        minkowski() {
            translate([rg_offset_x,0,0]) rg_added();
            sphere(r=.8,$fn=20);
        }
        sf_fixed();
    }
    else if (rg_probe=="moving-margin") intersection() {
        minkowski() { rg_added(); sphere(r=.8,$fn=20); }
        oc_carriage();
    }
    else if (rg_probe=="margin-positive") intersection() {
        minkowski() { rg_added(); sphere(r=1.2,$fn=20); }
        sf_fixed();
    }
    else if (rg_probe=="hardware") intersection() {
        rg_added(); sf_other_hardware();
    }
    else if (rg_probe=="motor") intersection() {
        rg_added(); ss_motor_envelope();
    }
    else if (rg_probe=="rear") intersection() { rg_added(); sf_rear(); }
    else if (rg_probe=="anchor-hole") intersection() {
        rg_added(); sf_anchor_holes();
    }
    else if (rg_probe=="positive") intersection() { rg_added(); rg_added(); }
    else assert(false, "Unknown root-web probe");
}

if (rg_part=="probe") rg_probe_geometry();
else if (rg_part=="base") rg_base();
else if (rg_part=="added") rg_added();
else if (rg_part=="context") {
    color([.74,.76,.78,.18]) sf_fixed();
    color([.16,.51,.78,.38]) rf_base();
    color([.95,.55,.14]) rg_added();
    color([.79,.56,.30,.30]) oc_carriage();
}
else assert(false, "Unknown root-web part");
