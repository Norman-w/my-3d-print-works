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
//   guides               one purchased 3 mm round guide rod on the male
//                        rotor axis, axially behind the input D-shaft, with
//                        exactly one purchased 3x7x10 linear bearing; the
//                        moving carriage carries one printed bearing holder
//                        and one removable cap
//   limit                printed open and engaged hard stops; magnets never
//                        define the final travel
//   material             PETG functional first article; PLA is fit-only
//   purchased            two independent 3 mm D shafts, four 3x6x2 rotary
//                        bearings, one 3x7x10 linear bearing, four nominal
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
// The input rotary pair stays close enough to the male gear for the moving
// D-shaft to be supported by both blind seats.  The coaxial LM3UU is placed
// behind the shaft's rear end; a 0.40 mm axial gap keeps two purchased rods
// from becoming one overlapping solid while the carriage completes its 3 mm
// travel.  The fixed output cage keeps the shorter 4.20 mm offset.
CENTER_CLUTCH_INPUT_BEARING_CENTER_OFFSET = 7.50;

CENTER_CLUTCH_GUIDE_ROD_D = 3.00;
CENTER_CLUTCH_GUIDE_ROD_CAPTURE = 0.80;
CENTER_CLUTCH_GUIDE_ROD_POCKET_D = CENTER_CLUTCH_GUIDE_ROD_D + 0.30;

// The vertical carriage uses one purchased LM3UU-class linear bearing on a
// single captured rod that shares the male rotor's X/Z axis.  Its axial Y
// station is behind the complete input D-shaft and rotary-bearing stack, with
// the selector shoe and gear kept clear of the holder/cap.  The bearing is
// modeled as a separate reference part; only the holder, support web and
// removable printed cap belong to the carriage's printed output.  These are
// first-article FDM values and still require a fit coupon.
CENTER_CLUTCH_LINEAR_BEARING_ID = 3.00;
CENTER_CLUTCH_LINEAR_BEARING_OD = 7.00;
CENTER_CLUTCH_LINEAR_BEARING_L = 10.00;
CENTER_CLUTCH_LINEAR_BEARING_COUNT = 1;
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
CENTER_CLUTCH_LINEAR_BEARING_CENTER_Y_OFFSET = -24.50;
CENTER_CLUTCH_LINEAR_BEARING_RETAINER_ID = 6.40;
CENTER_CLUTCH_LINEAR_BEARING_RETAINER_OD = 12.40;
CENTER_CLUTCH_LINEAR_BEARING_RETAINER_T = 0.80;
CENTER_CLUTCH_LINEAR_BEARING_RETAINER_LIP_OD = 7.00;
CENTER_CLUTCH_LINEAR_BEARING_RETAINER_SKIRT_ID = 11.00;
CENTER_CLUTCH_LINEAR_BEARING_RETAINER_SKIRT_OD = 11.60;
CENTER_CLUTCH_LINEAR_BEARING_RETAINER_SKIRT_L = 1.00;
CENTER_CLUTCH_LINEAR_BEARING_ROD_NOMINAL_CLEARANCE =
    CENTER_CLUTCH_LINEAR_BEARING_ID - CENTER_CLUTCH_GUIDE_ROD_D;

// The purchased LM3UU reference keeps the exact 3x7x10 mm envelope while
// making the sleeve, seals and four ball rows readable in the browser. The
// near-side window is a display cutaway only; it is never part of the printed
// carriage and does not change the procurement envelope.
CENTER_CLUTCH_LINEAR_BEARING_BODY_L = 8.80;
CENTER_CLUTCH_LINEAR_BEARING_SEAL_L = 0.60;
CENTER_CLUTCH_LINEAR_BEARING_BALL_D = 0.72;
CENTER_CLUTCH_LINEAR_BEARING_BALL_PITCH_R = 2.15;
CENTER_CLUTCH_LINEAR_BEARING_BALL_ROWS = [-3.30, -1.10, 1.10, 3.30];
CENTER_CLUTCH_LINEAR_BEARING_BALLS_PER_ROW = 8;
CENTER_CLUTCH_LINEAR_BEARING_CUTAWAY_DEPTH =
    CENTER_CLUTCH_LINEAR_BEARING_OD / 2
        - CENTER_CLUTCH_LINEAR_BEARING_ID / 2 - 0.08;

