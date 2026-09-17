// 中心 R3C3 纯永磁离合机构载架
//
// This file is included by cabinet_clutch.scad after the native world helpers
// and the CH1 03C pair library have been defined.  It intentionally contains
// no top-level geometry: the root scene owns dispatch and this file owns only
// the removable plate, bearing cages, captured guides, carriage and stops.
//
// Mechanical contract:
//   axis                 world +Y
//   input                male rotor + its own short D shaft and two rotary
//                        bearings; the whole set travels +Y
//   output               female rotor + its own short D shaft and two fixed
//                        rotary bearings; it rotates in the output cage
//   guides               two purchased 3 mm round guide rods with exactly one
//                        purchased 3x7x10 linear bearing on each side (left +
//                        right, not an upper/lower stack); the carriage carries
//                        one printed bearing holder and one cap per side
//   limit                printed open and engaged hard stops; magnets never
//                        define the final travel
//   material             PETG functional first article; PLA is fit-only
//   purchased            two independent 3 mm D shafts, four 3x6x2 rotary
//                        bearings, two 3x7x10 linear bearings, four nominal
//                        2 mm magnets

//#region 导入/依赖
// cabinet_clutch.scad supplies the world coordinates, pair modules, colors,
// cylinder_y(), d_rod_y(), center_gt2_*() and the cabinet dimensions.
//#endregion

//#region 常量/配置
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

CENTER_CLUTCH_GUIDE_ROD_D = 3.00;
CENTER_CLUTCH_GUIDE_ROD_CAPTURE = 0.80;
CENTER_CLUTCH_GUIDE_ROD_POCKET_D = CENTER_CLUTCH_GUIDE_ROD_D + 0.30;

// The vertical carriage uses a purchased LM3UU-class linear bearing on each
// captured rod.  The bearing is modeled as a separate reference part; only
// the holder and its removable printed cap belong to the carriage's printed
// output.  These are first-article FDM values and still require a fit coupon.
CENTER_CLUTCH_LINEAR_BEARING_ID = 3.00;
CENTER_CLUTCH_LINEAR_BEARING_OD = 7.00;
CENTER_CLUTCH_LINEAR_BEARING_L = 10.00;
CENTER_CLUTCH_LINEAR_BEARING_COUNT = 2;
CENTER_CLUTCH_LINEAR_BEARING_SEAT_D =
    CENTER_CLUTCH_LINEAR_BEARING_OD + 0.20;
CENTER_CLUTCH_LINEAR_BEARING_SEAT_RADIAL_CLEARANCE =
    (CENTER_CLUTCH_LINEAR_BEARING_SEAT_D
        - CENTER_CLUTCH_LINEAR_BEARING_OD) / 2;
CENTER_CLUTCH_LINEAR_BEARING_HOLDER_OD = 12.00;
CENTER_CLUTCH_LINEAR_BEARING_HOLDER_L = 11.60;
CENTER_CLUTCH_LINEAR_BEARING_HOLDER_BACK_SHOULDER_T = 0.80;
CENTER_CLUTCH_LINEAR_BEARING_HOLDER_FRONT_NECK_D = 10.80;
CENTER_CLUTCH_LINEAR_BEARING_HOLDER_FRONT_NECK_L = 1.00;
CENTER_CLUTCH_LINEAR_BEARING_SEAT_DEPTH =
    CENTER_CLUTCH_LINEAR_BEARING_HOLDER_L
        - CENTER_CLUTCH_LINEAR_BEARING_HOLDER_BACK_SHOULDER_T;
CENTER_CLUTCH_LINEAR_BEARING_RETAINER_ID = 6.40;
CENTER_CLUTCH_LINEAR_BEARING_RETAINER_OD = 12.40;
CENTER_CLUTCH_LINEAR_BEARING_RETAINER_T = 0.80;
CENTER_CLUTCH_LINEAR_BEARING_RETAINER_LIP_OD = 7.00;
CENTER_CLUTCH_LINEAR_BEARING_RETAINER_SKIRT_ID = 11.00;
CENTER_CLUTCH_LINEAR_BEARING_RETAINER_SKIRT_OD = 11.60;
CENTER_CLUTCH_LINEAR_BEARING_RETAINER_SKIRT_L = 1.00;
CENTER_CLUTCH_LINEAR_BEARING_ROD_NOMINAL_CLEARANCE =
    CENTER_CLUTCH_LINEAR_BEARING_ID - CENTER_CLUTCH_GUIDE_ROD_D;

// Internal side-clearance datum for the stop-pad/upright layout. It is not a
// bearing running clearance and is intentionally not exported as one.
CENTER_CLUTCH_SIDE_CLEARANCE = 0.30;
// Keep the rail aliases for the stop-pad envelope and existing scene helpers;
// they describe the purchased rod cross-section, not a printed square rail.
CENTER_CLUTCH_RAIL_W = CENTER_CLUTCH_GUIDE_ROD_D;
CENTER_CLUTCH_RAIL_Z = CENTER_CLUTCH_GUIDE_ROD_D;
CENTER_CLUTCH_RAIL_CLEAR = CENTER_CLUTCH_SIDE_CLEARANCE;
CENTER_CLUTCH_RAIL_X_OFFSET = 10.00;
CENTER_CLUTCH_RAIL_Z_OFFSET = 9.00;
CENTER_CLUTCH_SHOE_L = CENTER_CLUTCH_LINEAR_BEARING_HOLDER_L;
CENTER_CLUTCH_SHOE_OUTER = CENTER_CLUTCH_LINEAR_BEARING_HOLDER_OD;

