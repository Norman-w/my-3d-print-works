// CH1 03C 打印版 GT2 复合子母轮 — 参数真值源
// 单位：毫米；打印坐标轴为 Z，装配时通过旋转让轴向回到世界 Y。

//#region 导入/依赖
// 无外部依赖。花键啮合轮沿用 CH1 03C X1C 细版的 2.4 mm 节距。
//#endregion

//#region 常量/配置
GT2_CLUTCH_MODEL = is_undef(GT2_CLUTCH_MODEL)
    ? "assembly"
    : GT2_CLUTCH_MODEL;

// 长花键轴位置基准：独立 X1C 样件默认 10T / 2.4 mm；主场景会在
// include 前覆盖为现有 12T / 3 mm 传动杆，避免把两个节距混合装配。
GT2_LONG_TEETH = is_undef(GT2_LONG_TEETH)
    ? 10
    : GT2_LONG_TEETH;
GT2_LONG_PITCH_MM = is_undef(GT2_LONG_PITCH_MM)
    ? 2.4
    : GT2_LONG_PITCH_MM;
GT2_LONG_TOOTH_DEPTH = is_undef(GT2_LONG_TOOTH_DEPTH)
    ? 0.60
    : GT2_LONG_TOOTH_DEPTH;

// 子轮改为 15T。它仍与长轴共用 2.4 mm 节距，增加的齿数同时带来更大的
// 节圆和更大的中心距，不靠任意平移破坏齿轮啮合。
GT2_MALE_TEETH = is_undef(GT2_MALE_TEETH)
    ? 15
    : GT2_MALE_TEETH;
GT2_MALE_PITCH_MM = is_undef(GT2_MALE_PITCH_MM)
    ? GT2_LONG_PITCH_MM
    : GT2_MALE_PITCH_MM;
GT2_MALE_TOOTH_DEPTH = is_undef(GT2_MALE_TOOTH_DEPTH)
    ? 0.60
    : GT2_MALE_TOOTH_DEPTH;
GT2_MALE_GEAR_T = is_undef(GT2_MALE_GEAR_T)
    ? 3.20
    : GT2_MALE_GEAR_T;
GT2_GEAR_MESH_CLEARANCE = is_undef(GT2_GEAR_MESH_CLEARANCE)
    ? 0.12
    : GT2_GEAR_MESH_CLEARANCE;

// 圆角三角离合接口改为较深的浅锥圆角结构：根部略大、插入端略收，
// 不用垂直直壁硬插；三角公牙直接从齿轮下方开始，不再增加圆形垫圈层。
GT2_DOG_INTERFACE_R = 2.95;
GT2_DOG_INTERFACE_TAPER_R = is_undef(GT2_DOG_INTERFACE_TAPER_R)
    ? 0.20
    : GT2_DOG_INTERFACE_TAPER_R;
GT2_DOG_INTERFACE_HEAD_R = 0.30;
// The leading face is rounded but slightly smaller than the root head, so
// the male dog starts entering the continuous female taper instead of
// presenting a blunt vertical edge.
GT2_DOG_INTERFACE_TIP_HEAD_R = is_undef(GT2_DOG_INTERFACE_TIP_HEAD_R)
    ? 0.24
    : GT2_DOG_INTERFACE_TIP_HEAD_R;
GT2_DOG_INTERFACE_H = is_undef(GT2_DOG_INTERFACE_H)
    ? 3.00
    : GT2_DOG_INTERFACE_H;
GT2_DOG_INTERFACE_ROTATION_DEG = 30;
GT2_DOG_GEAR_OVERLAP = 0.20;

// 打印轴孔：名义 Ø3 mm D 轴；只在各自的齿轮/带轮本体内保留一小段盲孔。
// 公母狗牙接驳段不再让 D 轴贯通，中心位置留给相斥磁铁。
GT2_D_AXIS_D = 3.00;
GT2_D_AXIS_FLAT_DEPTH = 0.50;
GT2_D_BORE_RADIAL_CLEARANCE = 0.15;
GT2_D_BORE_FLAT_CLEARANCE = 0.12;
GT2_D_BORE_DEPTH = is_undef(GT2_D_BORE_DEPTH)
    ? 3.00
    : GT2_D_BORE_DEPTH;

