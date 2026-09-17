// 中心 R3C3 纯永磁离合机构板与公轮阶梯轴
//
// This file is included after cabinet_clutch.scad has defined the native world
// helpers and the CH1 03C pair library.  The input side is intentionally small:
// the male rotor is keyed to one stepped shaft (D-round-D), the round section
// runs directly in one stationary LM3UU, and the lower D section enters a
// printed sleeve carrying one Ø5×5 mm cylindrical magnet.  There is no input
// carriage, second guide, stop lug, spring, fork or printed input rotary cage.
//
// The output side remains a separately serviceable two-bearing cage.  The
// linear-bearing seat is a long rectangular bar bored Ø7.20 through Y and
// printed as one solid with the removable clutch mechanism plate.  The bar has
// no fastener holes: the plate's own four M3 holes attach the complete part.

//#region 导入/依赖
// cabinet_clutch.scad supplies WORLD_PARTITION_BACK_Z, CENTER_GT2_Z,
// center_gt2_*(), cylinder_y(), d_rod_y(), d_profile_2d(), GT2_* and colors.
//#endregion

//#region 常量/配置
// Output rotor radial support: two purchased 3×6×2 bearings remain on the
// fixed female/output side.  The input side uses no separate rotary cage.
CENTER_CLUTCH_BEARING_OD = 6.00;
CENTER_CLUTCH_BEARING_ID = 3.00;
CENTER_CLUTCH_BEARING_W = 2.00;
CENTER_CLUTCH_BEARING_SEAT_D = is_undef(
    CENTER_CLUTCH_BEARING_SEAT_DIAMETER_MM
)
    ? 6.10
    : CENTER_CLUTCH_BEARING_SEAT_DIAMETER_MM;
CENTER_CLUTCH_BEARING_BLOCK_X = 14.00;
CENTER_CLUTCH_BEARING_BLOCK_Z = 14.00;
CENTER_CLUTCH_BEARING_BLOCK_T = 3.20;
CENTER_CLUTCH_BEARING_BACK_SHOULDER_T = 0.60;
CENTER_CLUTCH_BEARING_REFERENCE_CENTER_OFFSET =
    -CENTER_CLUTCH_BEARING_BACK_SHOULDER_T;
CENTER_CLUTCH_BEARING_SEAT_DEPTH = CENTER_CLUTCH_BEARING_BLOCK_T
    - CENTER_CLUTCH_BEARING_BACK_SHOULDER_T;
CENTER_CLUTCH_BEARING_CENTER_OFFSET = 4.20;
CENTER_CLUTCH_BEARING_PAIR_SPACING = 4.00;

// The removable plate lives behind the partition.  The linear-bearing block
// reaches rearward from the plate to the male/output axis and is deliberately
// a single rectangular printed part; the thin back cover never carries this
// load path.
CENTER_CLUTCH_PLATE_Z = WORLD_PARTITION_BACK_Z - 0.80;
CENTER_CLUTCH_PLATE_T = 3.20;
CENTER_CLUTCH_PLATE_W = 34.00;
CENTER_CLUTCH_PLATE_MOUNT_X_OFFSET = 12.00;
CENTER_CLUTCH_PLATE_MOUNT_Y_OFFSET = 4.00;
CENTER_CLUTCH_PLATE_KEY_W = 4.00;
CENTER_CLUTCH_PLATE_KEY_H = 6.00;
CENTER_CLUTCH_PLATE_KEY_D = 1.00;
CENTER_CLUTCH_M3_CLEAR_D = 3.40;
CENTER_CLUTCH_SUPPORT_KEY_CLEAR = 0.30;
CENTER_CLUTCH_PLATE_REAR_Z = CENTER_CLUTCH_PLATE_Z
    - CENTER_CLUTCH_PLATE_T;

// The center 2GT belt crosses the service plate between the fixed output
// rotor and the front drawer pulley.  This opening is a true CSG passage.
CENTER_CLUTCH_PLATE_BELT_PASSAGE_RADIAL_CLEAR = 0.45;
CENTER_CLUTCH_PLATE_BELT_PASSAGE_AXIAL_CLEAR = 0.45;
CENTER_CLUTCH_PLATE_BELT_PASSAGE_HALF_X =
    CENTER_GT2_BELT_BASE_OUTER_R
    + GT2_BELT_RADIAL_CLEARANCE
    + CENTER_CLUTCH_PLATE_BELT_PASSAGE_RADIAL_CLEAR;
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
CENTER_CLUTCH_LINEAR_BEARING_CENTER_Y_OFFSET = -7.00;
CENTER_CLUTCH_LINEAR_BEARING_BLOCK_X = 18.00;
CENTER_CLUTCH_LINEAR_BEARING_BLOCK_Y = 14.00;
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

