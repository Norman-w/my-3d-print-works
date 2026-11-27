use <load_path_guard.scad>;
use <../perpendicular-u-joint-guard-v1.16-root-radius/strength_guard.scad>;
// Actual CAD comparison: old body blue, added reinforcement orange.
color([.22,.52,.70])strength_raw();
color([1,.42,.12])difference(){load_path_raw();strength_raw();}