// One nominal Ø2 mm axial magnet per mating center. The printed pocket is
// enlarged slightly for a hand-fit. Both pockets are exactly concentric with
// the shaft axis; the female pocket opens from the bottom of the mother slot.
// A second pair lives in the selector magnetic shoe; keeping its spacing here
// prevents the web animation and the printed trigger from acquiring separate
// magic numbers.
GT2_MAGNET_NOMINAL_D = 2.00;
GT2_MAGNET_POCKET_D = is_undef(GT2_MAGNET_POCKET_D)
    ? 2.20
    : GT2_MAGNET_POCKET_D;
GT2_MAGNET_POCKET_H = is_undef(GT2_MAGNET_POCKET_H)
    ? 1.80
    : GT2_MAGNET_POCKET_H;
// 标准 2GT/GT2：2 mm 节距、12T、6 mm 皮带。打印轮不带法兰或大轮毂。
GT2_PULLEY_TEETH = is_undef(GT2_PULLEY_TEETH)
    ? 12
    : GT2_PULLEY_TEETH;
GT2_PULLEY_PITCH_MM = is_undef(GT2_PULLEY_PITCH_MM)
    ? 2.0
    : GT2_PULLEY_PITCH_MM;
GT2_BELT_WIDTH = is_undef(GT2_BELT_WIDTH)
    ? 6.0
    : GT2_BELT_WIDTH;
GT2_PULLEY_FACE_T = is_undef(GT2_PULLEY_FACE_T)
    ? 7.20
    : GT2_PULLEY_FACE_T;
GT2_PULLEY_PLD = is_undef(GT2_PULLEY_PLD)
    ? 0.254
    : GT2_PULLEY_PLD;
GT2_PULLEY_TOOTH_DEPTH = is_undef(GT2_PULLEY_TOOTH_DEPTH)
    ? 0.75
    : GT2_PULLEY_TOOTH_DEPTH;
GT2_PULLEY_ROOT_CLEARANCE = is_undef(GT2_PULLEY_ROOT_CLEARANCE)
    ? 0.06
    : GT2_PULLEY_ROOT_CLEARANCE;

// 皮带最外侧不是简单的“带轮外径 + 皮带总厚度”。这里按节圆外侧的
// 保守回弹包络预算 0.90 mm，已包含标准背胶厚度和首件误差，用于最坏方向
// 的花键轴避让检查；该包络只在缩略图显示，不导出到 STL。
GT2_BELT_BACK_OFFSET = is_undef(GT2_BELT_BACK_OFFSET)
    ? 0.90
    : GT2_BELT_BACK_OFFSET;
GT2_BELT_GUIDE_R_MARGIN = is_undef(GT2_BELT_GUIDE_R_MARGIN)
    ? 0.05
    : GT2_BELT_GUIDE_R_MARGIN;
// 下端改为完整覆盖皮带下侧的承托盘，而不是只有一圈薄唇；轴向厚度固定为 1 mm。
GT2_BELT_LOWER_RETAINER_T = is_undef(GT2_BELT_LOWER_RETAINER_T)
    ? 1.00
    : GT2_BELT_LOWER_RETAINER_T;
// 上端只保留较薄的导向唇，便于闭环皮带装入；下端完整承托负责防脱落。
GT2_BELT_GUIDE_LIP_T = is_undef(GT2_BELT_GUIDE_LIP_T)
    ? 0.60
    : GT2_BELT_GUIDE_LIP_T;
GT2_BELT_RADIAL_CLEARANCE = is_undef(GT2_BELT_RADIAL_CLEARANCE)
    ? 0.45
    : GT2_BELT_RADIAL_CLEARANCE;

