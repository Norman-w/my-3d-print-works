// 后仓 03C 横走蛇形闭环销轴路径。父文件需已 include cabinet_params 与 ch1_03c_params。

//#region 导入/依赖
include <cabinet_chain_pins.gen.scad>
//#endregion

//#region 常量/配置
SPROCKET_TEETH = 12;
BLUNT_TEETH = 8;                 // 所有绿色导向轮统一使用的最小轮
WALL_CLEAR = 0.40;
DRIVE_RETURN_X_TRIM = -4.00;     // 上方 8T 导向轮向世界 X− 错开
SERVICE_PRESS_RETURN_X_TRIM = 16.00; // 下方 8T 导向轮向世界 X+ 错开
MOTOR_RETURN_X_OFFSET_MM = -2.00; // 下方电机 12T 轮保持箱壁安全轴心
// The generated solver receives this from the center-clutch contract. Keep a
// zero fallback so the path file remains inspectable by itself, but do not
// assign back to the same OpenSCAD variable: self-redefinition would shadow
// the generated -19.50 mm value and silently leave the wheels at old heights.
CHAIN_PATH_VERTICAL_SHIFT = is_undef(SNAKE_CHAIN_VERTICAL_SHIFT)
    ? 0
    : SNAKE_CHAIN_VERTICAL_SHIFT;
//#endregion

//#region 模型/类型
function drive_pitch_r() = P / (2 * sin(180 / SPROCKET_TEETH));

function drive_outer_r() = drive_pitch_r() + 0.38 * P;

function translator_r() = P / (2 * sin(180 / BLUNT_TEETH));

function guide_outer_r() = translator_r() + 0.12 * P;

function wall_inset() = WALL + drive_outer_r() + WALL_CLEAR;

function return_x() = wall_inset();

function blunt_dx() = (W - wall_inset()) - col_center_x(N_COL - 1);

// Keep the old 8T side anchors.  The former 12T/8T pair used this offset to
// make different pitch radii share a vertical tangent; now both wheels on a
// side are 8T, so the offset only preserves the established cabinet envelope.
function guide_anchor_dx() = drive_pitch_r() - translator_r();

function chain_row_center_z(row) = row_center_z(row) + CHAIN_PATH_VERTICAL_SHIFT;

function polar_xy(c, r, a) = [c[0] + r * cos(a), c[1] + r * sin(a), 0];

function external_a(c1, r1, c2, r2) =
    let (
        d = norm(c2 - c1),
        gamma = atan2(c2[1] - c1[1], c2[0] - c1[0]),
        ac = acos((r1 - r2) / d)
    ) gamma + ac;
//#endregion

//#region 私有成员
function right_sprocket_c(z_hi) = [
    W - wall_inset() + guide_anchor_dx(),
    z_hi - translator_r(),
    0
];

function right_blunt_c(z_lo) = [
    W - wall_inset() + guide_anchor_dx(),
    z_lo + translator_r(),
    0
];

function left_sprocket_c(z_hi) = [
    col_center_x(0) - blunt_dx() - guide_anchor_dx(),
    z_hi - translator_r(),
    0
];

function left_blunt_c(z_lo) = [
    col_center_x(0) - blunt_dx() - guide_anchor_dx(),
    z_lo + translator_r(),
    0
];

function right_leave_a() = external_a(
    right_sprocket_c(chain_row_center_z(N_ROW - 1)),
    translator_r(),
    right_blunt_c(chain_row_center_z(N_ROW - 2)),
    translator_r()
);

function s_span_check() = (90 - right_leave_a() + 360) % 360;

// The service run follows the clutch magnet-bottom datum. The independent
// return guide center below keeps its small guide wheel floor-safe.
function service_chain_z() = row_center_z(0) - ROW_PITCH + CHAIN_PATH_VERTICAL_SHIFT;

function return_drive_center_y() = is_undef(SNAKE_CHAIN_RETURN_GUIDE_CENTER_Y)
    ? service_chain_z() - translator_r()
    : SNAKE_CHAIN_RETURN_GUIDE_CENTER_Y;

function drive_c() = [
    return_x() + 2 * drive_pitch_r() + translator_r() + DRIVE_RETURN_X_TRIM,
    return_drive_center_y(),
    0
];