// Moving input shaft.  Relative Y is measured from the male gear underside:
// upper D enters the male blind socket, the Ø3 round section is the only
// sliding journal, and the lower D enters the sleeve's upper D socket.
CENTER_CLUTCH_INPUT_SHAFT_UPPER_D_START = -GT2_INPUT_SHAFT_UPPER_D_EXTERNAL;
CENTER_CLUTCH_INPUT_SHAFT_UPPER_D_LENGTH = GT2_D_BORE_DEPTH
    + GT2_INPUT_SHAFT_UPPER_D_EXTERNAL
    + GT2_INPUT_SHAFT_TRANSITION_OVERLAP;
CENTER_CLUTCH_INPUT_SHAFT_ROUND_START = -20.60;
CENTER_CLUTCH_INPUT_SHAFT_ROUND_LENGTH = 20.40;
CENTER_CLUTCH_INPUT_SHAFT_LOWER_D_START = -20.40;
CENTER_CLUTCH_INPUT_SHAFT_LOWER_D_LENGTH = 3.60;
CENTER_CLUTCH_INPUT_SHAFT_ROUND_D = GT2_INPUT_SHAFT_ROUND_D;
CENTER_CLUTCH_INPUT_SHAFT_TRANSITION_OVERLAP =
    GT2_INPUT_SHAFT_TRANSITION_OVERLAP;

// Printed sleeve: upper outer D profile, lower round boss, blind Ø5.20×5.20
// pocket for a purchased Ø5×5 magnet.  “M5” here is the magnet size; the
// printed round boss is Ø8 to leave a 1.40 mm radial wall around that pocket.
CENTER_CLUTCH_INPUT_SLEEVE_TOP_OFFSET = -17.00;
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

// Output shaft remains a separate D shaft and stays fixed in Y.
CENTER_CLUTCH_SHAFT_OUTPUT_START = -3.40;
CENTER_CLUTCH_SHAFT_OUTPUT_LENGTH = 14.00;
CENTER_CLUTCH_SHAFT_COLLAR_OD = 7.20;
CENTER_CLUTCH_SHAFT_COLLAR_BORE_D = 3.35;
CENTER_CLUTCH_SHAFT_COLLAR_T = 0.60;

// A small printed fit coupon contains three rectangular bearing-bar samples.
CENTER_CLUTCH_FIT_COUPON_BLOCK_W = 12.00;
CENTER_CLUTCH_FIT_COUPON_BLOCK_H = 12.00;
CENTER_CLUTCH_FIT_COUPON_BLOCK_T = 10.00;
CENTER_CLUTCH_FIT_COUPON_SEAT_VARIANTS = [7.20, 7.30, 7.40];
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

function center_clutch_plate_y0(row) =
    min(
        center_clutch_linear_bearing_y0(row) - 2.00,
        center_clutch_output_base_y(row) - 4.00
    );

function center_clutch_plate_y1(row) =
    center_clutch_output_base_y(row) + 10.00;

function center_clutch_plate_h(row) =
    center_clutch_plate_y1(row) - center_clutch_plate_y0(row);

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
module center_clutch_bearing_block_y(x, y, z) {
    seat_y0 = y - CENTER_CLUTCH_BEARING_BLOCK_T / 2;
    difference() {
        translate([
            x - CENTER_CLUTCH_BEARING_BLOCK_X / 2,
            y - CENTER_CLUTCH_BEARING_BLOCK_T / 2,
            z - CENTER_CLUTCH_BEARING_BLOCK_Z / 2
        ])
            cube([
                CENTER_CLUTCH_BEARING_BLOCK_X,
                CENTER_CLUTCH_BEARING_BLOCK_T,
                CENTER_CLUTCH_BEARING_BLOCK_Z
            ]);
        cylinder_y(
            x,
            seat_y0 - EPS,
            z,
            CENTER_CLUTCH_BEARING_SEAT_D,
            CENTER_CLUTCH_BEARING_SEAT_DEPTH + EPS
        );
    }
}

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

