// ============================================================
// v3 散热孔 — 散热片顶部长槽 + 两侧进气槽
// 所有位置与尺寸均参数化，待散热片实测后校准。
// ============================================================
include <parameters.scad>
include <utilities.scad>

module top_vent_cuts() {
    if (ENABLE_TOP_VENTS) {
        for (i = [0 : TOP_VENT_COUNT - 1]) {
            vy = HEATSINK_CENTER_Y
                 + (i - (TOP_VENT_COUNT - 1)/2) * TOP_VENT_SLOT_PITCH;
            translate([HEATSINK_CENTER_X, vy, BOX_INNER_TOP_H - 0.1])
                linear_extrude(height = WALL_THICKNESS + 0.4)
                    rounded_rect_2d(TOP_VENT_SLOT_LENGTH,
                                    TOP_VENT_SLOT_WIDTH,
                                    TOP_VENT_SLOT_WIDTH/2);
        }
    }
}

module side_vent_cuts() {
    if (ENABLE_SIDE_VENTS) {
        for (sy = [-1, 1]) {
            for (i = [0 : SIDE_VENT_COUNT - 1]) {
                vz = SIDE_VENT_Z_FIRST + i * SIDE_VENT_Z_PITCH;
                hull() {
                    for (dx = [-1, 1])
                        translate([HEATSINK_CENTER_X
                                   + dx * (SIDE_VENT_SLOT_LENGTH
                                           - SIDE_VENT_SLOT_HEIGHT)/2,
                                   sy * (BOX_INNER_WIDTH/2
                                         + SIDE_WALL_THICKNESS/2), vz])
                            rotate([90, 0, 0])
                                cylinder(d = SIDE_VENT_SLOT_HEIGHT,
                                         h = SIDE_WALL_THICKNESS + 0.4,
                                         center = true, $fn = 20);
                }
            }
        }
    }
}
