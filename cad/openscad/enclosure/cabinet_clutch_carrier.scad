// 中心 R3C3 纯永磁离合机构板与公轮阶梯轴
//
// This file is included after cabinet_clutch.scad has defined the native world
// helpers and the CH1 03C pair library.  The input side is intentionally small:
// the male rotor is keyed to one stepped shaft (D-round-D), the round section
// runs directly in one stationary LM3UU, and the lower D section enters a
// printed sleeve carrying one Ø5×5 mm cylindrical magnet.  There is no input
// carriage, second guide, stop lug, spring, fork or printed input rotary cage.
//
// The output side uses two purchased 3×6×2 bearings in one long rectangular
// bar above the mother wheel.  The bar is printed as one solid with the
// removable clutch mechanism plate and has only the two bearing pockets.  The
// output shaft is D at the mother-wheel socket, then round through both
// bearings, with only a short round tip above the upper seat.
// The input LM3UU seat remains a compact rectangular region in that same plate;
// its Y thickness is exactly the purchased bearing envelope and it is bored
// Ø7.20 through Y with no holder fastener holes.

//#region 导入/依赖
// cabinet_clutch.scad supplies WORLD_PARTITION_BACK_Z, CENTER_GT2_Z,
// center_gt2_*(), cylinder_y(), d_rod_y(), d_profile_2d(), GT2_* and colors.
//#endregion

//#region 常量/配置
// Output rotor radial support: two purchased 3×6×2 bearings sit in one solid
// rectangular bar above the fixed female/output rotor.  The input side uses
// no separate rotary cage.
CENTER_CLUTCH_BEARING_OD = 6.00;
CENTER_CLUTCH_BEARING_ID = 3.00;
CENTER_CLUTCH_BEARING_W = 2.00;
CENTER_CLUTCH_BEARING_SEAT_D = is_undef(
    CENTER_CLUTCH_BEARING_SEAT_DIAMETER_MM
)
    ? 6.10
    : CENTER_CLUTCH_BEARING_SEAT_DIAMETER_MM;
CENTER_CLUTCH_BEARING_BLOCK_X = 14.00;
CENTER_CLUTCH_BEARING_BLOCK_Y = 6.40;
CENTER_CLUTCH_BEARING_BLOCK_Y0_OFFSET = 0.40;
CENTER_CLUTCH_BEARING_BACK_SHOULDER_T = 0.60;
CENTER_CLUTCH_BEARING_REFERENCE_CENTER_OFFSET =
    0.00;
CENTER_CLUTCH_BEARING_SEAT_DEPTH = CENTER_CLUTCH_BEARING_W
    + CENTER_CLUTCH_BEARING_BACK_SHOULDER_T;
CENTER_CLUTCH_BEARING_CENTER_OFFSET =
    CENTER_CLUTCH_BEARING_BLOCK_Y0_OFFSET + CENTER_CLUTCH_BEARING_W / 2;
CENTER_CLUTCH_BEARING_PAIR_SPACING = CENTER_CLUTCH_BEARING_BLOCK_Y
    - CENTER_CLUTCH_BEARING_W;
CENTER_CLUTCH_BEARING_BLOCK_Z_MARGIN = 1.00;
CENTER_CLUTCH_BEARING_BLOCK_Z_OVERLAP = 0.20;

// The rear chain layer crosses the output bearing bars in the axial (world Z)
// direction.  Open a local window only through that chain layer; the bearing
// seats and the solid web around the shaft stay untouched at the shaft datum.
// The relief is generated from the same WHEEL_POSES used by the chain preview,
// so the 8T guide envelope cannot silently drift away from the printed part.
CENTER_CLUTCH_CHAIN_RELIEF_RADIAL_CLEARANCE = 0.55;
CENTER_CLUTCH_CHAIN_RELIEF_AXIAL_CLEARANCE = 0.45;

// The relief is paired with a generated opposite-side "clay brush" bulge.  It
// is deliberately not a second rectangular gusset: the removed relief volume
// supplies the brush's point, direction and strength, just as an Inflate/Clay
// brush in a sculpting app would push the host material outward.  The chain
// window stays open; the rounded bulge carries the local bending load back into
// the solid bar.  All placement comes from the hit wheel pose below.
CENTER_CLUTCH_CHAIN_EMBOSS_MODE =
    "relief-volume-inflated-nomad-brush";
CENTER_CLUTCH_CHAIN_EMBOSS_FORCE_POINT_MODE =
    "relief-centroid";
CENTER_CLUTCH_CHAIN_EMBOSS_FORCE_DIRECTION_MODE =
    "relief-to-opposite-host-face";
CENTER_CLUTCH_CHAIN_EMBOSS_FORCE_MAGNITUDE_SCALE = 1.00;
CENTER_CLUTCH_CHAIN_EMBOSS_BRUSH_RADIUS_SCALE = 0.82;
CENTER_CLUTCH_CHAIN_EMBOSS_BRUSH_AXIAL_SCALE = 1.00;
CENTER_CLUTCH_CHAIN_EMBOSS_BRUSH_FALLOFF = 1.50;
CENTER_CLUTCH_CHAIN_EMBOSS_DEPTH = 3.40;
CENTER_CLUTCH_CHAIN_EMBOSS_ROOT_WIDTH = 5.80;
CENTER_CLUTCH_CHAIN_EMBOSS_OUTER_WIDTH = 3.40;
CENTER_CLUTCH_CHAIN_EMBOSS_ROOT_RADIUS = 1.20;
CENTER_CLUTCH_CHAIN_EMBOSS_OUTER_RADIUS = 1.00;
CENTER_CLUTCH_CHAIN_EMBOSS_ROOT_OVERLAP = 1.20;
CENTER_CLUTCH_CHAIN_EMBOSS_Z_MARGIN = 0.90;
CENTER_CLUTCH_CHAIN_EMBOSS_ROOT_SUPPORT_MARGIN = 0.75;
CENTER_CLUTCH_CHAIN_EMBOSS_RADIAL_BULGE = 0.12;
CENTER_CLUTCH_CHAIN_EMBOSS_PROFILE_STEPS = 47;
CENTER_CLUTCH_CHAIN_EMBOSS_CAP_STEPS = 16;
// The lofted section radius rounds the cheek's chain-facing, top and bottom
// surfaces as well as its outer nose. The root still penetrates the bar, so
// this rounds the exposed load path instead of leaving a sharp plate edge.
CENTER_CLUTCH_CHAIN_EMBOSS_EDGE_RADIUS = 0.50;
// These root parameters define the broad embedded blend and remain part of
// the exported mechanical contract. The actual visible transition is one
// continuous smoothstep loft, not a second root block or overlay.
CENTER_CLUTCH_CHAIN_EMBOSS_ROOT_FILLET_RADIUS = 0.85;
CENTER_CLUTCH_CHAIN_EMBOSS_ROOT_FLARE = 1.10;
CENTER_CLUTCH_CHAIN_EMBOSS_ROOT_FILLET_STEPS = 10;

// 固定绿色 8T 导向轮的唯一机械接口。绿色轮不是主动轮：轮内压入
// MR63/3×6×2，内圈由可采购的 M3 肩螺钉（光杆 Ø3）承载，螺纹端从
// 后仓 -Z 侧拧入板上一体 Boss 的盲导孔。普通全牙 M3 不穿过轴承。
// 轮心来自生成的 WHEEL_POSES；蓝色 12T 主动轮故意排除在这组安装座之外。
CENTER_CLUTCH_CHAIN_IDLER_BEARING_ID = 3.00;
CENTER_CLUTCH_CHAIN_IDLER_BEARING_OD = 6.00;
CENTER_CLUTCH_CHAIN_IDLER_BEARING_W = 2.00;
CENTER_CLUTCH_CHAIN_IDLER_AXLE_D = 3.00;
CENTER_CLUTCH_CHAIN_IDLER_AXLE_PROFILE =
    "M3-shoulder-screw-smooth-3mm-round";
CENTER_CLUTCH_CHAIN_IDLER_AXLE_SMOOTH_L = 8.50;
CENTER_CLUTCH_CHAIN_IDLER_THREAD_L = 4.20;
CENTER_CLUTCH_CHAIN_IDLER_THREAD_PILOT_D = 2.40;
CENTER_CLUTCH_CHAIN_IDLER_THREAD_PILOT_DEPTH = 4.20;
CENTER_CLUTCH_CHAIN_IDLER_BOSS_OD = 8.00;
CENTER_CLUTCH_CHAIN_IDLER_BOSS_ROOT_OD = 11.00;
CENTER_CLUTCH_CHAIN_IDLER_BOSS_ROOT_FLARE_T = 1.50;
// Do not leave the tapered root merely coplanar with the board face.  The
// extra 0.25 mm is buried inside the partition/row strip so the Boss and its
// host are one printable solid even at the row-1 idler near the support bar.
CENTER_CLUTCH_CHAIN_IDLER_BOSS_ROOT_OVERLAP = 0.25;
CENTER_CLUTCH_CHAIN_IDLER_BOSS_AXIAL_CLEARANCE = 0.45;
CENTER_CLUTCH_CHAIN_IDLER_BOSS_MOUNT_MODE =
    "partition-or-row-strip-integral-blind-pilot";
CENTER_CLUTCH_CHAIN_IDLER_BOSS_SCREW_ENTRY = "-Z";

// The removable plate seats directly on the rear face of the fixed partition.
// Every drawer cell repeats the same four-corner boss pattern: the bosses
// project rearward from the partition, stop 0.50 mm before the plate rear
// face, and contain blind pilot holes for the mushroom-head self-tapping
// screws.  The thin final rear cover never carries this load path.
CENTER_CLUTCH_PLATE_PARTITION_GAP = 0.00;
CENTER_CLUTCH_PLATE_Z = WORLD_PARTITION_BACK_Z
    - CENTER_CLUTCH_PLATE_PARTITION_GAP;
CENTER_CLUTCH_PLATE_T = 3.20;
CENTER_CLUTCH_PLATE_W = 34.00;
CENTER_CLUTCH_PLATE_MOUNT_X_OFFSET = 12.00;
CENTER_CLUTCH_PLATE_MOUNT_Y_OFFSET = 4.00;
CENTER_CLUTCH_M3_CLEAR_D = 3.40;
CENTER_CLUTCH_PLATE_FASTENER_COUNT = 4;
CENTER_CLUTCH_PARTITION_SELF_TAP_PILOT_D = 2.40;
CENTER_CLUTCH_PARTITION_BOSS_PER_CELL_COUNT = 4;
CENTER_CLUTCH_PARTITION_BOSS_OD = 5.00;
CENTER_CLUTCH_PARTITION_BOSS_HEIGHT = CENTER_CLUTCH_PLATE_T - 0.50;
CENTER_CLUTCH_PARTITION_SELF_TAP_PILOT_DEPTH =
    CENTER_CLUTCH_PARTITION_BOSS_HEIGHT - 0.50;
