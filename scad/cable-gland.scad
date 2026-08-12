// ============================================================
// v3 双线缆出线孔 — 线缆沿 Y，盒体/PCB 长轴沿 X。
// 分型面 Z=0 穿过线缆轴线，上下壳各形成一个半圆。
// ============================================================
include <parameters.scad>

_CH_R = GLAND_HOLE_DIAM / 2;
_CH_L = SIDE_WALL_THICKNESS + GLAND_WALL_EXTRA * 2;

module cable_channel_half_bottom() {
    translate([0, 0, -0.01])
        rotate([90, 0, 0])
            cylinder(r = _CH_R, h = _CH_L, center = true, $fn = 32);
}

module cable_channel_half_top() {
    translate([0, 0, 0.01])
        rotate([90, 0, 0])
            cylinder(r = _CH_R, h = _CH_L, center = true, $fn = 32);
}