// 母座外壁现在与皮带防脱导向外延齐平，形成一圈连续厚壁；GT2 齿圈位于
// 母座另一侧的独立轴向层，因此不会填平母槽，也不需要法兰。
GT2_MOTHER_OUTER_R = is_undef(GT2_MOTHER_OUTER_R)
    ? GT2_PULLEY_TEETH * GT2_PULLEY_PITCH_MM / (2 * PI)
        + GT2_BELT_BACK_OFFSET
        + GT2_BELT_GUIDE_R_MARGIN
    : GT2_MOTHER_OUTER_R;
GT2_MOTHER_T = is_undef(GT2_MOTHER_T)
    ? 3.70
    : GT2_MOTHER_T;
GT2_MOTHER_POCKET_DEPTH = is_undef(GT2_MOTHER_POCKET_DEPTH)
    ? 3.25
    : GT2_MOTHER_POCKET_DEPTH;
// Frozen center-station clutch travel. The open gap is measured from the
// male dog tip to the mother pocket mouth; effective insertion is the amount
// that enters the pocket after the gap is closed. Total travel is therefore
// gap + insertion, while the remaining pocket depth is the bottom clearance.
GT2_MOTHER_GAP = is_undef(GT2_MOTHER_GAP)
    ? 0.60
    : GT2_MOTHER_GAP;
GT2_MOTHER_EFFECTIVE_INSERTION = is_undef(GT2_MOTHER_EFFECTIVE_INSERTION)
    ? 2.40
    : GT2_MOTHER_EFFECTIVE_INSERTION;
GT2_CLUTCH_ENGAGE_STROKE_MM = is_undef(GT2_CLUTCH_ENGAGE_STROKE_MM)
    ? GT2_MOTHER_GAP + GT2_MOTHER_EFFECTIVE_INSERTION
    : GT2_CLUTCH_ENGAGE_STROKE_MM;
GT2_MOTHER_BOTTOM_CLEARANCE = is_undef(GT2_MOTHER_BOTTOM_CLEARANCE)
    ? GT2_MOTHER_POCKET_DEPTH - GT2_MOTHER_EFFECTIVE_INSERTION
    : GT2_MOTHER_BOTTOM_CLEARANCE;
// The engaged dog still stops 0.85 mm above the mother-pocket bottom. Let the
// female magnet sit 0.45 mm proud of that floor, leaving the frozen 0.40 mm
// face-to-face non-contact clearance instead of making the magnets the stop.
GT2_MAGNET_NONCONTACT_CLEARANCE_MM = is_undef(
    GT2_MAGNET_NONCONTACT_CLEARANCE_MM
)
    ? 0.40
    : GT2_MAGNET_NONCONTACT_CLEARANCE_MM;
GT2_FEMALE_MAGNET_PROJECTION_MM = GT2_MOTHER_BOTTOM_CLEARANCE
    - GT2_MAGNET_NONCONTACT_CLEARANCE_MM;
GT2_ACTUATOR_TRIGGER_SPACING_MM = is_undef(GT2_ACTUATOR_TRIGGER_SPACING_MM)
    ? 12.00
    : GT2_ACTUATOR_TRIGGER_SPACING_MM;
GT2_MOTHER_POCKET_CLEARANCE = is_undef(GT2_MOTHER_POCKET_CLEARANCE)
    ? 0.25
    : GT2_MOTHER_POCKET_CLEARANCE;
GT2_MOTHER_ENTRY_CLEARANCE = is_undef(GT2_MOTHER_ENTRY_CLEARANCE)
    ? 0.42
    : GT2_MOTHER_ENTRY_CLEARANCE;
GT2_MOTHER_PULLEY_OVERLAP = is_undef(GT2_MOTHER_PULLEY_OVERLAP)
    ? 0.20
    : GT2_MOTHER_PULLEY_OVERLAP;
// The female receiver faces the male dog from the opposite side. Flipping
// the local +Z axis mirrors the X/Y profile, so the pocket needs one 60 deg
// phase correction to put its three rounded lobes over the male's three
// valleys in the common world XZ plane.
GT2_MOTHER_POCKET_PHASE_DEG = is_undef(GT2_MOTHER_POCKET_PHASE_DEG)
    ? 60.00
    : GT2_MOTHER_POCKET_PHASE_DEG;

