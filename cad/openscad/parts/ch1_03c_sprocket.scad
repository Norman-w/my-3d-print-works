// Mechanical contract
// process: resin (SLA/DLP) recommended; FDM only with 0.2 mm nozzle and larger SEAT_CLEARANCE
// material: to be confirmed — rigid resin or PETG/nylon; not a substitute for steel sprockets
// parting_plane: n/a (single printable disc + hub)
// opening_direction: n/a
// fastener: 3 mm shaft through-bore + optional M2 set-screw tap hole
// seal: n/a
// print_orientation: hub face down, axis = +Z (tooth profile in XY)
// units: mm
// source: docs/parts/CH1-03C-roller-chain.md
// note: roller-chain sprockets with pointed teeth; not involute gears

//#region 导入/依赖
include <ch1_03c_sprocket_params.scad>
//#endregion

//#region 常量/配置
$fa = 8;
$fs = 0.22;

SIZE = "1x";                     // 1x | 1.5x | 2x | 3x | 4x
PART = "sprocket";               // sprocket | family | wrap_check
eps = 0.05;
//#endregion

//#region 模型/类型
// 尺寸名与齿数表在 params；本文件只消费 SIZE / PART。
//#endregion

//#region 私有成员
module sprocket_outline(n) {
    pitch_r = sprocket_pitch_r(n);
    difference() {
        polygon(sharp_sprocket_points(n));
        for (i = [0:n - 1])
            rotate(i * 360 / n)
                translate([pitch_r, 0])
                    circle(r = seat_r);
    }
}

module hub_solid(n) {
    cylinder(d = hub_od_of(n), h = HUB_H, center = true);
}

module bore_cut(n) {
    cylinder(d = bore_d, h = HUB_H + tooth_w + 2, center = true);
}

module set_screw_cut(n) {
    translate([bore_d / 2 - eps, 0, 0])
        rotate([0, 90, 0])
            cylinder(d = SET_SCREW_D, h = hub_od_of(n) / 2 + eps);
}

module lighten_cuts(n) {
    root_r = sprocket_root_r(n);
    hub_r = hub_od_of(n) / 2;
    ring = root_r - hub_r;
    if (ring > LIGHTEN_MIN_RING) {
        hole_d = min(8, 0.42 * ring);
        hole_at = (hub_r + root_r) / 2;
        for (i = [0:5])
            rotate(30 + i * 60)
                translate([hole_at, 0, 0])
                    cylinder(d = hole_d, h = HUB_H + tooth_w + 2, center = true);
    }
}

module roller_preview(n) {
    pitch_r = sprocket_pitch_r(n);
    for (i = [0:n - 1])
        rotate(i * 360 / n)
            translate([pitch_r, 0, 0])
                cylinder(d = d1, h = inner_width, center = true);
}

//#endregion

//#region 公开 API
module ch1_03c_sprocket(n) {
    assert(n >= BASE_TEETH, "teeth below 1x (12) is not the working-well minimum");
    difference() {
        union() {
            linear_extrude(height = tooth_w, center = true, convexity = max(8, n))
                sprocket_outline(n);
            hub_solid(n);
        }
        bore_cut(n);
        set_screw_cut(n);
        lighten_cuts(n);
    }
}

module ch1_03c_sprocket_family() {
    for (i = [0:len(SCALE_TEETH) - 1])
        translate([family_x(i), 0, 0])
            ch1_03c_sprocket(SCALE_TEETH[i]);
}

module ch1_03c_sprocket_wrap_check(n) {
    ch1_03c_sprocket(n);
    %roller_preview(n);
}

if (PART == "family") {
    ch1_03c_sprocket_family();
} else if (PART == "wrap_check") {
    assert(is_known_size(SIZE), str("unknown SIZE: ", SIZE));
    ch1_03c_sprocket_wrap_check(teeth_of(SIZE));
} else {
    assert(is_known_size(SIZE), str("unknown SIZE: ", SIZE));
    ch1_03c_sprocket(teeth_of(SIZE));
}
//#endregion

//#region 业务逻辑
// 齿形 = 尖齿星形（谷底在滚子角，齿顶在中间）再减去节圆滚子座。
// 轮毂比齿圈厚，但外径缩进内链板包络；顶丝孔只打穿轮毂一侧。
//#endregion

//#region 方法/工具
// 导出用 -D SIZE='"2x"' 或 -D PART='"family"' / -D PART='"wrap_check"'。
//#endregion
