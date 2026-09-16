// 中心 R3C3 纯永磁离合机构载架
//
// This file is included by cabinet_clutch.scad after the native world helpers
// and the CH1 03C pair library have been defined.  It intentionally contains
// no top-level geometry: the root scene owns dispatch and this file owns only
// the removable plate, bearing cages, captured guides, carriage and stops.
//
// Mechanical contract:
//   axis                 world +Y
//   input                male rotor + its own short D shaft and two bearings;
//                        the whole set travels +Y
//   output               female rotor + its own short D shaft and two fixed
//                        bearings; it rotates in the output cage
//   guides               two captured 3 mm rails, 0.30 mm running clearance
//   limit                printed open and engaged hard stops; magnets never
//                        define the final travel
//   material             PETG functional first article; PLA is fit-only
//   purchased            two independent 3 mm D shafts, four 3x6x2 bearings,
//                        four nominal 2 mm magnets

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

CENTER_CLUTCH_RAIL_W = 3.00;
CENTER_CLUTCH_RAIL_Z = 3.00;
CENTER_CLUTCH_RAIL_CLEAR = 0.30;
CENTER_CLUTCH_RAIL_X_OFFSET = 9.00;
CENTER_CLUTCH_RAIL_Z_OFFSET = 8.00;
CENTER_CLUTCH_RAIL_ANCHOR_T = 2.40;
CENTER_CLUTCH_SHOE_L = 6.00;
CENTER_CLUTCH_SHOE_OUTER = CENTER_CLUTCH_RAIL_W
    + 2 * CENTER_CLUTCH_RAIL_CLEAR + 1.60;

// The upright is deliberately outside the input rotor's radial envelope. Keep
// its four datums named so the interference audit consumes the same values as
// the printed carriage instead of copying a clearance number into Python.
CENTER_CLUTCH_CARRIAGE_UPRIGHT_CENTER_X_OFFSET = 6.40;
CENTER_CLUTCH_CARRIAGE_UPRIGHT_X_T = 2.40;
CENTER_CLUTCH_CARRIAGE_UPRIGHT_Z0 = 5.20;
CENTER_CLUTCH_CARRIAGE_UPRIGHT_H = 3.00;
CENTER_CLUTCH_CARRIAGE_UPRIGHT_Y0 = -10.00;
CENTER_CLUTCH_CARRIAGE_UPRIGHT_L = 8.40;

CENTER_CLUTCH_CARRIAGE_STOP_TAB_Y = -9.00;
CENTER_CLUTCH_CARRIAGE_STOP_TAB_T = 1.20;
CENTER_CLUTCH_OPEN_STOP_Y = -10.20;
CENTER_CLUTCH_ENGAGED_STOP_Y = CENTER_CLUTCH_CARRIAGE_STOP_TAB_Y
    + GT2_CLUTCH_ENGAGE_STROKE_MM
    + CENTER_CLUTCH_CARRIAGE_STOP_TAB_T;
CENTER_CLUTCH_STOP_BAR_W = 22.00;
CENTER_CLUTCH_STOP_BAR_Z = CENTER_CLUTCH_RAIL_Z + 2 * CENTER_CLUTCH_RAIL_CLEAR;

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

function center_clutch_rail_y0(row) = center_clutch_input_base_y(row) - 10.50;

function center_clutch_rail_y1(row) = center_clutch_output_base_y(row) + 9.00;

function center_clutch_rail_length(row) = center_clutch_rail_y1(row)
    - center_clutch_rail_y0(row);

function center_clutch_plate_y0(row) = center_clutch_rail_y0(row) - 1.00;

function center_clutch_plate_y1(row) = center_clutch_rail_y1(row) + 1.00;

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

function center_clutch_carriage_stop_y(row) = center_clutch_input_base_y(row)
    + CENTER_CLUTCH_CARRIAGE_STOP_TAB_Y;

