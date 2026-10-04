// Assembly-path screen for the one-piece output crosshead candidate.
// This is a nominal CAD probe, not an installed motor or a proven assembly.
use <electric-output-crosshead-screen.scad>
use <electric-end-switch-side-cap.scad>
use <electric-rocker-pivot-joint-screen.scad>
use <electric-rocker-clamped-fork-screen.scad>

oa_probe = "cap-crosshead";
oa_cap_progress = 0;       // 0..1: remove the detached right cap along +Y by 25 mm
oa_rocker_y_offset = 0;    // shift rocker toward +Y before axial insertion

assert(oa_cap_progress >= 0 && oa_cap_progress <= 1);
assert(oa_rocker_y_offset >= 0 && oa_rocker_y_offset <= 20);

if (oa_probe == "cap-crosshead")
    intersection() {
        translate([0, 25*oa_cap_progress, 0]) ss_cap();
        oc_crosshead();
    }
else if (oa_probe == "switch-tool-crosshead")
    intersection() {
        ss_switch_adjustment_tools();
        oc_crosshead();
    }
else if (oa_probe == "rocker-crosshead-axial")
    intersection() {
        translate([0, oa_rocker_y_offset, 0]) pj_rocker();
        oc_crosshead();
    }
else if (oa_probe == "rocker-fork-axial")
    intersection() {
        translate([0, oa_rocker_y_offset, 0]) pj_rocker();
        cf_bracket();
    }
else
    assert(false, "Unknown output assembly probe");
