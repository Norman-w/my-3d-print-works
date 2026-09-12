// Mechanical contract
// process: purchased-part clearance / assembly visualization; this model is not a printable motor
// material: Pololu 100:1 Micro Metal Gearmotor HP 6V, no encoder, item #1101
// parting_plane: n/a; the purchased motor is represented as one clearance envelope
// opening_direction: output axis is local +Z from the gearbox face toward the D-shaft tip
// fastener: the motor body is an external purchased part; mounting hardware is not modeled here
// seal: n/a
// print_orientation: visualization only; do not print this motor envelope
// units: mm
// source: https://www.pololu.com/product/1101 and the Micro Metal Gearmotor dimensions drawing
// note: official dimensions used here are 10 x 12 mm gearbox cross-section, 9 mm gearbox length,
//       3 mm D output shaft x 9 mm long, and 25.6 mm maximum motor/gearbox body length.

//#region 导入/依赖
// 无外部库；尺寸常量直接对应官方产品/图纸。
//#endregion

//#region 常量/配置
$fa = 8;
$fs = 0.20;

MOTOR_GEARBOX_W = 10.0;
MOTOR_GEARBOX_H = 12.0;
MOTOR_GEARBOX_L = 9.0;
MOTOR_BODY_W = 10.0;
MOTOR_BODY_H = 10.0;
MOTOR_BODY_TOTAL_L = 25.6;
MOTOR_BODY_L = MOTOR_BODY_TOTAL_L - MOTOR_GEARBOX_L;
MOTOR_SHAFT_D = 3.0;
MOTOR_SHAFT_L = 9.0;
MOTOR_SHAFT_FLAT_DEPTH = 0.50;
MOTOR_GEARBOX_CORNER_R = 1.0;
MOTOR_BODY_CORNER_R = 2.0;
MOTOR_TERMINAL_W = 1.5;
MOTOR_TERMINAL_SPACING = 7.0;
MOTOR_TERMINAL_H = 1.4;
MOTOR_EPS = 0.05;
//#endregion

//#region 模型/类型
// 局部坐标：输出齿轮箱前端面 z=0；减速箱/电机向 -Z 延伸；D 轴向 +Z 延伸。
//#endregion

//#region 私有成员
module rounded_prism_xy(w, d, h, r, z0) {
    translate([0, 0, z0])
        hull() {
            for (x = [-w / 2 + r, w / 2 - r], y = [-d / 2 + r, d / 2 - r])
                translate([x, y, 0])
                    cylinder(r = r, h = h);
        }
}

module d_shaft() {
    // 3 mm D shaft: the flat is 0.5 mm in from the circular envelope.
    difference() {
        translate([0, 0, -MOTOR_EPS])
            cylinder(d = MOTOR_SHAFT_D, h = MOTOR_SHAFT_L + MOTOR_EPS);
        translate([
            MOTOR_SHAFT_D / 2 - MOTOR_SHAFT_FLAT_DEPTH,
            -MOTOR_SHAFT_D,
            -2 * MOTOR_EPS
        ])
            cube([
                MOTOR_SHAFT_D,
                2 * MOTOR_SHAFT_D,
                MOTOR_SHAFT_L + 4 * MOTOR_EPS
            ]);
    }
}

module gearbox_body() {
    rounded_prism_xy(
        MOTOR_GEARBOX_W,
        MOTOR_GEARBOX_H,
        MOTOR_GEARBOX_L,
        MOTOR_GEARBOX_CORNER_R,
        -MOTOR_GEARBOX_L
    );
}

module motor_can() {
    rounded_prism_xy(
        MOTOR_BODY_W,
        MOTOR_BODY_H,
        MOTOR_BODY_L + MOTOR_EPS,
        MOTOR_BODY_CORNER_R,
        -MOTOR_BODY_TOTAL_L
    );
}

module rear_terminals() {
    // The product has two narrow rear electrical tabs; cables are sold separately.
    for (x = [-MOTOR_TERMINAL_SPACING / 2, MOTOR_TERMINAL_SPACING / 2])
        translate([x, 0, -MOTOR_BODY_TOTAL_L + MOTOR_TERMINAL_H / 2])
            cube([MOTOR_TERMINAL_W, 2.0, MOTOR_TERMINAL_H], center = true);
}

//#endregion

//#region 公开 API
module pololu_micro_metal_motor_100_1_hp_6v() {
    union() {
        gearbox_body();
        motor_can();
        d_shaft();
        rear_terminals();
    }
}

module pololu_micro_metal_motor_100_1_hp_6v_colored() {
    color("#aeb7c2") gearbox_body();
    color("#343a40") motor_can();
    color("#d6d9dc") d_shaft();
    color("#c28b35") rear_terminals();
}
//#endregion

//#region 业务逻辑
// 输出轴的 D 平面沿局部 +X；与本项目动力轮的 D 孔方向一致。
// 电机总长 25.6 mm 不包含向前伸出的 9 mm 输出轴；装配时 shaft 进入动力轮通孔。
//#endregion

//#region 方法/工具
// 供根文件 use；不要直接把本库文件当作独立导出入口。
//#endregion
