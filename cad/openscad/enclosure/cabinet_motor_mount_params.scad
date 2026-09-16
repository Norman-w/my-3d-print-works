// 蛇形动力电机圆角矩形 Ω 形固定套/向下固定座的共享尺寸真值源。
// 局部参考原点：snake_drive_c() 的轮轴中心；Y=0 为链轮中心平面。
// 本文件的局部 X/Y/Z 直接对应柜体世界 X/Y/Z；Z 是柜底向上的高度轴。

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
MOTOR_MOUNT_SLIDE_STROKE = 6.0;  // Ω套/电机沿柜体 Z 调节

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
// below the motor.
MOTOR_MOUNT_OMEGA_MOUTH_SIGN = -1;
MOTOR_MOUNT_OMEGA_MOUTH_W = MOTOR_MOUNT_OMEGA_OUTER_W;

// The bottom of the Ω sleeve ends in two short horizontal mounting seats.
// In the rear view they are the outward ledges in `_ |    | _`, not legs.
// Their screw holes are normal to local/world Z, so the fixing direction is
// vertically downward into the cabinet-floor bosses.
MOTOR_MOUNT_OMEGA_SEAT_W = 13.0;
MOTOR_MOUNT_OMEGA_SEAT_L = MOTOR_MOUNT_OMEGA_BODY_L;
MOTOR_MOUNT_OMEGA_SEAT_T = 3.0;        // local/world Z thickness
MOTOR_MOUNT_OMEGA_SEAT_R = 1.0;
MOTOR_MOUNT_OMEGA_SEAT_OVERLAP = 1.5;  // positive solid overlap into side wall
MOTOR_MOUNT_OMEGA_SEAT_CONNECT_H = 4.4;
// Two holes are on the front row and two on the rear row.  The rows are
// deliberately inset from both ends of each seat; they are not two holes
// clustered at the rear edge.
MOTOR_MOUNT_OMEGA_SEAT_FASTENER_EDGE_MARGIN_Y = 5.0;
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

MOTOR_MOUNT_OMEGA_SPRING_SEAT_H = 1.0;

// 预览中的硬弹簧与大蘑菇头压紧螺钉；真实弹簧/螺钉仍是采购件。
// 外径必须大于“柱外径 + 线径×2”，否则弹簧会与导向柱干涉。
MOTOR_MOUNT_SPRING_OD = 8.0;
MOTOR_MOUNT_SPRING_WIRE_D = 1.1;
MOTOR_MOUNT_SPRING_ID =
    MOTOR_MOUNT_SPRING_OD - 2 * MOTOR_MOUNT_SPRING_WIRE_D;
MOTOR_MOUNT_SPRING_FREE_L = 14.0;
MOTOR_MOUNT_SPRING_START_CLEAR = 0.25;
MOTOR_MOUNT_SPRING_SEAT_TOP_Z =
    TEN_Z + MOTOR_MOUNT_OMEGA_SEAT_TOP_Z
        + MOTOR_MOUNT_OMEGA_SPRING_SEAT_H;
MOTOR_MOUNT_SPRING_START_Z =
    MOTOR_MOUNT_SPRING_SEAT_TOP_Z + MOTOR_MOUNT_SPRING_START_CLEAR;
MOTOR_MOUNT_SPRING_TOP_Z =
    MOTOR_MOUNT_SPRING_START_Z + MOTOR_MOUNT_SPRING_FREE_L;

// 柜体上的四组 Boss：底部是比座子更大的承托/限位基台，上方是可套入座孔
// 的实体导向柱。基台露出柜底并决定座子最低高度；导向柱不打穿箱底。
MOTOR_MOUNT_BOSS_STAGE1_EMBED = 0.45;
MOTOR_MOUNT_BOSS_STAGE1_Z0 = WALL - MOTOR_MOUNT_BOSS_STAGE1_EMBED;
MOTOR_MOUNT_BOSS_SEAT_STOP_CLEARANCE = 0.20;
MOTOR_MOUNT_BOSS_STAGE1_TOP_Z =
    TEN_Z + MOTOR_MOUNT_OMEGA_SEAT_BOTTOM_Z
        - MOTOR_MOUNT_BOSS_SEAT_STOP_CLEARANCE;
MOTOR_MOUNT_BOSS_STAGE1_H =
    MOTOR_MOUNT_BOSS_STAGE1_TOP_Z - MOTOR_MOUNT_BOSS_STAGE1_Z0;
MOTOR_MOUNT_BOSS_STAGE1_RAIL_W = MOTOR_MOUNT_OMEGA_SEAT_W + 2.0;
MOTOR_MOUNT_BOSS_STAGE1_RAIL_L = MOTOR_MOUNT_OMEGA_SEAT_L + 4.0;
MOTOR_MOUNT_BOSS_STAGE1_RAIL_R = 1.2;
MOTOR_MOUNT_BOSS_POST_TOP_CLEARANCE = 0.30;
MOTOR_MOUNT_BOSS_GUIDE_TOP_Z =
    MOTOR_MOUNT_SPRING_TOP_Z - MOTOR_MOUNT_BOSS_POST_TOP_CLEARANCE;
MOTOR_MOUNT_BOSS_GUIDE_H =
    MOTOR_MOUNT_BOSS_GUIDE_TOP_Z - MOTOR_MOUNT_BOSS_STAGE1_TOP_Z;
