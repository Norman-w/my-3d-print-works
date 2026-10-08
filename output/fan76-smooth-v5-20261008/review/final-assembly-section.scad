// Imported final meshes, exact phase, no procedural preview substitutes.
color([0.12,0.43,0.68]) intersection(){import("../stl/fan76-smooth-v5-body-clean.stl");translate([-100,0,-1]) cube([200,100,400]);}
color([0.87,0.48,0.08]) translate([0,0,146]) intersection(){import("../stl/fan-tee-v5-nozzle15-clean.stl");translate([-100,0,-1]) cube([200,100,400]);}