module center_clutch_shaft_collar_y(x, y0, z) {
    // Purchased/fit reference collar for the fixed output D shaft.
    translate([x, y0, z])
        rotate([-90, 0, 0])
            difference() {
                cylinder(
                    d = CENTER_CLUTCH_SHAFT_COLLAR_OD,
                    h = CENTER_CLUTCH_SHAFT_COLLAR_T,
                    $fn = 64
                );
                translate([0, 0, -EPS])
                    cylinder(
                        d = CENTER_CLUTCH_SHAFT_COLLAR_BORE_D,
                        h = CENTER_CLUTCH_SHAFT_COLLAR_T + 2 * EPS,
                        $fn = 48
                    );
            }
}

module center_clutch_z_arm(x, y, z0, z1, width = 2.00, depth = 3.20) {
    translate([
        x - width / 2,
        y - depth / 2,
        min(z0, z1)
    ])
        cube([width, depth, abs(z1 - z0)]);
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

//#region 公开 API：机构板、输出笼与固定直线轴承块
module center_clutch_plate_belt_passage(col, row) {
    x = center_clutch_axis_x(col);
    y = center_gt2_belt_y(row);
    translate([
        x - CENTER_CLUTCH_PLATE_BELT_PASSAGE_HALF_X,
        y - CENTER_CLUTCH_PLATE_BELT_PASSAGE_Y / 2,
        CENTER_CLUTCH_PLATE_Z - CENTER_CLUTCH_PLATE_T - EPS
    ])
        cube([
            2 * CENTER_CLUTCH_PLATE_BELT_PASSAGE_HALF_X,
            CENTER_CLUTCH_PLATE_BELT_PASSAGE_Y,
            CENTER_CLUTCH_PLATE_T + 2 * EPS
        ]);
}

module center_clutch_linear_bearing_block_y(col, row) {
    x = center_clutch_axis_x(col);
    y = center_clutch_linear_bearing_center_y(row);
    z0 = CENTER_CLUTCH_PLATE_REAR_Z
        - CENTER_CLUTCH_LINEAR_BEARING_BLOCK_Z_LENGTH;
    difference() {
        // Long bar: it overlaps the rear of the main plate by 0.20 mm, and its
        // outer end surrounds the male-axis LM3UU hole in Z.
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
            // Locating keys enter captured partition slots. They locate the
            // removable service plate but do not carry the shaft load.
            for (sx = [-1, 1])
                translate([
                    x + sx * 10.00 - CENTER_CLUTCH_PLATE_KEY_W / 2,
                    y0 + h / 2 - CENTER_CLUTCH_PLATE_KEY_H / 2,
                    CENTER_CLUTCH_PLATE_Z
                ])
                    cube([
                        CENTER_CLUTCH_PLATE_KEY_W,
                        CENTER_CLUTCH_PLATE_KEY_H,
                        CENTER_CLUTCH_PLATE_KEY_D
                    ]);
            // The LM3UU seat is part of this same printed mechanism plate.
            // Only the bearing bore is subtracted from the otherwise solid
            // support; there is no separate holder or holder fastener set.
            center_clutch_linear_bearing_block_y(col, row);
        }
        // Four plate-to-partition M3 holes.
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
                    h = CENTER_CLUTCH_PLATE_T
                        + CENTER_CLUTCH_PLATE_KEY_D + 2 * EPS,
                    $fn = 40
                );
        center_clutch_plate_belt_passage(col, row);
    }
}

module center_clutch_partition_support_cuts(col, row) {
    x = center_clutch_axis_x(col);
    y0 = center_clutch_plate_y0(row);
    h = center_clutch_plate_h(row);
    for (sx = [-1, 1])
        translate([
            x + sx * 10.00
                - (CENTER_CLUTCH_PLATE_KEY_W
                    + 2 * CENTER_CLUTCH_SUPPORT_KEY_CLEAR) / 2,
            y0 + h / 2
                - (CENTER_CLUTCH_PLATE_KEY_H
                    + 2 * CENTER_CLUTCH_SUPPORT_KEY_CLEAR) / 2,
            WORLD_PARTITION_BACK_Z - EPS
        ])
            cube([
                CENTER_CLUTCH_PLATE_KEY_W
                    + 2 * CENTER_CLUTCH_SUPPORT_KEY_CLEAR,
                CENTER_CLUTCH_PLATE_KEY_H
                    + 2 * CENTER_CLUTCH_SUPPORT_KEY_CLEAR,
                WORLD_PARTITION_T + 2 * EPS
            ]);
    for (sx = [-1, 1], sy = [-1, 1])
        translate([
            x + sx * CENTER_CLUTCH_PLATE_MOUNT_X_OFFSET,
            y0 + (sy < 0
                ? CENTER_CLUTCH_PLATE_MOUNT_Y_OFFSET
                : h - CENTER_CLUTCH_PLATE_MOUNT_Y_OFFSET),
            WORLD_PARTITION_BACK_Z - EPS
        ])
            cylinder(
                d = CENTER_CLUTCH_M3_CLEAR_D,
                h = WORLD_PARTITION_T + 2 * EPS,
                $fn = 40
            );
}

