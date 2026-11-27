// CH1 03C 花键轴 Z+ 侧小齿轮 + Y− 侧狗牙 — 参数真值源
// 单位：毫米；花键轴和小齿轮都沿世界 Y，齿轮截面在 XZ 平面。

//#region 导入/依赖
// 无外部依赖。轮廓采用本项目长花键轴的简化直齿原型。
//#endregion

//#region 常量/配置
SPLINE_GEAR_DOG_MODEL = is_undef(SPLINE_GEAR_DOG_MODEL)
    ? "solid"
    : SPLINE_GEAR_DOG_MODEL;

// 被啮合的长花键轴：仅用于计算 Z+ 侧小齿轮的中心距和缩略图背景。
SPLINE_TEETH = 10;
SPLINE_PITCH_MM = 2.4;
SPLINE_TOOTH_DEPTH = 0.60;

// 目标齿轮约 Ø10 mm。12T 在 2.4 mm 节距下的名义齿顶直径约 10.37 mm。
SPLINE_GEAR_TEETH = is_undef(SPLINE_GEAR_TEETH)
    ? 12
    : SPLINE_GEAR_TEETH;
SPLINE_GEAR_PITCH_MM = is_undef(SPLINE_GEAR_PITCH_MM)
    ? SPLINE_PITCH_MM
    : SPLINE_GEAR_PITCH_MM;
SPLINE_GEAR_TOOTH_DEPTH = is_undef(SPLINE_GEAR_TOOTH_DEPTH)
    ? 0.60
    : SPLINE_GEAR_TOOTH_DEPTH;
SPLINE_GEAR_T = is_undef(SPLINE_GEAR_T) ? 2.40 : SPLINE_GEAR_T;
SPLINE_GEAR_BORE_D = is_undef(SPLINE_GEAR_BORE_D)
    ? 3.24
    : SPLINE_GEAR_BORE_D; // Ø3 mm 圆轴的打印间隙孔

// 两个平行 Y 轴齿轮的中心距 = 两个节圆半径之和 + FDM 啮合余量；
// 小齿轮落在花键轴 Z+ 侧。
SPLINE_GEAR_MESH_CLEARANCE = is_undef(SPLINE_GEAR_MESH_CLEARANCE)
    ? 0.12
    : SPLINE_GEAR_MESH_CLEARANCE;
SPLINE_GEAR_CENTER_X = is_undef(SPLINE_GEAR_CENTER_X)
    ? 0
    : SPLINE_GEAR_CENTER_X;
SPLINE_GEAR_CENTER_Y = is_undef(SPLINE_GEAR_CENTER_Y)
    ? 0
    : SPLINE_GEAR_CENTER_Y;
SPLINE_GEAR_CENTER_Z = is_undef(SPLINE_GEAR_CENTER_Z)
    ? SPLINE_TEETH * SPLINE_PITCH_MM / (2 * PI)
        + SPLINE_GEAR_TEETH * SPLINE_GEAR_PITCH_MM / (2 * PI)
        + SPLINE_GEAR_MESH_CLEARANCE
    : SPLINE_GEAR_CENTER_Z;

SPLINE_GEAR_TIP_START = is_undef(SPLINE_GEAR_TIP_START)
    ? 0.18
    : SPLINE_GEAR_TIP_START;
SPLINE_GEAR_TIP_END = is_undef(SPLINE_GEAR_TIP_END)
    ? 0.50
    : SPLINE_GEAR_TIP_END;
SPLINE_GEAR_ROOT_END = is_undef(SPLINE_GEAR_ROOT_END)
    ? 0.75
    : SPLINE_GEAR_ROOT_END;

// 狗牙与齿轮共用 Y 轴，狗牙基体叠在齿轮本体的 Y− 侧；
// 主方案是一个沿 Y− 伸出的圆角三角凸台，母件用放大间隙的圆角三角槽接收。
// 三爪参数仍保留作轻载备用方案，但默认接口切换到更容易盲插的圆角三角。
SPLINE_DOG_INTERFACE = is_undef(SPLINE_DOG_INTERFACE)
    ? "rounded_triangle"
    : SPLINE_DOG_INTERFACE;
SPLINE_DOG_CLAW_COUNT = is_undef(SPLINE_DOG_CLAW_COUNT)
    ? 3
    : SPLINE_DOG_CLAW_COUNT;
SPLINE_DOG_BASE_R = is_undef(SPLINE_DOG_BASE_R)
    ? 2.95
    : SPLINE_DOG_BASE_R;
// 三角凸台是三个圆柱圆头的凸包，外接圆直径 = 2 * (2.95 + 0.30) = Ø6.50。
SPLINE_DOG_TRI_VERTEX_R = is_undef(SPLINE_DOG_TRI_VERTEX_R)
    ? 2.95
    : SPLINE_DOG_TRI_VERTEX_R;