CENTER_CLUTCH_PARTITION_SELF_TAP_BOTTOM_WALL =
    CENTER_CLUTCH_PARTITION_BOSS_HEIGHT
        - CENTER_CLUTCH_PARTITION_SELF_TAP_PILOT_DEPTH;
CENTER_CLUTCH_PARTITION_BOSS_COUNT =
    N_COL * N_ROW * CENTER_CLUTCH_PARTITION_BOSS_PER_CELL_COUNT;
CENTER_CLUTCH_PLATE_REAR_Z = CENTER_CLUTCH_PLATE_Z
    - CENTER_CLUTCH_PLATE_T;

// The center 2GT belt crosses the service plate between the fixed output
// rotor and the front drawer pulley.  This opening is a true CSG passage.
CENTER_CLUTCH_PLATE_BELT_PASSAGE_RADIAL_CLEAR = 0.45;
CENTER_CLUTCH_PLATE_BELT_PASSAGE_AXIAL_CLEAR = 0.45;
CENTER_CLUTCH_PLATE_BELT_SLOT_CENTER_OFFSET =
    CENTER_GT2_BELT_BASE_INNER_R + CENTER_GT2_BELT_T / 2;
CENTER_CLUTCH_PLATE_BELT_SLOT_HALF_X = CENTER_GT2_BELT_T / 2
    + CENTER_GT2_BELT_TOOTH_H
    + CENTER_CLUTCH_PLATE_BELT_PASSAGE_RADIAL_CLEAR;
// This remains the outer envelope half-width for contract/clearance checks;
// the printed plate itself contains two slots at +/- the center offset.
CENTER_CLUTCH_PLATE_BELT_PASSAGE_HALF_X =
    CENTER_CLUTCH_PLATE_BELT_SLOT_CENTER_OFFSET
    + CENTER_CLUTCH_PLATE_BELT_SLOT_HALF_X;
CENTER_CLUTCH_PLATE_BELT_PASSAGE_Y = GT2_BELT_WIDTH
    + 2 * CENTER_CLUTCH_PLATE_BELT_PASSAGE_AXIAL_CLEAR;

// One fixed rectangular bar carries one LM3UU. Its long Z direction is the
// direct printed connection from the main plate to the male-axis bearing hole;
// the end extends past the bearing OD so the purchased bearing is enclosed in
// Z rather than hanging out of the rear of the bar.
CENTER_CLUTCH_LINEAR_BEARING_ID = 3.00;
CENTER_CLUTCH_LINEAR_BEARING_OD = 7.00;
CENTER_CLUTCH_LINEAR_BEARING_L = 10.00;
CENTER_CLUTCH_LINEAR_BEARING_COUNT = 1;
CENTER_CLUTCH_LINEAR_BEARING_SEAT_D =
    CENTER_CLUTCH_LINEAR_BEARING_OD + 0.20;
CENTER_CLUTCH_LINEAR_BEARING_SEAT_RADIAL_CLEARANCE =
    (CENTER_CLUTCH_LINEAR_BEARING_SEAT_D
        - CENTER_CLUTCH_LINEAR_BEARING_OD) / 2;
// Keep the fixed LM3UU/seat just below the male rotor. The 0.40 mm datum is
// the nominal rotating clearance from the male rotor lower face to the solid
// bar upper face; it removes the old 2.00 mm dead space without making the
// printed gear and seat a rubbing pair.
CENTER_CLUTCH_LINEAR_BEARING_INPUT_ROTOR_CLEARANCE = 0.40;
CENTER_CLUTCH_LINEAR_BEARING_CENTER_Y_OFFSET =
    -CENTER_CLUTCH_LINEAR_BEARING_INPUT_ROTOR_CLEARANCE
        - CENTER_CLUTCH_LINEAR_BEARING_L / 2;
CENTER_CLUTCH_LINEAR_BEARING_BLOCK_X = 18.00;
CENTER_CLUTCH_LINEAR_BEARING_BLOCK_Y = CENTER_CLUTCH_LINEAR_BEARING_L;
CENTER_CLUTCH_LINEAR_BEARING_BLOCK_Z_MARGIN = 1.00;
CENTER_CLUTCH_LINEAR_BEARING_BLOCK_Z_LENGTH =
    CENTER_CLUTCH_PLATE_REAR_Z
        - (CENTER_GT2_Z
            - CENTER_CLUTCH_LINEAR_BEARING_OD / 2
            - CENTER_CLUTCH_LINEAR_BEARING_BLOCK_Z_MARGIN);
// A small overlap into the plate makes the seat one watertight printed solid
// instead of two coincident-face solids. It is not an extra external boss.
CENTER_CLUTCH_LINEAR_BEARING_BLOCK_Z_OVERLAP = 0.20;
// Kept as zero-valued contract fields to make the absence of holder fasteners
// machine-checkable. Only the plate itself has its four partition M3 holes.
CENTER_CLUTCH_LINEAR_BEARING_BLOCK_MOUNT_X_OFFSET = 0.00;
CENTER_CLUTCH_LINEAR_BEARING_BLOCK_MOUNT_Y_OFFSET = 0.00;
CENTER_CLUTCH_LINEAR_BEARING_BLOCK_MOUNT_D = 0.00;
CENTER_CLUTCH_LINEAR_BEARING_BLOCK_MOUNT_COUNT = 0;
CENTER_CLUTCH_LINEAR_BEARING_MOVES_WITH_INPUT = false;

// LM3UU visual/reference geometry.  The purchased envelope is exactly
// Ø7×10 with a Ø3 bore; the sleeve/balls are for the browser and do not become
// a printed bearing claim.
CENTER_CLUTCH_LINEAR_BEARING_BODY_L = 8.80;
CENTER_CLUTCH_LINEAR_BEARING_SEAL_L = 0.60;
CENTER_CLUTCH_LINEAR_BEARING_BALL_D = 0.72;
CENTER_CLUTCH_LINEAR_BEARING_BALL_PITCH_R = 2.15;
CENTER_CLUTCH_LINEAR_BEARING_BALL_ROWS = [-3.30, -1.10, 1.10, 3.30];
CENTER_CLUTCH_LINEAR_BEARING_BALLS_PER_ROW = 8;
CENTER_CLUTCH_LINEAR_BEARING_CUTAWAY_DEPTH =
    CENTER_CLUTCH_LINEAR_BEARING_OD / 2
        - CENTER_CLUTCH_LINEAR_BEARING_ID / 2 - 0.08;

// The compact seat keeps its lower edge as the engaged contact datum. The
// sleeve therefore moves up with the shortened seat instead of leaving an
// unused axial gap below the LM3UU.
CENTER_CLUTCH_INPUT_SLEEVE_TOP_OFFSET =
    CENTER_CLUTCH_LINEAR_BEARING_CENTER_Y_OFFSET
        - CENTER_CLUTCH_LINEAR_BEARING_BLOCK_Y / 2
        - GT2_CLUTCH_ENGAGE_STROKE_MM;

// Moving input shaft.  Relative Y is measured from the male gear underside:
// upper D enters the male blind socket, the Ø3 round section is the only
// sliding journal, and the lower D enters the sleeve's upper D socket.
CENTER_CLUTCH_INPUT_SHAFT_UPPER_D_START = -GT2_INPUT_SHAFT_UPPER_D_EXTERNAL;
CENTER_CLUTCH_INPUT_SHAFT_UPPER_D_LENGTH = GT2_D_BORE_DEPTH
    + GT2_INPUT_SHAFT_UPPER_D_EXTERNAL
    + GT2_INPUT_SHAFT_TRANSITION_OVERLAP;
CENTER_CLUTCH_INPUT_SHAFT_LOWER_D_LENGTH = 3.60;
CENTER_CLUTCH_INPUT_SHAFT_LOWER_D_START =
    CENTER_CLUTCH_INPUT_SLEEVE_TOP_OFFSET
        - CENTER_CLUTCH_INPUT_SHAFT_LOWER_D_LENGTH
        + GT2_INPUT_SHAFT_TRANSITION_OVERLAP;
CENTER_CLUTCH_INPUT_SHAFT_ROUND_START =
    CENTER_CLUTCH_INPUT_SHAFT_LOWER_D_START
        - GT2_INPUT_SHAFT_TRANSITION_OVERLAP;
CENTER_CLUTCH_INPUT_SHAFT_ROUND_END =
    CENTER_CLUTCH_INPUT_SHAFT_UPPER_D_START
        + GT2_INPUT_SHAFT_TRANSITION_OVERLAP;
CENTER_CLUTCH_INPUT_SHAFT_ROUND_LENGTH =
    CENTER_CLUTCH_INPUT_SHAFT_ROUND_END
        - CENTER_CLUTCH_INPUT_SHAFT_ROUND_START;
CENTER_CLUTCH_INPUT_SHAFT_ROUND_D = GT2_INPUT_SHAFT_ROUND_D;
CENTER_CLUTCH_INPUT_SHAFT_TRANSITION_OVERLAP =
    GT2_INPUT_SHAFT_TRANSITION_OVERLAP;

// Printed sleeve: upper outer D profile, lower round boss, blind Ø5.20×5.20
// pocket for a purchased Ø5×5 magnet.  “M5” here is the magnet size; the
// printed round boss is Ø8 to leave a 1.40 mm radial wall around that pocket.
CENTER_CLUTCH_INPUT_SLEEVE_UPPER_D_HEIGHT = 4.20;
CENTER_CLUTCH_INPUT_SLEEVE_UPPER_D = 7.60;
CENTER_CLUTCH_INPUT_SLEEVE_UPPER_D_FLAT = 0.80;
CENTER_CLUTCH_INPUT_SLEEVE_LOWER_ROUND_OD = 8.00;
CENTER_CLUTCH_INPUT_SLEEVE_LOWER_ROUND_HEIGHT = 6.40;
CENTER_CLUTCH_INPUT_SLEEVE_D_SOCKET_DEPTH = 3.60;
CENTER_CLUTCH_INPUT_SLEEVE_D_SOCKET_CLEARANCE =
    GT2_INPUT_SLEEVE_D_BORE_CLEARANCE;
CENTER_CLUTCH_INPUT_SLEEVE_MAGNET_D = GT2_INPUT_SLEEVE_MAGNET_NOMINAL_D;
CENTER_CLUTCH_INPUT_SLEEVE_MAGNET_L = GT2_INPUT_SLEEVE_MAGNET_NOMINAL_L;
CENTER_CLUTCH_INPUT_SLEEVE_MAGNET_POCKET_D =
    GT2_INPUT_SLEEVE_MAGNET_POCKET_D;