// A compact printed coupon is exported separately from the mechanism. The
// first row samples the three FDM seat diameters; the single-rod frame checks
// the coaxial guide behind the male rotor and one real bearing; the bottom row provides free
// caps for the actual holder neck. These are fit-tuning data, not new
// assembly datums.
CENTER_CLUTCH_FIT_COUPON_FRAME_W = 10.00;
CENTER_CLUTCH_FIT_COUPON_FRAME_L = 34.00;
CENTER_CLUTCH_FIT_COUPON_FRAME_BASE_Z = -9.00;
CENTER_CLUTCH_FIT_COUPON_FRAME_BASE_T = 2.00;
CENTER_CLUTCH_FIT_COUPON_END_BLOCK_Y = 4.00;
CENTER_CLUTCH_FIT_COUPON_END_BLOCK_Z0 = -7.00;
CENTER_CLUTCH_FIT_COUPON_END_BLOCK_H = 14.00;
CENTER_CLUTCH_FIT_COUPON_CARRIAGE_CENTER_Y = 17.00;
CENTER_CLUTCH_FIT_COUPON_SEAT_SAMPLE_Z = 18.00;
CENTER_CLUTCH_FIT_COUPON_CAP_SAMPLE_Z = -18.00;
CENTER_CLUTCH_FIT_COUPON_SEAT_VARIANTS = [7.20, 7.30, 7.40];

// Internal side-clearance datum for the stop-pad/upright layout. It is not a
// bearing running clearance and is intentionally not exported as one.
CENTER_CLUTCH_SIDE_CLEARANCE = 0.30;
// The single guide is a purchased rod, not a printed square rail. Its X/Z
// offsets are the radial placement of the rod center from the mating axis.
// Both are zero: the LM3UU is coaxial with the input male rotor.
CENTER_CLUTCH_GUIDE_ROD_X_OFFSET = 0.00;
CENTER_CLUTCH_GUIDE_ROD_Z_OFFSET = 0.00;
// Keep the rail aliases for the existing scene/validator API while making the
// signed placement explicit: X=0 and Z=0 put the guide on the male rotor
// axis.  Its Y span is behind the moving input shaft at both end states.
CENTER_CLUTCH_RAIL_W = CENTER_CLUTCH_GUIDE_ROD_D;
CENTER_CLUTCH_RAIL_Z = CENTER_CLUTCH_GUIDE_ROD_D;
CENTER_CLUTCH_RAIL_CLEAR = CENTER_CLUTCH_SIDE_CLEARANCE;
CENTER_CLUTCH_RAIL_X_OFFSET = CENTER_CLUTCH_GUIDE_ROD_X_OFFSET;
CENTER_CLUTCH_RAIL_Z_OFFSET = CENTER_CLUTCH_GUIDE_ROD_Z_OFFSET;
CENTER_CLUTCH_SHOE_L = CENTER_CLUTCH_LINEAR_BEARING_HOLDER_L;
CENTER_CLUTCH_SHOE_OUTER = CENTER_CLUTCH_LINEAR_BEARING_HOLDER_OD;

// The upright is deliberately outside the input rotor's radial envelope. Keep
// its four datums named so the interference audit consumes the same values as
// the printed carriage instead of copying a clearance number into Python.
CENTER_CLUTCH_CARRIAGE_UPRIGHT_CENTER_X_OFFSET = 6.20;
CENTER_CLUTCH_CARRIAGE_UPRIGHT_X_T = 2.00;
CENTER_CLUTCH_CARRIAGE_UPRIGHT_Z0 = 5.20;
CENTER_CLUTCH_CARRIAGE_UPRIGHT_H = 3.00;
CENTER_CLUTCH_CARRIAGE_UPRIGHT_Y0 =
    CENTER_CLUTCH_LINEAR_BEARING_CENTER_Y_OFFSET
        - CENTER_CLUTCH_LINEAR_BEARING_HOLDER_L / 2
        - CENTER_CLUTCH_SIDE_CLEARANCE;
CENTER_CLUTCH_CARRIAGE_UPRIGHT_L =
    -CENTER_CLUTCH_INPUT_BEARING_CENTER_OFFSET
        + CENTER_CLUTCH_BEARING_BLOCK_T / 2
        + CENTER_CLUTCH_SIDE_CLEARANCE
        - CENTER_CLUTCH_CARRIAGE_UPRIGHT_Y0;

// The moving carriage is stopped by two dedicated side hard-stop lugs. The
// bearing-holder ends remain free to pass the guide-rod capture hardware; they
// are a seat for a purchased linear bearing, not a travel datum or a sliding
// surface. The bearing ID and the rod remain a nominal coaxial purchased-part
// interface and are not faked as a printed bearing surface.
CENTER_CLUTCH_CARRIAGE_SHOE_Y0 =
    CENTER_CLUTCH_LINEAR_BEARING_CENTER_Y_OFFSET
        - CENTER_CLUTCH_LINEAR_BEARING_HOLDER_L / 2;
CENTER_CLUTCH_CARRIAGE_SHOE_L = CENTER_CLUTCH_SHOE_L;
CENTER_CLUTCH_CARRIAGE_SHOE_Y1 = CENTER_CLUTCH_CARRIAGE_SHOE_Y0
    + CENTER_CLUTCH_CARRIAGE_SHOE_L;
