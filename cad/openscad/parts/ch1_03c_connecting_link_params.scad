// CH1 03C 连接节五金 — 由 docs/parts/CH1-03C-roller-chain.md 参数化
// 单位：毫米。03C 链条本体是外购碳钢件；这里是连接节穿销/弹片的参考模型。

//#region 导入/依赖
include <../ch1_03c_params.scad>
//#endregion

//#region 常量/配置
$fa = 6;
$fs = 0.08;

// 文档明确给出的连接节主尺寸。
CONNECTING_PIN_PAIR_SPACING = P;       // 两根穿销的中心距 = 链条节距
CONNECTING_PIN_SHAFT_D = d2;           // 03C 销轴直径
CONNECTING_PIN_LENGTH = Lc;            // 03C 图面销轴总长
CONNECTING_PIN_HEAD_D = rivet_d;       // 固定端圆头的参考直径
CONNECTING_PIN_HEAD_H = rivet_h;

// 卖家文档没有给 03C CL 卡簧的完整展开图；以下是按用户提供的
// 「加长销/加长销带挡板」图和实物照片建立的装配参考假设。
// 卡簧按用户给出的实物轮廓建模：右端敞口；两根销的位置各有一段围绕销槽
// 的圆弧，圆弧之间由上下两条收腰弹臂连接。它不是等宽 U 槽，也不是两个
// 独立的 C 形耳片或实心连接链板。
CONNECTING_PIN_GROOVE_D = 1.20;
RETAINING_CLIP_T = T;                 // 03C 片厚；图示 04C 的 T=0.8 不套用
// 槽宽要覆盖整片厚度，并留少量侧向装配余量；原 0.34 mm 小于片厚，不能落槽。
CONNECTING_PIN_GROOVE_W = RETAINING_CLIP_T + 0.12;
CONNECTING_PIN_GROOVE_FROM_TIP = 0.48;
CONNECTING_PIN_GROOVE_CENTER = CONNECTING_PIN_LENGTH / 2 - CONNECTING_PIN_GROOVE_FROM_TIP;
CONNECTING_LINK_EPS = 0.05;
RETAINING_CLIP_H = h2;                // 外轮廓高度，沿用连接节链板高度
RETAINING_CLIP_OUTER_R = RETAINING_CLIP_H / 2;
RETAINING_CLIP_PIN_ARC_INNER_R = CONNECTING_PIN_GROOVE_D / 2 + 0.05;
RETAINING_CLIP_CLOSED_PIN_X = -CONNECTING_PIN_PAIR_SPACING / 2;
RETAINING_CLIP_OPEN_PIN_X = CONNECTING_PIN_PAIR_SPACING / 2;
// 右侧两段圆弧的末端张开到槽底直径附近，但小于完整销身直径，形成锁止口。
RETAINING_CLIP_OPEN_HALF_ANGLE = 68;
RETAINING_CLIP_THROAT_GAP_H = 2 * RETAINING_CLIP_PIN_ARC_INNER_R * sin(RETAINING_CLIP_OPEN_HALF_ANGLE);
RETAINING_CLIP_OPEN_TIP_X = RETAINING_CLIP_OPEN_PIN_X + RETAINING_CLIP_OUTER_R + CONNECTING_LINK_EPS;
// 中间开口在两销之间放宽，在销位处收回到圆弧；这样圆弧不会被直线开口吞掉。
RETAINING_CLIP_SLOT_CENTER_HALF_H = 1.05;
RETAINING_CLIP_PIN_JOIN_HALF_H = 0.55;
RETAINING_CLIP_SLOT_RAMP_X = 0.85;
RETAINING_CLIP_PIN_JOIN_DX = sqrt(
    RETAINING_CLIP_PIN_ARC_INNER_R * RETAINING_CLIP_PIN_ARC_INNER_R
    - RETAINING_CLIP_PIN_JOIN_HALF_H * RETAINING_CLIP_PIN_JOIN_HALF_H
);
RETAINING_CLIP_LEFT_JOIN_X = RETAINING_CLIP_CLOSED_PIN_X + RETAINING_CLIP_PIN_JOIN_DX;
RETAINING_CLIP_RIGHT_JOIN_X = RETAINING_CLIP_OPEN_PIN_X - RETAINING_CLIP_PIN_JOIN_DX;
RETAINING_CLIP_LEFT_RAMP_X = RETAINING_CLIP_CLOSED_PIN_X + RETAINING_CLIP_SLOT_RAMP_X;
RETAINING_CLIP_RIGHT_RAMP_X = RETAINING_CLIP_OPEN_PIN_X - RETAINING_CLIP_SLOT_RAMP_X;
RETAINING_CLIP_OPEN_HALF_H = RETAINING_CLIP_THROAT_GAP_H / 2;
//#endregion