// The upright is deliberately outside the input rotor's radial envelope. Keep
// its four datums named so the interference audit consumes the same values as
// the printed carriage instead of copying a clearance number into Python.
CENTER_CLUTCH_CARRIAGE_UPRIGHT_CENTER_X_OFFSET = 6.20;
CENTER_CLUTCH_CARRIAGE_UPRIGHT_X_T = 2.00;
CENTER_CLUTCH_CARRIAGE_UPRIGHT_Z0 = 5.20;
CENTER_CLUTCH_CARRIAGE_UPRIGHT_H = 3.00;
CENTER_CLUTCH_CARRIAGE_UPRIGHT_Y0 = -10.00;
CENTER_CLUTCH_CARRIAGE_UPRIGHT_L = 8.40;

// The moving carriage is stopped by the two bearing-holder ends themselves. A
// former full-width crossbar passed through both rails and the bearing blocks;
// that was a real solid interference, not a harmless contact datum. The
// printed holder is a seat for a purchased linear bearing, not the sliding
// surface. The bearing ID and the rod remain a nominal coaxial purchased-part
// interface and are not faked as a printed bearing surface.
CENTER_CLUTCH_CARRIAGE_SHOE_Y0 = -10.40;
CENTER_CLUTCH_CARRIAGE_SHOE_L = CENTER_CLUTCH_SHOE_L;
CENTER_CLUTCH_CARRIAGE_SHOE_Y1 = CENTER_CLUTCH_CARRIAGE_SHOE_Y0
    + CENTER_CLUTCH_CARRIAGE_SHOE_L;
CENTER_CLUTCH_STOP_PAD_T = 1.20;
CENTER_CLUTCH_STOP_PAD_W = CENTER_CLUTCH_RAIL_W + 1.00;
CENTER_CLUTCH_STOP_PAD_Z = CENTER_CLUTCH_RAIL_Z + 1.00;
CENTER_CLUTCH_STOP_PAD_X_OFFSET = 0.60;
CENTER_CLUTCH_OPEN_STOP_Y = CENTER_CLUTCH_CARRIAGE_SHOE_Y0
    - CENTER_CLUTCH_STOP_PAD_T;
CENTER_CLUTCH_ENGAGED_STOP_Y = CENTER_CLUTCH_CARRIAGE_SHOE_Y1
    + GT2_CLUTCH_ENGAGE_STROKE_MM;

// The plate sits immediately behind the partition, with a rearward arm to
// the clutch axis. It is a separate service part; the thin back cover never
// receives a bearing seat or transmission load.
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
// The center 2GT belt runs from the rear female rotor to the front drawer
// pulley. The service plate is intentionally in that Z interval, so it needs
// its own through-passage; the partition passage alone cannot clear the belt.
// Keep the corridor wider than the belt envelope on both axes and leave the
// M3 mounts outside it.
CENTER_CLUTCH_PLATE_BELT_PASSAGE_RADIAL_CLEAR = 0.45;
CENTER_CLUTCH_PLATE_BELT_PASSAGE_AXIAL_CLEAR = 0.45;
CENTER_CLUTCH_PLATE_BELT_PASSAGE_HALF_X =
    CENTER_GT2_BELT_BASE_OUTER_R
    + GT2_BELT_RADIAL_CLEARANCE
    + CENTER_CLUTCH_PLATE_BELT_PASSAGE_RADIAL_CLEAR;
CENTER_CLUTCH_PLATE_BELT_PASSAGE_Y =
    GT2_BELT_WIDTH
    + 2 * CENTER_CLUTCH_PLATE_BELT_PASSAGE_AXIAL_CLEAR;

CENTER_CLUTCH_SHAFT_INPUT_START = -10.90;
CENTER_CLUTCH_SHAFT_INPUT_LENGTH =
    GT2_D_BORE_DEPTH - CENTER_CLUTCH_SHAFT_INPUT_START;
CENTER_CLUTCH_SHAFT_OUTPUT_START = -3.40;
CENTER_CLUTCH_SHAFT_OUTPUT_LENGTH = 14.00;
CENTER_CLUTCH_SHAFT_COLLAR_OD = 7.20;
CENTER_CLUTCH_SHAFT_COLLAR_BORE_D = 3.35;
CENTER_CLUTCH_SHAFT_COLLAR_T = 0.60;
//#endregion

//#region 尺寸函数
function center_clutch_input_base_y(row) = center_gt2_male_base_y(row);

function center_clutch_output_base_y(row) = center_gt2_female_base_y(row);

function center_clutch_axis_x(col) = clutch_col_x(col);

function center_clutch_axis_z() = center_gt2_z();

function center_clutch_rail_z() = center_clutch_axis_z()
    + CENTER_CLUTCH_RAIL_Z_OFFSET;

function center_clutch_rail_y0(row) = center_clutch_input_base_y(row)
    + CENTER_CLUTCH_CARRIAGE_SHOE_Y0;

// Only the input carriage travels on these rails. The fixed output cage has
// its own z-arms to the service plate, so extending the rails to the output
// bearing stack would unnecessarily put them through the selector shoe. The
// rails span the union of the open and engaged shoe envelopes and are captured
// between the two separate stop brackets at their end faces.
function center_clutch_rail_y1(row) = center_clutch_input_base_y(row)
    + CENTER_CLUTCH_CARRIAGE_SHOE_Y1
    + GT2_CLUTCH_ENGAGE_STROKE_MM;