// 上方回程轮正下方的 8T 下压/服务轮。其下切线与离合磁铁触发高度
// 重合，底部链段因此可以水平穿过全部五个离合站。
function service_press_c() = [
    return_x() + 2 * drive_pitch_r() + translator_r()
        + SERVICE_PRESS_RETURN_X_TRIM,
    service_chain_z() + translator_r(),
    0
];

function entry_c() = [
    return_x() + translator_r(),
    chain_row_center_z(N_ROW - 1) - translator_r(),
    0
];

// 后视图中，蛇形链条唯一的动力位放在右下方的回程张紧位；回程顺序
// 为服务水平段→下方绿轮→上方绿轮→蓝色主动轮→左侧回程。两只绿轮
// 不共享 X 坐标，生成脚本用相反侧内切线避免旧的麻花环。
function power_c() = right_sprocket_c(chain_row_center_z(N_ROW - 1));

function right_turn_sprockets_without_power() = [
    for (row = [N_ROW - 3:-2:0])
        right_sprocket_c(chain_row_center_z(row))
];

function ten_path_c() = [
    return_x() + drive_pitch_r() + MOTOR_RETURN_X_OFFSET_MM,
    TEN_Z,
    0
];

// The motorized sprocket is the former lower return/tensioner wheel.  Keep a
// named alias so the motor, cover, D shaft, bearing list, and motion metadata
// cannot silently drift to the old upper guide position.
function snake_drive_c() = ten_path_c();

function right_turn_sprockets() = [
    for (row = [N_ROW - 1:-2:0])
        right_sprocket_c(chain_row_center_z(row))
];

function left_turn_sprockets() = [
    for (row = [N_ROW - 2:-2:1])
        left_sprocket_c(chain_row_center_z(row))
];

function blunt_centers() = [
    for (k = [0:N_ROW - 2])
        (k % 2 == 0
            ? right_blunt_c(chain_row_center_z(N_ROW - 2 - k))
            : left_blunt_c(chain_row_center_z(N_ROW - 2 - k))),
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
// 所有固定绿色导向位统一采用 8T 钝齿节圆，侧边同半径后直接形成四分之一圆弧；
// 新增的下压/服务轮与上方回程轮组成竖直折返；两轮按同一减角方向挂链，
// 上方回程轮再通过外切线接入向 X− 偏移的 12T 电机轮，只有底部主动轮保留 12T。
// 抽屉层数保持奇数，底仓横穿后进入这组回程导向，再进张紧 U。
// 后视左 = 柜体 +X；power_c() 是旧高 X 上方普通导向轮，entry_c() 是低 X
// 的普通导向轮，snake_drive_c() 是右下方带电机的回程张紧轮位。
//#endregion

//#region 方法/工具
assert(N_COL == 5 && N_ROW == 3, "snake layout is for the 5x3 drawer layout");
assert(len(snake_pins()) % 2 == 0, "snake pin count must be even");
assert(len(snake_pins()) == SNAKE_PIN_N, "generated pin count must match");
assert(TEN_Z >= WALL + drive_outer_r() - 0.01, "tensioner teeth must stay above the inner floor");
assert(BLUNT_TEETH >= 8, "03C guide wheel must be at least 8T");
assert(translator_r() > P / 2, "8T guide wheel must accept one-pitch pin chord");
assert(guide_outer_r() < drive_outer_r(), "small guide envelope should stay below the 12T drive envelope");
assert(abs(s_span_check() - 90) < 1, "8T guide wrap should be a quarter turn onto the vertical chain");
assert(service_press_c()[1] + guide_outer_r() < drive_c()[1] - guide_outer_r(),
    "lower service press guide must stay separated from the upper return guide");
assert(abs(service_press_c()[0] - drive_c()[0]) > 0.1,
    "upper and lower return guides must not share an X coordinate");
assert(norm(snake_drive_c() - service_press_c()) > drive_outer_r() + guide_outer_r() + 0.40,
    "lower service press guide must clear the 12T motor drive envelope");
assert(abs(snake_drive_c()[0]
        - (return_x() + drive_pitch_r() + MOTOR_RETURN_X_OFFSET_MM)) < 0.01,
    "motor return X offset must stay in the generated chain path");
assert(norm(snake_drive_c() - motor_mount_c()) < 0.01,
    "snake drive and motor cover/floor fixing-seat center must stay aligned");
//#endregion
