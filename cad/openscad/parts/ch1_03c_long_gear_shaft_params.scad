// CH1 03C 长齿轮轴 — 参数真值源
// 单位：毫米。坐标约定：轴线沿世界 Y；齿轮截面位于 XZ 平面。

//#region 导入/依赖
// 无外部依赖；数值与现有 cabinet_clutch.scad 的 3 mm 节距齿轮保持一致。
//#endregion

//#region 常量/配置
LONG_GEAR_MODEL = is_undef(LONG_GEAR_MODEL) ? "solid" : LONG_GEAR_MODEL;
// x1c_fine = 0.4 mm 喷嘴下的细杆主方案；standard = 原 12T/3 mm 兼容回退。
LONG_GEAR_PRESET = is_undef(LONG_GEAR_PRESET) ? "x1c_fine" : LONG_GEAR_PRESET;

LONG_GEAR_TEETH = is_undef(LONG_GEAR_TEETH)
    ? (LONG_GEAR_PRESET == "x1c_fine" ? 10 : 12)
    : LONG_GEAR_TEETH;
LONG_GEAR_PITCH_MM = is_undef(LONG_GEAR_PITCH_MM)
    ? (LONG_GEAR_PRESET == "x1c_fine" ? 2.4 : 3.0)
    : LONG_GEAR_PITCH_MM;
LONG_GEAR_TOOTH_DEPTH = is_undef(LONG_GEAR_TOOTH_DEPTH)
    ? (LONG_GEAR_PRESET == "x1c_fine" ? 0.60 : 0.82)
    : LONG_GEAR_TOOTH_DEPTH;

// 细版略放宽齿根槽，使 0.4 mm 喷嘴仍有可辨识的开口；standard 保持
// 原仓库 0.20→0.80 的齿顶/齿根分配。
LONG_GEAR_TIP_START = is_undef(LONG_GEAR_TIP_START)
    ? (LONG_GEAR_PRESET == "x1c_fine" ? 0.18 : 0.20)
    : LONG_GEAR_TIP_START;
LONG_GEAR_TIP_END = is_undef(LONG_GEAR_TIP_END)
    ? 0.50
    : LONG_GEAR_TIP_END;
LONG_GEAR_ROOT_END = is_undef(LONG_GEAR_ROOT_END)
    ? (LONG_GEAR_PRESET == "x1c_fine" ? 0.75 : 0.80)
    : LONG_GEAR_ROOT_END;

// 当前 cabinet_clutch 的上下同步轮中心间距约 158.93 mm；取 159 mm，
// 让齿段覆盖几乎整个动力杆，同时保留两端装同步轮的 D 轴伸出段。
LONG_GEAR_LENGTH = is_undef(LONG_GEAR_LENGTH) ? 159.0 : LONG_GEAR_LENGTH;
LONG_GEAR_END_STUB_LENGTH = is_undef(LONG_GEAR_END_STUB_LENGTH)
    ? 6.0
    : LONG_GEAR_END_STUB_LENGTH;       // 齿段两端各外露 6 mm
LONG_GEAR_STUB_OVERLAP = is_undef(LONG_GEAR_STUB_OVERLAP)
    ? 0.20
    : LONG_GEAR_STUB_OVERLAP;           // 实心版端轴向齿段内搭接

LONG_GEAR_END_D = 3.0;                // 两端同步轮安装轴：名义 Ø3 mm
LONG_GEAR_END_FLAT_DEPTH = 0.50;      // D 平面从圆周切入 0.50 mm

// sleeve 版套在现有金属 Ø3 mm D 轴上；按仓库现有打印配合写法给径向余量。
LONG_GEAR_BORE_RADIAL_CLEARANCE = 0.12;
LONG_GEAR_BORE_FLAT_CLEARANCE = 0.12;

LONG_GEAR_EPS = 0.05;
//#endregion

//#region 模型/类型
// solid  = 实心齿轮轴 + 两端整体 D 轴；
// sleeve = 长齿轮本体带 D 孔，套在外部金属 D 轴上。
//#endregion

//#region 私有成员：齿形函数
function long_gear_pitch_r() =
    LONG_GEAR_TEETH * LONG_GEAR_PITCH_MM / (2 * PI);

function long_gear_root_r() =
    long_gear_pitch_r() - LONG_GEAR_TOOTH_DEPTH;

function long_gear_tip_r() =
    long_gear_pitch_r() + LONG_GEAR_TOOTH_DEPTH;

function long_gear_outer_d() =
    2 * long_gear_tip_r();

function long_gear_tip_land_mm() =
    (LONG_GEAR_TIP_END - LONG_GEAR_TIP_START)
        * LONG_GEAR_PITCH_MM
        * long_gear_tip_r() / long_gear_pitch_r();

function long_gear_root_gap_mm() =
    (1.0 - LONG_GEAR_ROOT_END)
        * LONG_GEAR_PITCH_MM
        * long_gear_root_r() / long_gear_pitch_r();

function long_gear_polar(r, a) = [r * cos(a), r * sin(a)];

// 每个齿沿 Y 方向是连续直齿；XZ 截面采用参数化的齿顶平台轮廓。
// standard 复用旧的 0.20→0.80 分配，x1c_fine 则把齿顶起点前移、齿根槽放宽。
function long_gear_points() = [
    for (i = [0:LONG_GEAR_TEETH - 1])
        for (p = [
            [0.00, long_gear_root_r()],
            [LONG_GEAR_TIP_START, long_gear_tip_r()],
            [LONG_GEAR_TIP_END, long_gear_tip_r()],
            [LONG_GEAR_ROOT_END, long_gear_root_r()]
        ])
            let (a = (i + p[0]) * 360 / LONG_GEAR_TEETH)
                long_gear_polar(p[1], a)
];
//#endregion

//#region 公开 API
// 根入口由 ch1_03c_long_gear_shaft.scad 消费；参数文件本身不输出几何。
//#endregion

//#region 业务逻辑
// 该组件的默认工作方向是：Y 轴为长度方向，XZ 平面为齿轮截面。
//#endregion

//#region 方法/工具
assert(LONG_GEAR_PRESET == "x1c_fine" || LONG_GEAR_PRESET == "standard",
    "unknown long gear preset");
assert(LONG_GEAR_TEETH >= 6, "long gear needs at least 6 teeth");
assert(LONG_GEAR_PITCH_MM > 0, "gear pitch must be positive");
assert(long_gear_root_r() > 0, "gear root radius must be positive");
assert(
    0 < LONG_GEAR_TIP_START
    && LONG_GEAR_TIP_START < LONG_GEAR_TIP_END
    && LONG_GEAR_TIP_END < LONG_GEAR_ROOT_END
    && LONG_GEAR_ROOT_END < 1,
    "invalid tooth profile fractions"
);
assert(LONG_GEAR_LENGTH > 0, "gear length must be positive");
assert(LONG_GEAR_END_STUB_LENGTH >= 0, "end stub length cannot be negative");
assert(LONG_GEAR_END_D > 0, "end shaft diameter must be positive");
//#endregion