CENTER_CLUTCH_INPUT_SLEEVE_MAGNET_POCKET_DEPTH =
    GT2_INPUT_SLEEVE_MAGNET_POCKET_DEPTH;
CENTER_CLUTCH_INPUT_SLEEVE_MAGNET_BOTTOM_CLEARANCE =
    CENTER_CLUTCH_INPUT_SLEEVE_LOWER_ROUND_HEIGHT
        - CENTER_CLUTCH_INPUT_SLEEVE_MAGNET_POCKET_DEPTH;

// Output shaft remains fixed in Y.  The lower D section keys into the
// mother-wheel blind D socket; it immediately becomes a Ø3 round journal for
// both 3×6×2 bearings.  The round end is deliberately only 0.80 mm above the
// integral bar, so there is no long unsupported neck.
CENTER_CLUTCH_SHAFT_OUTPUT_PROFILE = "D-round";
CENTER_CLUTCH_SHAFT_OUTPUT_D_START = -3.40;
CENTER_CLUTCH_SHAFT_OUTPUT_D_LENGTH = 3.60;
CENTER_CLUTCH_SHAFT_OUTPUT_ROUND_START = -0.20;
CENTER_CLUTCH_SHAFT_OUTPUT_ROUND_LENGTH = 7.80;
CENTER_CLUTCH_SHAFT_OUTPUT_ROUND_D = GT2_D_AXIS_D;
CENTER_CLUTCH_SHAFT_OUTPUT_TOP_PROTRUSION = 0.80;
CENTER_CLUTCH_SHAFT_OUTPUT_MOTHER_SOCKET_OVERLAP = GT2_D_BORE_DEPTH;
CENTER_CLUTCH_SHAFT_OUTPUT_START = CENTER_CLUTCH_SHAFT_OUTPUT_D_START;
CENTER_CLUTCH_SHAFT_OUTPUT_LENGTH =
    CENTER_CLUTCH_SHAFT_OUTPUT_ROUND_START
        + CENTER_CLUTCH_SHAFT_OUTPUT_ROUND_LENGTH
        - CENTER_CLUTCH_SHAFT_OUTPUT_START;

//#endregion

//#region 尺寸函数
function center_clutch_input_base_y(row) = center_gt2_male_base_y(row);

function center_clutch_output_base_y(row) = center_gt2_female_base_y(row);

function center_clutch_axis_x(col) = clutch_col_x(col);

function center_clutch_axis_z() = center_gt2_z();

function center_clutch_linear_bearing_z() = center_clutch_axis_z();

function center_clutch_linear_bearing_center_y(row) =
    center_clutch_input_base_y(row)
        + CENTER_CLUTCH_LINEAR_BEARING_CENTER_Y_OFFSET;

function center_clutch_linear_bearing_y0(row) =
    center_clutch_linear_bearing_center_y(row)
        - CENTER_CLUTCH_LINEAR_BEARING_BLOCK_Y / 2;

function center_clutch_linear_bearing_y1(row) =
    center_clutch_linear_bearing_center_y(row)
        + CENTER_CLUTCH_LINEAR_BEARING_BLOCK_Y / 2;

function center_clutch_input_sleeve_top_y(row) =
    center_clutch_input_base_y(row)
        + CENTER_CLUTCH_INPUT_SLEEVE_TOP_OFFSET;

function center_clutch_input_sleeve_bottom_y(row) =
    center_clutch_input_sleeve_top_y(row)
        - CENTER_CLUTCH_INPUT_SLEEVE_UPPER_D_HEIGHT
        - CENTER_CLUTCH_INPUT_SLEEVE_LOWER_ROUND_HEIGHT;

function center_clutch_input_sleeve_magnet_top_y(row) =
    center_clutch_input_sleeve_bottom_y(row)
        + CENTER_CLUTCH_INPUT_SLEEVE_MAGNET_POCKET_DEPTH;

function center_clutch_output_bearing_y(row, index) =
    center_clutch_output_base_y(row)
        + CENTER_CLUTCH_BEARING_CENTER_OFFSET
        + index * CENTER_CLUTCH_BEARING_PAIR_SPACING;

function center_clutch_output_bearing_bar_y0(row) =
    center_clutch_output_base_y(row)
        + CENTER_CLUTCH_BEARING_BLOCK_Y0_OFFSET;

function center_clutch_output_bearing_bar_y1(row) =
    center_clutch_output_bearing_bar_y0(row)
        + CENTER_CLUTCH_BEARING_BLOCK_Y;

function center_clutch_output_bearing_bar_z0() =
    center_clutch_axis_z()
        - CENTER_CLUTCH_BEARING_OD / 2
        - CENTER_CLUTCH_BEARING_BLOCK_Z_MARGIN;

function center_clutch_output_bearing_bar_z1() =
    CENTER_CLUTCH_PLATE_REAR_Z
        + CENTER_CLUTCH_BEARING_BLOCK_Z_OVERLAP;

function center_clutch_output_bearing_bar_z_length() =
    center_clutch_output_bearing_bar_z1()
        - center_clutch_output_bearing_bar_z0();

function center_clutch_chain_relief_z0() =
    SNAKE_CHAIN_CENTER_Z
        - SNAKE_CHAIN_HALF_DEPTH
        - CENTER_CLUTCH_CHAIN_RELIEF_AXIAL_CLEARANCE;

function center_clutch_chain_relief_z1() =
    SNAKE_CHAIN_CENTER_Z
        + SNAKE_CHAIN_HALF_DEPTH
        + CENTER_CLUTCH_CHAIN_RELIEF_AXIAL_CLEARANCE;

function center_clutch_chain_relief_z_length() =
    center_clutch_chain_relief_z1()
        - center_clutch_chain_relief_z0();

function center_clutch_output_bearing_bar_center_y(row) =
    (center_clutch_output_bearing_bar_y0(row)
        + center_clutch_output_bearing_bar_y1(row)) / 2;

function center_clutch_chain_relief_radius() =
    SNAKE_CHAIN_GUIDE_OUTER_R_MM
        + CENTER_CLUTCH_CHAIN_RELIEF_RADIAL_CLEARANCE;

// Treat the removed chain window as a sculpting brush rather than a hard-coded
// added block.  The three force elements are explicit and traceable:
//   point     = the generated relief cylinder centroid (the hit wheel pose),
//   direction = from that relief toward the opposite solid host face, and
//   magnitude = the requested emboss depth scaled by the brush strength.
// The radius and Z span are likewise taken from the same relief envelope, so a
// future chain/guide change reshapes the bulge instead of leaving a stale lug.
function center_clutch_chain_emboss_force_magnitude() =
    CENTER_CLUTCH_CHAIN_EMBOSS_DEPTH
        * CENTER_CLUTCH_CHAIN_EMBOSS_FORCE_MAGNITUDE_SCALE;

function center_clutch_chain_emboss_brush_radius() =
    center_clutch_chain_relief_radius()
        * CENTER_CLUTCH_CHAIN_EMBOSS_BRUSH_RADIUS_SCALE;

function center_clutch_chain_emboss_brush_half_z() =
    center_clutch_chain_relief_z_length() / 2
        * CENTER_CLUTCH_CHAIN_EMBOSS_BRUSH_AXIAL_SCALE
        + CENTER_CLUTCH_CHAIN_EMBOSS_Z_MARGIN;

// WHEEL_POSES 的第 0 项是唯一的 12T 动力轮；其余九项才是网页中显示为
// 绿色的 8T 固定导向轮。这个过滤器同时被安装座、链条碰撞和输出固定条
// 让位使用，避免把蓝色主动轮误切成绿色轴承座。
function center_clutch_chain_idler_wheel_poses() = [
    for (i = [1:len(WHEEL_POSES) - 1]) WHEEL_POSES[i]
];

function center_clutch_chain_idler_boss_rear_z() =
    SNAKE_CHAIN_CENTER_Z
        + SNAKE_CHAIN_HALF_DEPTH
        + CENTER_CLUTCH_CHAIN_IDLER_BOSS_AXIAL_CLEARANCE;

function center_clutch_chain_idler_row_host(wheel) =
    let(
        matches = [
            for (row = [0:N_ROW - 1])
                if (
                    wheel[0] >= center_clutch_row_plate_x0()
                    && wheel[0] <= center_clutch_row_plate_x1()
                    && wheel[1] >= center_clutch_plate_y0(row)
                    && wheel[1] <= center_clutch_plate_y1(row)
                ) row
        ]
    )
        len(matches) == 0 ? -1 : matches[0];

function center_clutch_chain_idler_partition_count() =
    len([
        for (wheel = center_clutch_chain_idler_wheel_poses())
            if (center_clutch_chain_idler_row_host(wheel) < 0) wheel
    ]);

function center_clutch_chain_idler_row_count() =
    len([
        for (wheel = center_clutch_chain_idler_wheel_poses())
            if (center_clutch_chain_idler_row_host(wheel) >= 0) wheel
    ]);

function center_clutch_chain_emboss_smoothstep(u) =
    u * u * (3 - 2 * u);

function center_clutch_chain_emboss_profile_s(u, root_s, outer_s) =
    root_s + (outer_s - root_s) * u;

function center_clutch_chain_emboss_support_half_width(nx, ny) =
    // The support distance is measured along the cheek normal.  X-normal
    // cheeks meet the X end face of the bar (14 mm span); Y-normal cheeks
    // meet the Y end face (6.4 mm span).  Keeping this mapping explicit is
    // important: using the tangent dimension here creates a floating narrow
    // neck under an otherwise broad cheek.
    abs(nx) * CENTER_CLUTCH_BEARING_BLOCK_X / 2
        + abs(ny) * CENTER_CLUTCH_BEARING_BLOCK_Y / 2;

function center_clutch_chain_emboss_support_edge_span(nx, ny) =
    // This is the span along the bar face, perpendicular to the normal.
    abs(nx) >= abs(ny)
        ? CENTER_CLUTCH_BEARING_BLOCK_Y
        : CENTER_CLUTCH_BEARING_BLOCK_X;

function center_clutch_chain_emboss_root_width(nx, ny) =
    let(
        projected_width = 2 * (
            center_clutch_chain_emboss_support_half_width(nx, ny)
                + CENTER_CLUTCH_CHAIN_EMBOSS_ROOT_SUPPORT_MARGIN
        ),
        edge_width = center_clutch_chain_emboss_support_edge_span(nx, ny)
            + 2 * CENTER_CLUTCH_CHAIN_EMBOSS_ROOT_SUPPORT_MARGIN
    )
        max(
            CENTER_CLUTCH_CHAIN_EMBOSS_ROOT_WIDTH,
            min(projected_width, edge_width)
        );

