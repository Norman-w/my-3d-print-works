// 蛇形动力电机圆角矩形 Ω 形固定套/向下固定座的共享尺寸真值源。
// 局部参考原点：snake_drive_c() 的轮轴中心；Y=0 为链轮中心平面。
// 这里仍沿旧链条局部 Y 伸向背板；网页适配器会把它映射到当前世界深度轴。

//#region 导入/依赖
include <cabinet_params.scad>
include <../parts/ch1_03c_sprocket_params.scad>
// The generated chain solution is the shared nominal position of the movable
// lower return carriage.  It keeps the lower fixing-seat datum and the chain
// sprocket datum on the same measured pitch solution.
include <cabinet_chain_pins.gen.scad>
//#endregion

//#region 常量/配置
MOTOR_MOUNT_SPROCKET_TEETH = 12;
MOTOR_MOUNT_WALL_CLEAR = 0.40;
MOTOR_MOUNT_CHAIN_Y = PARTITION_BACK_Y + 12.0;
MOTOR_MOUNT_SLIDE_STROKE = 6.0;  // Ω套/电机沿旧 Z 调节；网页世界中对应竖直 Y

// 电机/动力轮几何
MOTOR_MOUNT_WHEEL_BACK_GAP = 0.50;
MOTOR_MOUNT_COVER_FRONT_Y_LOCAL = HUB_H / 2 + MOTOR_MOUNT_WHEEL_BACK_GAP;
MOTOR_MOUNT_OMEGA_BODY_L = 28.0;
MOTOR_MOUNT_OMEGA_MOTOR_W = 10.0; // Pololu gearbox/body max X
MOTOR_MOUNT_OMEGA_MOTOR_H = 12.0; // Pololu gearbox max cross-section height
MOTOR_MOUNT_OMEGA_CLEAR = 0.80;    // FDM clearance around the purchased motor
MOTOR_MOUNT_OMEGA_WALL_T = 2.80;
// The motor is rectangular with rounded corners, so the sleeve follows that
// envelope instead of replacing it with a circular tube.  The inner radius
// is the gearbox corner radius plus the FDM clearance; the outer radius adds
// the structural wall thickness.
MOTOR_MOUNT_OMEGA_INNER_W =
    MOTOR_MOUNT_OMEGA_MOTOR_W + 2 * MOTOR_MOUNT_OMEGA_CLEAR;
MOTOR_MOUNT_OMEGA_INNER_H =
    MOTOR_MOUNT_OMEGA_MOTOR_H + 2 * MOTOR_MOUNT_OMEGA_CLEAR;
MOTOR_MOUNT_OMEGA_INNER_R = 1.80;
MOTOR_MOUNT_OMEGA_OUTER_W =
    MOTOR_MOUNT_OMEGA_INNER_W + 2 * MOTOR_MOUNT_OMEGA_WALL_T;
MOTOR_MOUNT_OMEGA_OUTER_H =
    MOTOR_MOUNT_OMEGA_INNER_H + 2 * MOTOR_MOUNT_OMEGA_WALL_T;
MOTOR_MOUNT_OMEGA_OUTER_R =
    MOTOR_MOUNT_OMEGA_INNER_R + MOTOR_MOUNT_OMEGA_WALL_T;
// The lower mouth makes the rear-view profile read as Ω.  It cuts through the
// complete lower span of the outer sleeve, so no curved-bottom bridge remains
// below the motor.  The legacy chain adapter maps local -Z to current world
// -Y, i.e. the downward direction.
MOTOR_MOUNT_OMEGA_MOUTH_SIGN = -1;
MOTOR_MOUNT_OMEGA_MOUTH_W = MOTOR_MOUNT_OMEGA_OUTER_W;