GT2_EPS = 0.05;
//#endregion

//#region 尺寸函数
function gt2_pitch_r(teeth, pitch_mm) =
    teeth * pitch_mm / (2 * PI);

function gt2_root_r(teeth, pitch_mm, tooth_depth, root_clearance = 0) =
    gt2_pitch_r(teeth, pitch_mm)
        - (pitch_mm * 0.0 + tooth_depth)
        - root_clearance;

function gt2_tip_r(teeth, pitch_mm, pld) =
    gt2_pitch_r(teeth, pitch_mm) - pld;

function gt2_long_pitch_r() =
    gt2_pitch_r(GT2_LONG_TEETH, GT2_LONG_PITCH_MM);

function gt2_long_tip_r() =
    gt2_long_pitch_r() + GT2_LONG_TOOTH_DEPTH;

function gt2_male_pitch_r() =
    gt2_pitch_r(GT2_MALE_TEETH, GT2_MALE_PITCH_MM);

function gt2_male_tip_r() =
    gt2_male_pitch_r() + GT2_MALE_TOOTH_DEPTH;

function gt2_center_distance() =
    gt2_long_pitch_r()
        + gt2_male_pitch_r()
        + GT2_GEAR_MESH_CLEARANCE;

function gt2_old_center_distance() =
    gt2_long_pitch_r()
        + gt2_pitch_r(12, GT2_LONG_PITCH_MM)
        + GT2_GEAR_MESH_CLEARANCE;

function gt2_center_shift() =
    gt2_center_distance() - gt2_old_center_distance();

function gt2_pulley_pitch_r() =
    gt2_pitch_r(GT2_PULLEY_TEETH, GT2_PULLEY_PITCH_MM);

function gt2_pulley_tip_r() =
    gt2_tip_r(
        GT2_PULLEY_TEETH,
        GT2_PULLEY_PITCH_MM,
        GT2_PULLEY_PLD
    );

function gt2_pulley_root_r() =
    gt2_pulley_tip_r()
        - GT2_PULLEY_TOOTH_DEPTH
        - GT2_PULLEY_ROOT_CLEARANCE;

function gt2_belt_envelope_r() =
    gt2_pulley_pitch_r() + GT2_BELT_BACK_OFFSET;

function gt2_belt_guide_r() =
    gt2_belt_envelope_r() + GT2_BELT_GUIDE_R_MARGIN;

function gt2_belt_clearance_to_long_shaft() =
    gt2_center_distance()
        - gt2_long_tip_r()
        - gt2_belt_envelope_r();

function gt2_belt_guide_clearance_to_long_shaft() =
    gt2_center_distance()
        - gt2_long_tip_r()
        - gt2_belt_guide_r();

function gt2_mother_clearance_to_long_shaft() =
    gt2_center_distance()
        - gt2_long_tip_r()
        - GT2_MOTHER_OUTER_R;

function gt2_triangle_outer_r() =
    GT2_DOG_INTERFACE_R + GT2_DOG_INTERFACE_HEAD_R;

function gt2_triangle_tip_center_r() =
    GT2_DOG_INTERFACE_R - GT2_DOG_INTERFACE_TAPER_R;

function gt2_triangle_tip_outer_r() =
    gt2_triangle_tip_center_r() + GT2_DOG_INTERFACE_TIP_HEAD_R;

function gt2_triangle_inner_r() =
    GT2_DOG_INTERFACE_R * cos(30)
        - GT2_DOG_INTERFACE_HEAD_R;

function gt2_mother_pocket_outer_r() =
    gt2_triangle_outer_r() + GT2_MOTHER_POCKET_CLEARANCE;

function gt2_pulley_face_bottom_z() =
    GT2_BELT_LOWER_RETAINER_T;

function gt2_pulley_face_top_z() =
    gt2_pulley_face_bottom_z() + GT2_PULLEY_FACE_T;