CENTER_CLUTCH_STOP_PAD_T = 1.20;
CENTER_CLUTCH_STOP_PAD_W = CENTER_CLUTCH_RAIL_W + 1.00;
CENTER_CLUTCH_STOP_PAD_Z = CENTER_CLUTCH_RAIL_Z + 1.00;
CENTER_CLUTCH_STOP_PAD_X_OFFSET = 0.60;
// The side lugs are the actual open/engaged travel interfaces. They sit above
// the coaxial guide envelope, outside the male rotor radial tip, and are tied
// back to the central support web by the moving carriage bridges. The
// stationary copies are tied to the mechanism plate by short axial arms.
CENTER_CLUTCH_STOP_LUG_X_OFFSET = 10.00;
CENTER_CLUTCH_STOP_LUG_X_T = 3.00;
// The lugs sit outside the male rotor radial envelope; their carriage bridges
// return inward to the central support web at the same upper side datum.
CENTER_CLUTCH_STOP_LUG_Z_OFFSET = 5.00;
CENTER_CLUTCH_STOP_LUG_Z_T = 2.00;
// The lug support rises at the lug X datum to the removable service plate. It
// no longer needs the former long orange outer route around the rotor/cap.
CENTER_CLUTCH_STOP_LUG_ROUTE_X_OFFSET =
    CENTER_CLUTCH_STOP_LUG_X_OFFSET;
CENTER_CLUTCH_STOP_LUG_ROUTE_W = 0.80;
CENTER_CLUTCH_OPEN_STOP_Y = CENTER_CLUTCH_CARRIAGE_SHOE_Y0
    - CENTER_CLUTCH_STOP_PAD_T;
CENTER_CLUTCH_ENGAGED_STOP_Y = CENTER_CLUTCH_CARRIAGE_SHOE_Y1
    + GT2_CLUTCH_ENGAGE_STROKE_MM;

// The support web overlaps the coaxial holder at its forward end and the
// re-positioned first rotary block at its rear end. It is the printed load
// path tying the linear guide into the same moving carriage.
CENTER_CLUTCH_LINEAR_BEARING_SUPPORT_WEB_X_T = 5.00;
CENTER_CLUTCH_LINEAR_BEARING_SUPPORT_WEB_Y0 =
    CENTER_CLUTCH_LINEAR_BEARING_CENTER_Y_OFFSET
        - CENTER_CLUTCH_LINEAR_BEARING_HOLDER_L / 2
        - CENTER_CLUTCH_SIDE_CLEARANCE;
CENTER_CLUTCH_LINEAR_BEARING_SUPPORT_WEB_Y1 =
    -CENTER_CLUTCH_INPUT_BEARING_CENTER_OFFSET
        + CENTER_CLUTCH_BEARING_BLOCK_T / 2
        + CENTER_CLUTCH_SIDE_CLEARANCE;
CENTER_CLUTCH_LINEAR_BEARING_SUPPORT_WEB_Z0 = 4.00;
CENTER_CLUTCH_LINEAR_BEARING_SUPPORT_WEB_Z1 = 7.50;

// The single guide end bracket routes symmetrically to the removable service
// plate.  Its vertical legs sit outside the Ø12.4 moving cap; the lower stop
// lugs remain the actual carriage travel datums.
CENTER_CLUTCH_GUIDE_STOP_ROUTE_X_OFFSET = 9.00;
CENTER_CLUTCH_GUIDE_STOP_ROUTE_W = 1.50;

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

CENTER_CLUTCH_SHAFT_INPUT_START = -13.70;
CENTER_CLUTCH_SHAFT_INPUT_LENGTH =
    GT2_D_BORE_DEPTH - CENTER_CLUTCH_SHAFT_INPUT_START;
CENTER_CLUTCH_GUIDE_ROD_TO_INPUT_SHAFT_CLEARANCE =
    CENTER_CLUTCH_SHAFT_INPUT_START
        - (
            CENTER_CLUTCH_LINEAR_BEARING_CENTER_Y_OFFSET
                + CENTER_CLUTCH_LINEAR_BEARING_HOLDER_L / 2
                + GT2_CLUTCH_ENGAGE_STROKE_MM
                + CENTER_CLUTCH_LINEAR_BEARING_RETAINER_T
                + CENTER_CLUTCH_GUIDE_ROD_CAPTURE
        );
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

function center_clutch_linear_bearing_z() = center_clutch_axis_z()
    + CENTER_CLUTCH_GUIDE_ROD_Z_OFFSET;

function center_clutch_rail_y0(row) = center_clutch_input_base_y(row)
    + CENTER_CLUTCH_LINEAR_BEARING_CENTER_Y_OFFSET
    - CENTER_CLUTCH_LINEAR_BEARING_HOLDER_L / 2;

