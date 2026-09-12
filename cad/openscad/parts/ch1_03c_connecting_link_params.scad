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

// 卖家文档没有给 CL 弹片专用槽宽/展开图；以下是装配原型的显式假设。
// 夹片从销轴侧面滑入槽内，内孔小于销身但大于槽底，形成卡持。
CONNECTING_PIN_GROOVE_D = 1.20;
CONNECTING_PIN_GROOVE_W = 0.34;
CONNECTING_PIN_GROOVE_FROM_TIP = 0.48;
CONNECTING_PIN_GROOVE_CENTER = CONNECTING_PIN_LENGTH / 2 - CONNECTING_PIN_GROOVE_FROM_TIP;

RETAINING_CLIP_T = 0.30;
RETAINING_CLIP_EAR_OD = 2.20;
RETAINING_CLIP_HOLE_D = CONNECTING_PIN_GROOVE_D + 0.12;
RETAINING_CLIP_ENTRY_W = 0.40;
RETAINING_CLIP_BRIDGE_T = 0.48;
RETAINING_CLIP_BRIDGE_Z = 0.72;
CONNECTING_LINK_EPS = 0.05;
//#endregion

//#region 模型/类型
// 连接节局部坐标：两销中心位于 x=±P/2，销轴沿 +Y；固定头在 -Y 端。
// 弹片位于 +Y 端槽内，两个 C 形耳孔的开口朝外，便于侧向滑入。
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

module retaining_clip_profile_2d() {
    difference() {
        union() {
            for (x = [-CONNECTING_PIN_PAIR_SPACING / 2, CONNECTING_PIN_PAIR_SPACING / 2])
                translate([x, 0])
                    circle(d = RETAINING_CLIP_EAR_OD);
            translate([0, RETAINING_CLIP_BRIDGE_Z])
                square([
                    CONNECTING_PIN_PAIR_SPACING + RETAINING_CLIP_EAR_OD,
                    RETAINING_CLIP_BRIDGE_T
                ], center = true);
        }
        for (side = [-1, 1]) {
            translate([side * CONNECTING_PIN_PAIR_SPACING / 2, 0])
                circle(d = RETAINING_CLIP_HOLE_D);
            // 侧向入口：切到外缘，保留上方桥接和内侧耳根。
            translate([
                side * (
                    CONNECTING_PIN_PAIR_SPACING / 2
                    + RETAINING_CLIP_EAR_OD / 2
                    - 0.05
                ),
                0
            ])
                square([
                    RETAINING_CLIP_EAR_OD,
                    RETAINING_CLIP_ENTRY_W
                ], center = true);
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
// 此文件是库；独立导出入口见 cad/openscad/ch1_03c_connecting_pin.scad
// 和 cad/openscad/ch1_03c_retaining_clip.scad。
//#endregion