module center_clutch_output_cage(col, row) {
    x = center_clutch_axis_x(col);
    z = center_clutch_axis_z();
    for (index = [0:1]) {
        bearing_y = center_clutch_output_bearing_y(row, index);
        center_clutch_bearing_block_y(x, bearing_y, z);
        for (sx = [-1, 1])
            center_clutch_z_arm(
                x + sx * 7.00,
                bearing_y,
                z + 5.30,
                CENTER_CLUTCH_PLATE_REAR_Z,
                2.00,
                CENTER_CLUTCH_BEARING_BLOCK_T
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
    color(COLOR_SHAFT)
        d_rod_y(
            x,
            center_clutch_output_base_y(row)
                + CENTER_CLUTCH_SHAFT_OUTPUT_START,
            z,
            CENTER_CLUTCH_SHAFT_OUTPUT_LENGTH
        );
    for (index = [0:1])
        center_clutch_shaft_collar_y(
            x,
            center_clutch_output_bearing_y(row, index)
                - CENTER_CLUTCH_BEARING_BLOCK_T / 2
                - CENTER_CLUTCH_SHAFT_COLLAR_T,
            z
        );
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

//#region 公开 API：配合测试片与兼容空接口
module center_clutch_linear_bearing_fit_coupon_sample(x, seat_d) {
    difference() {
        translate([
            x - CENTER_CLUTCH_FIT_COUPON_BLOCK_W / 2,
            -CENTER_CLUTCH_FIT_COUPON_BLOCK_T / 2,
            -CENTER_CLUTCH_FIT_COUPON_BLOCK_H / 2
        ])
            cube([
                CENTER_CLUTCH_FIT_COUPON_BLOCK_W,
                CENTER_CLUTCH_FIT_COUPON_BLOCK_T,
                CENTER_CLUTCH_FIT_COUPON_BLOCK_H
            ]);
        cylinder_y(
            x,
            -CENTER_CLUTCH_FIT_COUPON_BLOCK_T / 2 - EPS,
            0,
            seat_d,
            CENTER_CLUTCH_FIT_COUPON_BLOCK_T + 2 * EPS
        );
    }
}

module center_clutch_linear_bearing_fit_coupon() {
    // Three long-bar seat samples. Install one real LM3UU in each candidate
    // and slide the round Ø3 section through by hand before printing the bar.
    for (index = [0:len(CENTER_CLUTCH_FIT_COUPON_SEAT_VARIANTS) - 1])
        center_clutch_linear_bearing_fit_coupon_sample(
            (index - 1) * 15.00,
            CENTER_CLUTCH_FIT_COUPON_SEAT_VARIANTS[index]
        );
}

// Retired input-side structures are kept as named empty diagnostic entry
// points so an old command cannot silently reintroduce the orange mechanism.
module center_clutch_input_carriage(col, row, engaged = false) {}
module center_clutch_guide_rails(col, row) {}
module center_clutch_linear_bearing_retainers(col, row, engaged = false) {}
module center_clutch_stops(col, row) {}
module center_clutch_input_bearings(col, row, engaged = false) {}
module center_clutch_linear_bearing_holder_y(x, y, z, seat_d = 7.20) {}
module center_clutch_linear_bearing_retainer_y(x, y1, z) {}
module center_clutch_stop_bar(col, row, y) {}
module center_clutch_stop_lugs(col, row, y) {}
module center_clutch_linear_bearing_support_web_y(x, base_y, bearing_z) {}
module center_clutch_carriage_stop_bridge(x, base_y, z, sx) {}
//#endregion

//#region 公开 API：中心机构总装
module center_clutch_carrier(col, row, engaged = false, purchased = true) {
    color("#536d78") center_clutch_mechanism_plate(col, row);
    color("#4c6470") center_clutch_output_cage(col, row);
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
assert(CENTER_CLUTCH_LINEAR_BEARING_BLOCK_Y
        >= CENTER_CLUTCH_LINEAR_BEARING_L + 2.0,
    "LM3UU bar must have enough Y length for a press-fit seat");
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
//#endregion