function center_clutch_engaged_carriage_stop_y(row) =
    center_clutch_carriage_stop_y(row) + GT2_CLUTCH_ENGAGE_STROKE_MM;
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
    plate_rear_z = CENTER_CLUTCH_PLATE_Z - CENTER_CLUTCH_PLATE_T;
    for (sx = [-1, 1]) {
        rail_x = x + sx * CENTER_CLUTCH_RAIL_X_OFFSET;
        translate([
            rail_x - CENTER_CLUTCH_RAIL_W / 2,
            y0,
            rail_z - CENTER_CLUTCH_RAIL_Z / 2
        ])
            cube([
                CENTER_CLUTCH_RAIL_W,
                y1 - y0,
                CENTER_CLUTCH_RAIL_Z
            ]);
        // End anchors tie the rails into the removable plate. The rails are
        // not cantilevered from the rotor shafts.
        for (anchor_y = [y0, y1 - CENTER_CLUTCH_RAIL_ANCHOR_T])
            center_clutch_z_arm(
                rail_x,
                anchor_y + CENTER_CLUTCH_RAIL_ANCHOR_T / 2,
                rail_z - CENTER_CLUTCH_RAIL_Z / 2,
                plate_rear_z,
                CENTER_CLUTCH_RAIL_W,
                CENTER_CLUTCH_RAIL_ANCHOR_T
            );
    }
}
//#endregion

//#region 公开 API：输入滑架与实体止挡
module center_clutch_rail_capture_shoe(x, y, z) {
    difference() {
        translate([
            x - CENTER_CLUTCH_SHOE_OUTER / 2,
            y - CENTER_CLUTCH_SHOE_L / 2,
            z - CENTER_CLUTCH_SHOE_OUTER / 2
        ])
            cube([
                CENTER_CLUTCH_SHOE_OUTER,
                CENTER_CLUTCH_SHOE_L,
                CENTER_CLUTCH_SHOE_OUTER
            ]);
        translate([
            x - (CENTER_CLUTCH_RAIL_W + 2 * CENTER_CLUTCH_RAIL_CLEAR) / 2,
            y - CENTER_CLUTCH_SHOE_L / 2 - EPS,
            z - (CENTER_CLUTCH_RAIL_Z + 2 * CENTER_CLUTCH_RAIL_CLEAR) / 2
        ])
            cube([
                CENTER_CLUTCH_RAIL_W + 2 * CENTER_CLUTCH_RAIL_CLEAR,
                CENTER_CLUTCH_SHOE_L + 2 * EPS,
                CENTER_CLUTCH_RAIL_Z + 2 * CENTER_CLUTCH_RAIL_CLEAR
            ]);
    }
}

module center_clutch_input_carriage(col, row, engaged = false) {
    x = center_clutch_axis_x(col);
    z = center_clutch_axis_z();
    base_y = center_clutch_input_base_y(row);
    shift = engaged ? GT2_CLUTCH_ENGAGE_STROKE_MM : 0;
    rail_z = center_clutch_rail_z();
    translate([0, shift, 0]) {
        for (index = [0:1])
            center_clutch_bearing_block_y(
                x,
                center_clutch_input_bearing_y(row, index),
                z
            );

        // Side uprights connect the bearing blocks to the two captured shoes
        // without crossing the input rotor's gear/dog envelope.
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
            center_clutch_rail_capture_shoe(
                x + sx * CENTER_CLUTCH_RAIL_X_OFFSET,
                base_y - 7.40,
                rail_z
            );
        }

        // This crossbar is the moving stop tab. It lands on the lower fixed
        // stop in open position and on the upper fixed stop after exactly the
        // frozen 3.00 mm stroke.
        translate([
            x - CENTER_CLUTCH_STOP_BAR_W / 2,
            base_y + CENTER_CLUTCH_CARRIAGE_STOP_TAB_Y,
            rail_z - CENTER_CLUTCH_STOP_BAR_Z / 2
        ])
            cube([
                CENTER_CLUTCH_STOP_BAR_W,
                CENTER_CLUTCH_CARRIAGE_STOP_TAB_T,
                CENTER_CLUTCH_STOP_BAR_Z
            ]);
    }
}

