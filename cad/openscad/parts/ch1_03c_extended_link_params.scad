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

// 平台位于两夹片内侧的 10 mm 净空间中；主体厚 5.0 mm，前后各有 0.8 mm
// 的对称加强筋，总包络 6.6 mm，两侧仍各留 1.7 mm 装配间隙。
PLATFORM_T = 5.0;
PLATFORM_RIB_T = 0.8;
PLATFORM_CENTER_Y =
    EXTENDED_FIRST_CLIP_Y
    + RETAINING_CLIP_T / 2
    + EXTENDED_NET_PLATFORM_CLEAR / 2;
PLATFORM_PIN_LINE_Z = 0.0;
// 两根穿销的中心是 x=±P/2；轴承仍位于两销正中（x=0），但向下错开，
// 让轴承座与穿销孔在 Z 向分离，避免形成几乎为零的薄桥。
PLATFORM_BEARING_CENTER_Z = -2.0;
PLATFORM_PIN_HOLE_D = CONNECTING_PIN_SHAFT_D + 0.20;
PLATFORM_PIN_BOSS_D = 4.0;
// 下方轴承承载 boss 用圆角矩形，给座孔和加强筋留连续实体。
PLATFORM_BEARING_BOSS_D = 5.8;
PLATFORM_BEARING_BOSS_H = 3.6;
PLATFORM_BEARING_BOSS_CENTER_Z = -1.4;
PLATFORM_BEARING_BOSS_CORNER_R = 0.5;
PLATFORM_BEARING_BOSS_BOTTOM_Z =
    PLATFORM_BEARING_BOSS_CENTER_Z - PLATFORM_BEARING_BOSS_H / 2;

// 681 系列微型深沟球轴承：1×3×1 mm（内径×外径×宽度）；优先购买 681-2RS
// 或 681ZZ 防尘版本。轴承宽度沿世界 Z，装入下方 boss 后由承托环锁住。
CLUTCH_BEARING_ID = 1.0;
CLUTCH_BEARING_OD = 3.0;
CLUTCH_BEARING_B = 1.0;
CLUTCH_BEARING_SEAT_CLEARANCE = 0.05;
CLUTCH_BEARING_SEAT_D = CLUTCH_BEARING_OD + CLUTCH_BEARING_SEAT_CLEARANCE;
CLUTCH_BEARING_SHAFT_CLEARANCE = 0.20;
CLUTCH_BEARING_SHAFT_D = CLUTCH_BEARING_ID + CLUTCH_BEARING_SHAFT_CLEARANCE;
CLUTCH_BEARING_SEAT_OVERTRAVEL = 0.10;
// 轴承从 boss 下方沿 +Z 压入；上端止挡位于销孔下缘之外，避免座孔切入穿销区。
CLUTCH_BEARING_SEAT_DEPTH =
    PLATFORM_BEARING_CENTER_Z + CLUTCH_BEARING_B / 2
    + CLUTCH_BEARING_SEAT_OVERTRAVEL
    - (PLATFORM_BEARING_BOSS_BOTTOM_Z - 0.10);
CLUTCH_BEARING_SEAT_START_Z = PLATFORM_BEARING_BOSS_BOTTOM_Z - 0.10;
CLUTCH_BEARING_SEAT_END_Z =
    CLUTCH_BEARING_SEAT_START_Z + CLUTCH_BEARING_SEAT_DEPTH;
// 下承托环是独立打印件：轴承装入后从下方压入/点胶固定。
CLUTCH_BEARING_RETAINER_T = 0.60;
CLUTCH_BEARING_RETAINER_OD = 3.78;
CLUTCH_BEARING_RETAINER_RECESS_D = 3.90;
CLUTCH_BEARING_RETAINER_ID = CLUTCH_BEARING_SHAFT_D;
CLUTCH_BEARING_RETAINER_TOP_Z =
    PLATFORM_BEARING_CENTER_Z - CLUTCH_BEARING_B / 2;
CLUTCH_BEARING_RETAINER_CENTER_Z =
    CLUTCH_BEARING_RETAINER_TOP_Z - CLUTCH_BEARING_RETAINER_T / 2;
CLUTCH_BEARING_RETAINER_BOTTOM_Z =
    CLUTCH_BEARING_RETAINER_TOP_Z - CLUTCH_BEARING_RETAINER_T;