function center_clutch_rail_length(row) = center_clutch_rail_y1(row)
    - center_clutch_rail_y0(row);

function center_clutch_plate_y0(row) = center_clutch_rail_y0(row) - 1.00;

// The plate still spans the fixed output cage even though the captured rails
// stop at the input carriage. This keeps the output bearing arms attached to
// the same removable service datum.
function center_clutch_plate_y1(row) = center_clutch_output_base_y(row) + 10.00;

function center_clutch_plate_h(row) = center_clutch_plate_y1(row)
    - center_clutch_plate_y0(row);

function center_clutch_input_bearing_y(row, index) =
    center_clutch_input_base_y(row)
    - CENTER_CLUTCH_BEARING_CENTER_OFFSET
    - index * CENTER_CLUTCH_BEARING_PAIR_SPACING;

function center_clutch_output_bearing_y(row, index) =
    center_clutch_output_base_y(row)
    + CENTER_CLUTCH_BEARING_CENTER_OFFSET
    + index * CENTER_CLUTCH_BEARING_PAIR_SPACING;

function center_clutch_open_stop_y(row) = center_clutch_input_base_y(row)
    + CENTER_CLUTCH_OPEN_STOP_Y;

function center_clutch_engaged_stop_y(row) = center_clutch_input_base_y(row)
    + CENTER_CLUTCH_ENGAGED_STOP_Y;

function center_clutch_carriage_shoe_y0(row) = center_clutch_input_base_y(row)
    + CENTER_CLUTCH_CARRIAGE_SHOE_Y0;

function center_clutch_carriage_shoe_y1(row) = center_clutch_input_base_y(row)
    + CENTER_CLUTCH_CARRIAGE_SHOE_Y1;

function center_clutch_linear_bearing_center_y(row) =
    center_clutch_input_base_y(row)
        + CENTER_CLUTCH_CARRIAGE_SHOE_Y0
        + CENTER_CLUTCH_LINEAR_BEARING_HOLDER_L / 2;

function center_clutch_linear_bearing_front_y(row) =
    center_clutch_linear_bearing_center_y(row)
        + CENTER_CLUTCH_LINEAR_BEARING_HOLDER_L / 2;

function center_clutch_engaged_carriage_shoe_y0(row) =
    center_clutch_carriage_shoe_y0(row) + GT2_CLUTCH_ENGAGE_STROKE_MM;

function center_clutch_engaged_carriage_shoe_y1(row) =
    center_clutch_carriage_shoe_y1(row) + GT2_CLUTCH_ENGAGE_STROKE_MM;
//#endregion

//#region 私有成员：轴承/承力几何
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
    // A bearing is a purchased 3x6x2 part. This annulus is display/reference
    // geometry and is never included in a printed carrier STL.
    translate([x, y, z])
        rotate([90, 0, 0])
            difference() {
                cylinder(d = CENTER_CLUTCH_BEARING_OD,
                    h = CENTER_CLUTCH_BEARING_W,
                    center = true,
                    $fn = 64);
                cylinder(d = CENTER_CLUTCH_BEARING_ID,
                    h = CENTER_CLUTCH_BEARING_W + 2 * EPS,
                    center = true,
                    $fn = 48);
            }
}

