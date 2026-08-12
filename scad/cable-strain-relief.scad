// ============================================================
// v3 双线缆应力释放 — 两根线从 Y- / Y+ 相对侧壁进入。
// 上下交错夹齿在 Z=0 附近把 5mm 线缆压到约 4mm。
// ============================================================
include <parameters.scad>

TOOTH_COUNT       = 3;
TOOTH_WIDTH_X     = 8.0;
TOOTH_BASE_Y      = 4.0;
TOOTH_TOP_Y       = 1.5;
TOOTH_GAP         = 4.0;
TOOTH_SPACING     = 4.0;
TOOTH_FIRST_Y     = 4.0;

module cable_clamp_teeth_bottom() {
    tooth_h = BOX_INNER_BOTTOM_H - TOOTH_GAP/2;

    for (sy = [-1, 1]) {
        for (i = [0 : TOOTH_COUNT - 1]) {
            ty = sy * (BOX_INNER_WIDTH/2 - TOOTH_FIRST_Y
                       - i * TOOTH_SPACING);
            translate([CABLE_ENTRY_X, ty, -BOX_INNER_BOTTOM_H])
                _tooth_bottom(TOOTH_WIDTH_X, TOOTH_BASE_Y,
                              TOOTH_TOP_Y, tooth_h);
        }
    }
}

module cable_clamp_teeth_top() {
    tooth_h = BOX_INNER_TOP_H - TOOTH_GAP/2;
    count = TOOTH_COUNT - 1;
    offset = TOOTH_SPACING/2;

    for (sy = [-1, 1]) {
        for (i = [0 : count - 1]) {
            ty = sy * (BOX_INNER_WIDTH/2 - TOOTH_FIRST_Y
                       - offset - i * TOOTH_SPACING);
            translate([CABLE_ENTRY_X, ty, TOOTH_GAP/2])
                _tooth_top(TOOTH_WIDTH_X, TOOTH_BASE_Y,
                           TOOTH_TOP_Y, tooth_h);
        }
    }
}

// 线缆内侧的成对导向柱，限制其在 X 方向摆动。
// 柱间净宽由 5mm 线缆 + 0.8mm 装配余量计算，不在此处夹紧线缆。
GUIDE_POST_ABOVE      = 5.0;
GUIDE_POST_BASE_EXTRA = 1.5;
GUIDE_POST_BASE_H     = 3.0;

module cable_guide_posts_bottom() {
    post_h = BOX_INNER_BOTTOM_H + GUIDE_POST_ABOVE;
    s = GUIDE_POST_DIAMETER;
    bs = s + GUIDE_POST_BASE_EXTRA * 2;
    inner_y = BOX_INNER_WIDTH/2 - TOOTH_FIRST_Y
              - (TOOTH_COUNT - 1) * TOOTH_SPACING - 3.0;

    for (sy = [-1, 1], sx = [-1, 1]) {
        px = CABLE_ENTRY_X + sx * GUIDE_POST_CENTER_OFFSET;
        py = sy * inner_y;

        translate([px, py, -BOX_INNER_BOTTOM_H]) {
            cylinder(d1 = bs, d2 = s,
                     h = min(GUIDE_POST_BASE_H, post_h), $fn = 24);
            if (post_h > GUIDE_POST_BASE_H)
                translate([0, 0, GUIDE_POST_BASE_H])
                    cylinder(d = s,
                             h = post_h - GUIDE_POST_BASE_H, $fn = 20);
        }
    }
}

module _tooth_bottom(w, base_d, top_d, h) {
    hull() {
        translate([-w/2, -base_d/2, 0])
            cube([w, base_d, 0.01]);
        translate([-w/2, -top_d/2, h - 0.01])
            cube([w, top_d, 0.01]);
    }
}

module _tooth_top(w, base_d, top_d, h) {
    hull() {
        translate([-w/2, -top_d/2, 0])
            cube([w, top_d, 0.01]);
        translate([-w/2, -base_d/2, h - 0.01])
            cube([w, base_d, 0.01]);
    }
}