function center_clutch_chain_emboss_profile_half_width(
    u,
    root_face_width,
    root_width,
    force_depth = CENTER_CLUTCH_CHAIN_EMBOSS_DEPTH
) =
    let(
        // The bar face is at u = overlap / total path.  The inner blend
        // finishes exactly there, and the outer taper starts from the same
        // width.  Smoothstep has zero slope at both ends, so no shoulder is
        // introduced where the cheek emerges from the solid bar.
        total_s = CENTER_CLUTCH_CHAIN_EMBOSS_ROOT_OVERLAP
            + force_depth
            - CENTER_CLUTCH_CHAIN_EMBOSS_OUTER_RADIUS,
        bar_face_u = CENTER_CLUTCH_CHAIN_EMBOSS_ROOT_OVERLAP / total_s,
        root_face_half = root_face_width / 2,
        root_half = root_width / 2,
        outer_half = CENTER_CLUTCH_CHAIN_EMBOSS_OUTER_WIDTH / 2,
        inside_u = min(1, u / bar_face_u),
        outside_u = max(
            0,
            min(1, (u - bar_face_u) / (1 - bar_face_u))
        ),
        inside_eased = center_clutch_chain_emboss_smoothstep(inside_u),
        outside_eased = center_clutch_chain_emboss_smoothstep(outside_u),
        brush_falloff = pow(
            max(0, sin(180 * outside_u)),
            CENTER_CLUTCH_CHAIN_EMBOSS_BRUSH_FALLOFF
        ),
        brush_bulge = center_clutch_chain_emboss_brush_radius()
            * CENTER_CLUTCH_CHAIN_EMBOSS_RADIAL_BULGE
            * brush_falloff,
        half_width = u <= bar_face_u
            ? root_face_half + (root_half - root_face_half) * inside_eased
            : root_half + (outer_half - root_half) * outside_eased,
        radial_bulge = u > bar_face_u ? brush_bulge : 0
    )
        half_width + radial_bulge;

function center_clutch_chain_emboss_profile_half_z(
    u,
    base_half_z,
    force_depth = CENTER_CLUTCH_CHAIN_EMBOSS_DEPTH
) =
    let(
        total_s = CENTER_CLUTCH_CHAIN_EMBOSS_ROOT_OVERLAP
            + force_depth
            - CENTER_CLUTCH_CHAIN_EMBOSS_OUTER_RADIUS,
        bar_face_u = CENTER_CLUTCH_CHAIN_EMBOSS_ROOT_OVERLAP / total_s,
        inside_u = min(1, u / bar_face_u),
        inside_eased = center_clutch_chain_emboss_smoothstep(inside_u),
        outside_u = max(
            0,
            min(1, (u - bar_face_u) / (1 - bar_face_u))
        ),
        brush_falloff = pow(
            max(0, sin(180 * outside_u)),
            CENTER_CLUTCH_CHAIN_EMBOSS_BRUSH_FALLOFF
        ),
        brush_z_bulge = center_clutch_chain_emboss_brush_radius()
            * 0.08
            * brush_falloff
    )
        base_half_z + (
            u <= bar_face_u
                ? CENTER_CLUTCH_CHAIN_EMBOSS_ROOT_FLARE * (1 - inside_eased)
                : brush_z_bulge
        );

function center_clutch_chain_emboss_profile_half_s(
    u,
    force_depth = CENTER_CLUTCH_CHAIN_EMBOSS_DEPTH
) =
    let(
        total_s = CENTER_CLUTCH_CHAIN_EMBOSS_ROOT_OVERLAP
            + force_depth
            - CENTER_CLUTCH_CHAIN_EMBOSS_OUTER_RADIUS,
        bar_face_u = CENTER_CLUTCH_CHAIN_EMBOSS_ROOT_OVERLAP / total_s,
        outside_u = max(
            0,
            min(1, (u - bar_face_u) / (1 - bar_face_u))
        ),
        outside_eased = center_clutch_chain_emboss_smoothstep(outside_u),
        root_half_s = CENTER_CLUTCH_CHAIN_EMBOSS_ROOT_RADIUS
            + CENTER_CLUTCH_CHAIN_EMBOSS_ROOT_FLARE,
        outer_half_s = CENTER_CLUTCH_CHAIN_EMBOSS_OUTER_RADIUS
    )
        u <= bar_face_u
            ? root_half_s
            : root_half_s
                + (outer_half_s - root_half_s) * outside_eased;

module center_clutch_chain_emboss_root_section(
    cx,
    cy,
    nx,
    ny,
    s,
    half_s,
    half_t,
    half_z,
    z_center
) {
    // An ellipsoidal section keeps the upper/lower and left/right root
    // surfaces continuous.  Adjacent sections are hulled in small steps,
    // giving a printable radial transition rather than a pair of rectangles
    // joined at a single line.
    translate([
        cx + nx * s,
        cy + ny * s,
        z_center
    ])
        rotate([0, 0, atan2(ny, nx)])
            scale([half_s, half_t, half_z])
                sphere(r = 1, $fn = 48);
}

function center_clutch_chain_wheel_hits_bar(col, row, wheel) =
    let(
        x0 = center_clutch_axis_x(col)
            - CENTER_CLUTCH_BEARING_BLOCK_X / 2,
        x1 = center_clutch_axis_x(col)
            + CENTER_CLUTCH_BEARING_BLOCK_X / 2,
        y0 = center_clutch_output_bearing_bar_y0(row),
        y1 = center_clutch_output_bearing_bar_y1(row),
        dx = max(max(x0 - wheel[0], 0), wheel[0] - x1),
        dy = max(max(y0 - wheel[1], 0), wheel[1] - y1)
    )
        sqrt(dx * dx + dy * dy)
            <= center_clutch_chain_relief_radius() + EPS;

function center_clutch_chain_emboss_normal_x(col, row, wheel) =
    let(
        dx = center_clutch_axis_x(col) - wheel[0],
        dy = center_clutch_output_bearing_bar_center_y(row) - wheel[1]
    )
        abs(dx) >= abs(dy) ? (dx >= 0 ? 1 : -1) : 0;

function center_clutch_chain_emboss_normal_y(col, row, wheel) =
    let(
        dx = center_clutch_axis_x(col) - wheel[0],
        dy = center_clutch_output_bearing_bar_center_y(row) - wheel[1]
    )
        abs(dx) >= abs(dy) ? 0 : (dy >= 0 ? 1 : -1);

module center_clutch_chain_emboss_cheek(col, row, wheel) {
    // The radiused cheek is the formed-looking reinforcement on the opposite
    // side of the chain relief. It is fused into the same carrier as the blind
    // idler Boss; it is not a second STL or a viewer-only overlay.
    if (center_clutch_chain_wheel_hits_bar(col, row, wheel)) {
        cx = center_clutch_axis_x(col);
        cy = center_clutch_output_bearing_bar_center_y(row);
        nx = center_clutch_chain_emboss_normal_x(col, row, wheel);
        ny = center_clutch_chain_emboss_normal_y(col, row, wheel);
        support_distance = center_clutch_chain_emboss_support_half_width(nx, ny);
        // The wheel pose is the brush force point. nx/ny is the force direction
        // from the removed relief toward the opposite solid host face, and the
        // depth below is the force magnitude. Keeping these values local makes
        // the sculpt-like deformation follow each generated wheel independently.
        force_point = [wheel[0], wheel[1], SNAKE_CHAIN_CENTER_Z];
        force_direction = [nx, ny, 0];
        force_depth = center_clutch_chain_emboss_force_magnitude();
        root_width = center_clutch_chain_emboss_root_width(nx, ny);
        support_edge_span = center_clutch_chain_emboss_support_edge_span(nx, ny);
        // Match the real bar-face span at the load root.  The cheek then
        // tapers continuously toward the chain-side nose; it does not start
        // with a narrow neck or a wider-than-supported mushroom head.
        // Keep the visible root just inside the actual support face.  This
        // avoids a coplanar strip along the bar's top/bottom edges while the
        // cheek still overlaps deeply in the normal direction; the result is
        // a fused, printable root rather than an edge-to-edge attachment.
        root_face_width = min(root_width, support_edge_span - 2 * EPS);
        profile_root_width = root_face_width;
        root_face_s = support_distance
            - CENTER_CLUTCH_CHAIN_EMBOSS_ROOT_OVERLAP;
        outer_center_s = support_distance
            + force_depth
            - CENTER_CLUTCH_CHAIN_EMBOSS_OUTER_RADIUS;
        brush_half_z = center_clutch_chain_emboss_brush_half_z();
        z0 = force_point[2] - brush_half_z;
        z1 = force_point[2] + brush_half_z;
        // Use one continuous family of overlapping convex-hull brush dabs,
        // fused into the bar before the chain window is cut. The relief
        // supplies the force point, radius and axial span; the generated
        // opposite-face normal supplies the push axis. The broad root is
        // buried in the bar so the visible result is one material volume,
        // not a colored add-on or a narrow-neck mushroom.
        hull() {
            for (i = [0:CENTER_CLUTCH_CHAIN_EMBOSS_PROFILE_STEPS - 1]) {
                    u0 = i / CENTER_CLUTCH_CHAIN_EMBOSS_PROFILE_STEPS;
                    u1 = (i + 1) / CENTER_CLUTCH_CHAIN_EMBOSS_PROFILE_STEPS;
                    s0 = center_clutch_chain_emboss_profile_s(
                        u0, root_face_s, outer_center_s
                    );
                    s1 = center_clutch_chain_emboss_profile_s(
                        u1, root_face_s, outer_center_s
                    );
                    t0 = center_clutch_chain_emboss_profile_half_width(
                        u0, root_face_width, profile_root_width, force_depth
                    );
                    t1 = center_clutch_chain_emboss_profile_half_width(
                        u1, root_face_width, profile_root_width, force_depth
                    );
                    // Keep the longitudinal section radius constant across
                    // adjacent hulls.  The width and Z profiles carry the
                    // root fillet; a changing hull radius would make the
                    // shared section edge numerically overlap itself in the
                    // Manifold STL triangulator.
                    half_s0 = center_clutch_chain_emboss_profile_half_s(
                        u0, force_depth
                    );
                    half_s1 = center_clutch_chain_emboss_profile_half_s(
                        u1, force_depth
                    );
                    half_z0 = center_clutch_chain_emboss_profile_half_z(
                        u0, (z1 - z0) / 2, force_depth
                    );
                    half_z1 = center_clutch_chain_emboss_profile_half_z(
                        u1, (z1 - z0) / 2, force_depth
                    );
                    // A single hull over the complete brush path is
                    // intentional. Pairwise hulls leave visible lobe seams;
                    // the global hull makes the material read as one
                    // continuous inflated mound, like a clay/Inflate stroke.
                    center_clutch_chain_emboss_root_section(
                        cx, cy, nx, ny,
                        s0,
                        half_s0,
                        t0,
                        half_z0,
                        (z0 + z1) / 2
                    );
                    center_clutch_chain_emboss_root_section(
                        cx, cy, nx, ny,
                        s1,
                        half_s1,
                        t1,
                        half_z1,
                        (z0 + z1) / 2
                    );
                }
            }
        }
}