function gt2_mother_receiver_bottom_z() =
    gt2_pulley_face_top_z() - GT2_MOTHER_PULLEY_OVERLAP;

function gt2_mother_receiver_top_z() =
    gt2_mother_receiver_bottom_z() + GT2_MOTHER_T;

function gt2_mother_floor_t() =
    GT2_MOTHER_T - GT2_MOTHER_POCKET_DEPTH;

function gt2_mother_pocket_floor_z() =
    gt2_mother_receiver_top_z() - GT2_MOTHER_POCKET_DEPTH;

function gt2_male_total_h() =
    GT2_MALE_GEAR_T
        - GT2_DOG_GEAR_OVERLAP
        + GT2_DOG_INTERFACE_H;

function gt2_female_total_h() =
    gt2_mother_receiver_top_z();

function gt2_male_magnet_pocket_z0() =
    gt2_male_total_h() - GT2_MAGNET_POCKET_H;

function gt2_female_magnet_pocket_z0() =
    gt2_mother_pocket_floor_z()
        - GT2_MAGNET_POCKET_H
        + GT2_FEMALE_MAGNET_PROJECTION_MM;

function gt2_male_spline_clearance() =
    gt2_center_distance()
        - gt2_long_tip_r()
        - gt2_triangle_outer_r();

function gt2_male_gear_points() =
    let(
        teeth = GT2_MALE_TEETH,
        root_r = gt2_male_pitch_r() - GT2_MALE_TOOTH_DEPTH,
        tip_r = gt2_male_tip_r()
    )
        gt2_gear_points(
            teeth,
            root_r,
            tip_r,
            0.18,
            0.50,
            0.75
        );

function gt2_long_gear_points() =
    gt2_gear_points(
        GT2_LONG_TEETH,
        gt2_long_pitch_r() - GT2_LONG_TOOTH_DEPTH,
        gt2_long_tip_r(),
        0.18,
        0.50,
        0.75
    );

function gt2_gear_polar(r, a) = [r * cos(a), r * sin(a)];

function gt2_gear_points(
    teeth,
    root_r,
    tip_r,
    tip_start,
    tip_end,
    root_end
) = [
    for (i = [0:teeth - 1])
        for (p = [
            [0.00, root_r],
            [tip_start, tip_r],
            [tip_end, tip_r],
            [root_end, root_r]
        ])
            let (a = (i + p[0]) * 360 / teeth)
                gt2_gear_polar(p[1], a)
];

// 2GT 圆弧齿的 FDM 友好多点近似：峰顶和过渡段留足圆弧趋势，槽底比
// 名义值再深一点，避免 0.4 mm 喷嘴首件把皮带齿卡死。
function gt2_pulley_points() =
    let(
        teeth = GT2_PULLEY_TEETH,
        root_r = gt2_pulley_root_r(),
        tip_r = gt2_pulley_tip_r(),
        depth = tip_r - root_r,
        profile = [
            [0.00, 0.00],
            [0.07, 0.10],
            [0.14, 0.38],
            [0.20, 0.82],
            [0.26, 1.00],
            [0.48, 1.00],
            [0.54, 0.82],
            [0.60, 0.38],
            [0.67, 0.10],
            [1.00, 0.00]
        ]
    ) [
        for (i = [0:teeth - 1])
            for (p = profile)
                let (
                    r = root_r + depth * p[1],
                    a = (i + p[0]) * 360 / teeth
                )
                    gt2_gear_polar(r, a)
    ];
//#endregion