// Only the input carriage travels on this captured rod. The fixed output cage
// has its own z-arms to the service plate, so extending the guide to the output
// bearing stack would unnecessarily put it through the selector shoe. The rod
// spans the open and engaged holder envelopes and ends before the input D-shaft
// rear tip, leaving a real axial separation between the two purchased rods.
function center_clutch_rail_y1(row) = center_clutch_input_base_y(row)
    + CENTER_CLUTCH_LINEAR_BEARING_CENTER_Y_OFFSET
    + CENTER_CLUTCH_LINEAR_BEARING_HOLDER_L / 2
    + GT2_CLUTCH_ENGAGE_STROKE_MM;

// The engaged rod-capture bracket starts after the moving cap. This keeps the
// 0.80 mm rod capture behind the 0.80 mm retainer flange instead of making the
// same Y slice serve both as a removable cap envelope and as a hard stop.
function center_clutch_guide_rod_y1(row) = center_clutch_rail_y1(row)
    + CENTER_CLUTCH_LINEAR_BEARING_RETAINER_T
    + CENTER_CLUTCH_GUIDE_ROD_CAPTURE;

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
    - CENTER_CLUTCH_INPUT_BEARING_CENTER_OFFSET
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
        + CENTER_CLUTCH_LINEAR_BEARING_CENTER_Y_OFFSET;

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
    y1 = center_clutch_guide_rod_y1(row);
    // One purchased round guide rod is captured in the two compact end
    // brackets. It is collinear with the male rotor axis but sits behind the
    // moving input D-shaft; the rod passes through the single LM3UU carried by
    // the moving carriage and is never a printed sliding surface.
    cylinder_y(
        x + CENTER_CLUTCH_GUIDE_ROD_X_OFFSET,
        y0 - CENTER_CLUTCH_GUIDE_ROD_CAPTURE,
        rail_z,
        CENTER_CLUTCH_GUIDE_ROD_D,
        y1 - y0 + CENTER_CLUTCH_GUIDE_ROD_CAPTURE
    );
}
//#endregion

//#region 公开 API：输入滑架、直线轴承套与实体止挡
module center_clutch_linear_bearing_holder_y(
    x,
    y,
    z,
    seat_d = CENTER_CLUTCH_LINEAR_BEARING_SEAT_D
) {
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
            seat_d,
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
            // Both the bearing-side lip and the front flange must remain a
            // through-ring around the guide rod.  The previous cut stopped
            // inside the flange, leaving a blind plug at its front end; that
            // could trap the rod and was especially easy to miss in the
            // translucent assembly view.
            cylinder_y(
                x,
                y1 - CENTER_CLUTCH_LINEAR_BEARING_HOLDER_BACK_SHOULDER_T - EPS,
                z,
                CENTER_CLUTCH_LINEAR_BEARING_RETAINER_ID,
                CENTER_CLUTCH_LINEAR_BEARING_HOLDER_BACK_SHOULDER_T
                    + CENTER_CLUTCH_LINEAR_BEARING_RETAINER_T
                    + 2 * EPS
            );
            cylinder_y(
                x,
                y1 - CENTER_CLUTCH_LINEAR_BEARING_RETAINER_SKIRT_L - EPS,
                z,
                CENTER_CLUTCH_LINEAR_BEARING_RETAINER_SKIRT_ID,
                CENTER_CLUTCH_LINEAR_BEARING_RETAINER_SKIRT_L
                    + CENTER_CLUTCH_LINEAR_BEARING_RETAINER_T
                    + 2 * EPS
            );
        }
    }
}

module center_clutch_linear_bearing_fit_coupon_single_frame() {
    frame_w = CENTER_CLUTCH_FIT_COUPON_FRAME_W;
    frame_l = CENTER_CLUTCH_FIT_COUPON_FRAME_L;
    end_block_l = CENTER_CLUTCH_FIT_COUPON_END_BLOCK_Y;
    // The fixed end blocks accept one real Ø3 rod. The long open span is
    // deliberately empty so a carriage fitted with one purchased LM3UU can
    // be pushed through the complete vertical travel check by hand.
    translate([
        -frame_w / 2,
        0,
        CENTER_CLUTCH_FIT_COUPON_FRAME_BASE_Z
    ])
        cube([
            frame_w,
            frame_l,
            CENTER_CLUTCH_FIT_COUPON_FRAME_BASE_T
        ]);
    for (y0 = [
        0,
        frame_l - end_block_l
    ])
        difference() {
            translate([
                -frame_w / 2,
                y0,
                CENTER_CLUTCH_FIT_COUPON_END_BLOCK_Z0
            ])
                cube([
                    frame_w,
                    end_block_l,
                    CENTER_CLUTCH_FIT_COUPON_END_BLOCK_H
                ]);
            cylinder_y(
                0,
                y0 - EPS,
                0,
                CENTER_CLUTCH_GUIDE_ROD_POCKET_D,
                end_block_l + 2 * EPS
            );
        }