module center_clutch_chain_emboss_cheeks(col, row) {
    if (col == 0 || col == N_COL - 1)
        for (wheel = center_clutch_chain_idler_wheel_poses())
            center_clutch_chain_emboss_cheek(col, row, wheel);
}

module center_clutch_chain_axial_window(col) {
    // Only the two outer columns can meet the side return guides. The window
    // is still driven by every generated wheel pose: non-intersecting poses
    // subtract nothing, while a future route change automatically updates the
    // affected station without a second hand-authored notch.
    if (col == 0 || col == N_COL - 1)
        for (wheel = center_clutch_chain_idler_wheel_poses())
            translate([
                wheel[0],
                wheel[1],
                center_clutch_chain_relief_z0()
            ])
                cylinder(
                    d = 2 * (
                        SNAKE_CHAIN_GUIDE_OUTER_R_MM
                            + CENTER_CLUTCH_CHAIN_RELIEF_RADIAL_CLEARANCE
                    ),
                    h = center_clutch_chain_relief_z_length(),
                    $fn = 64
                );
}

function center_clutch_plate_y0(row) =
    min(
        center_clutch_linear_bearing_y0(row) - 2.00,
        center_clutch_output_base_y(row) - 4.00
    );

function center_clutch_plate_y1(row) =
    center_clutch_output_base_y(row) + 10.00;

function center_clutch_plate_h(row) =
    center_clutch_plate_y1(row) - center_clutch_plate_y0(row);

// The rear cavity is one continuous service volume.  The removable printed
// carrier is therefore one horizontal strip per drawer row, with each station
// retaining its own four-hole datum and its own integral LM3UU/output-bearing
// supports.  This avoids fifteen disconnected plates while keeping every
// station generated from this one source module.
function center_clutch_row_plate_x0() =
    center_clutch_axis_x(0) - CENTER_CLUTCH_PLATE_W / 2;

function center_clutch_row_plate_x1() =
    center_clutch_axis_x(N_COL - 1) + CENTER_CLUTCH_PLATE_W / 2;

function center_clutch_row_plate_length() =
    center_clutch_row_plate_x1() - center_clutch_row_plate_x0();

function center_clutch_row_plate_left_clearance() =
    center_clutch_row_plate_x0() - WORLD_GRID_ORIGIN_X;

function center_clutch_row_plate_right_clearance() =
    WORLD_GRID_ORIGIN_X + WORLD_GRID_W - center_clutch_row_plate_x1();

// Compatibility datums for old inspection callers.  They now describe the
// fixed LM3UU block, not a retired guide rail or moving carriage.
function center_clutch_rail_y0(row) = center_clutch_linear_bearing_y0(row);

function center_clutch_rail_y1(row) = center_clutch_linear_bearing_y1(row);

function center_clutch_guide_rod_y1(row) = center_clutch_linear_bearing_y1(row);

function center_clutch_rail_length(row) =
    center_clutch_rail_y1(row) - center_clutch_rail_y0(row);

function center_clutch_open_stop_y(row) =
    center_clutch_input_base_y(row)
        + CENTER_CLUTCH_INPUT_SLEEVE_BOTTOM_OFFSET;

function center_clutch_engaged_stop_y(row) =
    center_clutch_open_stop_y(row) + GT2_CLUTCH_ENGAGE_STROKE_MM;

function center_clutch_carriage_shoe_y0(row) =
    center_clutch_open_stop_y(row);

function center_clutch_carriage_shoe_y1(row) =
    center_clutch_open_stop_y(row);

function center_clutch_engaged_carriage_shoe_y0(row) =
    center_clutch_carriage_shoe_y0(row)
        + GT2_CLUTCH_ENGAGE_STROKE_MM;

function center_clutch_engaged_carriage_shoe_y1(row) =
    center_clutch_carriage_shoe_y1(row)
        + GT2_CLUTCH_ENGAGE_STROKE_MM;
//#endregion

//#region 私有成员：轴承、D 型截面与安装孔
module center_clutch_bearing_reference_y(x, y, z) {
    // Purchased 3×6×2 bearing; reference geometry only.
    translate([x, y, z])
        rotate([90, 0, 0])
            difference() {
                cylinder(
                    d = CENTER_CLUTCH_BEARING_OD,
                    h = CENTER_CLUTCH_BEARING_W,
                    center = true,
                    $fn = 64
                );
                cylinder(
                    d = CENTER_CLUTCH_BEARING_ID,
                    h = CENTER_CLUTCH_BEARING_W + 2 * EPS,
                    center = true,
                    $fn = 48
                );
            }
}

module center_clutch_d_prism_y(
    x,
    y0,
    z,
    d,
    flat_depth,
    length,
    clearance = 0
) {
    translate([x, y0, z])
        rotate([-90, 0, 0])
            linear_extrude(height = length, convexity = 6)
                d_profile_2d(d, flat_depth, clearance);
}
//#endregion

//#region 公开 API：机构板、输出轴承固定条与固定直线轴承块
module center_clutch_plate_belt_passage(col, row) {
    x = center_clutch_axis_x(col);
    y = center_gt2_belt_y(row);
    // The active belt crosses the plate on its two straight radial strips;
    // do not remove the solid bridge between them.
    center_gt2_belt_straight_passage_slots(
        x,
        y,
        CENTER_CLUTCH_PLATE_REAR_Z - EPS,
        CENTER_CLUTCH_PLATE_T + 2 * EPS,
        CENTER_CLUTCH_PLATE_BELT_PASSAGE_RADIAL_CLEAR,
        CENTER_CLUTCH_PLATE_BELT_PASSAGE_AXIAL_CLEAR
    );
}

module center_clutch_linear_bearing_block_y(col, row) {
    x = center_clutch_axis_x(col);
    y = center_clutch_linear_bearing_center_y(row);
    z0 = CENTER_CLUTCH_PLATE_REAR_Z
        - CENTER_CLUTCH_LINEAR_BEARING_BLOCK_Z_LENGTH;
    difference() {
        // Compact bar: its Y thickness is exactly the LM3UU envelope, it
        // overlaps the rear of the main plate by 0.20 mm, and its outer end
        // surrounds the male-axis LM3UU hole in Z.
        translate([
            x - CENTER_CLUTCH_LINEAR_BEARING_BLOCK_X / 2,
            y - CENTER_CLUTCH_LINEAR_BEARING_BLOCK_Y / 2,
            z0
        ])
            cube([
                CENTER_CLUTCH_LINEAR_BEARING_BLOCK_X,
                CENTER_CLUTCH_LINEAR_BEARING_BLOCK_Y,
                CENTER_CLUTCH_LINEAR_BEARING_BLOCK_Z_LENGTH
                    + CENTER_CLUTCH_LINEAR_BEARING_BLOCK_Z_OVERLAP
            ]);
        // One through Ø7.20 bearing hole along world Y. The purchased LM3UU
        // is press-fit from either side in this solid bar; no holder mounting
        // holes, round printed holder, cap or retainer is used.
        cylinder_y(
            x,
            y - CENTER_CLUTCH_LINEAR_BEARING_BLOCK_Y / 2 - EPS,
            center_clutch_axis_z(),
            CENTER_CLUTCH_LINEAR_BEARING_SEAT_D,
            CENTER_CLUTCH_LINEAR_BEARING_BLOCK_Y + 2 * EPS
        );
    }
}

module center_clutch_output_bearing_bar_y(col, row) {
    x = center_clutch_axis_x(col);
    y0 = center_clutch_output_bearing_bar_y0(row);
    y1 = center_clutch_output_bearing_bar_y1(row);
    z0 = center_clutch_output_bearing_bar_z0();
    difference() {
        // One solid rectangular bar runs directly from the two bearing seats
        // back into the removable mechanism plate.  It has no separate arms,
        // collars, cap or holder mounting holes.
        // Resolve the cube-to-cheek union before cutting the chain and bearing
        // windows.  This keeps the radiused opposite-side reinforcement a
        // single solid at the outer row, where the generated guide pose sits
        // within a fraction of a millimetre of the bar's Y edge.
        render(convexity = 12)
            union() {
                translate([
                    x - CENTER_CLUTCH_BEARING_BLOCK_X / 2,
                    y0,
                    z0
                ])
                    cube([
                        CENTER_CLUTCH_BEARING_BLOCK_X,
                        CENTER_CLUTCH_BEARING_BLOCK_Y,
                        center_clutch_output_bearing_bar_z_length()
                    ]);
                // The offset cheek is generated from the same relief envelope as
                // the chain passage, then fused into the bar before all bearing
                // pockets are cut. It is not a second printed component.
                center_clutch_chain_emboss_cheeks(col, row);
            }
        // Let the side-return chain and its 8T guide pass through a bounded
        // axial window.  This is a local relief in the bar's +Z-facing chain
        // band, not a full-depth notch: both 3×6×2 bearing seats remain in
        // the solid load path around the mother shaft.
        center_clutch_chain_axial_window(col);
        // Lower bearing is pressed from the mother-wheel side; upper bearing
        // is pressed from the opposite end. Each pocket leaves a 0.60 mm
        // internal shoulder and the middle web keeps the two bearings stable.
        cylinder_y(
            x,
            y0 - EPS,
            center_clutch_axis_z(),
            CENTER_CLUTCH_BEARING_SEAT_D,
            CENTER_CLUTCH_BEARING_SEAT_DEPTH + EPS
        );
        cylinder_y(
            x,
            y1 - CENTER_CLUTCH_BEARING_SEAT_DEPTH - EPS,
            center_clutch_axis_z(),
            CENTER_CLUTCH_BEARING_SEAT_D,
            CENTER_CLUTCH_BEARING_SEAT_DEPTH + EPS
        );
    }
}

module center_clutch_station_fastener_holes(x, y0, h) {
    // Keep the four plate-to-partition clearance holes as the final CSG cut
    // on both a single station plate and a continuous row strip.  The outer
    // green-idler Boss roots may approach a lower corner hole, but they must
    // never refill the hole just because their support is fused afterwards.
    for (sx = [-1, 1], sy = [-1, 1])
        translate([
            x + sx * CENTER_CLUTCH_PLATE_MOUNT_X_OFFSET,
            y0 + (sy < 0
                ? CENTER_CLUTCH_PLATE_MOUNT_Y_OFFSET
                : h - CENTER_CLUTCH_PLATE_MOUNT_Y_OFFSET),
            CENTER_CLUTCH_PLATE_REAR_Z - EPS
        ])
            cylinder(
                d = CENTER_CLUTCH_M3_CLEAR_D,
                h = CENTER_CLUTCH_PLATE_T + 2 * EPS,
                $fn = 40
            );
}