EXTENDED_LINK_EPS = 0.05;
CLUTCH_BEARING_RETAINER_RECESS_START_Z =
    PLATFORM_BEARING_BOSS_BOTTOM_Z - EXTENDED_LINK_EPS;
CLUTCH_BEARING_RETAINER_RECESS_DEPTH =
    CLUTCH_BEARING_RETAINER_TOP_Z
    - CLUTCH_BEARING_RETAINER_RECESS_START_Z
    + EXTENDED_LINK_EPS;
PLATFORM_TOTAL_HALF_T = PLATFORM_T / 2 + PLATFORM_RIB_T;
PLATFORM_SHAFT_BORE_START_Z = PLATFORM_BEARING_BOSS_BOTTOM_Z - EXTENDED_LINK_EPS;
PLATFORM_SHAFT_BORE_DEPTH =
    PLATFORM_PIN_BOSS_D / 2
    - PLATFORM_BEARING_BOSS_BOTTOM_Z
    + 2 * EXTENDED_LINK_EPS;
//#endregion

//#region 模型/类型
// 双销中心位于 x=±P/2、z=0；平台两个销孔在同一销线上。
// 681 轴承位于两销的正中 x=0、z=-2.0，轴向沿世界 Z；从下方压入 boss，
// 再用独立承托环锁住。平台沿 Y 厚 5.0 mm，前后筋后总包络 6.6 mm。
// 平台位于两夹片之间；夹片内侧净距严格为 10 mm。
//#endregion

//#region 公开 API
// include 后可调用：
// ch1_03c_extended_connecting_pin_pair()
// ch1_03c_extended_retaining_clips()
// ch1_03c_clutch_platform()
// ch1_03c_clutch_bearing_visual()
// ch1_03c_clutch_bearing_retainer()
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
    union() {
        hull() {
            for (x = [-CONNECTING_PIN_PAIR_SPACING / 2, CONNECTING_PIN_PAIR_SPACING / 2])
                translate([x, PLATFORM_PIN_LINE_Z])
                    circle(d = PLATFORM_PIN_BOSS_D);
        }

        translate([0, PLATFORM_BEARING_BOSS_CENTER_Z])
            offset(r = PLATFORM_BEARING_BOSS_CORNER_R)
                square([
                    PLATFORM_BEARING_BOSS_D - 2 * PLATFORM_BEARING_BOSS_CORNER_R,
                    PLATFORM_BEARING_BOSS_H - 2 * PLATFORM_BEARING_BOSS_CORNER_R
                ], center = true);
    }
}

module platform_gusset_one_profile_2d() {
    // 侧视截面中的渐降筋脚：高边连接右侧穿销 boss，低边完整落到下方轴承 boss。
    polygon([
        [0.80, -0.45],
        [3.70, -0.45],
        [2.60, -1.15],
        [2.45, -2.85],
        [1.35, -2.85],
        [0.85, -1.20]
    ]);
}

module platform_gusset_profile_2d() {
    platform_gusset_one_profile_2d();
    mirror([1, 0, 0])
        platform_gusset_one_profile_2d();
}

module platform_body() {
    union() {
        translate([0, PLATFORM_CENTER_Y, 0])
            rotate([90, 0, 0])
                linear_extrude(height = PLATFORM_T, center = true, convexity = 8)
                    platform_profile_2d();

        // 前后各一条对称筋，增加轴承 boss 到双销桥的抗弯截面。
        for (side = [-1, 1])
            translate([
                0,
                PLATFORM_CENTER_Y
                    + side * (PLATFORM_T / 2 + PLATFORM_RIB_T / 2),
                0
            ])
                rotate([90, 0, 0])
                    linear_extrude(height = PLATFORM_RIB_T, center = true, convexity = 6)
                        platform_gusset_profile_2d();
    }
}

module platform_bore_y(x, y_start, z, d, h) {
    translate([x, y_start, z])
        rotate([-90, 0, 0])
            cylinder(d = d, h = h);
}

module platform_bore_z(x, y, z_start, d, h) {
    translate([x, y, z_start])
        cylinder(d = d, h = h);
}

module clutch_bearing_annulus_z(od, id, h) {
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
        platform_body();