    // This is the moving test carriage. It is intentionally a separate
    // island in the STL: after printing, install one actual LM3UU, pass the
    // rod through it and slide the bridge between the end blocks. The bridge
    // is above the bearing OD so it cannot mask a bind.
    center_clutch_linear_bearing_holder_y(
        0,
        CENTER_CLUTCH_FIT_COUPON_CARRIAGE_CENTER_Y,
        0
    );
    translate([
        -CENTER_CLUTCH_LINEAR_BEARING_HOLDER_OD / 2,
        CENTER_CLUTCH_FIT_COUPON_CARRIAGE_CENTER_Y
            - CENTER_CLUTCH_LINEAR_BEARING_HOLDER_L / 2,
        CENTER_CLUTCH_LINEAR_BEARING_HOLDER_OD / 2 - 0.70
    ])
        cube([
            CENTER_CLUTCH_LINEAR_BEARING_HOLDER_OD,
            CENTER_CLUTCH_LINEAR_BEARING_HOLDER_L,
            2.00
        ]);
}

module center_clutch_linear_bearing_fit_coupon() {
    // Seat samples are ordered left-to-right: Ø7.20 / Ø7.30 / Ø7.40 mm.
    // They retain the same 0.80 mm rear shoulder and 1.00 mm cap neck as the
    // production holder, so only the FDM radial seat fit is being swept.
    for (index = [0:len(CENTER_CLUTCH_FIT_COUPON_SEAT_VARIANTS) - 1])
        center_clutch_linear_bearing_holder_y(
            (index - 1) * 16.00,
            CENTER_CLUTCH_LINEAR_BEARING_HOLDER_L / 2,
            CENTER_CLUTCH_FIT_COUPON_SEAT_SAMPLE_Z,
            CENTER_CLUTCH_FIT_COUPON_SEAT_VARIANTS[index]
        );

    // The caps are free pieces rather than fused to a holder. Fit one on the
    // installed holder after seating the bearing; the 6.40 mm opening must
    // clear the rod while the lip captures the Ø7 bearing end.
    for (index = [0:2])
        center_clutch_linear_bearing_retainer_y(
            (index - 1) * 16.00,
            CENTER_CLUTCH_LINEAR_BEARING_HOLDER_L + 5.00,
            CENTER_CLUTCH_FIT_COUPON_CAP_SAMPLE_Z
        );

    center_clutch_linear_bearing_fit_coupon_single_frame();
}

module center_clutch_linear_bearing_support_web_y(x, base_y, bearing_z) {
    // The web joins the rear side of the input rotary bearing blocks to the
    // coaxial holder. It starts above the Ø7.20 seat bore, so it cannot intrude
    // into the purchased LM3UU envelope, and it ends before the male rotor's
    // Y start. This is the printed load path for the single guide.
    translate([
        x - CENTER_CLUTCH_LINEAR_BEARING_SUPPORT_WEB_X_T / 2,
        base_y + CENTER_CLUTCH_LINEAR_BEARING_SUPPORT_WEB_Y0,
        bearing_z + CENTER_CLUTCH_LINEAR_BEARING_SUPPORT_WEB_Z0
    ])
        cube([
            CENTER_CLUTCH_LINEAR_BEARING_SUPPORT_WEB_X_T,
            CENTER_CLUTCH_LINEAR_BEARING_SUPPORT_WEB_Y1
                - CENTER_CLUTCH_LINEAR_BEARING_SUPPORT_WEB_Y0,
            CENTER_CLUTCH_LINEAR_BEARING_SUPPORT_WEB_Z1
                - CENTER_CLUTCH_LINEAR_BEARING_SUPPORT_WEB_Z0
        ]);
}

module center_clutch_carriage_stop_bridge(x, base_y, z, sx) {
    // Route each side hard-stop lug from the central carriage web at the same
    // upper-side datum. The lug remains outside the male rotor envelope and
    // does not cross the rotary bearing blocks.
    bridge_inner_x = x + sx * (
        CENTER_CLUTCH_LINEAR_BEARING_SUPPORT_WEB_X_T / 2 - 0.25
    );
    lug_inner_x = x + sx * (
        CENTER_CLUTCH_STOP_LUG_X_OFFSET
        - CENTER_CLUTCH_STOP_LUG_X_T / 2
    );
    bridge_z0 = z + CENTER_CLUTCH_STOP_LUG_Z_OFFSET - 0.60;
    translate([
        min(bridge_inner_x, lug_inner_x),
        base_y + CENTER_CLUTCH_CARRIAGE_SHOE_Y0,
        bridge_z0
    ])
        cube([
            abs(lug_inner_x - bridge_inner_x) + 0.25,
            CENTER_CLUTCH_CARRIAGE_SHOE_L,
            1.20
        ]);
}