module center_clutch_mechanism_plate(col, row) {
    x = center_clutch_axis_x(col);
    y0 = center_clutch_plate_y0(row);
    h = center_clutch_plate_h(row);
    difference() {
        union() {
            translate([
                x - CENTER_CLUTCH_PLATE_W / 2,
                y0,
                CENTER_CLUTCH_PLATE_REAR_Z
            ])
                cube([
                    CENTER_CLUTCH_PLATE_W,
                    h,
                    CENTER_CLUTCH_PLATE_T
                ]);
            // The LM3UU seat is part of this same printed mechanism plate.
            // Only the bearing bore is subtracted from the otherwise solid
            // support; there is no separate holder or holder fastener set.
            center_clutch_linear_bearing_block_y(col, row);
            // The output bearing bar is also part of the same printed plate.
            // Its only subtractions are the two Ø6.10 bearing pockets.
            center_clutch_output_bearing_bar_y(col, row);
        }
        // Four plate-to-partition self-tapping screw clearance holes.
        center_clutch_station_fastener_holes(x, y0, h);
        center_clutch_plate_belt_passage(col, row);
    }
}

module center_clutch_mechanism_row_plate(row) {
    x0 = center_clutch_row_plate_x0();
    y0 = center_clutch_plate_y0(row);
    h = center_clutch_plate_h(row);
    union() {
        render(convexity = 12)
            difference() {
                union() {
                    // One continuous rear-cavity carrier strip for this drawer row.
                    // Its station supports are fused into the same printed solid.
                    translate([x0, y0, CENTER_CLUTCH_PLATE_REAR_Z])
                        cube([
                            center_clutch_row_plate_length(),
                            h,
                            CENTER_CLUTCH_PLATE_T
                        ]);
                    for (col = [0:N_COL - 1]) {
                        center_clutch_linear_bearing_block_y(col, row);
                        center_clutch_output_bearing_bar_y(col, row);
                    }
                    // The green idler Bosses are part of the same row-strip solid.
                    // Fuse them before the station mounting holes and belt slots
                    // are cut, so a nearby root reinforces the plate without
                    // blocking the M3 screw path.
                    for (wheel = center_clutch_chain_idler_wheel_poses())
                        if (center_clutch_chain_idler_row_host(wheel) == row)
                            center_clutch_chain_idler_mount_boss(
                                wheel[0],
                                wheel[1],
                                CENTER_CLUTCH_PLATE_REAR_Z
                            );
                }
                // Keep the repeated cell datum at every station.  These holes line up
                // with the four blind-pilot bosses already fused to the partition.
                for (col = [0:N_COL - 1]) {
                    x = center_clutch_axis_x(col);
                    center_clutch_station_fastener_holes(x, y0, h);
                    center_clutch_plate_belt_passage(col, row);
                }
            }
    }
}

module center_clutch_mechanism_row_plates() {
    // The three carrier strips are disjoint physical shells in one published
    // STL. Keep them as separate children so Manifold does not invent a
    // coincident seam while merging the repeated X/Z profiles; each row is
    // already rendered and validated as its own closed solid.
    for (row = [0:N_ROW - 1])
        center_clutch_mechanism_row_plate(row);
}

// 一体化的导向轮轴承座。根部用 11 mm 圆角/锥形承力台，后端缩到 Ø8
// 轴承轴座，避免“细腿+大头”悬空结构；盲孔从 -Z 后仓侧开口，孔底不
// 穿入隔板或离合行板。这个模块只在两个真实承载板里被引用，不产生第二
// 套独立 STL。
module center_clutch_chain_idler_mount_boss(x, y, host_rear_z) {
    rear_z = center_clutch_chain_idler_boss_rear_z();
    flare_t = CENTER_CLUTCH_CHAIN_IDLER_BOSS_ROOT_FLARE_T;
    flare_z = host_rear_z - flare_t;
    host_overlap = CENTER_CLUTCH_CHAIN_IDLER_BOSS_ROOT_OVERLAP;
    main_length = flare_z - rear_z;
    pilot_depth = min(
        CENTER_CLUTCH_CHAIN_IDLER_THREAD_PILOT_DEPTH,
        main_length + flare_t - 0.75
    );
    assert(main_length > 0.50,
        "green idler boss must reach from the board to the chain datum");
    assert(pilot_depth > 2.50,
        "green idler M3 blind pilot must retain useful thread engagement");
    difference() {
        union() {
            translate([x, y, rear_z])
                cylinder(
                    d = CENTER_CLUTCH_CHAIN_IDLER_BOSS_OD,
                    h = main_length,
                    $fn = 48
                );
            // The broad root is at the board side (+Z), so the bending load
            // flows into the plate instead of ending in a thin cylindrical leg.
            translate([x, y, flare_z])
                cylinder(
                    d1 = CENTER_CLUTCH_CHAIN_IDLER_BOSS_OD,
                    d2 = CENTER_CLUTCH_CHAIN_IDLER_BOSS_ROOT_OD,
                    h = flare_t + host_overlap,
                    $fn = 48
                );
        }
        // Ø2.4 is the same M3 self-tapping pilot datum already used by the
        // partition/clutch-board bosses. It opens at the rear end and leaves
        // at least 0.75 mm before the host board's rear face.
        translate([x, y, rear_z - EPS])
            cylinder(
                d = CENTER_CLUTCH_CHAIN_IDLER_THREAD_PILOT_D,
                h = pilot_depth + EPS,
                $fn = 40
            );
    }
}

module center_clutch_chain_idler_row_mounts(row) {
    for (wheel = center_clutch_chain_idler_wheel_poses())
        if (center_clutch_chain_idler_row_host(wheel) == row)
            center_clutch_chain_idler_mount_boss(
                wheel[0],
                wheel[1],
                CENTER_CLUTCH_PLATE_REAR_Z
            );
}

module center_clutch_chain_idler_partition_mounts() {
    for (wheel = center_clutch_chain_idler_wheel_poses())
        if (center_clutch_chain_idler_row_host(wheel) < 0)
            center_clutch_chain_idler_mount_boss(
                wheel[0],
                wheel[1],
                WORLD_PARTITION_BACK_Z
            );
}

// The bottom service opening runs just below the lowest green guide. Keep a
// broad board-side root around every partition-hosted axle. This is not a
// filled-through hole: it only prevents the service cut from slicing away the
// integral boss root and leaves the remaining opening continuous elsewhere.
module center_clutch_chain_idler_partition_keep_zones() {
    keep_d = CENTER_CLUTCH_CHAIN_IDLER_BOSS_ROOT_OD + 0.20;
    for (wheel = center_clutch_chain_idler_wheel_poses())
        if (center_clutch_chain_idler_row_host(wheel) < 0)
            translate([
                wheel[0] - keep_d / 2,
                wheel[1] - keep_d / 2,
                WORLD_PARTITION_BACK_Z - 2 * EPS
            ])
                cube([
                    keep_d,
                    keep_d,
                    WORLD_PARTITION_T + 4 * EPS
                ]);
}

module center_clutch_partition_mount_bosses(col, row) {
    x = center_clutch_axis_x(col);
    y0 = center_clutch_plate_y0(row);
    h = center_clutch_plate_h(row);
    // Every drawer cell receives the same four-corner pattern.  Each boss
    // starts at the partition rear face and projects in -Z.  Its blind pilot
    // opens at the boss rear end for the screw and leaves a 0.50 mm solid
    // bottom wall at the partition side.
    for (sx = [-1, 1], sy = [-1, 1])
        translate([
            x + sx * CENTER_CLUTCH_PLATE_MOUNT_X_OFFSET,
            y0 + (sy < 0
                ? CENTER_CLUTCH_PLATE_MOUNT_Y_OFFSET
                : h - CENTER_CLUTCH_PLATE_MOUNT_Y_OFFSET),
            WORLD_PARTITION_BACK_Z - CENTER_CLUTCH_PARTITION_BOSS_HEIGHT
        ])
            difference() {
                cylinder(
                    d = CENTER_CLUTCH_PARTITION_BOSS_OD,
                    h = CENTER_CLUTCH_PARTITION_BOSS_HEIGHT,
                    $fn = 48
                );
                translate([0, 0, -EPS])
                    cylinder(
                        d = CENTER_CLUTCH_PARTITION_SELF_TAP_PILOT_D,
                        h = CENTER_CLUTCH_PARTITION_SELF_TAP_PILOT_DEPTH
                            + EPS,
                        $fn = 40
                    );
            }
}

//#endregion

//#region 公开 API：公轮阶梯轴、圆套与采购件参考
module center_clutch_input_shaft(col, row, engaged = false) {
    x = center_clutch_axis_x(col);
    z = center_clutch_axis_z();
    base_y = center_clutch_input_base_y(row);
    shift = CENTER_CLUTCH_TRAVEL_MM;
    color(COLOR_SHAFT)
        union() {
            // Upper D: four millimetres outside the gear plus the full blind
            // socket depth, so the shaft is keyed/fixed to the male rotor.
            d_rod_y(
                x,
                base_y + CENTER_CLUTCH_INPUT_SHAFT_UPPER_D_START + shift,
                z,
                CENTER_CLUTCH_INPUT_SHAFT_UPPER_D_LENGTH
            );
            // Only this round section enters the LM3UU. It is a continuation
            // of the same shaft, not a second independent guide rod.
            cylinder_y(
                x,
                base_y + CENTER_CLUTCH_INPUT_SHAFT_ROUND_START + shift,
                z,
                CENTER_CLUTCH_INPUT_SHAFT_ROUND_D,
                CENTER_CLUTCH_INPUT_SHAFT_ROUND_LENGTH
            );
            // Lower D is the keyed drive into the sleeve's upper D socket.
            d_rod_y(
                x,
                base_y + CENTER_CLUTCH_INPUT_SHAFT_LOWER_D_START + shift,
                z,
                CENTER_CLUTCH_INPUT_SHAFT_LOWER_D_LENGTH
            );
        }
}

