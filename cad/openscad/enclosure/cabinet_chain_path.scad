// 后仓 03C 横走蛇形闭环销轴路径。父文件需已 include cabinet_params 与 ch1_03c_params。

//#region 导入/依赖
include <cabinet_chain_pins.gen.scad>
//#endregion

//#region 常量/配置
SPROCKET_TEETH = 12;
BLUNT_TEETH = 8;
WALL_CLEAR = 0.40;
//#endregion

//#region 模型/类型
function drive_pitch_r() = P / (2 * sin(180 / SPROCKET_TEETH));

function drive_outer_r() = drive_pitch_r() + 0.38 * P;

function translator_r() = P / (2 * sin(180 / BLUNT_TEETH));

function wall_inset() = WALL + drive_outer_r() + WALL_CLEAR;

function return_x() = wall_inset();

function blunt_dx() = (W - wall_inset()) - col_center_x(N_COL - 1);

function pair_align_dx() = drive_pitch_r() - translator_r();

function polar_xy(c, r, a) = [c[0] + r * cos(a), c[1] + r * sin(a), 0];

function external_a(c1, r1, c2, r2) =
    let (
        d = norm(c2 - c1),
        gamma = atan2(c2[1] - c1[1], c2[0] - c1[0]),
        ac = acos((r1 - r2) / d)
    ) gamma + ac;
//#endregion

//#region 私有成员
function right_sprocket_c(z_hi) = [W - wall_inset(), z_hi - drive_pitch_r(), 0];

function right_blunt_c(z_lo) = [
    W - wall_inset() + pair_align_dx(),
    z_lo + translator_r(),
    0
];

function left_sprocket_c(z_hi) = [
    col_center_x(0) - blunt_dx(),
    z_hi - drive_pitch_r(),
    0
];

function left_blunt_c(z_lo) = [
    col_center_x(0) - blunt_dx() - pair_align_dx(),
    z_lo + translator_r(),
    0
];

function right_leave_a() = external_a(
    right_sprocket_c(row_center_z(N_ROW - 1)),
    drive_pitch_r(),
    right_blunt_c(row_center_z(N_ROW - 2)),
    translator_r()
);

function s_span_check() = (90 - right_leave_a() + 360) % 360;

function service_chain_z() = row_center_z(0) - ROW_PITCH;

function drive_c() = [
    return_x() + 3 * drive_pitch_r(),
    service_chain_z() - drive_pitch_r(),
    0
];

function entry_c() = [
    return_x() + drive_pitch_r(),
    row_center_z(N_ROW - 1) - drive_pitch_r(),
    0
];

// 后视图中，蛇形链条唯一的动力位放在右下方的回程张紧位；旧的高-X
// 上方转向位仍保留，但现在只承担普通导向，不再连接电机。
function power_c() = right_sprocket_c(row_center_z(N_ROW - 1));

function right_turn_sprockets_without_power() = [
    right_sprocket_c(row_center_z(2)),
    right_sprocket_c(row_center_z(0))
];

function ten_path_c() = [
    return_x() + drive_pitch_r(),
    TEN_Z,
    0
];

// The motorized sprocket is the former lower return/tensioner wheel.  Keep a
// named alias so the motor, cover, D shaft, bearing list, and motion metadata
// cannot silently drift to the old upper guide position.
function snake_drive_c() = ten_path_c();

function right_turn_sprockets() = [
    right_sprocket_c(row_center_z(4)),
    right_sprocket_c(row_center_z(2)),
    right_sprocket_c(row_center_z(0))
];

function left_turn_sprockets() = [
    left_sprocket_c(row_center_z(3)),
    left_sprocket_c(row_center_z(1))
];

function blunt_centers() = [
    right_blunt_c(row_center_z(3)),
    left_blunt_c(row_center_z(2)),
    right_blunt_c(row_center_z(1)),
    left_blunt_c(row_center_z(0)),
    right_blunt_c(service_chain_z())
];
//#endregion

//#region 公开 API
function snake_pins() = SNAKE_PINS;

function wheel_pose_rot(x, z) =
    let (hits = [for (w = WHEEL_POSES) if (norm([w[0] - x, w[1] - z]) < 0.2) w[2]])
        len(hits) == 0 ? 0 : hits[0];
//#endregion

//#region 视图层
// 路径在柜体 XZ：x=宽，y=高。装配时绕 X 转 90° 落到后仓，不再镜像。
//#endregion

//#region 业务逻辑
// 销轴由 solve_cabinet_chain.py 按弦长 P 走出；只动底端张紧轮 Z 闭合闭环。
// 每对 12T+钝齿节圆外切，外侧链条竖齐。5 层奇数，底仓横穿后进张紧 U。
// 后视左 = 柜体 +X；power_c() 是旧高 X 上方普通导向轮，entry_c() 是低 X
// 的普通导向轮，snake_drive_c() 是右下方带电机的回程张紧轮位。
//#endregion

//#region 方法/工具
assert(N_COL == 5 && N_ROW == 5, "snake layout is for 5x5");
assert(len(snake_pins()) % 2 == 0, "snake pin count must be even");
assert(len(snake_pins()) == SNAKE_PIN_N, "generated pin count must match");
assert(TEN_Z >= WALL + drive_outer_r() - 0.01, "tensioner teeth must stay above the inner floor");
assert(abs(s_span_check() - 90) < 1, "12T wrap should be a quarter turn onto the vertical chain");
assert(norm(snake_drive_c() - motor_mount_c()) < 0.01,
    "snake drive and motor cover/floor fixing-seat center must stay aligned");
//#endregion