module center_clutch_input_carriage(col, row, engaged = false) {
    x = center_clutch_axis_x(col);
    z = center_clutch_axis_z();
    base_y = center_clutch_input_base_y(row);
    shift = CENTER_CLUTCH_TRAVEL_MM;
    bearing_z = center_clutch_linear_bearing_z();
    translate([0, shift, 0]) {
        for (index = [0:1])
            center_clutch_bearing_block_y(
                x,
                center_clutch_input_bearing_y(row, index),
                z
            );

        // The two upper blocks are the input rotor's axial rotary support. The
        // one lower holder is the only vertical linear-bearing seat.
        center_clutch_linear_bearing_holder_y(
            x + CENTER_CLUTCH_GUIDE_ROD_X_OFFSET,
            base_y + CENTER_CLUTCH_LINEAR_BEARING_CENTER_Y_OFFSET,
            bearing_z
        );
        center_clutch_linear_bearing_support_web_y(x, base_y, bearing_z);
        for (sx = [-1, 1])
            center_clutch_carriage_stop_bridge(x, base_y, z, sx);

        // Side uprights keep the input rotary blocks tied together. They are
        // not vertical guide bearings and remain outside the rotor envelope.
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
            // Dedicated lower stop lug. It follows the carriage but is
            // deliberately separate from the single LM3UU cap, so the cap
            // never becomes the travel stop.
            translate([
                x + sx * CENTER_CLUTCH_STOP_LUG_X_OFFSET
                    - CENTER_CLUTCH_STOP_LUG_X_T / 2,
                base_y + CENTER_CLUTCH_CARRIAGE_SHOE_Y0,
                z + CENTER_CLUTCH_STOP_LUG_Z_OFFSET
                    - CENTER_CLUTCH_STOP_LUG_Z_T / 2
            ])
                cube([
                    CENTER_CLUTCH_STOP_LUG_X_T,
                    CENTER_CLUTCH_CARRIAGE_SHOE_L,
                    CENTER_CLUTCH_STOP_LUG_Z_T
                ]);
        }
    }
}

module center_clutch_linear_bearing_retainers(col, row, engaged = false) {
    x = center_clutch_axis_x(col);
    z = center_clutch_linear_bearing_z();
    shift = CENTER_CLUTCH_TRAVEL_MM;
    color("#8aa1ad")
        // One removable cap on the single coaxial guide rod.
        center_clutch_linear_bearing_retainer_y(
            x + CENTER_CLUTCH_GUIDE_ROD_X_OFFSET,
            center_clutch_linear_bearing_front_y(row) + shift,
            z
        );
}

module center_clutch_stop_bar(col, row, y) {
    x = center_clutch_axis_x(col);
    rail_z = center_clutch_rail_z();
    plate_rear_z = CENTER_CLUTCH_PLATE_Z - CENTER_CLUTCH_PLATE_T;
    rail_x = x + CENTER_CLUTCH_GUIDE_ROD_X_OFFSET;
    stop_is_before_rail = y < center_clutch_rail_y0(row);
    // One compact neutral end bracket captures the single rod axially. The
    // separate side lugs, not this rod bracket, define the 3 mm travel.
    difference() {
        translate([
            rail_x - CENTER_CLUTCH_STOP_PAD_W / 2,
            y,
            rail_z - CENTER_CLUTCH_STOP_PAD_Z / 2
        ])
            cube([
                CENTER_CLUTCH_STOP_PAD_W,
                CENTER_CLUTCH_STOP_PAD_T,
                CENTER_CLUTCH_STOP_PAD_Z
            ]);
        rod_pocket_y0 = stop_is_before_rail
            ? y + CENTER_CLUTCH_STOP_PAD_T - CENTER_CLUTCH_GUIDE_ROD_CAPTURE
            : y;
        translate([rail_x, rod_pocket_y0 - EPS, rail_z])
            rotate([-90, 0, 0])
                cylinder(
                    d = CENTER_CLUTCH_GUIDE_ROD_POCKET_D,
                    h = CENTER_CLUTCH_GUIDE_ROD_CAPTURE + 2 * EPS,
                    $fn = 48
                );
    }
    // Route only short support arms to the removable plate. The former long
    // orange U-shaped route was a diagnostic visual aid, not a required
    // sliding surface, so it is intentionally absent from the first article.
    for (sx = [-1, 1]) {
        route_x = x + sx * CENTER_CLUTCH_GUIDE_STOP_ROUTE_X_OFFSET;
        bridge_start = rail_x + sx * CENTER_CLUTCH_STOP_PAD_W / 2;
        if (abs(route_x - bridge_start) > EPS)
            translate([
                min(bridge_start, route_x),
                y,
                rail_z - CENTER_CLUTCH_STOP_PAD_Z / 2
            ])
                cube([
                    abs(route_x - bridge_start),
                    CENTER_CLUTCH_STOP_PAD_T,
                    CENTER_CLUTCH_STOP_PAD_Z
                ]);
        center_clutch_z_arm(
            route_x,
            y + CENTER_CLUTCH_STOP_PAD_T / 2,
            rail_z - CENTER_CLUTCH_STOP_PAD_Z / 2,
            plate_rear_z,
            CENTER_CLUTCH_GUIDE_STOP_ROUTE_W,
            CENTER_CLUTCH_STOP_PAD_T
        );
    }
}