module center_clutch_input_sleeve(col, row, engaged = false) {
    x = center_clutch_axis_x(col);
    z = center_clutch_axis_z();
    top_y = center_clutch_input_sleeve_top_y(row)
        + CENTER_CLUTCH_TRAVEL_MM;
    upper_y0 = top_y - CENTER_CLUTCH_INPUT_SLEEVE_UPPER_D_HEIGHT;
    bottom_y = upper_y0 - CENTER_CLUTCH_INPUT_SLEEVE_LOWER_ROUND_HEIGHT;
    difference() {
        union() {
            center_clutch_d_prism_y(
                x,
                upper_y0 - EPS,
                z,
                CENTER_CLUTCH_INPUT_SLEEVE_UPPER_D,
                CENTER_CLUTCH_INPUT_SLEEVE_UPPER_D_FLAT,
                CENTER_CLUTCH_INPUT_SLEEVE_UPPER_D_HEIGHT + EPS
            );
            cylinder_y(
                x,
                bottom_y,
                z,
                CENTER_CLUTCH_INPUT_SLEEVE_LOWER_ROUND_OD,
                CENTER_CLUTCH_INPUT_SLEEVE_LOWER_ROUND_HEIGHT + EPS
            );
        }
        // Upper D socket opens toward the fixed shaft. The 0.16 mm radial
        // clearance is only a first-article FDM fit datum.
        center_clutch_d_prism_y(
            x,
            top_y - CENTER_CLUTCH_INPUT_SLEEVE_D_SOCKET_DEPTH - EPS,
            z,
            GT2_D_AXIS_D,
            GT2_D_AXIS_FLAT_DEPTH,
            CENTER_CLUTCH_INPUT_SLEEVE_D_SOCKET_DEPTH + EPS,
            CENTER_CLUTCH_INPUT_SLEEVE_D_SOCKET_CLEARANCE
        );
        // Blind bottom pocket for the Ø5×5 purchased magnet. The 1.20 mm
        // remaining sleeve material is a printed floor/retainer, not a spring.
        cylinder_y(
            x,
            bottom_y - EPS,
            z,
            CENTER_CLUTCH_INPUT_SLEEVE_MAGNET_POCKET_D,
            CENTER_CLUTCH_INPUT_SLEEVE_MAGNET_POCKET_DEPTH + EPS
        );
    }
}

module center_clutch_input_sleeve_magnet_reference(col, row, engaged = false) {
    x = center_clutch_axis_x(col);
    z = center_clutch_axis_z();
    magnet_y = center_clutch_input_sleeve_bottom_y(row)
        + 0.10
        + CENTER_CLUTCH_TRAVEL_MM;
    color("#5b6670")
        cylinder_y(
            x,
            magnet_y,
            z,
            CENTER_CLUTCH_INPUT_SLEEVE_MAGNET_D,
            CENTER_CLUTCH_INPUT_SLEEVE_MAGNET_L
        );
}

module center_clutch_output_shaft(col, row) {
    x = center_clutch_axis_x(col);
    z = center_clutch_axis_z();
    base_y = center_clutch_output_base_y(row);
    color(COLOR_SHAFT)
        union() {
            // Short D section only: it keys into the mother-wheel blind D
            // socket and stops before the first bearing.
            d_rod_y(
                x,
                base_y + CENTER_CLUTCH_SHAFT_OUTPUT_D_START,
                z,
                CENTER_CLUTCH_SHAFT_OUTPUT_D_LENGTH
            );
            // Round journal immediately follows the D transition and passes
            // through both fixed 3×6×2 bearings.
            cylinder_y(
                x,
                base_y + CENTER_CLUTCH_SHAFT_OUTPUT_ROUND_START,
                z,
                CENTER_CLUTCH_SHAFT_OUTPUT_ROUND_D,
                CENTER_CLUTCH_SHAFT_OUTPUT_ROUND_LENGTH
            );
        }
}

module center_clutch_output_bearings(col, row) {
    x = center_clutch_axis_x(col);
    z = center_clutch_axis_z();
    color("#cfd4da")
        for (index = [0:1])
            center_clutch_bearing_reference_y(
                x,
                center_clutch_output_bearing_y(row, index)
                    + CENTER_CLUTCH_BEARING_REFERENCE_CENTER_OFFSET,
                z
            );
}

module center_clutch_linear_bearing_reference_y(x, y, z) {
    // Purchased LM3UU reference, exact Ø3×Ø7×10 envelope. The near-side
    // window is display-only and does not alter the procurement dimensions.
    color("#aeb8be")
        translate([x, y, z])
            rotate([90, 0, 0])
                difference() {
                    cylinder(
                        d = CENTER_CLUTCH_LINEAR_BEARING_OD,
                        h = CENTER_CLUTCH_LINEAR_BEARING_BODY_L,
                        center = true,
                        $fn = 64
                    );
                    cylinder(
                        d = CENTER_CLUTCH_LINEAR_BEARING_ID,
                        h = CENTER_CLUTCH_LINEAR_BEARING_BODY_L + 2 * EPS,
                        center = true,
                        $fn = 48
                    );
                    translate([
                        -CENTER_CLUTCH_LINEAR_BEARING_OD / 2 - EPS,
                        -CENTER_CLUTCH_LINEAR_BEARING_OD / 2 - EPS,
                        -CENTER_CLUTCH_LINEAR_BEARING_BODY_L / 2 - EPS
                    ])
                        cube([
                            CENTER_CLUTCH_LINEAR_BEARING_OD + 2 * EPS,
                            CENTER_CLUTCH_LINEAR_BEARING_CUTAWAY_DEPTH,
                            CENTER_CLUTCH_LINEAR_BEARING_BODY_L + 2 * EPS
                        ]);
                }
    color("#4d5b64")
        for (sy = [-1, 1])
            translate([
                x,
                y + sy * (
                    CENTER_CLUTCH_LINEAR_BEARING_BODY_L / 2
                    + CENTER_CLUTCH_LINEAR_BEARING_SEAL_L / 2
                ),
                z
            ])
                rotate([90, 0, 0])
                    difference() {
                        cylinder(
                            d = CENTER_CLUTCH_LINEAR_BEARING_OD,
                            h = CENTER_CLUTCH_LINEAR_BEARING_SEAL_L,
                            center = true,
                            $fn = 64
                        );
                        cylinder(
                            d = CENTER_CLUTCH_LINEAR_BEARING_ID + 0.40,
                            h = CENTER_CLUTCH_LINEAR_BEARING_SEAL_L + 2 * EPS,
                            center = true,
                            $fn = 48
                        );
                    }
    color("#303a40")
        for (row_y = [-3.30, -1.10, 1.10, 3.30])
            for (index = [0:7]) {
                angle = -90 + index * 360 / 8;
                translate([
                    x + CENTER_CLUTCH_LINEAR_BEARING_BALL_PITCH_R * cos(angle),
                    y + row_y,
                    z + CENTER_CLUTCH_LINEAR_BEARING_BALL_PITCH_R * sin(angle)
                ])
                    sphere(
                        d = CENTER_CLUTCH_LINEAR_BEARING_BALL_D,
                        $fn = 16
                    );
            }
}

module center_clutch_linear_bearings(col, row, engaged = false) {
    // Fixed in the rectangular bar. The moving D-round-D input shaft passes
    // through it, so the bearing/reference must never receive +Y animation.
    x = center_clutch_axis_x(col);
    z = center_clutch_linear_bearing_z();
    color("#b7c0c8")
        center_clutch_linear_bearing_reference_y(
            x,
            center_clutch_linear_bearing_center_y(row),
            z
        );
}

module center_clutch_purchased_references(col, row, engaged = false) {
    center_clutch_input_shaft(col, row, engaged);
    center_clutch_input_sleeve_magnet_reference(col, row, engaged);
    center_clutch_output_shaft(col, row);
    center_clutch_output_bearings(col, row);
    center_clutch_linear_bearings(col, row, engaged);
}
//#endregion

//#region 公开 API
//#endregion

//#region 公开 API：中心机构总装
module center_clutch_carrier(
    col,
    row,
    engaged = false,
    purchased = true,
    include_plate = true
) {
    if (include_plate)
        color("#536d78") center_clutch_mechanism_plate(col, row);
    color("#7c909d") center_clutch_input_sleeve(col, row, engaged);
    if (purchased)
        center_clutch_purchased_references(col, row, engaged);
}
//#endregion

//#region 业务校验
assert(CENTER_CLUTCH_BEARING_SEAT_D > CENTER_CLUTCH_BEARING_OD,
    "output bearing seat must clear the purchased bearing OD");
assert(CENTER_CLUTCH_BEARING_SEAT_DEPTH
        >= CENTER_CLUTCH_BEARING_W + 0.40,
    "output bearing seat needs a rear axial shoulder");
assert(CENTER_CLUTCH_BEARING_BLOCK_X
        > CENTER_CLUTCH_BEARING_SEAT_D + 2.0,
    "output bearing bar must leave printable wall around each bearing pocket");
assert(CENTER_CLUTCH_BEARING_BLOCK_Y
        >= 2 * CENTER_CLUTCH_BEARING_SEAT_DEPTH
            - CENTER_CLUTCH_BEARING_W + 1.0,
    "output bearing bar must leave a solid middle web between the two pockets");
assert(CENTER_CLUTCH_BEARING_BLOCK_Y0_OFFSET > 0,
    "mother wheel must clear the lower edge of the output bearing bar");
assert(CENTER_CLUTCH_BEARING_BLOCK_Z_MARGIN > 0
        && CENTER_CLUTCH_BEARING_BLOCK_Z_OVERLAP > 0,
    "output bearing bar must have a radial margin and plate overlap");
assert(CENTER_CLUTCH_BEARING_REFERENCE_CENTER_OFFSET == 0,
    "output bearing references must be coaxial with the pockets");
assert(abs(
    center_clutch_output_bearing_y(2, 0)
        - (center_clutch_output_bearing_bar_y0(2)
            + CENTER_CLUTCH_BEARING_W / 2)
    ) < 0.001,
    "lower output bearing must sit at the lower bar pocket");
assert(abs(
    center_clutch_output_bearing_y(2, 1)
        - (center_clutch_output_bearing_bar_y1(2)
            - CENTER_CLUTCH_BEARING_W / 2)
    ) < 0.001,
    "upper output bearing must sit at the upper bar pocket");
assert(CENTER_CLUTCH_SHAFT_OUTPUT_D_START
        <= -GT2_D_BORE_DEPTH + 0.001
        && CENTER_CLUTCH_SHAFT_OUTPUT_D_START
            + CENTER_CLUTCH_SHAFT_OUTPUT_D_LENGTH >= 0 - 0.001,
    "output D shaft must span the full mother-wheel blind socket");
