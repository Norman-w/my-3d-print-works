// SmartPartsDrawer 柜体外壳 — 尺寸真值源：本文件
// 单位：毫米。中心首件冻结为 5 列 × 3 层抽屉，底部保留 1 层服务空间。
// 这版把 X- 侧服务区单独让给电机、回程蛇链和安装/紧固包络；抽屉格
// 宽度必须由剩余净宽推导，不能再沿用旧的 240 mm 抽屉区常数。

//#region 导入/依赖
// 无外部库；几何由本文件常数驱动。
//#endregion

//#region 常量/配置
SERVICE_W = 44.0;                // X- 服务区：电机、回程链和安装件的保留包络
SERVICE_LAYERS = 1;
W = 250.0;                       // X1C 256 mm 名义宽度内，左右各留 3 mm
D = 120;
WALL = 3.2;
PARTITION_T = 3.0;
FRONT_NET = 60;
BACK_PANEL_T = 5.0;
GRID_T = 2.4;
N_COL = 5;
N_ROW = 3;
DESIGN_BAY_H = 55.30;             // 三层方案的真实抽屉净高；不再沿用旧 6 层反推值
REF_ROWS = N_ROW;
CHAIN_LAYER_CLEAR_OD = 22.0;
DRAWER_CLEAR = 1.0;
DRAWER_FLOOR = 1.6;
RABBET_W = 1.6;
PANEL_FIT = 0.35;
EPS = 0.05;
X1C_BUILD_X = 256.0;
X1C_BUILD_Y = 256.0;
X1C_BUILD_Z = 256.0;
X1C_FRAME_EDGE_MARGIN = 3.0;
GRID_W = W - 2 * WALL - SERVICE_W;
REF_GRID_H = REF_ROWS * DESIGN_BAY_H + (REF_ROWS - 1) * GRID_T;
//#endregion

//#region 模型/类型
INNER_W = W - 2 * WALL;
DIV_T = GRID_T;
SHELF_T = GRID_T;
BAY_W = (GRID_W - (N_COL - 1) * DIV_T) / N_COL;
BAY_H = DESIGN_BAY_H;
ROW_PITCH = BAY_H + SHELF_T;
COL_PITCH = BAY_W + DIV_T;
GRID_H = N_ROW * BAY_H + (N_ROW - 1) * SHELF_T;
SERVICE_H = SERVICE_LAYERS * ROW_PITCH;
H = 2 * WALL + SERVICE_H + GRID_H;
INNER_H = H - 2 * WALL;
GRID_ORIGIN_X = WALL + SERVICE_W;
GRID_ORIGIN_Z = WALL + SERVICE_H;
REAR_CAVITY = D - FRONT_NET - PARTITION_T - BACK_PANEL_T;
PARTITION_FRONT_Y = FRONT_NET;
PARTITION_BACK_Y = FRONT_NET + PARTITION_T;
RABBET_DEPTH = BACK_PANEL_T;
PANEL_W = INNER_W + 2 * RABBET_W - 2 * PANEL_FIT;
PANEL_H = INNER_H + 2 * RABBET_W - 2 * PANEL_FIT;
PANEL_X = WALL - RABBET_W + PANEL_FIT;
PANEL_Y = D - BACK_PANEL_T;
PANEL_Z = WALL - RABBET_W + PANEL_FIT;

// 中心格前端主动轮的共享安装真值。世界坐标的 +Y 高度映射到柜体原生
// +Z，高度之外的世界 -Z 深度映射到柜体原生 +Y。轴线深度必须同时被
// cabinet.scad 的实体层板和 cabinet_clutch.scad 的后仓总装消费，避免
// 预览里的轴承孔与真正的柜体层板错位。
CENTER_FRONT_DRIVE_AXIS_NATIVE_Y = is_undef(
    CENTER_FRONT_DRIVE_AXIS_NATIVE_Y
)
    ? 14.2208
    : CENTER_FRONT_DRIVE_AXIS_NATIVE_Y;
CENTER_FRONT_RACK_GEAR_TEETH = 16;
CENTER_FRONT_RACK_GEAR_PITCH_MM = 3.0;
CENTER_FRONT_RACK_GEAR_TOOTH_DEPTH = 1.0;
CENTER_FRONT_RACK_GEAR_THICKNESS = 3.2;
CENTER_FRONT_RACK_BODY_HEIGHT = 3.8;
// The rack is a moving drawer-bottom drive part. Keep its complete X/Y envelope
// in the shared parameter source so the world preview and printable cabinet
// use the same above-shelf datum; the shelf remains intact below it.
CENTER_FRONT_RACK_BODY_X = CENTER_FRONT_RACK_GEAR_THICKNESS;
CENTER_FRONT_RACK_TOOTH_HEIGHT_X = 1.25;
CENTER_FRONT_RACK_TOOTH_OVERHANG_X = 0.20;
CENTER_FRONT_RACK_TOOTH_Y_MARGIN = 0.25;
CENTER_FRONT_RACK_FACE_OFFSET_X = 0.15;
CENTER_FRONT_RACK_ABOVE_SHELF_GAP = 0.05;
CENTER_FRONT_DRIVE_BEARING_GEAR_GAP = 0.35;
CENTER_FRONT_DRIVE_LIFT_MM = CENTER_FRONT_RACK_BODY_HEIGHT
    - DRAWER_CLEAR
    + CENTER_FRONT_RACK_ABOVE_SHELF_GAP;