//#region 业务校验
assert(
    GT2_CLUTCH_MODEL == "male"
        || GT2_CLUTCH_MODEL == "female"
        || GT2_CLUTCH_MODEL == "assembly",
    "unknown GT2 clutch pair model"
);
assert(GT2_LONG_TEETH >= 6, "long spline shaft needs at least 6 teeth");
assert(GT2_LONG_PITCH_MM > 0, "long spline pitch must be positive");
assert(GT2_MALE_TEETH >= 8, "male mating gear needs at least 8 teeth");
assert(
    GT2_MALE_PITCH_MM == GT2_LONG_PITCH_MM,
    "male mating gear pitch must match long spline shaft"
);
assert(
    gt2_male_pitch_r() - GT2_MALE_TOOTH_DEPTH
        > GT2_D_AXIS_D / 2 + GT2_D_BORE_RADIAL_CLEARANCE,
    "male gear root must leave wall around the D bore"
);
assert(GT2_MALE_GEAR_T > 0, "male gear thickness must be positive");
assert(GT2_MALE_GEAR_T >= 3.0,
    "male gear teeth need at least 3 mm axial thickness");
assert(GT2_DOG_INTERFACE_H >= 3.0,
    "dog interface needs about 3 mm insertion depth");
assert(abs(GT2_MOTHER_GAP - 0.60) < 0.001,
    "center clutch open gap is frozen at 0.60 mm");
assert(abs(GT2_MOTHER_EFFECTIVE_INSERTION - 2.40) < 0.001,
    "center clutch effective insertion is frozen at 2.40 mm");
assert(abs(GT2_CLUTCH_ENGAGE_STROKE_MM - 3.00) < 0.001,
    "center clutch total stroke is frozen at 3.00 mm");
assert(abs(GT2_MOTHER_BOTTOM_CLEARANCE - 0.85) < 0.001,
    "center clutch pocket bottom clearance is frozen at 0.85 mm");
assert(abs(GT2_MOTHER_GAP + GT2_MOTHER_EFFECTIVE_INSERTION
        - GT2_CLUTCH_ENGAGE_STROKE_MM) < 0.001,
    "clutch stroke must equal open gap plus effective insertion");
assert(abs(GT2_MOTHER_POCKET_DEPTH - GT2_MOTHER_EFFECTIVE_INSERTION
        - GT2_MOTHER_BOTTOM_CLEARANCE) < 0.001,
    "mother pocket depth must equal insertion plus bottom clearance");
assert(GT2_ACTUATOR_TRIGGER_SPACING_MM >= 12.0,
    "selector magnetic shoe needs at least 12 mm trigger spacing");
assert(
    GT2_DOG_GEAR_OVERLAP >= GT2_EPS
        && GT2_DOG_GEAR_OVERLAP < GT2_MALE_GEAR_T,
    "dog must overlap the gear band without adding a collar"
);
assert(GT2_DOG_INTERFACE_TAPER_R > 0
        && GT2_DOG_INTERFACE_TAPER_R < GT2_DOG_INTERFACE_R,
    "dog taper must be shallow and positive");
assert(
    GT2_DOG_INTERFACE_TIP_HEAD_R > 0
        && GT2_DOG_INTERFACE_TIP_HEAD_R <= GT2_DOG_INTERFACE_HEAD_R,
    "dog leading edge must stay rounded and no larger than the root"
);
assert(
    gt2_triangle_outer_r() < gt2_male_tip_r(),
    "dog outer radius must remain below the male gear tip radius"
);
assert(gt2_triangle_tip_outer_r() < gt2_triangle_outer_r(),
    "male dog tip must be slightly smaller than its root");
assert(GT2_PULLEY_TEETH == 12, "this compact envelope is reserved for 12T GT2");
assert(GT2_PULLEY_PITCH_MM == 2.0, "pulley must use the 2 mm GT2 pitch");
assert(GT2_BELT_WIDTH == 6.0, "pulley must be paired with a 6 mm belt");
assert(
    GT2_PULLEY_FACE_T >= GT2_BELT_WIDTH + 0.80,
    "pulley face must leave side clearance for the belt guide lips"
);
assert(GT2_BELT_GUIDE_LIP_T > 0,
    "belt guide lip thickness must be positive");
assert(GT2_BELT_LOWER_RETAINER_T == 1.0,
    "lower belt retainer must be 1 mm thick");
assert(gt2_pulley_root_r() > GT2_D_AXIS_D / 2 + 0.75,
    "GT2 pulley needs a printable wall around the D bore");
