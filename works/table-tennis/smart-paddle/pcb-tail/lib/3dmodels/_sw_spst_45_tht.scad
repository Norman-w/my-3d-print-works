// SW_SPST_4.5×4.5 THT — 焊盘中心 (±2.75, ±1.7) 与封装一致
// 金属爪从壳体边沿弯到焊盘再穿板；板厚 1.0 → 板下只留短焊脚
$fn = 28;

body = 4.5;
body_h = 3.20;
cap_t = 0.30;
act_d = 2.40;
act_h = 0.90;
stem_d = 1.70;
// 板下露出：约 1.0mm（1.0 板厚 + 少许焊脚，不再 3.2）
pin_below = 1.00;
pin_d = 0.45;
claw_t = 0.25;
claw_w = 0.55;
pad_xs = [-2.75, 2.75];
pad_ys = [-1.70, 1.70];

module rounded_box(w, d, h, r) {
  rr = min(r, w / 2 - 0.05, d / 2 - 0.05);
  hull()
    for (sx = [-1, 1], sy = [-1, 1])
      translate([sx * (w / 2 - rr), sy * (d / 2 - rr), 0])
        cylinder(h = h, r = rr);
}

// 一只爪：壳体侧壁 → 水平伸出到焊盘 XY → 竖直短脚穿板
module claw(px, py) {
  // 从壳体底边朝焊盘方向的水平臂（贴地）
  bx = (px > 0 ? 1 : -1) * (body / 2);
  hull() {
    translate([bx * 0.92, py * 0.55, claw_t / 2])
      cube([0.35, claw_w, claw_t], center = true);
    translate([px, py, claw_t / 2])
      cube([claw_w, claw_w, claw_t], center = true);
  }
  // 穿板短脚（Z=0 为 F.Cu，向下为负）
  translate([px, py, -pin_below / 2])
    cylinder(h = pin_below, d = pin_d, center = true);
}

color([0.18, 0.18, 0.2])
  rounded_box(body, body, body_h, 0.30);

color([0.10, 0.10, 0.11])
  translate([0, 0, body_h])
    cylinder(h = cap_t, d = act_d + 1.0);

color([0.08, 0.08, 0.09]) {
  translate([0, 0, body_h + cap_t])
    cylinder(h = act_h * 0.4, d = act_d);
  translate([0, 0, body_h + cap_t + act_h * 0.4])
    cylinder(h = act_h * 0.6, d = stem_d);
}

color("silver") {
  for (px = pad_xs, py = pad_ys)
    claw(px, py);
}
