// USB-C 16P vertical short H=5.8 — 焊盘/腰圆与封装一致
// 短脚系列：屏蔽脚板下约 0.7mm（见 docs/usb-c-vertical-16p-short）
$fn = 32;

fab_w = 9.75;
fab_d = 4.12;
shell_w = 8.94;
shell_d = 3.26;
h = 5.80;
wall = 0.35;
mouth_w = 8.25;
mouth_d = 2.56;
mouth_r = mouth_d / 2;
tongue_w = 2.40;
tongue_d = 0.70;
tongue_h = 3.80;
pad_w = 0.29;
pad_h = 1.10;
pad_t = 0.10;
row_y = 1.10;
pad_xs = [-2.73, -1.95, -1.17, -0.39, 0.39, 1.17, 1.95, 2.73];
slot_x = 4.325;
slot_w = 0.40;
slot_d = 0.90;
// 短脚：板下只留 ~0.7mm（原先 2.8 过长）
slot_below = 0.70;

module stadium_2d(w, d, r) {
  rr = min(r, d / 2, w / 2);
  hull()
    for (sx = [-1, 1])
      translate([sx * (w / 2 - rr), 0])
        circle(r = rr);
}

module shell_body(w, d, hh) {
  linear_extrude(height = hh, center = false)
    stadium_2d(w, d, d / 2);
}

module smt_stub(x, y) {
  // 贴片脚贴在板面，几乎不向下伸
  translate([x, y, pad_t / 2]) cube([pad_w, pad_h, pad_t], center = true);
}

module shield(x) {
  // 腰圆屏蔽脚：壳体侧壁向下短插
  translate([x, 0, -slot_below / 2])
    cube([slot_w, slot_d, slot_below + 0.35], center = true);
  // 与壳体连接的短桥（板面上）
  translate([x, 0, 0.25])
    cube([slot_w, slot_d, 0.50], center = true);
}

color("silver")
  difference() {
    shell_body(shell_w, shell_d, h);
    translate([0, 0, 0.55])
      linear_extrude(height = h)
        stadium_2d(mouth_w, mouth_d, mouth_r);
    translate([0, 0, h - 0.22])
      linear_extrude(height = 0.30)
        stadium_2d(mouth_w + 0.35, mouth_d + 0.25, mouth_r + 0.12);
  }

color("black")
  translate([0, 0, 0.55 + tongue_h / 2])
    cube([tongue_w, tongue_d, tongue_h], center = true);

color("Ivory")
  difference() {
    linear_extrude(height = 1.15)
      stadium_2d(fab_w, fab_d, 0.6);
    translate([0, 0, -0.05])
      linear_extrude(height = 1.40)
        stadium_2d(shell_w + 0.05, shell_d + 0.05, shell_d / 2);
  }

color("gold") {
  for (y = [-row_y, row_y])
    for (x = pad_xs)
      smt_stub(x, y);
}

color("silver") {
  shield(-slot_x);
  shield( slot_x);
}
