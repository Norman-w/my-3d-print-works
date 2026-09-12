// SmartPartsDrawer 柜体外壳 — 尺寸真值源：本文件
// 单位：毫米。格口冻结为原 5×6 的 44.8×30.27；顶层去掉一格成 5×5，底部仍加两层层距。

//#region 导入/依赖
// 无外部库；几何由本文件常数驱动。
//#endregion

//#region 常量/配置
SERVICE_W = 20.0;                // 左回程走廊；只在后仓空、前脸抽屉区做成实心颊板
SERVICE_LAYERS = 2;
W = 240 + SERVICE_W;
D = 120;
WALL = 3.2;
PARTITION_T = 3.0;
FRONT_NET = 60;
BACK_PANEL_T = 5.0;
GRID_T = 2.4;
N_COL = 5;
N_ROW = 5;
REF_ROWS = 6;                    // 格口高度按原 6 层冻结，不因减层而变高
CHAIN_LAYER_CLEAR_OD = 22.0;
DRAWER_CLEAR = 1.0;
DRAWER_FLOOR = 1.6;
RABBET_W = 1.6;
PANEL_FIT = 0.35;
EPS = 0.05;
GRID_W = 233.6;                  // 冻结：原 240 柜内宽
REF_GRID_H = 193.6;              // 冻结：原 6 层内高，只用来反推 BAY_H
//#endregion

//#region 模型/类型
INNER_W = W - 2 * WALL;
DIV_T = GRID_T;
SHELF_T = GRID_T;
BAY_W = (GRID_W - (N_COL - 1) * DIV_T) / N_COL;
BAY_H = (REF_GRID_H - (REF_ROWS - 1) * SHELF_T) / REF_ROWS;
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
// 格口仍约 44.8×30.27，层距约 32.67。5×5 抽屉；底仓两层层距给电器和张紧。
// 左侧 SERVICE_W 只在前脸抽屉高度做成实心颊板，后仓仍是一个大开间。
// 背板只坐止口；中部不设 Boss。侧边紧固和内嵌后盖下一轮再做。
//#endregion

//#region 方法/工具
assert(abs(FRONT_NET + PARTITION_T + REAR_CAVITY + BACK_PANEL_T - D) < 0.01);
assert(abs(N_COL * BAY_W + (N_COL - 1) * DIV_T - GRID_W) < 0.01);
assert(abs(N_ROW * BAY_H + (N_ROW - 1) * SHELF_T - GRID_H) < 0.01);
assert(abs(GRID_ORIGIN_X + GRID_W - (W - WALL)) < 0.01);
assert(abs(GRID_ORIGIN_Z + GRID_H - (H - WALL)) < 0.01);
assert(ROW_PITCH > CHAIN_LAYER_CLEAR_OD, "layer pitch must clear 03C 1x sprocket OD");
//#endregion
