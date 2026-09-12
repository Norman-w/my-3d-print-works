// SmartPartsDrawer 柜体外壳 — 尺寸真值源：本文件
// 单位：毫米。抽屉本体本轮不建模，只留格口和 1 mm 周边间隙。

//#region 导入/依赖
// 无外部库；几何由本文件常数驱动。
//#endregion

//#region 常量/配置
W = 240;
H = 200;
D = 120;
WALL = 3.2;
PARTITION_T = 3.0;
FRONT_NET = 60;
BACK_PANEL_T = 5.0;
GRID_T = 2.4;
N_COL = 5;
N_ROW = 6;
CHAIN_LAYER_CLEAR_OD = 22.0;     // 03C 1x 齿顶圆，层距必须大于此值
DRAWER_CLEAR = 1.0;
DRAWER_FLOOR = 1.6;
RABBET_W = 1.6;
PANEL_FIT = 0.35;
EPS = 0.05;
//#endregion

//#region 模型/类型
INNER_W = W - 2 * WALL;
INNER_H = H - 2 * WALL;
DIV_T = GRID_T;
SHELF_T = GRID_T;
REAR_CAVITY = D - FRONT_NET - PARTITION_T - BACK_PANEL_T;
PARTITION_FRONT_Y = FRONT_NET;
PARTITION_BACK_Y = FRONT_NET + PARTITION_T;
RABBET_DEPTH = BACK_PANEL_T;
PANEL_W = INNER_W + 2 * RABBET_W - 2 * PANEL_FIT;
PANEL_H = INNER_H + 2 * RABBET_W - 2 * PANEL_FIT;
PANEL_X = WALL - RABBET_W + PANEL_FIT;
PANEL_Y = D - BACK_PANEL_T;
PANEL_Z = WALL - RABBET_W + PANEL_FIT;

function bay_w() = (INNER_W - (N_COL - 1) * DIV_T) / N_COL;

function bay_h() = (INNER_H - (N_ROW - 1) * SHELF_T) / N_ROW;

function col_x(i) = WALL + i * (bay_w() + DIV_T);

function row_z(j) = WALL + j * (bay_h() + SHELF_T);

function col_center_x(i) = col_x(i) + bay_w() / 2;

function row_center_z(j) = row_z(j) + bay_h() / 2;

function div_center_x(i) = col_x(i) + bay_w() + DIV_T / 2;

function shelf_center_z(j) = row_z(j) + bay_h() + SHELF_T / 2;

function drawer_outer_w() = bay_w() - 2 * DRAWER_CLEAR;

function drawer_outer_h() = bay_h() - 2 * DRAWER_CLEAR;

function drawer_inner_h() = drawer_outer_h() - DRAWER_FLOOR;
//#endregion

//#region 私有成员
// 几何常数全部公开给根模型 include。
//#endregion

//#region 公开 API
// include 后使用 W / H / D / bay_w / col_center_x / PANEL_*。
//#endregion

//#region 业务逻辑
// 前仓净深 60：抽屉格；3 mm 隔板与外框一体；后仓放链轮/齿轮。
// 5×6 格口约 44.8×30.27，层距约 32.67，大于 03C 1x 链轮齿顶圆 Ø22。
// 预留下一版抽屉外廓约 42.8×28.27，内高约 26.7。
// 背板只坐止口；中部不设 Boss。侧边紧固和内嵌后盖下一轮再做。
//#endregion

//#region 方法/工具
assert(abs(FRONT_NET + PARTITION_T + REAR_CAVITY + BACK_PANEL_T - D) < 0.01);
assert(abs(N_COL * bay_w() + (N_COL - 1) * DIV_T - INNER_W) < 0.01);
assert(abs(N_ROW * bay_h() + (N_ROW - 1) * SHELF_T - INNER_H) < 0.01);
assert(bay_h() + SHELF_T > CHAIN_LAYER_CLEAR_OD, "layer pitch must clear 03C 1x sprocket OD");
//#endregion