// The bottom of the Ω sleeve ends in two short horizontal mounting seats.
// In the rear view they are the outward ledges in `_ |    | _`, not legs.
// Their screw holes are normal to local Z; the legacy adapter maps that axis
// to the current world's Y axis, so the fixing direction is downward.
MOTOR_MOUNT_OMEGA_SEAT_W = 13.0;
MOTOR_MOUNT_OMEGA_SEAT_L = MOTOR_MOUNT_OMEGA_BODY_L;
MOTOR_MOUNT_OMEGA_SEAT_T = 3.0;        // local Z / world Y thickness
MOTOR_MOUNT_OMEGA_SEAT_R = 1.0;
MOTOR_MOUNT_OMEGA_SEAT_OVERLAP = 2.8;  // positive solid overlap into side wall
MOTOR_MOUNT_OMEGA_SEAT_CONNECT_H = 4.4;
// Two holes are on the front row and two on the rear row.  The rows are
// deliberately inset from both ends of each seat; they are not two holes
// clustered at the rear edge.
MOTOR_MOUNT_OMEGA_SEAT_FASTENER_EDGE_MARGIN_Y = 3.5;
MOTOR_MOUNT_OMEGA_SEAT_FASTENER_OFFSETS_Y = [
    -MOTOR_MOUNT_OMEGA_SEAT_L / 2
        + MOTOR_MOUNT_OMEGA_SEAT_FASTENER_EDGE_MARGIN_Y,
    MOTOR_MOUNT_OMEGA_SEAT_L / 2
        - MOTOR_MOUNT_OMEGA_SEAT_FASTENER_EDGE_MARGIN_Y
];
MOTOR_MOUNT_OMEGA_BODY_REAR_Y_LOCAL =
    MOTOR_MOUNT_COVER_FRONT_Y_LOCAL + MOTOR_MOUNT_OMEGA_BODY_L;
MOTOR_MOUNT_OMEGA_SEAT_FRONT_Y_LOCAL =
    MOTOR_MOUNT_COVER_FRONT_Y_LOCAL;
MOTOR_MOUNT_OMEGA_SEAT_TOP_Z =
    -MOTOR_MOUNT_OMEGA_OUTER_H / 2
        + MOTOR_MOUNT_OMEGA_SEAT_CONNECT_H;
MOTOR_MOUNT_OMEGA_SEAT_BOTTOM_Z =
    MOTOR_MOUNT_OMEGA_SEAT_TOP_Z - MOTOR_MOUNT_OMEGA_SEAT_T;
MOTOR_MOUNT_OMEGA_SEAT_CENTER_Y_LOCAL =
    MOTOR_MOUNT_OMEGA_SEAT_FRONT_Y_LOCAL
        + MOTOR_MOUNT_OMEGA_SEAT_L / 2;
MOTOR_MOUNT_OMEGA_SEAT_CENTER_X =
    MOTOR_MOUNT_OMEGA_OUTER_W / 2
        + MOTOR_MOUNT_OMEGA_SEAT_W / 2
        - MOTOR_MOUNT_OMEGA_SEAT_OVERLAP;

// 柜体上的四组台阶式 boss。一级台阶名义高度 4 mm；底部再埋入
// 0.45 mm 作为打印融合量，所以它露出柜底约 3.55 mm，并在座子落下
// 时留下由参数控制的下限位间隙。二级是从一级顶面向上的 20 mm 空心
// 导向柱：螺钉轴线仍与四个孔完全同轴，弹簧套在导向柱外面。
MOTOR_MOUNT_BOSS_STAGE1_H = 4.0;
MOTOR_MOUNT_BOSS_STAGE1_EMBED = 0.45;
MOTOR_MOUNT_BOSS_STAGE1_Z0 = WALL - MOTOR_MOUNT_BOSS_STAGE1_EMBED;
MOTOR_MOUNT_BOSS_STAGE1_TOP_Z =
    MOTOR_MOUNT_BOSS_STAGE1_Z0 + MOTOR_MOUNT_BOSS_STAGE1_H;