SPLINE_DOG_TRI_HEAD_R = is_undef(SPLINE_DOG_TRI_HEAD_R)
    ? 0.30
    : SPLINE_DOG_TRI_HEAD_R;
SPLINE_DOG_TRI_H_Y = is_undef(SPLINE_DOG_TRI_H_Y)
    ? 0.75
    : SPLINE_DOG_TRI_H_Y;
SPLINE_DOG_TRI_ROTATION_DEG = is_undef(SPLINE_DOG_TRI_ROTATION_DEG)
    ? 30
    : SPLINE_DOG_TRI_ROTATION_DEG;
// 三角凸台与基体沿 Y 方向重叠一点，避免 STL 只在共面处接触。
SPLINE_DOG_INTERFACE_OVERLAP_Y = is_undef(SPLINE_DOG_INTERFACE_OVERLAP_Y)
    ? 0.10
    : SPLINE_DOG_INTERFACE_OVERLAP_Y;

// 三爪备用几何：同样是圆头胶囊，但不作为默认打印接口。
SPLINE_DOG_CLAW_ROOT_CENTER_R = is_undef(
    SPLINE_DOG_CLAW_ROOT_CENTER_R
)
    ? 2.70
    : SPLINE_DOG_CLAW_ROOT_CENTER_R;
SPLINE_DOG_CLAW_TIP_CENTER_R = is_undef(
    SPLINE_DOG_CLAW_TIP_CENTER_R
)
    ? 3.40
    : SPLINE_DOG_CLAW_TIP_CENTER_R;
SPLINE_DOG_CLAW_HEAD_R = is_undef(SPLINE_DOG_CLAW_HEAD_R)
    ? 0.35
    : SPLINE_DOG_CLAW_HEAD_R;
SPLINE_DOG_BASE_T = is_undef(SPLINE_DOG_BASE_T)
    ? 1.00
    : SPLINE_DOG_BASE_T;
SPLINE_DOG_INTERFACE_H_Y = is_undef(SPLINE_DOG_INTERFACE_H_Y)
    ? SPLINE_DOG_TRI_H_Y
    : SPLINE_DOG_INTERFACE_H_Y;
SPLINE_DOG_T = is_undef(SPLINE_DOG_T)
    ? SPLINE_DOG_BASE_T + SPLINE_DOG_INTERFACE_H_Y
    : SPLINE_DOG_T;
SPLINE_DOG_BORE_D = is_undef(SPLINE_DOG_BORE_D)
    ? 3.30
    : SPLINE_DOG_BORE_D;
SPLINE_DOG_GEAR_OVERLAP = is_undef(SPLINE_DOG_GEAR_OVERLAP)
    ? 0.20
    : SPLINE_DOG_GEAR_OVERLAP;
SPLINE_DOG_BASE_CENTER_Y = is_undef(SPLINE_DOG_BASE_CENTER_Y)
    ? SPLINE_GEAR_CENTER_Y
        - SPLINE_GEAR_T / 2
        + SPLINE_DOG_GEAR_OVERLAP
        - SPLINE_DOG_BASE_T / 2
    : SPLINE_DOG_BASE_CENTER_Y;
SPLINE_DOG_CLAW_CENTER_Y = is_undef(SPLINE_DOG_CLAW_CENTER_Y)
    ? SPLINE_DOG_BASE_CENTER_Y
        - SPLINE_DOG_BASE_T / 2
        + SPLINE_DOG_INTERFACE_OVERLAP_Y
        - SPLINE_DOG_INTERFACE_H_Y / 2
    : SPLINE_DOG_CLAW_CENTER_Y;
SPLINE_DOG_INTERFACE_CENTER_Y = is_undef(SPLINE_DOG_INTERFACE_CENTER_Y)
    ? SPLINE_DOG_CLAW_CENTER_Y
    : SPLINE_DOG_INTERFACE_CENTER_Y;
SPLINE_DOG_SPLINE_CLEARANCE = is_undef(SPLINE_DOG_SPLINE_CLEARANCE)
    ? 0.25
    : SPLINE_DOG_SPLINE_CLEARANCE;
SPLINE_DOG_MATE_SPLINE_CLEARANCE = is_undef(
    SPLINE_DOG_MATE_SPLINE_CLEARANCE
)
    ? 0.25
    : SPLINE_DOG_MATE_SPLINE_CLEARANCE;

