// Actual edge-finished clip and nominal 20x20 mating envelopes. Not a print file.
color([1,.48,.10])import("../exports/perpendicular-u-joint-v1.18-toe-bridge/guard-v1.18.stl");
color([.53,.57,.62])translate([0,0,10])cube([112,20,20],center=true);
color([.14,.36,.72])translate([0,0,-10])cube([20,110,20],center=true);