module center_clutch_stop_bar(col, row, y) {
    x = center_clutch_axis_x(col);
    rail_z = center_clutch_rail_z();
    plate_rear_z = CENTER_CLUTCH_PLATE_Z - CENTER_CLUTCH_PLATE_T;
    translate([
        x - CENTER_CLUTCH_STOP_BAR_W / 2,
        y,
        rail_z - CENTER_CLUTCH_STOP_BAR_Z / 2
    ])
        cube([
            CENTER_CLUTCH_STOP_BAR_W,
            CENTER_CLUTCH_CARRIAGE_STOP_TAB_T,
            CENTER_CLUTCH_STOP_BAR_Z
        ]);
    for (sx = [-1, 1])
        center_clutch_z_arm(
            x + sx * (CENTER_CLUTCH_STOP_BAR_W / 2 - 1.00),
            y + CENTER_CLUTCH_CARRIAGE_STOP_TAB_T / 2,
            rail_z - CENTER_CLUTCH_STOP_BAR_Z / 2,
            plate_rear_z,
            2.00,
            CENTER_CLUTCH_CARRIAGE_STOP_TAB_T
        );
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
    shift = engaged ? GT2_CLUTCH_ENGAGE_STROKE_MM : 0;
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
    shift = engaged ? GT2_CLUTCH_ENGAGE_STROKE_MM : 0;
    color("#cfd4da")
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
        for (index = [0:1])
            center_clutch_bearing_reference_y(
                x,
                center_clutch_output_bearing_y(row, index)
                    + CENTER_CLUTCH_BEARING_REFERENCE_CENTER_OFFSET,
                z
            );
}

module center_clutch_purchased_references(col, row, engaged = false) {
    center_clutch_input_shaft(col, row, engaged);
    center_clutch_output_shaft(col, row);
    center_clutch_input_bearings(col, row, engaged);
    center_clutch_output_bearings(col, row);
}
//#endregion

//#region 公开 API：中心机构总装
module center_clutch_carrier(col, row, engaged = false, purchased = true) {
    color("#536d78") center_clutch_mechanism_plate(col, row);
    color("#4c6470") center_clutch_output_cage(col, row);
    color("#657f8c") center_clutch_guide_rails(col, row);
    color("#d26b38") center_clutch_stops(col, row);
    color("#748c99") center_clutch_input_carriage(col, row, engaged);
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
assert(CENTER_CLUTCH_RAIL_CLEAR >= 0.30,
    "captured guides need at least 0.30 mm running clearance per side");
assert(CENTER_CLUTCH_RAIL_X_OFFSET > CENTER_CLUTCH_BEARING_BLOCK_X / 2,
    "guide rails must stand outside the rotor bearing block");
assert(CENTER_CLUTCH_RAIL_Z_OFFSET > CENTER_CLUTCH_BEARING_BLOCK_Z / 2,
    "guide rails must stand outside the rotor envelope");
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
assert(CENTER_CLUTCH_ENGAGED_STOP_Y
        >= CENTER_CLUTCH_CARRIAGE_STOP_TAB_Y
            + GT2_CLUTCH_ENGAGE_STROKE_MM
            + CENTER_CLUTCH_CARRIAGE_STOP_TAB_T,
    "engaged stop must close on the carriage stop tab after the full stroke");
assert(abs(
        CENTER_CLUTCH_ENGAGED_STOP_Y
        - (CENTER_CLUTCH_CARRIAGE_STOP_TAB_Y
            + GT2_CLUTCH_ENGAGE_STROKE_MM
            + CENTER_CLUTCH_CARRIAGE_STOP_TAB_T)
    ) < 0.001,
    "engaged hard stop must be one tab thickness above the engaged tab");
assert(center_clutch_rail_length(CENTER_GT2_ROW) > GT2_CLUTCH_ENGAGE_STROKE_MM,
    "guide rails must retain the moving carriage through the full stroke");
assert(center_clutch_output_bearing_y(CENTER_GT2_ROW, 1)
        + CENTER_CLUTCH_BEARING_BLOCK_T / 2
        < center_clutch_rail_y1(CENTER_GT2_ROW) + 1.0,
    "output bearing cage must stay inside the guide/plate service envelope");
//#endregion