// Thumbnail-only lower receiver: a matching rounded-triangle pocket is cut
// into its Y+ face with a deliberately generous FDM clearance.
// This radius is the reserved maximum radial envelope for the future opposite
// end; any added outer structure must stay inside it to clear the spline shaft.
SPLINE_DOG_RADIAL_ENVELOPE_R = is_undef(SPLINE_DOG_RADIAL_ENVELOPE_R)
    ? 3.80
    : SPLINE_DOG_RADIAL_ENVELOPE_R;
SPLINE_DOG_MATE_T = 1.00;
SPLINE_DOG_MATE_R = is_undef(SPLINE_DOG_MATE_R)
    ? SPLINE_DOG_RADIAL_ENVELOPE_R
    : SPLINE_DOG_MATE_R;
SPLINE_DOG_MATE_BORE_D = 3.30;
SPLINE_DOG_MATE_POCKET_DEPTH = 0.75;
SPLINE_DOG_MATE_POCKET_CLEARANCE = 0.25;
SPLINE_DOG_MATE_GAP = 0.35;
SPLINE_DOG_MATE_CENTER_Y =
    SPLINE_DOG_INTERFACE_CENTER_Y
        - SPLINE_DOG_INTERFACE_H_Y / 2
        - SPLINE_DOG_MATE_GAP
        - SPLINE_DOG_MATE_T / 2;

SPLINE_GEAR_EPS = 0.05;
//#endregion

//#region 模型/类型
// solid = 仅输出齿轮 + 下置狗牙的打印件。
// thumbnail = 预览件，额外显示一小段位于 Z=0 的花键轴背景，不用于打印。
//#endregion

//#region 私有成员：齿形函数
function spline_gear_pitch_r(teeth, pitch_mm) =
    teeth * pitch_mm / (2 * PI);

function spline_gear_root_r(teeth, pitch_mm, tooth_depth) =
    spline_gear_pitch_r(teeth, pitch_mm) - tooth_depth;

function spline_gear_tip_r(teeth, pitch_mm, tooth_depth) =
    spline_gear_pitch_r(teeth, pitch_mm) + tooth_depth;

function spline_gear_outer_d() =
    2 * spline_gear_tip_r(
        SPLINE_GEAR_TEETH,
        SPLINE_GEAR_PITCH_MM,
        SPLINE_GEAR_TOOTH_DEPTH
    );

function spline_gear_center_distance() =
    SPLINE_GEAR_CENTER_Z;

function spline_gear_dog_claw_outer_r() =
    SPLINE_DOG_CLAW_TIP_CENTER_R + SPLINE_DOG_CLAW_HEAD_R;

function spline_gear_dog_claw_inner_r() =
    SPLINE_DOG_CLAW_ROOT_CENTER_R - SPLINE_DOG_CLAW_HEAD_R;

function spline_gear_dog_triangle_outer_r() =
    SPLINE_DOG_TRI_VERTEX_R + SPLINE_DOG_TRI_HEAD_R;

function spline_gear_dog_triangle_inner_r() =
    SPLINE_DOG_TRI_VERTEX_R * cos(30) - SPLINE_DOG_TRI_HEAD_R;

function spline_gear_dog_interface_outer_r() =
    SPLINE_DOG_INTERFACE == "rounded_triangle"
        ? spline_gear_dog_triangle_outer_r()
        : spline_gear_dog_claw_outer_r();

function spline_gear_dog_spline_clearance() =
    spline_gear_center_distance()
        - spline_gear_tip_r(
            SPLINE_TEETH,
            SPLINE_PITCH_MM,
            SPLINE_TOOTH_DEPTH
        )
        - spline_gear_dog_interface_outer_r();

function spline_gear_dog_mate_spline_clearance() =
    spline_gear_center_distance()
        - spline_gear_tip_r(
            SPLINE_TEETH,
            SPLINE_PITCH_MM,
            SPLINE_TOOTH_DEPTH
        )
        - SPLINE_DOG_MATE_R;

function spline_gear_tip_land_mm() =
    (SPLINE_GEAR_TIP_END - SPLINE_GEAR_TIP_START)
        * SPLINE_GEAR_PITCH_MM
        * spline_gear_tip_r(
            SPLINE_GEAR_TEETH,
            SPLINE_GEAR_PITCH_MM,
            SPLINE_GEAR_TOOTH_DEPTH
        )
        / spline_gear_pitch_r(
            SPLINE_GEAR_TEETH,
            SPLINE_GEAR_PITCH_MM
        );

function spline_gear_polar(r, a) = [r * cos(a), r * sin(a)];

function spline_gear_points(teeth, root_r, tip_r) = [
    for (i = [0:teeth - 1])
        for (p = [
            [0.00, root_r],
            [SPLINE_GEAR_TIP_START, tip_r],
            [SPLINE_GEAR_TIP_END, tip_r],
            [SPLINE_GEAR_ROOT_END, root_r]
        ])
            let (a = (i + p[0]) * 360 / teeth)
                spline_gear_polar(p[1], a)
];
//#endregion