//#region 模型/类型
// 连接节局部坐标：两销中心位于 x=±P/2，销轴沿 +Y；固定头在 -Y 端。
// 弹片位于 +Y 端槽内：局部 -X 是闭合圆弧端，局部 +X 是两段圆弧形成的敞口端；
// 两弹臂从闭端向开口侧销逐渐收腰，右侧圆弧的内缘落入销轴环槽。
// 独立打印时绕 X 轴旋转 90° 铺平。
//#endregion

//#region 公开 API
// include 后可调用 ch1_03c_connecting_pin_pair()、ch1_03c_retaining_clip()。
//#endregion

//#region 私有成员
module connecting_pin_groove_cut(x) {
    translate([
        x,
        CONNECTING_PIN_GROOVE_CENTER - CONNECTING_PIN_GROOVE_W / 2,
        0
    ])
        rotate([-90, 0, 0])
            difference() {
                cylinder(
                    d = CONNECTING_PIN_SHAFT_D + 0.60,
                    h = CONNECTING_PIN_GROOVE_W
                );
                translate([0, 0, -CONNECTING_LINK_EPS])
                    cylinder(
                        d = CONNECTING_PIN_GROOVE_D,
                        h = CONNECTING_PIN_GROOVE_W + 2 * CONNECTING_LINK_EPS
                    );
            }
}

module connecting_pin_one(x) {
    difference() {
        union() {
            translate([x, -CONNECTING_PIN_LENGTH / 2, 0])
                rotate([-90, 0, 0])
                    cylinder(d = CONNECTING_PIN_SHAFT_D, h = CONNECTING_PIN_LENGTH);
            translate([x, -CONNECTING_PIN_LENGTH / 2, 0])
                rotate([-90, 0, 0])
                    cylinder(d = CONNECTING_PIN_HEAD_D, h = CONNECTING_PIN_HEAD_H);
        }
        connecting_pin_groove_cut(x);
    }
}

module retaining_clip_outer_profile_2d() {
    // 绿色箭头所示的外轮廓：两销中心同轴的长圆外廓，右端由内腔切开。
    union() {
        translate([RETAINING_CLIP_CLOSED_PIN_X, 0])
            circle(r = RETAINING_CLIP_OUTER_R);
        translate([RETAINING_CLIP_OPEN_PIN_X, 0])
            circle(r = RETAINING_CLIP_OUTER_R);
        translate([RETAINING_CLIP_CLOSED_PIN_X, -RETAINING_CLIP_OUTER_R])
            square([
                CONNECTING_PIN_PAIR_SPACING,
                2 * RETAINING_CLIP_OUTER_R
            ]);
    }
}