assert(CENTER_CLUTCH_SHAFT_OUTPUT_ROUND_START
        <= CENTER_CLUTCH_SHAFT_OUTPUT_D_START
            + CENTER_CLUTCH_SHAFT_OUTPUT_D_LENGTH + 0.001
        && CENTER_CLUTCH_SHAFT_OUTPUT_ROUND_START
            + CENTER_CLUTCH_SHAFT_OUTPUT_ROUND_LENGTH
            >= CENTER_CLUTCH_SHAFT_OUTPUT_D_START - 0.001,
    "output D-to-round transition must overlap");
assert(CENTER_CLUTCH_SHAFT_OUTPUT_ROUND_START
        <= CENTER_CLUTCH_BEARING_BLOCK_Y0_OFFSET
            + CENTER_CLUTCH_BEARING_W / 2 + 0.001
        && CENTER_CLUTCH_SHAFT_OUTPUT_ROUND_START
            + CENTER_CLUTCH_SHAFT_OUTPUT_ROUND_LENGTH
            >= CENTER_CLUTCH_BEARING_BLOCK_Y0_OFFSET
                + CENTER_CLUTCH_BEARING_BLOCK_Y
                + CENTER_CLUTCH_SHAFT_OUTPUT_TOP_PROTRUSION - 0.001,
    "output round shaft must cover both bearings and leave only the short tip");
assert(CENTER_CLUTCH_LINEAR_BEARING_COUNT == 1,
    "center input needs exactly one LM3UU");
assert(CENTER_CLUTCH_LINEAR_BEARING_ID
        == CENTER_CLUTCH_INPUT_SHAFT_ROUND_D,
    "LM3UU bore must match the round section of the stepped input shaft");
assert(CENTER_CLUTCH_LINEAR_BEARING_SEAT_D
        >= CENTER_CLUTCH_LINEAR_BEARING_OD + 0.20 - 0.001,
    "LM3UU bar seat must start at 0.10 mm radial FDM clearance");
assert(CENTER_CLUTCH_LINEAR_BEARING_BLOCK_X
        > CENTER_CLUTCH_LINEAR_BEARING_SEAT_D + 2.0,
    "LM3UU bar must leave printable side wall around the bearing hole");
assert(abs(CENTER_CLUTCH_LINEAR_BEARING_BLOCK_Y
        - CENTER_CLUTCH_LINEAR_BEARING_L) < 0.001,
    "LM3UU bar Y thickness must equal the purchased bearing envelope");
assert(CENTER_CLUTCH_LINEAR_BEARING_INPUT_ROTOR_CLEARANCE >= 0.30 - 0.001
        && CENTER_CLUTCH_LINEAR_BEARING_INPUT_ROTOR_CLEARANCE <= 0.60 + 0.001,
    "LM3UU bar must keep 0.30-0.60 mm nominal clearance below the male rotor");
assert(abs(CENTER_CLUTCH_LINEAR_BEARING_CENTER_Y_OFFSET
        + CENTER_CLUTCH_LINEAR_BEARING_L / 2
        + CENTER_CLUTCH_LINEAR_BEARING_INPUT_ROTOR_CLEARANCE) < 0.001,
    "LM3UU bar upper face must follow the male rotor clearance datum");
assert(CENTER_CLUTCH_LINEAR_BEARING_BLOCK_Z_LENGTH
        > CENTER_CLUTCH_LINEAR_BEARING_BLOCK_Z_MARGIN,
    "LM3UU bar must reach from the plate to the clutch axis");
assert(CENTER_CLUTCH_LINEAR_BEARING_BLOCK_MOUNT_COUNT == 0
        && CENTER_CLUTCH_LINEAR_BEARING_BLOCK_MOUNT_D == 0,
    "integrated LM3UU seat must have no holder mounting holes");
assert(CENTER_CLUTCH_PLATE_REAR_Z
        - CENTER_CLUTCH_LINEAR_BEARING_BLOCK_Z_LENGTH
        <= CENTER_GT2_Z
            - CENTER_CLUTCH_LINEAR_BEARING_OD / 2
            - CENTER_CLUTCH_LINEAR_BEARING_BLOCK_Z_MARGIN + 0.001,
    "integrated LM3UU seat must enclose the bearing OD in Z");
assert(CENTER_CLUTCH_INPUT_SHAFT_UPPER_D_START < 0
        && CENTER_CLUTCH_INPUT_SHAFT_UPPER_D_START
            + CENTER_CLUTCH_INPUT_SHAFT_UPPER_D_LENGTH
            >= GT2_D_BORE_DEPTH - 0.001,
    "upper D shaft must key into the male blind socket");
assert(-CENTER_CLUTCH_INPUT_SHAFT_UPPER_D_START
        <= GT2_INPUT_SHAFT_UPPER_D_EXTERNAL + 0.001,
    "upper D shaft must transition to round immediately below the male rotor");
assert(CENTER_CLUTCH_INPUT_SHAFT_ROUND_START
        + CENTER_CLUTCH_INPUT_SHAFT_ROUND_LENGTH
        >= CENTER_CLUTCH_INPUT_SHAFT_UPPER_D_START - 0.001,
    "round shaft must overlap the upper D transition");
assert(CENTER_CLUTCH_INPUT_SHAFT_LOWER_D_START
        <= CENTER_CLUTCH_INPUT_SHAFT_ROUND_START + 0.20 + 0.001
        && CENTER_CLUTCH_INPUT_SHAFT_LOWER_D_START
            + CENTER_CLUTCH_INPUT_SHAFT_LOWER_D_LENGTH
            >= CENTER_CLUTCH_INPUT_SHAFT_ROUND_START - 0.001,
    "lower D shaft must overlap the round transition");
assert(CENTER_CLUTCH_INPUT_SHAFT_LOWER_D_START
        + CENTER_CLUTCH_INPUT_SHAFT_LOWER_D_LENGTH
        > CENTER_CLUTCH_INPUT_SHAFT_LOWER_D_START,
    "lower D shaft must have positive length");
assert(CENTER_CLUTCH_INPUT_SLEEVE_UPPER_D_HEIGHT > 0
        && CENTER_CLUTCH_INPUT_SLEEVE_LOWER_ROUND_HEIGHT > 0,
    "input sleeve upper D and lower round sections must be positive");
assert(CENTER_CLUTCH_INPUT_SLEEVE_D_SOCKET_DEPTH
        <= CENTER_CLUTCH_INPUT_SLEEVE_UPPER_D_HEIGHT + 0.001,
    "sleeve D socket must stay inside the upper D section");
assert(CENTER_CLUTCH_INPUT_SLEEVE_MAGNET_D == 5.00
        && CENTER_CLUTCH_INPUT_SLEEVE_MAGNET_L == 5.00,
    "input sleeve must use a nominal M5x5 cylindrical magnet");
assert(CENTER_CLUTCH_INPUT_SLEEVE_MAGNET_POCKET_D
        >= CENTER_CLUTCH_INPUT_SLEEVE_MAGNET_D,
    "M5 magnet pocket must clear the purchased magnet");
assert(CENTER_CLUTCH_INPUT_SLEEVE_MAGNET_POCKET_DEPTH
        >= CENTER_CLUTCH_INPUT_SLEEVE_MAGNET_L,
    "M5 magnet pocket must contain the full magnet length");
assert(CENTER_CLUTCH_INPUT_SLEEVE_LOWER_ROUND_OD
        - CENTER_CLUTCH_INPUT_SLEEVE_MAGNET_POCKET_D >= 2.80 - 0.001,
    "round sleeve must leave at least 1.40 mm radial magnet wall");
assert(CENTER_CLUTCH_INPUT_SLEEVE_MAGNET_BOTTOM_CLEARANCE >= 1.00,
    "sleeve must retain a solid floor below the M5 magnet");
assert(abs(
    center_clutch_linear_bearing_y0(2)
        - (center_clutch_input_sleeve_top_y(2)
            + GT2_CLUTCH_ENGAGE_STROKE_MM)
    ) < 0.001,
    "engaged sleeve upper edge must meet the integrated bearing seat");
assert(center_clutch_linear_bearing_y0(2)
        - center_clutch_input_sleeve_top_y(2)
        >= GT2_CLUTCH_ENGAGE_STROKE_MM - 0.001,
    "open sleeve must clear the integrated bearing seat by the full stroke");
assert(CENTER_CLUTCH_PLATE_BELT_PASSAGE_HALF_X
        < CENTER_CLUTCH_PLATE_W / 2,
    "center belt passage must stay inside the mechanism plate");
assert(CENTER_CLUTCH_PLATE_BELT_PASSAGE_Y > GT2_BELT_WIDTH,
    "center belt passage must include axial clearance");
assert(CENTER_CLUTCH_PLATE_PARTITION_GAP == 0,
    "mechanism plate must seat directly on the partition rear face");
assert(CENTER_CLUTCH_PARTITION_BOSS_PER_CELL_COUNT == 4,
    "each drawer cell must have four corner locating bosses");
assert(CENTER_CLUTCH_PARTITION_BOSS_COUNT
        == N_COL * N_ROW * CENTER_CLUTCH_PARTITION_BOSS_PER_CELL_COUNT,
    "partition boss count must repeat across every drawer cell");
assert(CENTER_CLUTCH_PARTITION_BOSS_HEIGHT
        == CENTER_CLUTCH_PLATE_T - 0.50,
    "partition boss must finish 0.50 mm below the plate rear face");
assert(CENTER_CLUTCH_PARTITION_SELF_TAP_PILOT_DEPTH
        + CENTER_CLUTCH_PARTITION_SELF_TAP_BOTTOM_WALL
        == CENTER_CLUTCH_PARTITION_BOSS_HEIGHT,
    "boss self-tap pilot must leave its partition-side bottom wall");
assert(CENTER_CLUTCH_PARTITION_SELF_TAP_PILOT_DEPTH > 0,
    "boss self-tap pilot depth must be positive");
assert(CENTER_CLUTCH_PARTITION_BOSS_OD
        > CENTER_CLUTCH_PARTITION_SELF_TAP_PILOT_D + 2.0,
    "boss must leave radial material around the self-tap pilot");
assert(CENTER_CLUTCH_PLATE_FASTENER_COUNT == 4,
    "mechanism plate must retain four self-tapping screw locations");
assert(N_COL >= 1 && N_ROW >= 1,
    "continuous rear carrier needs at least one station and one row");
assert(center_clutch_row_plate_length() > CENTER_CLUTCH_PLATE_W,
    "row carrier must span the station array instead of one local plate");
assert(center_clutch_row_plate_left_clearance() >= 1.0 - EPS
        && center_clutch_row_plate_right_clearance() >= 1.0 - EPS,
    "continuous row carrier must stay inside the rear drawer grid with side clearance");
assert(center_clutch_row_plate_length() < X1C_BUILD_X - 2 * X1C_FRAME_EDGE_MARGIN,
    "continuous row carrier must fit the reserved X1C print envelope");
//#endregion