module center_clutch_shaft_collar_y(x, y0, z) {
    // A metal D shaft is shown with a thin axial shoulder/retaining ring at
    // the open side of each blind bearing seat. The ring is a purchased/fit
    // reference, not a claim that this small collar should be printed in PETG.
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
//#endregion

//#region 公开 API：机构板、笼和导轨
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

module center_clutch_mechanism_plate(col, row) {
    x = center_clutch_axis_x(col);
    y0 = center_clutch_plate_y0(row);
    h = center_clutch_plate_h(row);
    difference() {
        union() {
            translate([
                x - CENTER_CLUTCH_PLATE_W / 2,
                y0,
                CENTER_CLUTCH_PLATE_Z - CENTER_CLUTCH_PLATE_T
            ])
                cube([
                    CENTER_CLUTCH_PLATE_W,
                    h,
                    CENTER_CLUTCH_PLATE_T
                ]);
            // Two locating keys enter the partition-side support slots. They
            // locate the plate but do not carry the rotating shaft load.
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
        }
        // Four M3 clearance holes are normal to the plate. M3 screws fasten
        // this service plate to the partition/side support; no hole is put
        // through the thin removable back panel.
        for (sx = [-1, 1], sy = [-1, 1])
            translate([
                x + sx * CENTER_CLUTCH_PLATE_MOUNT_X_OFFSET,
                y0 + (sy < 0
                    ? CENTER_CLUTCH_PLATE_MOUNT_Y_OFFSET
                    : h - CENTER_CLUTCH_PLATE_MOUNT_Y_OFFSET),
                CENTER_CLUTCH_PLATE_Z - CENTER_CLUTCH_PLATE_T - EPS
            ])
                cylinder(
                    d = CENTER_CLUTCH_M3_CLEAR_D,
                    h = CENTER_CLUTCH_PLATE_T + CENTER_CLUTCH_PLATE_KEY_D
                        + 2 * EPS,
                    $fn = 40
                );
        // The center 2GT loop crosses this plate on its way from the rear
        // output rotor to the front drawer pulley. This is a true through
        // opening in the service plate, not a transparent preview hint.
        center_clutch_plate_belt_passage(col, row);
    }
}

module center_clutch_partition_support_cuts(col, row) {
    // The service plate sits 0.80 mm behind the partition. Two locating keys
    // enter captured rectangular slots; four M3 clearance holes line up with
    // the plate and are intentionally through-holes for an M3 screw plus a
    // front-side nut/washer. The thin removable back cover is not involved.
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
    plate_rear_z = CENTER_CLUTCH_PLATE_Z - CENTER_CLUTCH_PLATE_T;
    for (index = [0:1]) {
        bearing_y = center_clutch_output_bearing_y(row, index);
        center_clutch_bearing_block_y(x, bearing_y, z);
        for (sx = [-1, 1])
            center_clutch_z_arm(
                x + sx * 7.00,
                bearing_y,
                z + 5.30,
                plate_rear_z,
                2.00,
                CENTER_CLUTCH_BEARING_BLOCK_T
            );
    }
}

module center_clutch_guide_rails(col, row) {
    x = center_clutch_axis_x(col);
    rail_z = center_clutch_rail_z();
    y0 = center_clutch_rail_y0(row);
    y1 = center_clutch_rail_y1(row);
    // These are purchased round guide rods, shown as reference geometry. The
    // two rods are captured in the bored stop pads at both ends; the printed
    // carriage carries the two relieved sleeves around them.
    for (sx = [-1, 1]) {
        rail_x = x + sx * CENTER_CLUTCH_RAIL_X_OFFSET;
        cylinder_y(
            rail_x,
            y0 - CENTER_CLUTCH_GUIDE_ROD_CAPTURE,
            rail_z,
            CENTER_CLUTCH_GUIDE_ROD_D,
            y1 - y0 + 2 * CENTER_CLUTCH_GUIDE_ROD_CAPTURE
        );
    }
}
//#endregion

//#region 公开 API：输入滑架、直线轴承套与实体止挡
module center_clutch_linear_bearing_holder_y(x, y, z) {
    y0 = y - CENTER_CLUTCH_LINEAR_BEARING_HOLDER_L / 2;
    y1 = y + CENTER_CLUTCH_LINEAR_BEARING_HOLDER_L / 2;
    difference() {
        // The printed body is a two-datum holder: the 7.20 mm seat is bored
        // from the front, while the 0.80 mm rear shoulder stops the purchased
        // 3x7x10 bearing. The front neck receives the separate snap/press cap.
        union() {
            cylinder_y(
                x,
                y0,
                z,
                CENTER_CLUTCH_LINEAR_BEARING_HOLDER_OD,
                CENTER_CLUTCH_LINEAR_BEARING_HOLDER_L
                    - CENTER_CLUTCH_LINEAR_BEARING_HOLDER_FRONT_NECK_L
                    + EPS
            );
            cylinder_y(
                x,
                y1 - CENTER_CLUTCH_LINEAR_BEARING_HOLDER_FRONT_NECK_L - EPS,
                z,
                CENTER_CLUTCH_LINEAR_BEARING_HOLDER_FRONT_NECK_D,
                CENTER_CLUTCH_LINEAR_BEARING_HOLDER_FRONT_NECK_L + EPS
            );
        }
        // The rod bore is deliberately larger than the nominal rod so the
        // printed holder never becomes the sliding surface.
        cylinder_y(
            x,
            y0 - EPS,
            z,
            CENTER_CLUTCH_GUIDE_ROD_POCKET_D,
            CENTER_CLUTCH_LINEAR_BEARING_HOLDER_L + 2 * EPS
        );
        // The bearing seat is Ø7.20 mm for a nominal Ø7.00 mm bearing. Its
        // 10.80 mm depth leaves the 0.80 mm front recess for the cap's inner
        // retaining lip while the bearing remains seated against the rear.
        cylinder_y(
            x,
            y0 + CENTER_CLUTCH_LINEAR_BEARING_HOLDER_BACK_SHOULDER_T,
            z,
            CENTER_CLUTCH_LINEAR_BEARING_SEAT_D,
            CENTER_CLUTCH_LINEAR_BEARING_SEAT_DEPTH + EPS
        );
    }
}

module center_clutch_linear_bearing_retainer_y(x, y1, z) {
    // Printed front cap. The large flange captures the bearing end, the
    // narrow inner lip reaches into the 0.80 mm front recess, and the outer
    // skirt locates on the holder's reduced front neck. No screw or spring is
    // needed for this first-article retention interface.
    difference() {
        union() {
            cylinder_y(
                x,
                y1 - EPS,
                z,
                CENTER_CLUTCH_LINEAR_BEARING_RETAINER_OD,
                CENTER_CLUTCH_LINEAR_BEARING_RETAINER_T + EPS
            );
            cylinder_y(
                x,
                y1 - CENTER_CLUTCH_LINEAR_BEARING_HOLDER_BACK_SHOULDER_T,
                z,
                CENTER_CLUTCH_LINEAR_BEARING_RETAINER_LIP_OD,
                CENTER_CLUTCH_LINEAR_BEARING_HOLDER_BACK_SHOULDER_T + EPS
            );
            cylinder_y(
                x,
                y1 - CENTER_CLUTCH_LINEAR_BEARING_RETAINER_SKIRT_L,
                z,
                CENTER_CLUTCH_LINEAR_BEARING_RETAINER_SKIRT_OD,
                CENTER_CLUTCH_LINEAR_BEARING_RETAINER_SKIRT_L + 2 * EPS
            );
        }
        union() {
            cylinder_y(
                x,
                y1 - CENTER_CLUTCH_LINEAR_BEARING_HOLDER_BACK_SHOULDER_T - EPS,
                z,
                CENTER_CLUTCH_LINEAR_BEARING_RETAINER_ID,
                CENTER_CLUTCH_LINEAR_BEARING_HOLDER_BACK_SHOULDER_T + 3 * EPS
            );
            cylinder_y(
                x,
                y1 - CENTER_CLUTCH_LINEAR_BEARING_RETAINER_SKIRT_L,
                z,
                CENTER_CLUTCH_LINEAR_BEARING_RETAINER_SKIRT_ID,
                CENTER_CLUTCH_LINEAR_BEARING_RETAINER_SKIRT_L + 3 * EPS
            );
        }
    }
}

module center_clutch_input_carriage(col, row, engaged = false) {
    x = center_clutch_axis_x(col);
    z = center_clutch_axis_z();
    base_y = center_clutch_input_base_y(row);
    shift = CENTER_CLUTCH_TRAVEL_MM;
    rail_z = center_clutch_rail_z();
    translate([0, shift, 0]) {
        for (index = [0:1])
            center_clutch_bearing_block_y(
                x,
                center_clutch_input_bearing_y(row, index),
                z
            );

        // Side uprights connect the bearing blocks to exactly two linear-bearing
        // holders: sx=-1 is left and sx=+1 is right in world X.  The two
        // rotary bearing blocks above are a separate axial support pair; they
        // must not be read as a second pair of vertical guide bearings.
        for (sx = [-1, 1]) {
            translate([
                x + sx * CENTER_CLUTCH_CARRIAGE_UPRIGHT_CENTER_X_OFFSET
                    - CENTER_CLUTCH_CARRIAGE_UPRIGHT_X_T / 2,
                base_y + CENTER_CLUTCH_CARRIAGE_UPRIGHT_Y0,
                z + CENTER_CLUTCH_CARRIAGE_UPRIGHT_Z0
            ])
                cube([
                    CENTER_CLUTCH_CARRIAGE_UPRIGHT_X_T,
                    CENTER_CLUTCH_CARRIAGE_UPRIGHT_L,
                    CENTER_CLUTCH_CARRIAGE_UPRIGHT_H
                ]);
            center_clutch_linear_bearing_holder_y(
                x + sx * CENTER_CLUTCH_RAIL_X_OFFSET,
                base_y
                    + CENTER_CLUTCH_CARRIAGE_SHOE_Y0
                    + CENTER_CLUTCH_CARRIAGE_SHOE_L / 2,
                rail_z
            );
        }
    }
}

module center_clutch_linear_bearing_retainers(col, row, engaged = false) {
    x = center_clutch_axis_x(col);
    z = center_clutch_axis_z();
    shift = CENTER_CLUTCH_TRAVEL_MM;
    color("#8aa1ad")
        // One removable cap on each side guide rod.  These are left/right
        // retainers, not two retainers stacked above and below one rod.
        for (sx = [-1, 1])
            center_clutch_linear_bearing_retainer_y(
                x + sx * CENTER_CLUTCH_RAIL_X_OFFSET,
                center_clutch_linear_bearing_front_y(row) + shift,
                center_clutch_rail_z()
            );
}

module center_clutch_stop_bar(col, row, y) {
    x = center_clutch_axis_x(col);
    rail_x_offset = CENTER_CLUTCH_RAIL_X_OFFSET;
    rail_z = center_clutch_rail_z();
    plate_rear_z = CENTER_CLUTCH_PLATE_Z - CENTER_CLUTCH_PLATE_T;
    // Two short end caps sit just outward of the rod axes. Their 4.0 mm square
    // section is wider than the 3.0 mm rod plus clearance, while the outward
    // offset leaves the carriage uprights and central bearing blocks outside
    // the stop solid. A blind rod pocket at each inner face captures the
    // purchased rod axially; the rod, not a printed square face, carries the
    // sliding load.
    for (sx = [-1, 1]) {
        rail_x = x + sx * rail_x_offset;
        stop_x = x + sx * (rail_x_offset + CENTER_CLUTCH_STOP_PAD_X_OFFSET);
        stop_is_before_rail = y < center_clutch_rail_y0(row);
        difference() {
            translate([
                stop_x - CENTER_CLUTCH_STOP_PAD_W / 2,
                y,
                rail_z - CENTER_CLUTCH_STOP_PAD_Z / 2
            ])
                cube([
                    CENTER_CLUTCH_STOP_PAD_W,
                    CENTER_CLUTCH_STOP_PAD_T,
                    CENTER_CLUTCH_STOP_PAD_Z
                ]);
            rod_pocket_y0 = stop_is_before_rail
                ? y + CENTER_CLUTCH_STOP_PAD_T
                    - CENTER_CLUTCH_GUIDE_ROD_CAPTURE
                : y;
            translate([rail_x, rod_pocket_y0 - EPS, rail_z])
                rotate([-90, 0, 0])
                    cylinder(
                        d = CENTER_CLUTCH_GUIDE_ROD_POCKET_D,
                        h = CENTER_CLUTCH_GUIDE_ROD_CAPTURE + 2 * EPS,
                        $fn = 48
                    );
        }
        center_clutch_z_arm(
            stop_x + sx * CENTER_CLUTCH_STOP_PAD_W / 2,
            y + CENTER_CLUTCH_STOP_PAD_T / 2,
            rail_z - CENTER_CLUTCH_STOP_PAD_Z / 2,
            plate_rear_z,
            2.00,
            CENTER_CLUTCH_STOP_PAD_T
        );
    }
}

module center_clutch_stops(col, row) {
    center_clutch_stop_bar(col, row, center_clutch_open_stop_y(row));
    center_clutch_stop_bar(col, row, center_clutch_engaged_stop_y(row));
}
//#endregion

//#region 公开 API：独立轴与采购件参考
module center_clutch_input_shaft(col, row, engaged = false) {
    x = center_clutch_axis_x(col);
    z = center_clutch_axis_z();
    shift = CENTER_CLUTCH_TRAVEL_MM;
    color(COLOR_SHAFT)
        d_rod_y(
            x,
            center_clutch_input_base_y(row)
                + CENTER_CLUTCH_SHAFT_INPUT_START
                + shift,
            z,
            CENTER_CLUTCH_SHAFT_INPUT_LENGTH
        );
    for (index = [0:1])
        center_clutch_shaft_collar_y(
            x,
            center_clutch_input_bearing_y(row, index)
                - CENTER_CLUTCH_BEARING_BLOCK_T / 2
                - CENTER_CLUTCH_SHAFT_COLLAR_T
                + shift,
            z
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

module center_clutch_input_bearings(col, row, engaged = false) {
    x = center_clutch_axis_x(col);
    z = center_clutch_axis_z();
    shift = CENTER_CLUTCH_TRAVEL_MM;
    color("#cfd4da")
        // Two purchased rotary bearings on the input rotor, axially spaced
        // along Y.  Both move with the input carriage; this is not the
        // left/right linear-guidance pair.
        for (index = [0:1])
            translate([0, shift, 0])
                center_clutch_bearing_reference_y(
                    x,
                    center_clutch_input_bearing_y(row, index)
                        + CENTER_CLUTCH_BEARING_REFERENCE_CENTER_OFFSET,
                    z
                );
}

module center_clutch_output_bearings(col, row) {
    x = center_clutch_axis_x(col);
    z = center_clutch_axis_z();
    color("#cfd4da")
        // Two purchased rotary bearings on the fixed output rotor, axially
        // spaced along Y.  The output pair remains in the fixed cage.
        for (index = [0:1])
            center_clutch_bearing_reference_y(
                x,
                center_clutch_output_bearing_y(row, index)
                    + CENTER_CLUTCH_BEARING_REFERENCE_CENTER_OFFSET,
                z
                );
}

module center_clutch_linear_bearing_reference_y(x, y, z) {
    // Purchased LM3UU-class reference: nominal Ø3 bore, Ø7 housing and
    // 10 mm axial length. Keep the exact envelope and coaxial bore visible;
    // the ball rows are a supplier detail, not a printed geometry claim.
    translate([x, y, z])
        rotate([90, 0, 0])
            difference() {
                cylinder(
                    d = CENTER_CLUTCH_LINEAR_BEARING_OD,
                    h = CENTER_CLUTCH_LINEAR_BEARING_L,
                    center = true,
                    $fn = 64
                );
                cylinder(
                    d = CENTER_CLUTCH_LINEAR_BEARING_ID,
                    h = CENTER_CLUTCH_LINEAR_BEARING_L + 2 * EPS,
                    center = true,
                    $fn = 48
                );
            }
}

module center_clutch_linear_bearings(col, row, engaged = false) {
    x = center_clutch_axis_x(col);
    z = center_clutch_rail_z();
    shift = CENTER_CLUTCH_TRAVEL_MM;
    color("#b7c0c8")
        for (sx = [-1, 1])
            center_clutch_linear_bearing_reference_y(
                x + sx * CENTER_CLUTCH_RAIL_X_OFFSET,
                center_clutch_linear_bearing_center_y(row) + shift,
                z
            );
}

module center_clutch_purchased_references(col, row, engaged = false) {
    center_clutch_input_shaft(col, row, engaged);
    center_clutch_output_shaft(col, row);
    center_clutch_input_bearings(col, row, engaged);
    center_clutch_output_bearings(col, row);
    center_clutch_linear_bearings(col, row, engaged);
}
//#endregion

//#region 公开 API：中心机构总装
module center_clutch_carrier(col, row, engaged = false, purchased = true) {
    color("#536d78") center_clutch_mechanism_plate(col, row);
    color("#4c6470") center_clutch_output_cage(col, row);
    color("#657f8c") center_clutch_guide_rails(col, row);
    color("#d26b38") center_clutch_stops(col, row);
    color("#748c99") center_clutch_input_carriage(col, row, engaged);
    center_clutch_linear_bearing_retainers(col, row, engaged);
    if (purchased)
        center_clutch_purchased_references(col, row, engaged);
}
//#endregion

//#region 业务校验
assert(CENTER_CLUTCH_BEARING_SEAT_D > CENTER_CLUTCH_BEARING_OD,
    "center bearing seat must clear the purchased bearing OD");
assert(CENTER_CLUTCH_BEARING_SEAT_D >= 6.10,
    "center bearing seat starts at the 6.10 mm FDM coupon datum");
assert(CENTER_CLUTCH_BEARING_SEAT_DEPTH
        >= CENTER_CLUTCH_BEARING_W + 0.40,
    "blind bearing seat needs a rear axial shoulder");
assert(abs(
        CENTER_CLUTCH_BEARING_REFERENCE_CENTER_OFFSET
        + CENTER_CLUTCH_BEARING_BACK_SHOULDER_T
    ) < 0.001,
    "bearing reference must sit toward the open side of the blind seat");
assert(CENTER_CLUTCH_SHAFT_COLLAR_OD > CENTER_CLUTCH_BEARING_OD,
    "shaft retaining ring must capture the bearing inner stack");
assert(CENTER_CLUTCH_SHAFT_COLLAR_BORE_D > CENTER_CLUTCH_BEARING_ID,
    "shaft retaining ring must pass the 3 mm D shaft");
assert(CENTER_CLUTCH_SHAFT_INPUT_START
        + CENTER_CLUTCH_SHAFT_INPUT_LENGTH
        <= GT2_D_BORE_DEPTH + 0.001,
    "input D shaft must stop at the blind gear socket before the solid dog");
assert(CENTER_CLUTCH_LINEAR_BEARING_COUNT == 2,
    "center carriage needs one purchased linear bearing on each guide rod");
assert(abs(CENTER_CLUTCH_LINEAR_BEARING_ID
        - CENTER_CLUTCH_GUIDE_ROD_D) < 0.001,
    "linear bearing bore must match the nominal 3 mm guide rod");
assert(CENTER_CLUTCH_LINEAR_BEARING_SEAT_D
        >= CENTER_CLUTCH_LINEAR_BEARING_OD + 0.20 - 0.001,
    "linear bearing seat needs the initial 0.10 mm radial FDM clearance");
assert(CENTER_CLUTCH_LINEAR_BEARING_HOLDER_OD
        >= CENTER_CLUTCH_LINEAR_BEARING_SEAT_D + 4.0,
    "linear bearing holder must leave a printable radial wall");
assert(CENTER_CLUTCH_LINEAR_BEARING_SEAT_DEPTH
        >= CENTER_CLUTCH_LINEAR_BEARING_HOLDER_BACK_SHOULDER_T
            + CENTER_CLUTCH_LINEAR_BEARING_L - 0.001,
    "linear bearing holder seat must contain the 10 mm bearing and rear shoulder");
assert(CENTER_CLUTCH_LINEAR_BEARING_HOLDER_L
        >= CENTER_CLUTCH_LINEAR_BEARING_HOLDER_BACK_SHOULDER_T
            + CENTER_CLUTCH_LINEAR_BEARING_L
            + CENTER_CLUTCH_LINEAR_BEARING_RETAINER_T - 0.001,
    "linear bearing holder must leave a front recess for the retaining cap");
assert(CENTER_CLUTCH_LINEAR_BEARING_HOLDER_FRONT_NECK_D
        < CENTER_CLUTCH_LINEAR_BEARING_HOLDER_OD
        && CENTER_CLUTCH_LINEAR_BEARING_HOLDER_FRONT_NECK_L > 0,
    "linear bearing holder must provide a reduced front neck for the cap");
assert(CENTER_CLUTCH_LINEAR_BEARING_RETAINER_ID
        > CENTER_CLUTCH_LINEAR_BEARING_ID
        && CENTER_CLUTCH_LINEAR_BEARING_RETAINER_ID
            < CENTER_CLUTCH_LINEAR_BEARING_OD,
    "retaining cap inner opening must pass the rod and capture the bearing");
assert(CENTER_CLUTCH_LINEAR_BEARING_RETAINER_OD
        > CENTER_CLUTCH_LINEAR_BEARING_HOLDER_OD
        && CENTER_CLUTCH_LINEAR_BEARING_RETAINER_T > 0,
    "retaining cap must overlap the holder front and have positive thickness");
assert(CENTER_CLUTCH_LINEAR_BEARING_RETAINER_LIP_OD
        <= CENTER_CLUTCH_LINEAR_BEARING_OD + 0.001,
    "retaining cap inner lip must stay inside the bearing seat envelope");
assert(CENTER_CLUTCH_LINEAR_BEARING_RETAINER_SKIRT_ID
        > CENTER_CLUTCH_LINEAR_BEARING_HOLDER_FRONT_NECK_D,
    "retaining cap skirt must clear the holder front neck");
assert(CENTER_CLUTCH_LINEAR_BEARING_RETAINER_SKIRT_OD
        > CENTER_CLUTCH_LINEAR_BEARING_RETAINER_SKIRT_ID
        && CENTER_CLUTCH_LINEAR_BEARING_RETAINER_SKIRT_L
            >= CENTER_CLUTCH_LINEAR_BEARING_HOLDER_FRONT_NECK_L,
    "retaining cap skirt must form a positive locating wall");
assert(CENTER_CLUTCH_LINEAR_BEARING_ROD_NOMINAL_CLEARANCE >= -0.001,
    "linear bearing and guide rod nominal bore relationship must be non-negative");
assert(CENTER_CLUTCH_SIDE_CLEARANCE >= 0.30,
    "carriage side datum needs at least 0.30 mm stop-pad clearance");
assert(CENTER_CLUTCH_GUIDE_ROD_CAPTURE > 0
        && CENTER_CLUTCH_GUIDE_ROD_CAPTURE < CENTER_CLUTCH_STOP_PAD_T,
    "guide rod end capture must fit inside the stop pad");
assert(CENTER_CLUTCH_TRAVEL_MM >= -0.001
        && CENTER_CLUTCH_TRAVEL_MM <= GT2_CLUTCH_ENGAGE_STROKE_MM + 0.001,
    "center clutch travel override must stay within the open/engaged datums");
assert(CENTER_CLUTCH_RAIL_X_OFFSET > CENTER_CLUTCH_BEARING_BLOCK_X / 2,
    "guide rails must stand outside the rotor bearing block");
assert(CENTER_CLUTCH_RAIL_Z_OFFSET > CENTER_CLUTCH_BEARING_BLOCK_Z / 2,
    "guide rails must stand outside the rotor envelope");
assert(sqrt(
        pow(CENTER_CLUTCH_RAIL_X_OFFSET, 2)
        + pow(CENTER_CLUTCH_RAIL_Z_OFFSET, 2)
    ) - CENTER_CLUTCH_LINEAR_BEARING_HOLDER_OD / 2 - gt2_male_tip_r()
        >= 0.45,
    "linear bearing holder must clear the input rotor radial envelope");
assert(CENTER_CLUTCH_PLATE_Z < WORLD_PARTITION_BACK_Z,
    "mechanism plate must remain in the rear cavity behind the partition");
assert(CENTER_CLUTCH_PLATE_Z - CENTER_CLUTCH_PLATE_T
        > -D + WORLD_BACK_PANEL_T + 1.0,
    "mechanism plate must clear the thin removable back cover");
assert(CENTER_CLUTCH_PLATE_BELT_PASSAGE_HALF_X
        < CENTER_CLUTCH_PLATE_MOUNT_X_OFFSET
            - CENTER_CLUTCH_M3_CLEAR_D / 2 - 0.50,
    "center belt passage must leave the M3 mounting holes outside its slot");
assert(CENTER_CLUTCH_PLATE_BELT_PASSAGE_Y < center_clutch_plate_h(CENTER_GT2_ROW),
    "center belt passage must leave solid plate material above and below");
assert(abs(
        CENTER_CLUTCH_OPEN_STOP_Y + CENTER_CLUTCH_STOP_PAD_T
        - CENTER_CLUTCH_CARRIAGE_SHOE_Y0
    ) < 0.001,
    "open hard stop must meet the carriage shoe lower face");
assert(abs(
        CENTER_CLUTCH_ENGAGED_STOP_Y
        - (CENTER_CLUTCH_CARRIAGE_SHOE_Y1
            + GT2_CLUTCH_ENGAGE_STROKE_MM)
    ) < 0.001,
    "engaged hard stop must meet the carriage shoe upper face");
assert(abs(
        center_clutch_rail_y0(CENTER_GT2_ROW)
        - (center_clutch_input_base_y(CENTER_GT2_ROW)
            + CENTER_CLUTCH_CARRIAGE_SHOE_Y0)
    ) < 0.001,
    "guide rail lower face must meet the open shoe envelope");
assert(abs(
        center_clutch_rail_y1(CENTER_GT2_ROW)
        - (center_clutch_input_base_y(CENTER_GT2_ROW)
            + CENTER_CLUTCH_CARRIAGE_SHOE_Y1
            + GT2_CLUTCH_ENGAGE_STROKE_MM)
    ) < 0.001,
    "guide rail upper face must meet the engaged shoe envelope");
assert(center_clutch_rail_length(CENTER_GT2_ROW)
        >= CENTER_CLUTCH_CARRIAGE_SHOE_L
            + GT2_CLUTCH_ENGAGE_STROKE_MM - 0.001,
    "guide rails must retain the moving carriage through the full stroke");
assert(CENTER_CLUTCH_STOP_PAD_W > CENTER_CLUTCH_GUIDE_ROD_POCKET_D,
    "stop pad must overhang the guide rod pocket");
assert(
    CENTER_CLUTCH_RAIL_X_OFFSET + CENTER_CLUTCH_STOP_PAD_X_OFFSET
        - CENTER_CLUTCH_STOP_PAD_W / 2
        >= CENTER_CLUTCH_CARRIAGE_UPRIGHT_CENTER_X_OFFSET
            + CENTER_CLUTCH_CARRIAGE_UPRIGHT_X_T / 2
            + CENTER_CLUTCH_RAIL_CLEAR,
    "stop pad must clear the carriage upright outer edge"
);
assert(
    CENTER_CLUTCH_RAIL_X_OFFSET + CENTER_CLUTCH_STOP_PAD_X_OFFSET
        + CENTER_CLUTCH_STOP_PAD_W / 2
        <= CENTER_CLUTCH_RAIL_X_OFFSET
            + CENTER_CLUTCH_SHOE_OUTER / 2 + 0.001,
    "stop pad must remain within the linear-bearing holder outer envelope"
);
assert(center_clutch_output_bearing_y(CENTER_GT2_ROW, 1)
        + CENTER_CLUTCH_BEARING_BLOCK_T / 2
        < center_clutch_plate_y1(CENTER_GT2_ROW) + 0.01,
    "output bearing cage must stay inside the mechanism plate service envelope");
//#endregion
