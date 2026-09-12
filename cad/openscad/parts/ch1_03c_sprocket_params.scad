// CH1 03C 单排滚子链轮 — 尺寸真值源：docs/parts/CH1-03C-roller-chain.md
// 单位：毫米。1x = 能平稳啮合的最小节圆半径（12 齿），其余按节圆半径倍率取整齿数。

//#region 导入/依赖
include <../ch1_03c_params.scad>
//#endregion

//#region 常量/配置
BASE_TEETH = 12;                 // 1x：ISO 常用下限 9T，12T 弦运动 ≤3.5% 且 120° 包角约 4 齿
SCALE_NAMES = ["1x", "1.5x", "2x", "3x", "4x"];
SCALE_TEETH = [12, 18, 24, 36, 48];

TOOTH_WIDTH_RATIO = 0.90;        // 齿宽 / b1；小于 1 才能进入内节
SEAT_CLEARANCE = 0.12;           // 滚子座径向间隙（树脂默认；FDM 可加到 0.20）
TOOTH_ADDENDUM = 0.38 * P;       // 尖齿齿顶高；ISO da_max 太钝，这里用直线齿侧汇成尖点
GULLET_INSET = 0.05;             // 星形谷底略缩进滚子座，避免共面布尔残片
HUB_OD = 12.0;                   // 轮毂外径；1x 仍小于链板内包络
HUB_H = 6.0;                     // 轮毂轴向厚，轴心竖直打印时作底面
BORE_NOMINAL = 3.0;              // 默认 3 mm D 轴
BORE_CLEARANCE = 0.25;           // 圆孔打印间隙
D_FLAT_DEPTH = 0.50;             // 轴上切平深度（常见 3 mm D 轴 Ø3 → 对边 2.5）
D_FLAT_CLEARANCE = 0.12;         // 平面侧间隙，保证能推进
SET_SCREW_D = 1.6;               // M2 底孔，对准 D 平面
INDICATOR_H = 1.0;               // 轮毂圆面凸起，转动时看出是否在转
INDICATOR_D = 2.0;               // 指示凸点直径
INDICATOR_EDGE = 0.35;           // 凸点外沿到轮毂外圆的边距
PLATE_CLEAR = 0.40;              // 轮毂相对内链板径向让位
LIGHTEN_MIN_RING = 8.0;          // 齿根圆到轮毂的环宽大于此值才开减重孔
FAMILY_GAP = 6.0;

bore_d = BORE_NOMINAL + BORE_CLEARANCE;
d_flat_x = BORE_NOMINAL / 2 - D_FLAT_DEPTH + D_FLAT_CLEARANCE;
tooth_w = TOOTH_WIDTH_RATIO * b1;
seat_r = 0.505 * d1 + SEAT_CLEARANCE;
//#endregion

//#region 模型/类型
function teeth_of(size) =
    size == "1x" ? 12 :
    size == "1.5x" ? 18 :
    size == "2x" ? 24 :
    size == "3x" ? 36 :
    size == "4x" ? 48 :
    undef;

function is_known_size(size) = teeth_of(size) != undef;

function sprocket_pitch_r(n) = P / (2 * sin(180 / n));

function sprocket_pitch_d(n) = 2 * sprocket_pitch_r(n);

function sprocket_root_r(n) = sprocket_pitch_r(n) - seat_r;

function sprocket_valley_r(n) = sprocket_root_r(n) - GULLET_INSET;

function sprocket_outer_r(n) = sprocket_pitch_r(n) + TOOTH_ADDENDUM;

function sprocket_outer_d(n) = 2 * sprocket_outer_r(n);

function polar(r, a) = [r * cos(a), r * sin(a)];

// 2N 边：滚子角为谷底，中间为尖齿顶。
function sharp_sprocket_points(n) = [
    for (i = [0:2 * n - 1])
        polar(
            i % 2 == 0 ? sprocket_valley_r(n) : sprocket_outer_r(n),
            i * 180 / n
        )
];

function hub_od_of(n) =
    min(HUB_OD, 2 * (sprocket_pitch_r(n) - h2 / 2 - PLATE_CLEAR));

function family_x(i) =
    i <= 0
        ? sprocket_outer_r(SCALE_TEETH[0])
        : family_x(i - 1)
            + sprocket_outer_r(SCALE_TEETH[i - 1])
            + FAMILY_GAP
            + sprocket_outer_r(SCALE_TEETH[i]);
//#endregion

//#region 私有成员
// 几何常数全部公开给根模型 include。
//#endregion

//#region 公开 API
// include 后使用 teeth_of / sprocket_pitch_r / sprocket_outer_r / tooth_w / bore_d。
//#endregion

//#region 业务逻辑
// 节圆半径 R = P / (2 sin(180/N))。12/18/24/36/48 齿相对 12 齿的半径比约为 1.00 / 1.49 / 1.98 / 2.97 / 3.96。
// 齿形是尖齿星形 + 节圆滚子座，不是 ISO da_max 截顶。轮毂必须缩进链板内包络。
// D 孔平面在 +X，顶丝压平面；运转指示凸点在 +Y 的 +Z 轮毂面上。
//#endregion

//#region 方法/工具
// 无。
//#endregion
