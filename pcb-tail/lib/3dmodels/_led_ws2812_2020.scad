// LED_WS2812B-2020 2.0×2.0 — pads match KiCad PLCC4 (±0.915, ±0.55)
$fn = 24;

body = 2.0;
h = 0.85;
pad = 0.55;
pad_t = 0.08;
lens_r = 0.55;
lens_h = 0.15;

module pad_at(x, y) {
  translate([x, y, pad_t / 2]) cube([pad, pad, pad_t], center = true);
}

color("black")
  translate([0, 0, h / 2]) cube([body, body, h], center = true);

color("lightblue")
  translate([0, 0, h + lens_h / 2])
    cylinder(h = lens_h, r = lens_r, center = true);

// pin-1 corner mark toward pad1 (-X,-Y)
color("white")
  translate([-0.7, -0.7, h + 0.02]) sphere(r = 0.12);

color("gold") {
  pad_at(-0.915, -0.55);
  pad_at(-0.915,  0.55);
  pad_at( 0.915,  0.55);
  pad_at( 0.915, -0.55);
}