MOTOR_MOUNT_BOSS_STAGE1_RAIL_W = MOTOR_MOUNT_OMEGA_SEAT_W + 2.0;
MOTOR_MOUNT_BOSS_STAGE1_RAIL_L = MOTOR_MOUNT_OMEGA_SEAT_L + 4.0;
MOTOR_MOUNT_BOSS_STAGE1_RAIL_R = 1.2;
MOTOR_MOUNT_BOSS_GUIDE_H = 20.0;
MOTOR_MOUNT_BOSS_GUIDE_OD = 4.4;
MOTOR_MOUNT_BOSS_GUIDE_BORE_D = 3.6;
MOTOR_MOUNT_BOSS_GUIDE_TOP_Z =
    MOTOR_MOUNT_BOSS_STAGE1_TOP_Z + MOTOR_MOUNT_BOSS_GUIDE_H;

// Ω 套固定座的孔放大为导向柱通孔；M3 螺钉仍沿孔中心穿过。导向孔
// 比导向柱直径大 0.8 mm，弹簧座圈外径 8 mm，给硬弹簧提供平整承托。
MOTOR_MOUNT_OMEGA_SEAT_GUIDE_HOLE_D = MOTOR_MOUNT_BOSS_GUIDE_OD + 0.8;
MOTOR_MOUNT_OMEGA_SPRING_SEAT_OD = 8.0;
MOTOR_MOUNT_OMEGA_SPRING_SEAT_H = 1.0;

// 预览中的硬弹簧与大蘑菇头压紧螺钉；真实弹簧/螺钉仍是采购件。
MOTOR_MOUNT_SPRING_OD = 6.0;
MOTOR_MOUNT_SPRING_WIRE_D = 1.1;
MOTOR_MOUNT_SPRING_FREE_L = 14.0;
MOTOR_MOUNT_SPRING_START_CLEAR = 0.25;
MOTOR_MOUNT_SPRING_SEAT_TOP_Z =
    TEN_Z + MOTOR_MOUNT_OMEGA_SEAT_TOP_Z
        + MOTOR_MOUNT_OMEGA_SPRING_SEAT_H;
MOTOR_MOUNT_SPRING_START_Z =
    MOTOR_MOUNT_SPRING_SEAT_TOP_Z + MOTOR_MOUNT_SPRING_START_CLEAR;
MOTOR_MOUNT_SPRING_TOP_Z =
    MOTOR_MOUNT_SPRING_START_Z + MOTOR_MOUNT_SPRING_FREE_L;
MOTOR_MOUNT_SCREW_SHAFT_D = 3.2;
MOTOR_MOUNT_SCREW_HEAD_D = 6.0;
MOTOR_MOUNT_SCREW_HEAD_H = 2.4;
MOTOR_MOUNT_SCREW_HEAD_Z = MOTOR_MOUNT_SPRING_TOP_Z;
MOTOR_MOUNT_SCREW_CLEAR_D = MOTOR_MOUNT_BOSS_GUIDE_BORE_D;

// 旧名称保留为兼容别名，避免已有入口因重命名失效；实际几何由上面的
// 台阶导轨和导向柱生成，不再使用旧的四个独立圆柱接收座。
MOTOR_MOUNT_FLOOR_SEAT_D = MOTOR_MOUNT_BOSS_STAGE1_RAIL_W;
MOTOR_MOUNT_FLOOR_SEAT_H = MOTOR_MOUNT_BOSS_STAGE1_H;
MOTOR_MOUNT_FLOOR_BORE_D = MOTOR_MOUNT_BOSS_GUIDE_BORE_D;
MOTOR_MOUNT_EPS = 0.05;

MOTOR_MOUNT_FLOOR_SEAT_OFFSETS_X = [
    -MOTOR_MOUNT_OMEGA_SEAT_CENTER_X,
    MOTOR_MOUNT_OMEGA_SEAT_CENTER_X
];
//#endregion

//#region 模型/类型
// motor_mount_c() 与 cabinet_chain_path.scad 中的右下 snake_drive_c() 同一
// 动力轴中心。此处第二坐标是旧链条文件的竖向 Z，经过网页适配器后是世界 +Y。
//#endregion

