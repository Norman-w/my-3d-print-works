// CH1 03C 加长连接节 / 离合承载平台 — 由 docs/parts/CH1-03C-roller-chain.md 参数化
// 单位：毫米。销轴、夹片和轴承是外购件参考模型；平台是打印件原型。

//#region 导入/依赖
include <ch1_03c_connecting_link_params.scad>
//#endregion

//#region 常量/配置
// 以固定端头部的内侧面为 Y=0；销轴沿 +Y 延伸。
EXTENDED_PIN_BASE_LENGTH = CONNECTING_PIN_LENGTH;
EXTENDED_FIRST_CLIP_Y = EXTENDED_PIN_BASE_LENGTH - CONNECTING_PIN_GROOVE_FROM_TIP;
EXTENDED_NET_PLATFORM_CLEAR = 10.0;
// 两个夹片内侧之间的净距 = 第二夹片中心 - 第一夹片中心 - 夹片厚度。
EXTENDED_SECOND_CLIP_Y =
    EXTENDED_FIRST_CLIP_Y + EXTENDED_NET_PLATFORM_CLEAR + RETAINING_CLIP_T;
EXTENDED_PIN_LENGTH = EXTENDED_SECOND_CLIP_Y + CONNECTING_PIN_GROOVE_FROM_TIP;

PLATFORM_T = 3.0;
PLATFORM_CENTER_Y =
    EXTENDED_FIRST_CLIP_Y
    + RETAINING_CLIP_T / 2
    + EXTENDED_NET_PLATFORM_CLEAR / 2;
PLATFORM_PIN_LINE_Z = 0.0;
PLATFORM_BEARING_CENTER_Z = -5.0;
PLATFORM_PIN_HOLE_D = CONNECTING_PIN_SHAFT_D + 0.28;
PLATFORM_PIN_BOSS_D = 4.0;
PLATFORM_BEARING_BOSS_D = 9.6;

// 沿用已购买的 3×6×2 mm MR63 尺寸；FDM 首件需按实测把座孔放大。
CLUTCH_BEARING_ID = 3.0;
CLUTCH_BEARING_OD = 6.0;
CLUTCH_BEARING_B = 2.0;
CLUTCH_BEARING_SEAT_CLEARANCE = 0.05;
CLUTCH_BEARING_SEAT_D = CLUTCH_BEARING_OD + CLUTCH_BEARING_SEAT_CLEARANCE;
CLUTCH_BEARING_SHAFT_CLEARANCE = 0.40;
CLUTCH_BEARING_SHAFT_D = CLUTCH_BEARING_ID + CLUTCH_BEARING_SHAFT_CLEARANCE;
CLUTCH_BEARING_SEAT_DEPTH = CLUTCH_BEARING_B + 0.15;
EXTENDED_LINK_EPS = 0.05;
//#endregion

//#region 模型/类型
// 双销中心位于 x=±P/2、z=0；平台两个销孔在同一销线上。
// 中央轴承因 Ø6 大于半节距，置于销线下方 z=-5，形成悬挂式离合平台。
// 平台沿 Y 厚 3 mm，位于两夹片之间；夹片内侧净距严格为 10 mm。
//#endregion

//#region 公开 API
// include 后可调用：
// ch1_03c_extended_connecting_pin_pair()
// ch1_03c_extended_retaining_clips()
// ch1_03c_clutch_platform()
// ch1_03c_clutch_bearing_visual()
//#endregion

//#region 私有成员
module extended_pin_groove_cut(x, groove_y) {
    translate([x, groove_y - CONNECTING_PIN_GROOVE_W / 2, 0])
        rotate([-90, 0, 0])
            difference() {
                cylinder(
                    d = CONNECTING_PIN_SHAFT_D + 0.60,
                    h = CONNECTING_PIN_GROOVE_W
                );
                translate([0, 0, -EXTENDED_LINK_EPS])
                    cylinder(
                        d = CONNECTING_PIN_GROOVE_D,
                        h = CONNECTING_PIN_GROOVE_W + 2 * EXTENDED_LINK_EPS
                    );
            }
}

module extended_pin_one(x) {
    difference() {
        union() {
            translate([x, 0, 0])
                rotate([-90, 0, 0])
                    cylinder(d = CONNECTING_PIN_SHAFT_D, h = EXTENDED_PIN_LENGTH);
            translate([x, 0, 0])
                rotate([-90, 0, 0])
                    cylinder(d = CONNECTING_PIN_HEAD_D, h = CONNECTING_PIN_HEAD_H);
        }
        extended_pin_groove_cut(x, EXTENDED_FIRST_CLIP_Y);
        extended_pin_groove_cut(x, EXTENDED_SECOND_CLIP_Y);
    }
}

module extended_retaining_clip_at(y) {
    translate([0, y, 0])
        rotate([90, 0, 0])
            linear_extrude(
                height = RETAINING_CLIP_T,
                center = true,
                convexity = 6
            )
                retaining_clip_profile_2d();
}