MOTOR_MOUNT_BOSS_GUIDE_OD = 5.0;
MOTOR_MOUNT_BOSS_PILOT_D = 2.5;
MOTOR_MOUNT_BOSS_PILOT_DEPTH = 12.0;
MOTOR_MOUNT_BOSS_PILOT_BOTTOM_Z =
    MOTOR_MOUNT_BOSS_GUIDE_TOP_Z - MOTOR_MOUNT_BOSS_PILOT_DEPTH;
MOTOR_MOUNT_BOSS_PILOT_END_CLEARANCE = 4.0;

// Ω 套固定座的孔放大为导向柱滑动孔；M3 螺钉从中心进入柱顶盲孔。
// 弹簧套在柱外，座子上的座圈承托弹簧下端。
MOTOR_MOUNT_OMEGA_SEAT_GUIDE_HOLE_D = MOTOR_MOUNT_BOSS_GUIDE_OD + 0.8;
MOTOR_MOUNT_OMEGA_SPRING_SEAT_OD = MOTOR_MOUNT_SPRING_OD + 1.0;

MOTOR_MOUNT_SCREW_SHAFT_D = 3.2;
MOTOR_MOUNT_SCREW_HEAD_D = MOTOR_MOUNT_SPRING_OD + 1.0;
MOTOR_MOUNT_SCREW_HEAD_H = 2.4;
MOTOR_MOUNT_SCREW_HEAD_Z = MOTOR_MOUNT_SPRING_TOP_Z;
MOTOR_MOUNT_SCREW_CLEAR_D = MOTOR_MOUNT_OMEGA_SEAT_GUIDE_HOLE_D;

// 旧名称保留为兼容别名，避免已有入口因重命名失效；实际几何由上面的
// 台阶导轨和导向柱生成，不再使用旧的四个独立圆柱接收座。
MOTOR_MOUNT_FLOOR_SEAT_D = MOTOR_MOUNT_BOSS_STAGE1_RAIL_W;
MOTOR_MOUNT_FLOOR_SEAT_H = MOTOR_MOUNT_BOSS_STAGE1_H;
MOTOR_MOUNT_FLOOR_BORE_D = MOTOR_MOUNT_BOSS_PILOT_D;
MOTOR_MOUNT_EPS = 0.05;

MOTOR_MOUNT_FLOOR_SEAT_OFFSETS_X = [
    -MOTOR_MOUNT_OMEGA_SEAT_CENTER_X,
    MOTOR_MOUNT_OMEGA_SEAT_CENTER_X
];
//#endregion

//#region 模型/类型
// motor_mount_c() 与 cabinet_chain_path.scad 中的右下 snake_drive_c() 同一
// 动力轴中心；其第二坐标是柜体世界 Z 高度。
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
    && MOTOR_MOUNT_BOSS_STAGE1_TOP_Z < TEN_Z + MOTOR_MOUNT_OMEGA_SEAT_BOTTOM_Z
    && abs(
        TEN_Z + MOTOR_MOUNT_OMEGA_SEAT_BOTTOM_Z
            - MOTOR_MOUNT_BOSS_STAGE1_TOP_Z
            - MOTOR_MOUNT_BOSS_SEAT_STOP_CLEARANCE
    ) < 0.01,
    "boss base must be above the floor and define the seat stop");
assert(MOTOR_MOUNT_BOSS_STAGE1_H > 2.0,
    "boss base must have a printable support height");
assert(MOTOR_MOUNT_BOSS_GUIDE_H > 8.0,
    "guide post must be long enough to constrain the moving seat");
assert(MOTOR_MOUNT_BOSS_GUIDE_TOP_Z < MOTOR_MOUNT_SCREW_HEAD_Z,
    "guide post must end below the spring-loaded screw head");
assert(MOTOR_MOUNT_BOSS_PILOT_BOTTOM_Z
        > MOTOR_MOUNT_BOSS_STAGE1_TOP_Z
            + MOTOR_MOUNT_BOSS_PILOT_END_CLEARANCE,
    "blind pilot hole must leave solid material above the boss base");
assert(MOTOR_MOUNT_BOSS_GUIDE_OD
        - MOTOR_MOUNT_BOSS_PILOT_D > 1.0,
    "guide post must leave a printable annular wall around the pilot hole");
assert(MOTOR_MOUNT_OMEGA_SEAT_GUIDE_HOLE_D
        > MOTOR_MOUNT_BOSS_GUIDE_OD + 0.60
        && MOTOR_MOUNT_SPRING_ID
            > MOTOR_MOUNT_BOSS_GUIDE_OD + 0.60,
    "Omega guide holes need radial print clearance around the cabinet posts");
assert(MOTOR_MOUNT_OMEGA_SPRING_SEAT_OD > MOTOR_MOUNT_SPRING_OD
        && MOTOR_MOUNT_SPRING_ID > MOTOR_MOUNT_BOSS_GUIDE_OD,
    "spring seat collar must support the full spring diameter");
assert(MOTOR_MOUNT_SCREW_CLEAR_D > MOTOR_MOUNT_SCREW_SHAFT_D,
    "screw shaft must have clearance in the moving seat hole");
assert(MOTOR_MOUNT_OMEGA_SEAT_FASTENER_EDGE_MARGIN_Y
        > MOTOR_MOUNT_SCREW_HEAD_D / 2,
    "front/rear fastener rows must clear both seat ends");
//#endregion
