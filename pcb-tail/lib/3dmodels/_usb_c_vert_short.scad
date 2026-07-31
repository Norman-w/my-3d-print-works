// USB-C 16P vertical short H=5.8 — pads match USB_C_Receptacle_16P_Vertical_SMT_Short
// Fab 9.75×4.12; shell ~8.94×3.40; SMT y=±1.10; shield x=±4.325
$fn = 24;

fab_w = 9.75;
fab_d = 4.12;
shell_w = 8.94;
shell_d = 3.40;
h = 5.80;
pad_w = 0.29;
pad_h = 1.10;
pad_t = 0.15;
row_y = 1.10;
pad_xs = [-2.73, -1.95, -1.17, -0.39, 0.39, 1.17, 1.95, 2.73];
slot_x = 4.325;
slot_w = 0.40;
slot_d = 1.00;
slot_below = 2.80;

module smt_stub(x, y) {
  translate([x, y, pad_t / 2]) cube([pad_w, pad_h, pad_t], center = true);
}

module shield(x) {
  z0 = -slot_below;
  z1 = h * 0.45;
  translate([x, 0, (z0 + z1) / 2])
    cube([slot_w, slot_d, z1 - z0], center = true);
}

// Plastic frame to fab envelope
color("ivory")
  difference() {
    translate([0, 0, h / 2]) cube([fab_w, fab_d, h], center = true);
    translate([0, 0, h / 2 + 0.05])
      cube([shell_w + 0.2, shell_d + 0.2, h], center = true);
  }

// Metal shell + mouth on -Y (plug toward board butt)
color("silver")
  difference() {
    translate([0, 0, h / 2]) cube([shell_w, shell_d, h - 0.15], center = true);
    translate([0, -shell_d / 2 + 0.15, h * 0.55])
      cube([shell_w * 0.78, 0.55, h * 0.72], center = true);
  }

color("black")
  translate([0, -0.15, h * 0.52])
    cube([shell_w * 0.42, shell_d * 0.35, h * 0.55], center = true);

color("gold") {
  for (y = [-row_y, row_y])
    for (x = pad_xs)
      smt_stub(x, y);
}

color("silver") {
  shield(-slot_x);
  shield( slot_x);
}