        // 两根加长销沿 Y 穿过平台耳孔；轴承座位于两孔的正中。
        for (x = [-CONNECTING_PIN_PAIR_SPACING / 2, CONNECTING_PIN_PAIR_SPACING / 2])
            platform_bore_y(
                x,
                PLATFORM_CENTER_Y - PLATFORM_TOTAL_HALF_T - EXTENDED_LINK_EPS,
                PLATFORM_PIN_LINE_Z,
                PLATFORM_PIN_HOLE_D,
                2 * PLATFORM_TOTAL_HALF_T + 2 * EXTENDED_LINK_EPS
            );

        // 轴承内孔沿 Z 贯通 boss，给 1 mm 离合轴留 Ø1.20 mm 打印余量。
        platform_bore_z(
            0,
            PLATFORM_CENTER_Y,
            PLATFORM_SHAFT_BORE_START_Z,
            CLUTCH_BEARING_SHAFT_D,
            PLATFORM_SHAFT_BORE_DEPTH
        );

        // 下方 Ø3.05 座孔只延伸到销孔下缘以下，轴承从 -Z 侧压入。
        platform_bore_z(
            0,
            PLATFORM_CENTER_Y,
            CLUTCH_BEARING_SEAT_START_Z,
            CLUTCH_BEARING_SEAT_D,
            CLUTCH_BEARING_SEAT_DEPTH + EXTENDED_LINK_EPS
        );

        // 承托环的沉孔；装好轴承后由下方压入或点胶固定。
        platform_bore_z(
            0,
            PLATFORM_CENTER_Y,
            CLUTCH_BEARING_RETAINER_RECESS_START_Z,
            CLUTCH_BEARING_RETAINER_RECESS_D,
            CLUTCH_BEARING_RETAINER_RECESS_DEPTH
        );
    }
}

module ch1_03c_clutch_bearing_visual() {
    translate([0, PLATFORM_CENTER_Y, PLATFORM_BEARING_CENTER_Z]) {
        // 外圈、内圈和两侧密封盖；这是 681 采购件显示几何，不是打印轴承。
        // 轴承轴线为世界 Z，因此在平台上是上下方向。
        clutch_bearing_annulus_z(CLUTCH_BEARING_OD, 2.45, CLUTCH_BEARING_B);
        clutch_bearing_annulus_z(2.20, CLUTCH_BEARING_ID, CLUTCH_BEARING_B);
        for (z = [-CLUTCH_BEARING_B / 2 + 0.09, CLUTCH_BEARING_B / 2 - 0.09])
            translate([0, 0, z])
                clutch_bearing_annulus_z(
                    CLUTCH_BEARING_OD - 0.28,
                    CLUTCH_BEARING_ID + 0.22,
                    0.12
                );
    }
}

module ch1_03c_clutch_bearing_retainer() {
    translate([
        0,
        PLATFORM_CENTER_Y,
        CLUTCH_BEARING_RETAINER_CENTER_Z
    ])
        clutch_bearing_annulus_z(
            CLUTCH_BEARING_RETAINER_OD,
            CLUTCH_BEARING_RETAINER_ID,
            CLUTCH_BEARING_RETAINER_T
        );
}

module ch1_03c_extended_link_reference() {
    color("#b08d57") ch1_03c_extended_connecting_pin_pair();
    color("#9aa7b6") ch1_03c_extended_retaining_clips();
    color("#d17a3d") ch1_03c_clutch_platform();
    color("#b9c2ca") ch1_03c_clutch_bearing_visual();
    color("#a85c2a") ch1_03c_clutch_bearing_retainer();
}
//#endregion

//#region 方法/工具
assert(EXTENDED_SECOND_CLIP_Y - EXTENDED_FIRST_CLIP_Y - RETAINING_CLIP_T > 9.99);
assert(PLATFORM_T + 2 * PLATFORM_RIB_T < EXTENDED_NET_PLATFORM_CLEAR);
assert(PLATFORM_BEARING_BOSS_D > CLUTCH_BEARING_SEAT_D + 1.0);
assert(CLUTCH_BEARING_SEAT_END_Z < -PLATFORM_PIN_HOLE_D / 2);
assert(CLUTCH_BEARING_RETAINER_OD < CLUTCH_BEARING_RETAINER_RECESS_D);
assert(CLUTCH_BEARING_OD + CLUTCH_BEARING_SEAT_CLEARANCE < PLATFORM_T);
// 独立入口见 cad/openscad/ch1_03c_extended_connecting_pin.scad 等四个根文件。
//#endregion