module center_clutch_stop_lugs(col, row, y) {
    x = center_clutch_axis_x(col);
    z = center_clutch_axis_z();
    plate_rear_z = CENTER_CLUTCH_PLATE_Z - CENTER_CLUTCH_PLATE_T;
    // These are separate from the rod-capture bars. Each side lug is a
    // positive stop face for the moving carriage; its short rear arm ties into
    // the removable service-plate datum without entering the rotor/cap axis.
    for (sx = [-1, 1]) {
        lug_x = x + sx * CENTER_CLUTCH_STOP_LUG_X_OFFSET;
        lug_z = z + CENTER_CLUTCH_STOP_LUG_Z_OFFSET;
        translate([
            lug_x - CENTER_CLUTCH_STOP_LUG_X_T / 2,
            y,
            lug_z - CENTER_CLUTCH_STOP_LUG_Z_T / 2
        ])
            cube([
                CENTER_CLUTCH_STOP_LUG_X_T,
                CENTER_CLUTCH_STOP_PAD_T,
                CENTER_CLUTCH_STOP_LUG_Z_T
            ]);
        route_x = x + sx * CENTER_CLUTCH_STOP_LUG_ROUTE_X_OFFSET;
        center_clutch_z_arm(
            route_x,
            y + CENTER_CLUTCH_STOP_PAD_T / 2,
            lug_z - CENTER_CLUTCH_STOP_LUG_Z_T / 2,
            plate_rear_z,
            CENTER_CLUTCH_STOP_LUG_ROUTE_W,
            CENTER_CLUTCH_STOP_PAD_T
        );
    }
}