//#region 公开 API
function motor_mount_pitch_r() = sprocket_pitch_r(MOTOR_MOUNT_SPROCKET_TEETH);

function motor_mount_outer_r() =
    motor_mount_pitch_r() + TOOTH_ADDENDUM;

function motor_mount_return_x() =
    WALL + motor_mount_outer_r() + MOTOR_MOUNT_WALL_CLEAR;

function motor_mount_c() = [
    motor_mount_return_x() + motor_mount_pitch_r(),
    TEN_Z,
    0
];
//#endregion

//#region 业务逻辑
assert(MOTOR_MOUNT_OMEGA_INNER_W >= MOTOR_MOUNT_OMEGA_MOTOR_W
    + 2 * MOTOR_MOUNT_OMEGA_CLEAR - MOTOR_MOUNT_EPS
    && MOTOR_MOUNT_OMEGA_INNER_H >= MOTOR_MOUNT_OMEGA_MOTOR_H
    + 2 * MOTOR_MOUNT_OMEGA_CLEAR - MOTOR_MOUNT_EPS,
    "omega sleeve must clear the Pololu 10x12 mm gearbox");
assert(MOTOR_MOUNT_OMEGA_INNER_R >= 1.0 + MOTOR_MOUNT_OMEGA_CLEAR,
    "omega inner corner radius must clear the gearbox corners");
assert(MOTOR_MOUNT_OMEGA_SEAT_BOTTOM_Z
        < -MOTOR_MOUNT_OMEGA_OUTER_H / 2 + 1.5
    && MOTOR_MOUNT_OMEGA_SEAT_TOP_Z
        > -MOTOR_MOUNT_OMEGA_OUTER_H / 2,
    "omega mounting seats must overlap the lower sleeve wall");
assert(MOTOR_MOUNT_OMEGA_SEAT_CENTER_X > MOTOR_MOUNT_OMEGA_OUTER_W / 2,
    "omega mounting seats must extend outward from the sleeve sides");
assert(MOTOR_MOUNT_OMEGA_SEAT_CENTER_X
        - MOTOR_MOUNT_SCREW_HEAD_D / 2
        > MOTOR_MOUNT_OMEGA_OUTER_W / 2 + 0.20,
    "screw-head relief must clear the outside of the sleeve");
assert(MOTOR_MOUNT_BOSS_STAGE1_EMBED > 0
    && MOTOR_MOUNT_BOSS_STAGE1_EMBED < WALL,
    "stage-one boss embedment must fuse into, not pass through, the cabinet floor");
assert(MOTOR_MOUNT_BOSS_STAGE1_TOP_Z > WALL
    && MOTOR_MOUNT_BOSS_STAGE1_TOP_Z
        < TEN_Z + MOTOR_MOUNT_OMEGA_SEAT_BOTTOM_Z,
    "stage-one boss must expose above the floor and remain below the Omega seat");
assert(MOTOR_MOUNT_BOSS_GUIDE_OD > MOTOR_MOUNT_BOSS_GUIDE_BORE_D,
    "guide post must leave a printable annular wall");
assert(MOTOR_MOUNT_OMEGA_SEAT_GUIDE_HOLE_D
        > MOTOR_MOUNT_BOSS_GUIDE_OD + 0.60,
    "Omega guide holes need radial print clearance around the cabinet posts");
assert(MOTOR_MOUNT_OMEGA_SPRING_SEAT_OD > MOTOR_MOUNT_SPRING_OD,
    "spring seat collar must support the full spring diameter");
assert(MOTOR_MOUNT_SCREW_CLEAR_D > MOTOR_MOUNT_SCREW_SHAFT_D,
    "screw shaft must have clearance in the guide bore");
assert(MOTOR_MOUNT_OMEGA_SEAT_FASTENER_EDGE_MARGIN_Y
        > MOTOR_MOUNT_SCREW_HEAD_D / 2,
    "front/rear fastener rows must clear both seat ends");
//#endregion
