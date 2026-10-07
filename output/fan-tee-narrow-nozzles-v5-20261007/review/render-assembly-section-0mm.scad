// Review only: direct final binary STL import; no reconstructed CAD.
color([0.14,0.40,0.68]) intersection(){import("../stl/fan-tee-v5-mother-clean.stl");translate([-30,0,-19]) cube([60,30,220]);}
color([0.91,0.61,0.20]) intersection(){translate([0,0,34]) rotate([0,0,0]) import("../stl/fan-tee-v5-nozzle15-clean.stl");translate([-30,0,-19]) cube([60,30,230]);}
