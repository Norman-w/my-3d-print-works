// LED_WS2812B-2020 2.0×2.0 — pads (±0.915, ±0.55)
$fn = 40;

body = 2.0;
h = 0.90;
pad = 0.55;
pad_t = 0.08;
lens_r = 0.72;
lens_h = 0.18;

module pad_at(x, y) {
  translate([x, y, pad_t / 2]) cube([pad, pad, pad_t], center = true);
}

module rounded_sq(s, hh, r = 0.2) {
  hull()
    for (sx = [-1, 1], sy = [-1, 1])
      translate([sx * (s / 2 - r), sy * (s / 2 - r), 0])
        cylinder(h = hh, r = r);
}

color([0.05, 0.05, 0.06])
  rounded_sq(body, h, 0.18);

// 发光面
color([0.75, 0.88, 1.0])
  translate([0, 0, h])
    cylinder(h = lens_h, r = lens_r);

// pin1 角标
color("white")
  translate([-0.72, -0.72, h + 0.01])
    cylinder(h = 0.06, r = 0.12);

color("gold") {
  pad_at(-0.915, -0.55);
  pad_at(-0.915,  0.55);
  pad_at( 0.915,  0.55);
  pad_at( 0.915, -0.55);
}