module platform_profile_2d() {
    hull() {
        translate([0, PLATFORM_BEARING_CENTER_Z])
            circle(d = PLATFORM_BEARING_BOSS_D);
        for (x = [-CONNECTING_PIN_PAIR_SPACING / 2, CONNECTING_PIN_PAIR_SPACING / 2])
            translate([x, PLATFORM_PIN_LINE_Z])
                circle(d = PLATFORM_PIN_BOSS_D);
    }
}

module platform_bore_y(x, y_start, z, d, h) {
    translate([x, y_start, z])
        rotate([-90, 0, 0])
            cylinder(d = d, h = h);
}

module clutch_bearing_annulus_y(od, id, h) {
    rotate([-90, 0, 0])
        difference() {
            cylinder(d = od, h = h, center = true);
            cylinder(d = id, h = h + 2 * EXTENDED_LINK_EPS, center = true);
        }
}
//#endregion

//#region 业务逻辑
module ch1_03c_extended_connecting_pin_pair() {
    for (x = [-CONNECTING_PIN_PAIR_SPACING / 2, CONNECTING_PIN_PAIR_SPACING / 2])
        extended_pin_one(x);
}

module ch1_03c_extended_retaining_clips() {
    extended_retaining_clip_at(EXTENDED_FIRST_CLIP_Y);
    extended_retaining_clip_at(EXTENDED_SECOND_CLIP_Y);
}

module ch1_03c_clutch_platform() {
    difference() {
        translate([0, PLATFORM_CENTER_Y, 0])
            rotate([90, 0, 0])
                linear_extrude(height = PLATFORM_T, center = true, convexity = 8)
                    platform_profile_2d();

        // 两根加长销穿过平台的上方耳孔。
        for (x = [-CONNECTING_PIN_PAIR_SPACING / 2, CONNECTING_PIN_PAIR_SPACING / 2])
            platform_bore_y(
                x,
                PLATFORM_CENTER_Y - PLATFORM_T / 2 - EXTENDED_LINK_EPS,
                PLATFORM_PIN_LINE_Z,
                PLATFORM_PIN_HOLE_D,
                PLATFORM_T + 2 * EXTENDED_LINK_EPS
            );

        // +Y 面压入 3×6×2 轴承；背面保留 0.85 mm 台阶承托。
        platform_bore_y(
            0,
            PLATFORM_CENTER_Y - PLATFORM_T / 2 - EXTENDED_LINK_EPS,
            PLATFORM_BEARING_CENTER_Z,
            CLUTCH_BEARING_SHAFT_D,
            PLATFORM_T + 2 * EXTENDED_LINK_EPS
        );
        platform_bore_y(
            0,
            PLATFORM_CENTER_Y + PLATFORM_T / 2 - CLUTCH_BEARING_SEAT_DEPTH,
            PLATFORM_BEARING_CENTER_Z,
            CLUTCH_BEARING_SEAT_D,
            CLUTCH_BEARING_SEAT_DEPTH + EXTENDED_LINK_EPS
        );
    }
}

module ch1_03c_clutch_bearing_visual() {
    bearing_y = PLATFORM_CENTER_Y + PLATFORM_T / 2 - CLUTCH_BEARING_B / 2;
    translate([0, bearing_y, PLATFORM_BEARING_CENTER_Z]) {
        // 外圈、内圈和两侧密封盖；这是采购件显示几何，不是打印轴承。
        clutch_bearing_annulus_y(CLUTCH_BEARING_OD, 4.55, CLUTCH_BEARING_B);
        clutch_bearing_annulus_y(4.15, CLUTCH_BEARING_ID, CLUTCH_BEARING_B);
        for (y = [-CLUTCH_BEARING_B / 2 + 0.09, CLUTCH_BEARING_B / 2 - 0.09])
            translate([0, y, 0])
                clutch_bearing_annulus_y(
                    CLUTCH_BEARING_OD - 0.28,
                    CLUTCH_BEARING_ID + 0.22,
                    0.12
                );
    }
}

module ch1_03c_extended_link_reference() {
    color("#b08d57") ch1_03c_extended_connecting_pin_pair();
    color("#9aa7b6") ch1_03c_extended_retaining_clips();
    color("#d17a3d") ch1_03c_clutch_platform();
    color("#b9c2ca") ch1_03c_clutch_bearing_visual();
}
//#endregion

//#region 方法/工具
assert(EXTENDED_SECOND_CLIP_Y - EXTENDED_FIRST_CLIP_Y - RETAINING_CLIP_T > 9.99);
assert(PLATFORM_T < EXTENDED_NET_PLATFORM_CLEAR);
assert(PLATFORM_BEARING_BOSS_D > CLUTCH_BEARING_SEAT_D + 2 * 1.0);
// 独立入口见 cad/openscad/ch1_03c_extended_connecting_pin.scad 等四个根文件。
//#endregion