module retaining_clip_opening_2d() {
    // 绿色箭头所示的内轮廓：左销位圆弧 → 放宽的中间段 → 右销位圆弧 → 右端开口。
    // 直线在圆弧的上/下交点处过渡，不能从销中心直接切过去。
    union() {
        translate([RETAINING_CLIP_CLOSED_PIN_X, 0])
            circle(r = RETAINING_CLIP_PIN_ARC_INNER_R);
        translate([RETAINING_CLIP_OPEN_PIN_X, 0])
            circle(r = RETAINING_CLIP_PIN_ARC_INNER_R);
        polygon([
            [RETAINING_CLIP_LEFT_JOIN_X, -RETAINING_CLIP_PIN_JOIN_HALF_H],
            [RETAINING_CLIP_LEFT_RAMP_X, -RETAINING_CLIP_SLOT_CENTER_HALF_H],
            [RETAINING_CLIP_RIGHT_RAMP_X, -RETAINING_CLIP_SLOT_CENTER_HALF_H],
            [RETAINING_CLIP_RIGHT_JOIN_X, -RETAINING_CLIP_PIN_JOIN_HALF_H],
            [RETAINING_CLIP_OPEN_TIP_X, -RETAINING_CLIP_OPEN_HALF_H],
            [RETAINING_CLIP_OPEN_TIP_X, RETAINING_CLIP_OPEN_HALF_H],
            [RETAINING_CLIP_RIGHT_JOIN_X, RETAINING_CLIP_PIN_JOIN_HALF_H],
            [RETAINING_CLIP_RIGHT_RAMP_X, RETAINING_CLIP_SLOT_CENTER_HALF_H],
            [RETAINING_CLIP_LEFT_RAMP_X, RETAINING_CLIP_SLOT_CENTER_HALF_H],
            [RETAINING_CLIP_LEFT_JOIN_X, RETAINING_CLIP_PIN_JOIN_HALF_H]
        ]);
    }
}

module retaining_clip_profile_2d() {
    union() {
        difference() {
            retaining_clip_outer_profile_2d();
            retaining_clip_opening_2d();
        }
    }
}
//#endregion

//#region 业务逻辑
module ch1_03c_connecting_pin_pair() {
    for (x = [-CONNECTING_PIN_PAIR_SPACING / 2, CONNECTING_PIN_PAIR_SPACING / 2])
        connecting_pin_one(x);
}

module ch1_03c_retaining_clip() {
    // 与双销保持同一装配坐标；单独打印时应将夹片绕 X 轴旋转 90° 铺平。
    translate([0, CONNECTING_PIN_GROOVE_CENTER, 0])
        rotate([90, 0, 0])
            linear_extrude(
                height = RETAINING_CLIP_T,
                center = true,
                convexity = 6
            )
                retaining_clip_profile_2d();
}

module ch1_03c_connecting_link_reference() {
    color("#b08d57") ch1_03c_connecting_pin_pair();
    color("#9aa7b6") ch1_03c_retaining_clip();
}
//#endregion

//#region 方法/工具
assert(CONNECTING_PIN_GROOVE_W > RETAINING_CLIP_T);
assert(RETAINING_CLIP_THROAT_GAP_H > CONNECTING_PIN_GROOVE_D - 0.01);
assert(RETAINING_CLIP_THROAT_GAP_H < CONNECTING_PIN_SHAFT_D);
assert(RETAINING_CLIP_CLOSED_PIN_X < RETAINING_CLIP_OPEN_PIN_X);
assert(RETAINING_CLIP_OPEN_TIP_X > RETAINING_CLIP_OPEN_PIN_X);
assert(RETAINING_CLIP_PIN_JOIN_HALF_H < RETAINING_CLIP_PIN_ARC_INNER_R);
assert(RETAINING_CLIP_LEFT_JOIN_X < RETAINING_CLIP_LEFT_RAMP_X);
assert(RETAINING_CLIP_RIGHT_RAMP_X < RETAINING_CLIP_RIGHT_JOIN_X);
assert(RETAINING_CLIP_SLOT_CENTER_HALF_H > RETAINING_CLIP_PIN_JOIN_HALF_H);
assert(RETAINING_CLIP_OPEN_HALF_H < RETAINING_CLIP_PIN_ARC_INNER_R);
// 此文件是库；独立导出入口见 cad/openscad/ch1_03c_connecting_pin.scad
// 和 cad/openscad/ch1_03c_retaining_clip.scad。
//#endregion
