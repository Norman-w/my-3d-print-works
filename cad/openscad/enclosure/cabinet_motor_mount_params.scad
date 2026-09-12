// 动力电机固定罩/背板 boss 的共享尺寸真值源。
// 局部参考原点：power_c() 的轮轴中心；Y=0 为链轮中心平面。
// 背板内侧是世界 Y=D-BACK_PANEL_T，固定罩沿 +Y 伸向背板。

//#region 导入/依赖
include <cabinet_params.scad>
include <../parts/ch1_03c_sprocket_params.scad>
//#endregion

//#region 常量/配置
MOTOR_MOUNT_SPROCKET_TEETH = 12;
MOTOR_MOUNT_WALL_CLEAR = 0.40;
MOTOR_MOUNT_CHAIN_Y = PARTITION_BACK_Y + 12.0;
MOTOR_MOUNT_PANEL_Y = D - BACK_PANEL_T;
MOTOR_MOUNT_PANEL_Y_LOCAL = MOTOR_MOUNT_PANEL_Y - MOTOR_MOUNT_CHAIN_Y;

// 电机/动力轮几何
MOTOR_MOUNT_WHEEL_BACK_GAP = 0.50;
MOTOR_MOUNT_COVER_FRONT_Y_LOCAL = HUB_H / 2 + MOTOR_MOUNT_WHEEL_BACK_GAP;
MOTOR_MOUNT_COVER_BODY_L = 28.0;
MOTOR_MOUNT_COVER_REAR_WALL_T = 2.0;
MOTOR_MOUNT_COVER_BODY_REAR_Y_LOCAL =
    MOTOR_MOUNT_COVER_FRONT_Y_LOCAL + MOTOR_MOUNT_COVER_BODY_L;
MOTOR_MOUNT_COVER_FLANGE_T = 2.0;
MOTOR_MOUNT_COVER_OVERLAP = 0.05;
MOTOR_MOUNT_COVER_FLANGE_FRONT_Y_LOCAL =
    MOTOR_MOUNT_COVER_BODY_REAR_Y_LOCAL - MOTOR_MOUNT_COVER_OVERLAP;
MOTOR_MOUNT_COVER_FLANGE_REAR_Y_LOCAL =
    MOTOR_MOUNT_COVER_BODY_REAR_Y_LOCAL + MOTOR_MOUNT_COVER_FLANGE_T;
MOTOR_MOUNT_COVER_OUTER_W = 20.0;
MOTOR_MOUNT_COVER_OUTER_H = 22.0;
MOTOR_MOUNT_COVER_INNER_W = 14.0;
MOTOR_MOUNT_COVER_INNER_H = 16.0;
MOTOR_MOUNT_COVER_OUTER_R = 2.0;
MOTOR_MOUNT_COVER_INNER_R = 1.5;
MOTOR_MOUNT_COVER_FLANGE_W = 28.0;
MOTOR_MOUNT_COVER_FLANGE_H = 30.0;
MOTOR_MOUNT_COVER_CABLE_SLOT_W = 8.0;
MOTOR_MOUNT_COVER_CABLE_SLOT_H = 4.0;

// 四个角的安装孔/背板 boss；M3 螺钉沿 +Y 从罩体法兰拧入背板嵌件。
MOTOR_MOUNT_BOSS_OFFSET_X = 10.0;
MOTOR_MOUNT_BOSS_OFFSET_Z = 10.5;
MOTOR_MOUNT_BOSS_OD = 8.0;
MOTOR_MOUNT_BOSS_PAD_D = 14.0;
MOTOR_MOUNT_BOSS_PAD_H = 1.6;
MOTOR_MOUNT_BOSS_L =
    MOTOR_MOUNT_PANEL_Y_LOCAL - MOTOR_MOUNT_COVER_FLANGE_REAR_Y_LOCAL;
MOTOR_MOUNT_INSERT_D = 4.6;      // 常见 M3 热熔铜螺母外径包络
MOTOR_MOUNT_INSERT_L = 5.0;
MOTOR_MOUNT_SCREW_CLEAR_D = 3.4;
MOTOR_MOUNT_SCREW_HEAD_D = 6.0;
MOTOR_MOUNT_SCREW_HEAD_H = 1.4;
MOTOR_MOUNT_EPS = 0.05;

MOTOR_MOUNT_BOSS_OFFSETS = [
    [-MOTOR_MOUNT_BOSS_OFFSET_X, -MOTOR_MOUNT_BOSS_OFFSET_Z],
    [-MOTOR_MOUNT_BOSS_OFFSET_X, MOTOR_MOUNT_BOSS_OFFSET_Z],
    [MOTOR_MOUNT_BOSS_OFFSET_X, -MOTOR_MOUNT_BOSS_OFFSET_Z],
    [MOTOR_MOUNT_BOSS_OFFSET_X, MOTOR_MOUNT_BOSS_OFFSET_Z]
];
//#endregion

//#region 模型/类型
// motor_mount_c() 与 cabinet_chain_path.scad 中的 power_c()/entry_c() 同一动力轴中心。
//#endregion

//#region 公开 API
function motor_mount_pitch_r() = sprocket_pitch_r(MOTOR_MOUNT_SPROCKET_TEETH);

function motor_mount_outer_r() =
    motor_mount_pitch_r() + TOOTH_ADDENDUM;

function motor_mount_return_x() =
    WALL + motor_mount_outer_r() + MOTOR_MOUNT_WALL_CLEAR;

function motor_mount_c() = [
    motor_mount_return_x() + motor_mount_pitch_r(),
    row_center_z(N_ROW - 1) - motor_mount_pitch_r(),
    0
];
//#endregion

//#region 业务逻辑
assert(MOTOR_MOUNT_BOSS_L > MOTOR_MOUNT_INSERT_L + 1.0,
    "motor cover boss must leave a solid back wall behind the insert");
assert(MOTOR_MOUNT_COVER_INNER_W > 10.0 && MOTOR_MOUNT_COVER_INNER_H > 12.0,
    "cover cavity must clear the Pololu 10x12 mm gearbox");
//#endregion
