// SW_SPST_4.5x4.5 THT — pins match pcb/lib/tactile_45/params.py
// Body 4.5×4.5; THT pins at (±2.75, ±1.7); NOT SMD PTS645
$fn = 24;

body = 4.5;
body_h = 3.5;
act_d = 2.5;
act_h = 0.8;
pin_d = 0.40;
pin_below = 3.2;
pin_above = 0.35;

module pin(x, y) {
  translate([x, y, (pin_above - pin_below) / 2])
    cylinder(h = pin_above + pin_below, d = pin_d, center = true);
}

color("dimgray")
  translate([0, 0, body_h / 2]) cube([body, body, body_h], center = true);

color("black")
  translate([0, 0, body_h]) cylinder(h = 0.25, d = act_d + 0.7);

color("black")
  translate([0, 0, body_h + act_h / 2])
    cylinder(h = act_h, d = act_d, center = true);

color("silver") {
  pin(-2.75, -1.70);
  pin( 2.75, -1.70);
  pin(-2.75,  1.70);
  pin( 2.75,  1.70);
}
