// Mechanical contract
// process: resin (SLA/DLP) recommended; FDM with 0.2 mm nozzle acceptable for fit
// material: rigid resin or PETG; translation idler, not a steel drive sprocket
// parting_plane: n/a (disc + flanges)
// opening_direction: n/a
// fastener: 3 mm round shaft through-bore; no D-flat on the 8T hub
// seal: n/a
// print_orientation: flange face down; axis = +Z (tooth profile in XY)
// units: mm
// source: docs/parts/CH1-03C-roller-chain.md
// note: blunt teeth push the chain sideways; not the pointed 12T mesh profile

//#region 导入/依赖
include <ch1_03c_sprocket_params.scad>
//#endregion

//#region 常量/配置
$fa = 8;
$fs = 0.22;

BLUNT_TEETH = 8;
BLUNT_ADDENDUM = 0.12 * P;       // 钝顶；尖齿 12T 用 0.38 P
BLUNT_TIP_R = 0.55;
FLANGE_T = 0.80;
eps = 0.05;
PART = is_undef(PART) ? "idler" : PART;
//#endregion

//#region 模型/类型
function blunt_pitch_r(n) = P / (2 * sin(180 / n));

function blunt_outer_r(n) = blunt_pitch_r(n) + BLUNT_ADDENDUM;

function blunt_valley_r(n) = blunt_pitch_r(n) - seat_r - GULLET_INSET;

function blunt_flange_r(n) = blunt_valley_r(n) + 0.20;
//#endregion

//#region 私有成员
module blunt_outline(n) {
    pitch_r = blunt_pitch_r(n);
    tip_at = blunt_outer_r(n) - BLUNT_TIP_R;
    root = blunt_valley_r(n);
    difference() {
        union() {
            circle(r = root + 0.15);
            for (i = [0:n - 1])
                hull() {
                    rotate(i * 360 / n)
                        translate([root, 0])
                            circle(r = 0.55);
                    rotate((i + 0.5) * 360 / n)
                        translate([tip_at, 0])
                            circle(r = BLUNT_TIP_R);
                    rotate((i + 1) * 360 / n)
                        translate([root, 0])
                            circle(r = 0.55);
                }
        }
        for (i = [0:n - 1])
            rotate(i * 360 / n)
                translate([pitch_r, 0])
                    circle(r = seat_r);
    }
}

module blunt_flanges(n) {
    wt = tooth_w;
    for (s = [-1, 1])
        translate([0, 0, s * (wt / 2 + FLANGE_T / 2 - 0.15)])
            cylinder(d = 2 * blunt_flange_r(n), h = FLANGE_T, center = true);
}
//#endregion

//#region 公开 API
module ch1_03c_blunt_idler(n = BLUNT_TEETH) {
    assert(n >= 8, "blunt translator below 8T wraps tighter than the 03C visualization allows");
    difference() {
        union() {
            linear_extrude(height = tooth_w, center = true, convexity = max(8, n))
                blunt_outline(n);
            blunt_flanges(n);
        }
        cylinder(d = bore_d, h = tooth_w + 2 * FLANGE_T + 2, center = true);
    }
}

module ch1_03c_bearing_blunt_idler(n = BLUNT_TEETH) {
    assert(n >= 8, "blunt translator below 8T wraps tighter than the 03C visualization allows");
    seat_bottom = -BEARING_B / 2;
    seat_top = tooth_w / 2 + FLANGE_T + 1;
    difference() {
        union() {
            linear_extrude(height = tooth_w, center = true, convexity = max(8, n))
                blunt_outline(n);
            blunt_flanges(n);
        }
        // 从 +Z 侧压入，底部台阶承托 2 mm 轴承；后侧为 Ø3.4 导轴孔。
        union() {
            translate([0, 0, (seat_bottom + seat_top) / 2])
                cylinder(d = BEARING_SEAT_D, h = seat_top - seat_bottom);
            cylinder(
                d = BEARING_SHAFT_D,
                h = tooth_w + 2 * FLANGE_T + 2,
                center = true
            );
        }
    }
}

if (is_undef(BLUNT_LIB_ONLY) || !BLUNT_LIB_ONLY)
    if (PART == "bearing")
        ch1_03c_bearing_blunt_idler();
    else
        ch1_03c_blunt_idler();
//#endregion

//#region 业务逻辑
// 节圆仍按 03C 节距，齿顶截短并倒圆。两侧挡圈停在齿根，齿顶露在外面。
//#endregion

//#region 方法/工具
// 装配体 use 本文件；单独打开时导出一颗 8T 钝齿轮。
//#endregion