CENTER_FRONT_BEARING_GEAR_CLEARANCE = 0.35;
CENTER_FRONT_BEARING_ID = 3.0;
CENTER_FRONT_BEARING_OD = 6.0;
CENTER_FRONT_BEARING_WIDTH = 2.0;
CENTER_FRONT_BEARING_REINFORCEMENT_DISC_DIAMETER =
    CENTER_FRONT_BEARING_OD + 2.0;
CENTER_FRONT_BEARING_REINFORCEMENT_DISC_THICKNESS = 1.0;
CENTER_FRONT_BEARING_SEAT_DIAMETER = 6.10;
CENTER_FRONT_BEARING_RETAINER_THICKNESS =
    SHELF_T - CENTER_FRONT_BEARING_WIDTH;
CENTER_FRONT_BEARING_RETAINER_BORE_DIAMETER = 3.40;
CENTER_FRONT_RACK_GEAR_OUTER_RADIUS =
    CENTER_FRONT_RACK_GEAR_TEETH * CENTER_FRONT_RACK_GEAR_PITCH_MM
        / (2 * PI)
    + CENTER_FRONT_RACK_GEAR_TOOTH_DEPTH;
CENTER_FRONT_RACK_GEAR_PITCH_RADIUS =
    CENTER_FRONT_RACK_GEAR_TEETH * CENTER_FRONT_RACK_GEAR_PITCH_MM
        / (2 * PI);
CENTER_FRONT_SHELF_GEAR_CLEARANCE_RADIUS =
    CENTER_FRONT_RACK_GEAR_OUTER_RADIUS + 0.45;
CENTER_FRONT_BEARING_BOSS_XZ =
    2 * CENTER_FRONT_SHELF_GEAR_CLEARANCE_RADIUS + 0.40;

function center_front_rack_face_x(axis_x) =
    axis_x + CENTER_FRONT_RACK_GEAR_PITCH_RADIUS
        + CENTER_FRONT_RACK_FACE_OFFSET_X;

function bay_w() = BAY_W;

function bay_h() = BAY_H;

function col_x(i) = GRID_ORIGIN_X + i * COL_PITCH;

function row_z(j) = GRID_ORIGIN_Z + j * ROW_PITCH;

function col_center_x(i) = col_x(i) + BAY_W / 2;

function row_center_z(j) = row_z(j) + BAY_H / 2;

function div_center_x(i) = col_x(i) + BAY_W + DIV_T / 2;

function shelf_center_z(j) = row_z(j) + BAY_H + SHELF_T / 2;

function drawer_outer_w() = BAY_W - 2 * DRAWER_CLEAR;

function drawer_outer_h() = BAY_H - 2 * DRAWER_CLEAR;

function drawer_inner_h() = drawer_outer_h() - DRAWER_FLOOR;
//#endregion

//#region 私有成员
// 几何常数全部公开给根模型 include。
//#endregion

//#region 公开 API
// include 后使用 W / H / D / GRID_ORIGIN_* / bay_w / col_center_x / PANEL_*。
//#endregion

//#region 业务逻辑
// 当前目标格口约 38.0×55.3，层距约 57.7。5×3 抽屉；底部一层层距给
// 电器和张紧。X- SERVICE_W 只在前脸抽屉高度做成实心颊板，后仓仍是
// 一个大开间；后仓离合板允许跨越多个抽屉格，由连续行承载板承载。
// 前后仓隔板是独立件：箱体 x+、x-、y+、y- 四面各设置两套向内的加长 D 门接收件，
// 隔板对应位置带开放 D/U 入口和完整外 D 承压螺丝面的外套，从箱体内腔沿
// -X/+X/+Y/-Y 打 M3 自攻螺丝；x- 整列与 y- 整层的服务口在挂接墩处保留承力桥。
// 增加沿 Z 伸出的定位柱，避免侵入离合、链条和抽屉包络。
//#endregion

//#region 方法/工具
assert(abs(FRONT_NET + PARTITION_T + REAR_CAVITY + BACK_PANEL_T - D) < 0.01);
assert(abs(N_COL * BAY_W + (N_COL - 1) * DIV_T - GRID_W) < 0.01);
assert(abs(N_ROW * BAY_H + (N_ROW - 1) * SHELF_T - GRID_H) < 0.01);
assert(abs(GRID_ORIGIN_X + GRID_W - (W - WALL)) < 0.01);
assert(abs(GRID_ORIGIN_Z + GRID_H - (H - WALL)) < 0.01);
assert(W <= X1C_BUILD_X - 2 * X1C_FRAME_EDGE_MARGIN + EPS,
    "cabinet width must fit the X1C nominal bed with the reserved edge margin");
assert(H <= X1C_BUILD_Y + EPS && D <= X1C_BUILD_Z + EPS,
    "cabinet envelope must fit the X1C nominal build volume in the authored orientation");
assert(SERVICE_W >= 44.0 - EPS,
    "X- service zone must leave the motor and snake return clearance target");
assert(BAY_W > CENTER_FRONT_BEARING_BOSS_XZ / 2 + 8.0,
    "five drawer bays must retain side clearance around the front drive bearing seat");
assert(ROW_PITCH > CHAIN_LAYER_CLEAR_OD, "layer pitch must clear 03C 1x sprocket OD");
assert(abs(BAY_H - DESIGN_BAY_H) < 0.001, "drawer bay height must use the three-layer design value");
//#endregion