module center_clutch_stops(col, row) {
    open_stop_y = center_clutch_open_stop_y(row);
    engaged_stop_y = center_clutch_engaged_stop_y(row);
    center_clutch_stop_bar(col, row, open_stop_y);
    center_clutch_stop_lugs(col, row, open_stop_y);
    // The engaged rod-capture bar starts after the moving cap's flange. The
    // side lug still uses the frozen engaged stop datum, so the carriage's
    // lug face—not the bearing cap—sets the 3.00 mm stroke.
    center_clutch_stop_bar(
        col,
        row,
        engaged_stop_y + CENTER_CLUTCH_LINEAR_BEARING_RETAINER_T
    );
    center_clutch_stop_lugs(col, row, engaged_stop_y);
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
    // 10 mm axial length. It is a cutaway display model, not a printed
    // bearing: the sleeve, seals and ball rows make the load path legible
    // while the exact procurement envelope remains 3×7×10 mm.
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
                    // Rear-facing window exposes one ball track in the
                    // assembly view without changing the outer bounds.
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
        for (row_y = CENTER_CLUTCH_LINEAR_BEARING_BALL_ROWS)
            for (index = [0:CENTER_CLUTCH_LINEAR_BEARING_BALLS_PER_ROW - 1]) {
                angle = -90
                    + index * 360 / CENTER_CLUTCH_LINEAR_BEARING_BALLS_PER_ROW;
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
    x = center_clutch_axis_x(col);
    z = center_clutch_linear_bearing_z();
    shift = CENTER_CLUTCH_TRAVEL_MM;
    color("#b7c0c8")
        center_clutch_linear_bearing_reference_y(
            x + CENTER_CLUTCH_GUIDE_ROD_X_OFFSET,
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
    // The stop geometry is structural but deliberately uses the carrier
    // neutral color. The former orange diagnostic frames are not part of the
    // default visual or the printable first-article silhouette.
    color("#536d78") center_clutch_stops(col, row);
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
assert(CENTER_CLUTCH_LINEAR_BEARING_COUNT == 1,
    "center carriage needs exactly one purchased coaxial linear bearing");
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
assert(abs(
        CENTER_CLUTCH_LINEAR_BEARING_BODY_L
        + 2 * CENTER_CLUTCH_LINEAR_BEARING_SEAL_L
        - CENTER_CLUTCH_LINEAR_BEARING_L
    ) < 0.001,
    "LM3UU reference sleeve, seals and total length must keep the 10 mm envelope");
assert(CENTER_CLUTCH_LINEAR_BEARING_CUTAWAY_DEPTH > 0
        && CENTER_CLUTCH_LINEAR_BEARING_BALL_PITCH_R
            + CENTER_CLUTCH_LINEAR_BEARING_BALL_D / 2
            < CENTER_CLUTCH_LINEAR_BEARING_OD / 2,
    "LM3UU display cutaway and ball rows must stay inside the purchased envelope");
assert(len(CENTER_CLUTCH_FIT_COUPON_SEAT_VARIANTS) == 3
        && CENTER_CLUTCH_FIT_COUPON_FRAME_W
            > CENTER_CLUTCH_GUIDE_ROD_POCKET_D,
    "linear bearing fit coupon must provide three seat variants and a single rod frame");
assert(CENTER_CLUTCH_FIT_COUPON_FRAME_L > 2
        * CENTER_CLUTCH_FIT_COUPON_END_BLOCK_Y
        && CENTER_CLUTCH_FIT_COUPON_FRAME_W
            > CENTER_CLUTCH_GUIDE_ROD_POCKET_D,
    "linear bearing fit coupon must leave a usable open single-rod span");
assert(CENTER_CLUTCH_SIDE_CLEARANCE >= 0.30,
    "carriage side datum needs at least 0.30 mm stop-pad clearance");
assert(CENTER_CLUTCH_GUIDE_ROD_CAPTURE > 0
        && CENTER_CLUTCH_GUIDE_ROD_CAPTURE < CENTER_CLUTCH_STOP_PAD_T,
    "guide rod end capture must fit inside the stop pad");
assert(CENTER_CLUTCH_TRAVEL_MM >= -0.001
        && CENTER_CLUTCH_TRAVEL_MM <= GT2_CLUTCH_ENGAGE_STROKE_MM + 0.001,
    "center clutch travel override must stay within the open/engaged datums");
assert(abs(CENTER_CLUTCH_GUIDE_ROD_X_OFFSET) < 0.001,
    "coaxial guide rod must share the male rotor X axis");
assert(abs(CENTER_CLUTCH_GUIDE_ROD_Z_OFFSET) < 0.001,
    "coaxial guide rod must share the male rotor Z axis");
assert(CENTER_CLUTCH_GUIDE_ROD_TO_INPUT_SHAFT_CLEARANCE >= 0.40 - 0.001,
    "coaxial guide rod must clear the moving input D-shaft through full stroke");
assert(
    CENTER_CLUTCH_LINEAR_BEARING_CENTER_Y_OFFSET
        + CENTER_CLUTCH_LINEAR_BEARING_HOLDER_L / 2
        + GT2_CLUTCH_ENGAGE_STROKE_MM
        + CENTER_CLUTCH_LINEAR_BEARING_RETAINER_T
        + CENTER_CLUTCH_GUIDE_ROD_CAPTURE
        <= CENTER_CLUTCH_SHAFT_INPUT_START - 0.40 + 0.001,
    "coaxial guide rod capture must remain behind the input shaft");
assert(sqrt(
        pow(
            CENTER_CLUTCH_STOP_LUG_X_OFFSET
                - CENTER_CLUTCH_STOP_LUG_X_T / 2,
            2
        )
        + pow(
            CENTER_CLUTCH_STOP_LUG_Z_OFFSET
                - CENTER_CLUTCH_STOP_LUG_Z_T / 2,
            2
        )
    ) - gt2_male_tip_r() >= 0.45,
    "side travel lugs must clear the input rotor radial envelope");
assert(abs(
        CENTER_CLUTCH_STOP_LUG_ROUTE_X_OFFSET
        - CENTER_CLUTCH_STOP_LUG_X_OFFSET
    ) < 0.001,
    "side travel lug support must stay on its lug X datum");
assert(CENTER_CLUTCH_LINEAR_BEARING_SUPPORT_WEB_Z0
        > CENTER_CLUTCH_LINEAR_BEARING_SEAT_D / 2,
    "single linear-bearing support web must stay above the seat bore");
assert(CENTER_CLUTCH_LINEAR_BEARING_SUPPORT_WEB_Z1
        > CENTER_CLUTCH_LINEAR_BEARING_SUPPORT_WEB_Z0,
    "single linear-bearing support web must have positive height");
assert(CENTER_CLUTCH_LINEAR_BEARING_SUPPORT_WEB_Y1
        > CENTER_CLUTCH_LINEAR_BEARING_SUPPORT_WEB_Y0,
    "single linear-bearing support web must span the moving yoke");
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
    CENTER_CLUTCH_GUIDE_STOP_ROUTE_X_OFFSET
        - CENTER_CLUTCH_GUIDE_STOP_ROUTE_W / 2
        > CENTER_CLUTCH_LINEAR_BEARING_RETAINER_OD / 2
            + CENTER_CLUTCH_RAIL_CLEAR,
    "single guide stop support must clear the moving bearing cap"
);
assert(center_clutch_output_bearing_y(CENTER_GT2_ROW, 1)
        + CENTER_CLUTCH_BEARING_BLOCK_T / 2
        < center_clutch_plate_y1(CENTER_GT2_ROW) + 0.01,
    "output bearing cage must stay inside the mechanism plate service envelope");
//#endregion