//#region 公开 API
// 根入口由 ch1_03c_spline_gear_dog.scad 消费；参数文件本身不输出几何。
//#endregion

//#region 业务逻辑
// 这里的 Z+ 是“相对长花键轴中心向 Z+ 放置小齿轮中心”，不是把旧离合
// 载架的轴向约定搬过来。齿轮和狗牙均沿 Y，狗牙位于齿轮本体 Y− 侧。
//#endregion

//#region 方法/工具
assert(
    SPLINE_GEAR_DOG_MODEL == "solid"
        || SPLINE_GEAR_DOG_MODEL == "thumbnail",
    "unknown spline gear dog model"
);
assert(SPLINE_TEETH >= 6, "spline shaft needs at least 6 teeth");
assert(SPLINE_PITCH_MM > 0, "spline pitch must be positive");
assert(SPLINE_GEAR_TEETH >= 8, "small gear needs at least 8 teeth");
assert(SPLINE_GEAR_PITCH_MM == SPLINE_PITCH_MM,
    "mating gear pitch must match the spline shaft pitch");
assert(
    spline_gear_root_r(
        SPLINE_GEAR_TEETH,
        SPLINE_GEAR_PITCH_MM,
        SPLINE_GEAR_TOOTH_DEPTH
    ) > SPLINE_GEAR_BORE_D / 2,
    "gear bore must fit inside the gear root circle"
);
assert(SPLINE_GEAR_T > 0, "gear thickness must be positive");
assert(
    SPLINE_DOG_INTERFACE == "rounded_triangle"
        || SPLINE_DOG_INTERFACE == "three_claw",
    "unknown dog interface"
);
assert(SPLINE_DOG_CLAW_COUNT == 3, "backup dog interface uses three claws");
assert(SPLINE_DOG_BASE_R > SPLINE_DOG_BORE_D / 2,
    "dog base must fit around the dog bore");
assert(SPLINE_DOG_CLAW_HEAD_R > 0, "dog claw head radius must be positive");
assert(
    SPLINE_DOG_CLAW_TIP_CENTER_R > SPLINE_DOG_CLAW_ROOT_CENTER_R,
    "dog claw must extend radially outward"
);
assert(
    spline_gear_dog_claw_inner_r() < SPLINE_DOG_BASE_R,
    "rounded claw root must overlap the dog base"
);
assert(
    SPLINE_DOG_TRI_HEAD_R > 0,
    "rounded triangle head radius must be positive"
);
assert(
    spline_gear_dog_triangle_inner_r() < SPLINE_DOG_BASE_R,
    "rounded triangle must overlap the dog base"
);
assert(
    spline_gear_dog_interface_outer_r()
        < spline_gear_tip_r(
            SPLINE_GEAR_TEETH,
            SPLINE_GEAR_PITCH_MM,
            SPLINE_GEAR_TOOTH_DEPTH
        ),
    "dog claw outer diameter must be smaller than the upper gear"
);
assert(SPLINE_DOG_T > 0, "dog thickness must be positive");
assert(SPLINE_DOG_INTERFACE_H_Y > 0,
    "dog interface depth must be positive");
assert(SPLINE_DOG_INTERFACE_OVERLAP_Y > 0,
    "dog interface needs positive axial overlap");
assert(SPLINE_DOG_GEAR_OVERLAP > 0, "gear and dog need positive overlap");
assert(
    spline_gear_dog_spline_clearance() >= SPLINE_DOG_SPLINE_CLEARANCE,
    "dog claws must clear the long spline shaft"
);
assert(
    spline_gear_dog_mate_spline_clearance()
        >= SPLINE_DOG_MATE_SPLINE_CLEARANCE,
    "mating receiver must clear the long spline shaft"
);
assert(SPLINE_DOG_MATE_T > 0, "mating receiver thickness must be positive");
assert(
    SPLINE_DOG_MATE_R <= SPLINE_DOG_RADIAL_ENVELOPE_R,
    "mating receiver must stay inside the reserved radial envelope"
);
assert(SPLINE_DOG_MATE_R
    > spline_gear_dog_interface_outer_r()
        + SPLINE_DOG_MATE_POCKET_CLEARANCE,
    "mating receiver must contain the rounded pockets"
);
assert(
    0 < SPLINE_GEAR_TIP_START
        && SPLINE_GEAR_TIP_START < SPLINE_GEAR_TIP_END
        && SPLINE_GEAR_TIP_END < SPLINE_GEAR_ROOT_END
        && SPLINE_GEAR_ROOT_END < 1,
    "invalid tooth profile fractions"
);
//#endregion