assert(
    2 * gt2_pulley_tip_r() < 2 * GT2_MOTHER_OUTER_R,
    "GT2 tooth tips must stay inside the reserved mother outer envelope"
);
assert(
    gt2_mother_pocket_outer_r() < GT2_MOTHER_OUTER_R,
    "mother pocket must leave an outer ring wall"
);
assert(
    gt2_mother_floor_t() >= 0.40,
    "mother receiver floor needs at least 0.40 mm for FDM strength"
);
assert(
    GT2_MOTHER_ENTRY_CLEARANCE >= GT2_MOTHER_POCKET_CLEARANCE,
    "pocket mouth must not be tighter than its running clearance"
);
assert(
    gt2_triangle_tip_outer_r() + GT2_MOTHER_ENTRY_CLEARANCE
        < GT2_MOTHER_OUTER_R - 0.05,
    "pocket entry flare must leave a mother outer wall"
);
assert(
    GT2_MOTHER_POCKET_PHASE_DEG >= 0
        && GT2_MOTHER_POCKET_PHASE_DEG < 120,
    "mother pocket phase must stay within one triangular symmetry period"
);
assert(
    gt2_belt_clearance_to_long_shaft() >= GT2_BELT_RADIAL_CLEARANCE,
    "GT2 belt back envelope must clear the long spline shaft"
);
assert(
    gt2_belt_guide_clearance_to_long_shaft()
        >= GT2_BELT_RADIAL_CLEARANCE,
    "GT2 belt guide lip must clear the long spline shaft"
);
assert(
    gt2_mother_clearance_to_long_shaft() >= GT2_BELT_RADIAL_CLEARANCE,
    "mother outer ring must clear the long spline shaft"
);
assert(GT2_D_BORE_DEPTH >= 2.50,
    "short D-bore needs at least 2.5 mm engagement");
assert(
    GT2_D_BORE_DEPTH <= GT2_MALE_GEAR_T - 0.20,
    "male short D-bore must leave a top wall under the dog"
);
assert(
    GT2_D_BORE_DEPTH < gt2_mother_receiver_bottom_z() - 0.40,
    "short D-bore must stop before the mother receiver"
);
assert(GT2_MAGNET_POCKET_D >= GT2_MAGNET_NOMINAL_D,
    "magnet pocket must fit the nominal magnet");
assert(GT2_MAGNET_POCKET_H >= 1.20,
    "magnet pocket needs enough axial seating depth");
assert(
    GT2_MAGNET_POCKET_H < GT2_DOG_INTERFACE_H - 0.40,
    "male magnet pocket must stay inside the dog interface"
);
assert(
    gt2_male_magnet_pocket_z0() > GT2_MALE_GEAR_T,
    "male magnet pocket must not reach the gear band"
);
assert(
    gt2_female_magnet_pocket_z0() > gt2_pulley_face_bottom_z() + 0.40,
    "female magnet pocket must stay in the mother-side hub"
);
assert(GT2_MAGNET_NONCONTACT_CLEARANCE_MM > 0,
    "engaged magnets need a positive non-contact clearance");
assert(GT2_MAGNET_NONCONTACT_CLEARANCE_MM < GT2_MOTHER_BOTTOM_CLEARANCE,
    "female magnet projection must not consume the dog bottom clearance");
assert(abs(
        GT2_MOTHER_BOTTOM_CLEARANCE
        - GT2_FEMALE_MAGNET_PROJECTION_MM
        - GT2_MAGNET_NONCONTACT_CLEARANCE_MM
    ) < 0.001,
    "engaged magnet face clearance must be derived from the pocket bottom");
assert(GT2_FEMALE_MAGNET_PROJECTION_MM < GT2_MAGNET_POCKET_H,
    "female magnet projection must leave a blind pocket behind the magnet");
assert(
    abs(GT2_MOTHER_OUTER_R - gt2_belt_guide_r()) < 0.02,
    "mother receiver outer wall must be flush with the belt guide"
);
//#endregion
