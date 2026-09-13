// SmartPartsDrawer 抽屉动力母线与弹簧离合机构
//
// Mechanical contract
// process: FDM fit prototype; gears/pulleys in PETG or nylon, metal 3 mm D rod preferred
// material: PETG/nylon for printed parts; motor, belts, springs and screws are purchased parts
// parting_plane: cabinet back face Y = D; all new drive parts stay in the rear cavity or below drawers
// opening_direction: drawers pull toward +Y; the removable back panel is also pulled toward +Y
// fastener: M3 T-head countersunk screw used as the clutch follower; motor/rod mounts are parameterized
// seal: none — this is a mechanism prototype, not a watertight enclosure
// print_orientation: gears/pulleys flat with their axis vertical; clutch carrier and fork may need supports
// units: mm
//
// Coordinate contract: X=0 is the cabinet-left side when facing the front and
// X=W is cabinet-right. When facing the back, the visual left/right order is
// reversed: the front-left motor appears on the back-right.
// The existing cabinet_params.scad is the source of the 5×5 drawer grid.

//#region 导入/依赖
QUALITY = is_undef(QUALITY) ? 2 : QUALITY;
// cabinet.scad owns the generic PART/EXPLODE variables, so use namespaced
// controls for this root entry to keep its library include side-effect free.
CLUTCH_PART = is_undef(CLUTCH_PART) ? "assembly" : CLUTCH_PART;
CLUTCH_EXPLODE = is_undef(CLUTCH_EXPLODE) ? 0 : CLUTCH_EXPLODE;
ENGAGED = is_undef(ENGAGED) ? false : ENGAGED;
SELECTED_COLUMN = is_undef(SELECTED_COLUMN) ? 2 : SELECTED_COLUMN;
SELECTED_ROW = is_undef(SELECTED_ROW) ? 2 : SELECTED_ROW;

// cabinet.scad only exports its modules when CABINET_LIB_ONLY is false.
CABINET_LIB_ONLY = true;
include <cabinet.scad>
use <../parts/motor_pololu_micro_metal_100_1_hp_6v.scad>
//#endregion

//#region 常量/配置
$fa = QUALITY <= 1 ? 10 : 6;
$fs = QUALITY <= 1 ? 0.50 : 0.24;

// HTD3M-like pitch is kept as the single timing-belt pitch for this prototype.
TIMING_PITCH_MM = 3.0;
TIMING_TEETH = 20;
TIMING_TOOTH_DEPTH = 0.86;
TIMING_PULLEY_W = 5.0;
TIMING_BELT_W = 5.0;
TIMING_BELT_T = 1.8;
TIMING_BELT_CLEAR = 0.65;

// A 3 mm D rod is the default because it matches the Pololu output shaft.
// For a long production shaft, replace the rod with a metal D shaft or increase ROD_D.
ROD_D = 3.0;
ROD_FLAT_DEPTH = 0.50;
ROD_CLEARANCE = 0.12;
ROD_FLAT_CLEARANCE = 0.12;
ROD_WALL_CLEAR = 0.35;
ROUND_AXIS_D = ROD_D;
ROUND_BORE_D = ROD_D + 2 * ROD_CLEARANCE;

// The upper clutch wheel is a 12T spur/dog prototype.  The pitch and all mating
// wheels are shared so the open/closed relation is not hidden in placements.
CLUTCH_PITCH_MM = 3.0;
CLUTCH_GEAR_TEETH = 12;
CLUTCH_GEAR_TOOTH_DEPTH = 0.82;
CLUTCH_GEAR_T = 3.0;
CLUTCH_GEAR_PITCH_R = CLUTCH_GEAR_TEETH * CLUTCH_PITCH_MM / (2 * PI);
CLUTCH_GEAR_OUTER_R = CLUTCH_GEAR_PITCH_R + CLUTCH_GEAR_TOOTH_DEPTH;
CLUTCH_DOG_TEETH = 12;
CLUTCH_DOG_TOOTH_H = 0.90;
CLUTCH_DOG_T = 3.0;
CLUTCH_DOG_R = CLUTCH_GEAR_OUTER_R;
CLUTCH_HUB_D = 4.0;
CLUTCH_CARRIER_STEM_H = 0.60;
CLUTCH_DOG_CLEAR = 0.25;
CLUTCH_ENGAGED_OVERLAP = 0.20;
CLUTCH_DROP_MM = 10.0;

// The fork compresses a spring between the stationary lower dog and the upper
// carrier.  The open gap is deliberately 2× one dog tooth height as requested.
CLUTCH_OPEN_GAP = 2 * CLUTCH_DOG_TOOTH_H;
CLUTCH_SPRING_WIRE_D = 0.65;
CLUTCH_SPRING_OD = 4.8;
CLUTCH_SPRING_TURNS = 4;
CLUTCH_SPRING_MIN_H = 0.70;
CLUTCH_SCREW_D = 3.0;
CLUTCH_SCREW_HEAD_D = 6.0;
CLUTCH_SCREW_HEAD_H = 1.35;
CLUTCH_SCREW_SHAFT_L = 9.0;
CLUTCH_SCREW_RECESS_OPEN = 2 * CLUTCH_DOG_TOOTH_H;
CLUTCH_SCREW_FLUSH = 0.18;
COMPOUND_LAYER_GAP = 0.35;

// Rear cavity locations. The horizontal bus is behind the partition; the
// complete pulley OD must clear the partition rear edge, not just its center.
// The front pulleys sit under the drawer fronts and send motion along +Y.
DRIVE_AXIS_Y = PARTITION_BACK_Y + 13.0;
// Keep the front pulley close to the face while allowing its belt turn radius
// to remain inside the cabinet instead of protruding through Y=0.
FRONT_PULLEY_Y = 14.0;
// The service corridor and motor are on the front-left side. From the back
// this same motor is therefore the right-hand boundary drive.
MOTOR_X = WALL + SERVICE_W / 2;
// The two boundary axes are not drawer columns. The current cabinet has five
// drawer transmission columns, so the complete vertical-axis count is 2 + 5.
VERTICAL_AXIS_COUNT = N_COL + 2;
BUS_BOTTOM_Z = GRID_ORIGIN_Z - 5.0;
BUS_TOP_Z = H - WALL - 7.0;
MOTOR_FACE_Z = BUS_BOTTOM_Z - 28.0;
MOTOR_BODY_L = 25.6;
MOTOR_SHAFT_L = 9.0;
ROD_BOTTOM_Z = BUS_BOTTOM_Z - 6.0;
ROD_TOP_Z = BUS_TOP_Z + 6.0;
LEFT_D_AXIS_Z0 = MOTOR_FACE_Z + MOTOR_SHAFT_L - 1.0;

// The front-right idler runs in the rear cavity and is deliberately outboard
// of the 5 drawer axes; its receiver forms a short right-side extension.
// From the back this axis is on the left side of the view.
TIMING_PITCH_R = TIMING_TEETH * TIMING_PITCH_MM / (2 * PI);
TIMING_ROOT_R = TIMING_PITCH_R - TIMING_TOOTH_DEPTH;
TIMING_OUTER_R = TIMING_PITCH_R + TIMING_TOOTH_DEPTH;
// Smooth retaining flanges sit above and below every timing pulley. They are
// intentionally larger than the toothed outer circle so the belt cannot walk
// off the pulley in Z.
TIMING_FLANGE_MARGIN = 1.0;
TIMING_FLANGE_T = 0.80;
TIMING_FLANGE_R = TIMING_OUTER_R + TIMING_FLANGE_MARGIN;
TIMING_FLANGE_D = 2 * TIMING_FLANGE_R;
// The screw pushes the carriage toward +X (the cabinet's outside/right side).
// Leave the full flange diameter clear at the end of travel, not just the
// toothed pulley diameter.
TENSIONER_TRAVEL_MM = 8.0;
TENSIONER_SCREW_OUT_MM = is_undef(TENSIONER_SCREW_OUT_MM) ? 4.0 : TENSIONER_SCREW_OUT_MM;
TENSIONER_AXIS_GAP_MM = 1.0;
// The right tensioner is an additional axis, not drawer column N_COL-1.
// Keep the full retaining-flange envelope clear of the last drawer axis.
TENSIONER_AXIS_MIN_X = col_center_x(N_COL - 1)
    + TIMING_FLANGE_D + TENSIONER_AXIS_GAP_MM;
TENSIONER_AXIS_MAX_X = TENSIONER_AXIS_MIN_X + TENSIONER_TRAVEL_MM;
TENSIONER_X = TENSIONER_AXIS_MIN_X + TENSIONER_SCREW_OUT_MM;

// The drawer rack/drive geometry is intentionally explicit.  The horizontal
// rack is under each drawer; the rear timing pulley and front timing pulley
// share one Y-running belt.
DRAWER_RACK_TOOTH_H = 1.25;
DRAWER_RACK_PITCH = 3.0;
FRONT_GEAR_TEETH = 16;
FRONT_GEAR_TOOTH_DEPTH = 1.0;
FRONT_GEAR_T = 3.2;
FRONT_GEAR_PITCH_R = FRONT_GEAR_TEETH * CLUTCH_PITCH_MM / (2 * PI);
FRONT_GEAR_ROOT_R = FRONT_GEAR_PITCH_R - FRONT_GEAR_TOOTH_DEPTH;
FRONT_GEAR_OUTER_R = FRONT_GEAR_PITCH_R + FRONT_GEAR_TOOTH_DEPTH;

// Fork clearance is a real parameter: open state leaves the fork just above
// the recessed screw head; engaged state makes it nearly flush with the gear.
FORK_W = 14.0;
FORK_D = 9.0;
FORK_T = 2.4;
FORK_CLEAR_OPEN = 0.55;
FORK_CONTACT = 0.08;

// Front-right sliding tensioner. The fixed channel is tied into the cabinet
// right/back structure; the carriage captures the round shaft and moves in X.
// The shorter lead keeps the adjustment-head envelope clear of the last
// drawer axis. The fixed receiver is intentionally an outboard right wing.
TENSIONER_BASE_LEAD_MM = 18.0;
TENSIONER_BASE_X0 = TENSIONER_AXIS_MIN_X - TENSIONER_BASE_LEAD_MM;
TENSIONER_BASE_X1 = TENSIONER_AXIS_MAX_X + TIMING_FLANGE_R + 1.0;
TENSIONER_BASE_Y0 = DRIVE_AXIS_Y - 16.0;
TENSIONER_BASE_D = 40.0;
TENSIONER_BASE_END_W = 3.0;
// Keep the adjustment screw and spring on two visible, parallel lanes of the
// carriage. The pulley stays on the belt centerline, so the spring pocket is
// outside its 22.82 mm retaining-flange envelope instead of being hidden
// underneath the pulley.
TENSIONER_ADJ_Y = DRIVE_AXIS_Y - 8.5;
TENSIONER_SPRING_Y = DRIVE_AXIS_Y + 17.5;
// There are two physically independent X-running slide stages.  Each stage
// sits directly below one bus pulley; neither stage is a continuous carrier
// for the upper and lower pulley.
TENSIONER_SLIDE_COUNT = 2;
TENSIONER_STAGE_PULLEY_CLEAR = 0.50;
TENSIONER_CHANNEL_FLOOR_T = 3.2;
TENSIONER_CHANNEL_WALL_T = 3.2;
TENSIONER_CHANNEL_H = 12.0;
TENSIONER_TOP_LIP_T = 1.6;
// The carriage is intentionally offset toward -X.  The round-axis flange
// must reach the right side, while the moving shoe itself must still stay
// inside the fixed channel at maximum travel.
TENSIONER_CARRIAGE_W = 22.0;
TENSIONER_CARRIAGE_X_OFFSET = -3.0;
TENSIONER_CARRIAGE_D = 32.0;
TENSIONER_CARRIAGE_T = 6.4;
TENSIONER_GUIDE_CLEAR = 0.40;
TENSIONER_BEARING_OD = 9.0;
TENSIONER_BEARING_H = 2.0;
TENSIONER_BEARING_SEAT_OD = 10.4;
TENSIONER_BEARING_SEAT_H = 0.9;
TENSIONER_BEARING_FIT = 0.25;
TENSIONER_ADJ_ROD_D = 6.0;
TENSIONER_ADJ_BORE_D = 6.8;
TENSIONER_ADJ_HEAD_D = 10.0;
TENSIONER_ADJ_HEAD_L = 3.0;
TENSIONER_ADJ_SCREW_CLEAR = 0.35;
TENSIONER_SPRING_POCKET_D = 6.0;
TENSIONER_SPRING_POCKET_DEPTH = 3.0;
TENSIONER_SPRING_WIRE_D = 0.65;
TENSIONER_SPRING_OD = 4.8;
TENSIONER_SPRING_TURNS = 5;
TENSIONER_SPRING_MIN_L = 0.80;

// Colors are only for the assembly preview; STL units remain millimeters.
COLOR_CABINET = "#6f8f9a";
COLOR_DRAWER = "#d3b184";
COLOR_SHAFT = "#5c6876";
COLOR_TIMING = "#f0a23b";
COLOR_BELT = "#ce5c31";
COLOR_GEAR = "#d6a64a";
COLOR_DOG = "#a9b4c0";
COLOR_SPRING = "#e6c24a";
COLOR_FORK = "#45d85c";
COLOR_RACK = "#9a77c7";
COLOR_MOTOR = "#343a40";
COLOR_TENSIONER = "#e1b642";
COLOR_TENSIONER_BASE = "#b28724";
COLOR_TENSIONER_CARRIAGE = "#f0c64b";
//#endregion

//#region 模型/类型
// Part values:
//   assembly       complete cabinet + bus + all drawer take-offs + one fork
//   cabinet        cabinet shell and drawer ghosts
//   power_bus      seven-axis boundary/column bus, top/bottom belts, two slides
//   all_vertical_axes  D drive + five drawer axes + two short round spindles
//   drawer_drive   rear/front compound wheels, Y belts and drawer racks
//   clutch         all clutch stations
//   clutch_detail  one selected station with the spring, screw and fork
//   motor/left_d_axis/right_round_axis/side_axes/column/vertical_rack/idler/bus_belt
//   tensioner_slide/tensioner_base/tensioner_carriage/tensioner_spring/
//   tensioner_screw/tensioner_receiver
//   tensioner_stage_top/tensioner_stage_bottom
//   tensioner_bearing
//   tensioner_pulley_top/tensioner_pulley_bottom
//   upper_clutch/upper_spur/upper_dog/lower_takeoff/lower_dog/rear_pulley
//   spring/screw/fork/drawer_belt/front_compound/front_pulley/front_gear/drawer_rack
//                  individual verification pieces for the one-by-one workflow
//
// The upper clutch wheel has two functional faces represented in one carrier:
// its axis-Y spur row meshes the vertical toothed column, while its lower dog
// face is an axis-Z engagement face. The lower compound wheel has an upward
// dog face and a coaxial axis-Z timing pulley; the belt therefore runs from
// rear to front in the XY plane along Y. This hybrid is the minimum readable
// CAD abstraction for the directions in the request; the final bevel/tooth
// profile can be swapped in without changing the layout parameters.
//#endregion

//#region 私有成员：几何函数
function timing_points(teeth, root_r, tip_r) = [
    for (i = [0:teeth - 1])
        for (p = [[0.00, root_r], [0.20, tip_r], [0.50, tip_r], [0.80, root_r]])
            let (a = (i + p[0]) * 360 / teeth)
                [p[1] * cos(a), p[1] * sin(a)]
];

function clutch_col_x(i) = col_center_x(i);

function clutch_upper_open_z(row) = row_center_z(row) - CLUTCH_DROP_MM;

function clutch_fixed_dog_z(row) =
    clutch_upper_open_z(row)
    - CLUTCH_GEAR_T / 2
    - CLUTCH_DOG_T
    - CLUTCH_CARRIER_STEM_H
    - CLUTCH_OPEN_GAP
    - CLUTCH_DOG_T / 2;

function clutch_upper_z(row, engaged) =
    clutch_upper_open_z(row)
    - (engaged ? CLUTCH_OPEN_GAP + CLUTCH_ENGAGED_OVERLAP : 0);

function clutch_upper_dog_z(row, engaged) =
    clutch_upper_z(row, engaged)
    - CLUTCH_GEAR_T / 2
    - CLUTCH_DOG_T / 2
    - CLUTCH_CARRIER_STEM_H;

function clutch_takeoff_pulley_z(row) =
    clutch_fixed_dog_z(row)
    - CLUTCH_DOG_T / 2
    - COMPOUND_LAYER_GAP
    - TIMING_PULLEY_W / 2;

function drawer_belt_z(row) = clutch_takeoff_pulley_z(row);

function clutch_screw_top_z(row, engaged) =
    clutch_upper_z(row, engaged)
    + CLUTCH_GEAR_OUTER_R
    - (engaged ? CLUTCH_SCREW_FLUSH : CLUTCH_SCREW_RECESS_OPEN);

function drawer_front_gear_z(row) =
    drawer_belt_z(row)
    + TIMING_PULLEY_W / 2
    + COMPOUND_LAYER_GAP
    + FRONT_GEAR_T / 2;

function selected_col() = min(max(0, SELECTED_COLUMN), N_COL - 1);

function selected_row() = min(max(0, SELECTED_ROW), N_ROW - 1);

// The upper and lower tensioner stages share X/Y datums but have independent
// Z envelopes.  The fixed channel is below its pulley and the carriage sits
// just above the channel floor, leaving the pulley/flange free to turn.
function tensioner_level_z(level) =
    level == "top" ? BUS_TOP_Z : BUS_BOTTOM_Z;

function tensioner_channel_z1(level) =
    tensioner_level_z(level)
    - TIMING_PULLEY_W / 2
    - TIMING_FLANGE_T
    - TENSIONER_STAGE_PULLEY_CLEAR;

function tensioner_channel_z0(level) =
    tensioner_channel_z1(level) - TENSIONER_CHANNEL_H;

function tensioner_carriage_z0(level) =
    tensioner_channel_z0(level)
    + TENSIONER_CHANNEL_FLOOR_T
    + TENSIONER_GUIDE_CLEAR;

function tensioner_carriage_center_z(level) =
    tensioner_carriage_z0(level) + TENSIONER_CARRIAGE_T / 2;

function tensioner_carriage_top_z(level) =
    tensioner_carriage_z0(level) + TENSIONER_CARRIAGE_T;
//#endregion

//#region 私有成员：齿轮、D 轴和带
module gear_profile_2d(teeth, root_r, tip_r) {
    polygon(timing_points(teeth, root_r, tip_r));
}

module d_profile_2d(d, flat_depth, clearance = 0) {
    difference() {
        circle(d = d + 2 * clearance);
        translate([d / 2 - flat_depth + clearance, -(d + 2 * clearance)])
            square([d + 2 * clearance, 2 * (d + 2 * clearance)]);
    }
}

module d_rod_z(x, y, z0, length, d = ROD_D) {
    translate([x, y, z0])
        difference() {
            cylinder(d = d, h = length);
            translate([d / 2 - ROD_FLAT_DEPTH, -d, -EPS])
                cube([d, 2 * d, length + 2 * EPS]);
        }
}

module round_rod_z(x, y, z0, length, d = ROUND_AXIS_D) {
    translate([x, y, z0])
        cylinder(d = d, h = length);
}

module cylinder_x(x0, y, z, d, length) {
    // A local +Z cylinder rotated about Y becomes a world +X cylinder.
    translate([x0, y, z])
        rotate([0, 90, 0])
            cylinder(d = d, h = length);
}

module timing_pulley_z(x, y, z, teeth = TIMING_TEETH, bore = "d") {
    pitch_r = teeth * TIMING_PITCH_MM / (2 * PI);
    root_r = pitch_r - TIMING_TOOTH_DEPTH;
    tip_r = pitch_r + TIMING_TOOTH_DEPTH;
    difference() {
        union() {
            translate([x, y, z - TIMING_PULLEY_W / 2])
                linear_extrude(height = TIMING_PULLEY_W, convexity = 8)
                    gear_profile_2d(teeth, root_r, tip_r);
            // The two smooth planes are the belt guides. Their diameter is
            // larger than the toothed circle, but they stay outside the belt
            // width so they do not occupy the belt groove.
            translate([x, y, z - TIMING_PULLEY_W / 2 - TIMING_FLANGE_T])
                cylinder(d = TIMING_FLANGE_D, h = TIMING_FLANGE_T);
            translate([x, y, z + TIMING_PULLEY_W / 2])
                cylinder(d = TIMING_FLANGE_D, h = TIMING_FLANGE_T);
        }
        translate([x, y, z - TIMING_PULLEY_W / 2 - TIMING_FLANGE_T - EPS])
            if (bore == "d")
                linear_extrude(height = TIMING_PULLEY_W + 2 * TIMING_FLANGE_T + 2 * EPS)
                    d_profile_2d(ROD_D, ROD_FLAT_DEPTH, ROD_CLEARANCE);
            else
                cylinder(d = ROUND_BORE_D, h = TIMING_PULLEY_W + 2 * TIMING_FLANGE_T + 2 * EPS);
    }
}

module spur_gear_z(x, y, z, teeth, pitch_mm, tooth_depth, thickness, bore_d = 3.2) {
    pitch_r = teeth * pitch_mm / (2 * PI);
    difference() {
        translate([x, y, z - thickness / 2])
            linear_extrude(height = thickness, convexity = 8)
                gear_profile_2d(teeth, pitch_r - tooth_depth, pitch_r + tooth_depth);
        translate([x, y, z - thickness / 2 - EPS])
            cylinder(d = bore_d, h = thickness + 2 * EPS);
    }
}

module spur_gear_y(x, y, z, teeth, pitch_mm, tooth_depth, thickness, bore_d = 3.2) {
    // Local +Z is rotated to world -Y; the profile remains in the XZ plane.
    translate([x, y, z])
        rotate([90, 0, 0])
            difference() {
                linear_extrude(height = thickness, center = true, convexity = 8)
                    gear_profile_2d(
                        teeth,
                        teeth * pitch_mm / (2 * PI) - tooth_depth,
                        teeth * pitch_mm / (2 * PI) + tooth_depth
                    );
                cylinder(d = bore_d, h = thickness + 2 * EPS, center = true);
            }
}

module dog_face_z(x, y, z, teeth = CLUTCH_DOG_TEETH, upward = true) {
    root_r = CLUTCH_DOG_R - CLUTCH_DOG_TOOTH_H;
    // The same symmetric dog profile can face up or down.  The explicit
    // rotation documents which face the spring-loaded carrier presents.
    translate([x, y, z])
        rotate(upward ? [0, 0, 0] : [180, 0, 0])
            difference() {
                linear_extrude(height = CLUTCH_DOG_T, center = true, convexity = 8)
                    gear_profile_2d(teeth, root_r, CLUTCH_DOG_R);
                cylinder(d = CLUTCH_HUB_D, h = CLUTCH_DOG_T + 2 * EPS, center = true);
            }
}

module rounded_belt_capsule_2d(a0, a1, fixed, radius) {
    hull() {
        translate([a0, fixed]) circle(r = radius);
        translate([a1, fixed]) circle(r = radius);
    }
}

module belt_loop_x(x0, x1, y, z) {
    radial_half = TIMING_BELT_T / 2 + TIMING_BELT_CLEAR;
    outer = TIMING_PITCH_R + radial_half;
    inner = max(0.8, TIMING_PITCH_R - radial_half);
    translate([0, 0, z - TIMING_BELT_T / 2])
        linear_extrude(height = TIMING_BELT_T, convexity = 8)
            difference() {
                rounded_belt_capsule_2d(x0, x1, y, outer);
                rounded_belt_capsule_2d(x0, x1, y, inner);
            }
}

module belt_loop_y(x, y0, y1, z) {
    // Both drawer pulleys have vertical axes. The belt therefore lies in XY
    // and its two straight runs follow the drawer travel along Y.
    radial_half = TIMING_BELT_T / 2 + TIMING_BELT_CLEAR;
    outer = TIMING_PITCH_R + radial_half;
    inner = max(0.8, TIMING_PITCH_R - radial_half);
    translate([0, 0, z - TIMING_BELT_T / 2])
        linear_extrude(height = TIMING_BELT_T, convexity = 8)
            difference() {
                hull() {
                    translate([x, y0]) circle(r = outer);
                    translate([x, y1]) circle(r = outer);
                }
                hull() {
                    translate([x, y0]) circle(r = inner);
                    translate([x, y1]) circle(r = inner);
                }
            }
}
//#endregion

//#region 私有成员：齿杆、齿条和弹簧
module vertical_gear_rack(x, y) {
    rack_face_x = x + CLUTCH_GEAR_PITCH_R + 0.15;
    color(COLOR_RACK) {
        translate([rack_face_x, y - 1.0, ROD_BOTTOM_Z])
            cube([2.6, 2.0, ROD_TOP_Z - ROD_BOTTOM_Z]);
        for (z = [ROD_BOTTOM_Z + 1.5:CLUTCH_PITCH_MM:ROD_TOP_Z - 1.5])
            translate([rack_face_x - CLUTCH_DOG_TOOTH_H, y - 1.15, z - 0.48])
                cube([CLUTCH_DOG_TOOTH_H + 2.6, 2.3, 0.96]);
    }
}

module vertical_gear_column(x, y) {
    // A continuous D shaft plus a full-height toothed strip. Each axis-Y
    // upper clutch gear touches this strip at its station height.
    color(COLOR_SHAFT)
        d_rod_z(x, y, ROD_BOTTOM_Z, ROD_TOP_Z - ROD_BOTTOM_Z);
    vertical_gear_rack(x, y);
    for (z = [BUS_BOTTOM_Z, BUS_TOP_Z])
        color(COLOR_TIMING)
            timing_pulley_z(x, y, z);
    for (z = [BUS_BOTTOM_Z, BUS_TOP_Z])
        color(COLOR_SHAFT)
            translate([x, y, z])
                difference() {
                    cylinder(d = 8.0, h = 1.0, center = true);
                    cylinder(d = ROD_D + 2 * ROD_WALL_CLEAR, h = 1.2, center = true);
                }
}

module horizontal_drawer_rack(x, y0, y1, z) {
    length = y1 - y0;
    rack_face_x = x + FRONT_GEAR_PITCH_R + 0.15;
    rack_body_z = z - 1.9;
    color(COLOR_RACK) {
        // The rack is a vertical strip below the drawer. Its tooth height is
        // radial in X, so the vertical-axis pinion can actually mesh with it.
        translate([rack_face_x, y0, rack_body_z])
            cube([3.2, length, 3.8]);
        for (y = [y0 + DRAWER_RACK_PITCH / 2:DRAWER_RACK_PITCH:y1 - DRAWER_RACK_PITCH / 2])
            translate([rack_face_x - DRAWER_RACK_TOOTH_H, y - 0.42, rack_body_z + 0.25])
                cube([DRAWER_RACK_TOOTH_H + 0.20, 0.84, 3.3]);
    }
}

module compression_spring_z(x, y, z0, z1) {
    h = max(CLUTCH_SPRING_MIN_H, z1 - z0);
    translate([x, y, z0])
        linear_extrude(
            height = h,
            twist = 360 * CLUTCH_SPRING_TURNS,
            slices = max(24, CLUTCH_SPRING_TURNS * 12),
            convexity = 4
        )
            translate([CLUTCH_SPRING_OD / 2 - CLUTCH_SPRING_WIRE_D / 2, 0])
                circle(d = CLUTCH_SPRING_WIRE_D);
}

module compression_spring_x(x0, x1, y, z) {
    length = max(TENSIONER_SPRING_MIN_L, x1 - x0);
    translate([x0, y, z])
        rotate([0, 90, 0])
            linear_extrude(
                height = length,
                twist = 360 * TENSIONER_SPRING_TURNS,
                slices = max(32, TENSIONER_SPRING_TURNS * 16),
                convexity = 4
            )
                translate([
                    TENSIONER_SPRING_OD / 2 - TENSIONER_SPRING_WIRE_D / 2,
                    0
                ])
                    circle(d = TENSIONER_SPRING_WIRE_D);
}

module t_countersunk_screw_z(x, y, top_z) {
    head_bottom = top_z - CLUTCH_SCREW_HEAD_H;
    color("#707985")
        difference() {
            union() {
                translate([x, y, head_bottom - CLUTCH_SCREW_SHAFT_L])
                    cylinder(d = CLUTCH_SCREW_D, h = CLUTCH_SCREW_SHAFT_L);
                // The head is a flat-topped countersink: narrow at the lower
                // face and full diameter at the top face.
                translate([x, y, head_bottom])
                    cylinder(
                        d1 = CLUTCH_SCREW_D + 0.30,
                        d2 = CLUTCH_SCREW_HEAD_D,
                        h = CLUTCH_SCREW_HEAD_H
                    );
            }
            // Recess the T driver slot instead of adding a misleading raised
            // cross. The shallow cut remains visible in the assembly preview.
            translate([x - 1.8, y - 0.35, top_z - 0.42])
                cube([3.6, 0.70, 0.50]);
            translate([x - 0.35, y - 1.8, top_z - 0.42])
                cube([0.70, 3.6, 0.50]);
        }
}
//#endregion

//#region 公开 API：柜体与动力母线
module tensioner_slide_base(level = "top") {
    x0 = TENSIONER_BASE_X0;
    x1 = TENSIONER_BASE_X1;
    y0 = TENSIONER_BASE_Y0;
    y1 = TENSIONER_BASE_Y0 + TENSIONER_BASE_D;
    z0 = tensioner_channel_z0(level);
    z1 = tensioner_channel_z1(level);
    center_z = tensioner_carriage_center_z(level);

    // Fixed outer frame from the SketchUp reference. Every level has its own
    // channel: the lower and upper frames do not share a yoke or vertical
    // shaft. The left block is the screw station; the right block is the
    // spring pocket/end stop.
    color(COLOR_TENSIONER_BASE)
        difference() {
            union() {
                // Floor and side walls form the fixed sliding channel.
                translate([x0, y0, z0])
                    cube([x1 - x0, TENSIONER_BASE_D, TENSIONER_CHANNEL_FLOOR_T]);
                translate([x0, y0, z0])
                    cube([x1 - x0, TENSIONER_CHANNEL_WALL_T, TENSIONER_CHANNEL_H]);
                translate([x0, y1 - TENSIONER_CHANNEL_WALL_T, z0])
                    cube([x1 - x0, TENSIONER_CHANNEL_WALL_T, TENSIONER_CHANNEL_H]);

                // Low top lips capture the carriage shoulders. The 0.4 mm
                // guide clearance is below these lips, so the carriage can
                // translate in X but cannot lift out of the channel.
                translate([
                    x0,
                    y0 + TENSIONER_CHANNEL_WALL_T - EPS,
                    z1 - TENSIONER_TOP_LIP_T
                ])
                    cube([x1 - x0, 2.8 + EPS, TENSIONER_TOP_LIP_T]);
                translate([
                    x0,
                    y1 - TENSIONER_CHANNEL_WALL_T - 2.8,
                    z1 - TENSIONER_TOP_LIP_T
                ])
                    cube([x1 - x0, 2.8 + EPS, TENSIONER_TOP_LIP_T]);

                translate([x0, y0, z0])
                    cube([TENSIONER_BASE_END_W, TENSIONER_BASE_D, TENSIONER_CHANNEL_H]);
                translate([x1 - TENSIONER_BASE_END_W, y0, z0])
                    cube([TENSIONER_BASE_END_W, TENSIONER_BASE_D, TENSIONER_CHANNEL_H]);
            }

            // Large screw passage through the left end block. The screw head
            // remains outside the block; its 6 mm rod advances this level's
            // carriage independently.
            cylinder_x(
                x0 - EPS,
                TENSIONER_ADJ_Y,
                center_z,
                TENSIONER_ADJ_BORE_D,
                TENSIONER_BASE_END_W + 2 * EPS
            );

            // Small blind spring pocket in the right end block.
            cylinder_x(
                x1 - TENSIONER_BASE_END_W - EPS,
                TENSIONER_SPRING_Y,
                center_z,
                TENSIONER_SPRING_POCKET_D,
                TENSIONER_SPRING_POCKET_DEPTH + EPS
            );
        }
}

module tensioner_slide_carriage(level = "top") {
    cx = TENSIONER_X;
    cy = DRIVE_AXIS_Y;
    screw_y = TENSIONER_ADJ_Y;
    spring_y = TENSIONER_SPRING_Y;
    x0 = cx + TENSIONER_CARRIAGE_X_OFFSET - TENSIONER_CARRIAGE_W / 2;
    x1 = x0 + TENSIONER_CARRIAGE_W;
    y0 = TENSIONER_BASE_Y0 + TENSIONER_CHANNEL_WALL_T + TENSIONER_GUIDE_CLEAR;
    z0 = tensioner_carriage_z0(level);
    center_z = tensioner_carriage_center_z(level);

    color(COLOR_TENSIONER_CARRIAGE)
        difference() {
            union() {
                // One moving platform belongs to one belt level. It rides in
                // the fixed channel with the specified 0.4 mm running gap.
                translate([x0, y0, z0])
                    cube([
                        TENSIONER_CARRIAGE_W,
                        TENSIONER_CARRIAGE_D,
                        TENSIONER_CARRIAGE_T
                    ]);

                // The printed carriage has a shallow retaining seat. The
                // actual center ring is a separate bearing, added below as a
                // gray purchased part; it is not the carriage itself.
                translate([cx, cy, tensioner_carriage_top_z(level)])
                    difference() {
                        cylinder(
                            d = TENSIONER_BEARING_SEAT_OD,
                            h = TENSIONER_BEARING_SEAT_H
                        );
                        cylinder(
                            d = TENSIONER_BEARING_OD + TENSIONER_BEARING_FIT,
                            h = TENSIONER_BEARING_SEAT_H + 2 * EPS
                        );
                    }
            }

            // The bearing bore continues through the moving platform so the
            // short round spindle can actually pass through the bearing.
            translate([cx, cy, z0 - EPS])
                cylinder(
                    d = ROUND_BORE_D + 0.18,
                    h = TENSIONER_CARRIAGE_T
                        + TENSIONER_BEARING_SEAT_H + 2 * EPS
                );

            // Large blind socket mates with the adjustment screw rod.
            cylinder_x(
                x0 - EPS,
                screw_y,
                center_z,
                TENSIONER_ADJ_BORE_D,
                3.2
            );

            // Small blind seat locates the spring in the moving carriage.
            cylinder_x(
                x1 - TENSIONER_SPRING_POCKET_DEPTH,
                spring_y,
                center_z,
                TENSIONER_SPRING_POCKET_D,
                TENSIONER_SPRING_POCKET_DEPTH + EPS
            );
        }
}

module tensioner_bearing_ring(level = "top") {
    // SKP's middle circular ring is the bearing. Model it as a distinct
    // annulus so the close-up cannot be mistaken for a solid printed boss.
    color("#71808d")
        translate([
            TENSIONER_X,
            DRIVE_AXIS_Y,
            tensioner_carriage_top_z(level)
        ])
            difference() {
                cylinder(d = TENSIONER_BEARING_OD, h = TENSIONER_BEARING_H);
                cylinder(
                    d = ROUND_BORE_D + 0.18,
                    h = TENSIONER_BEARING_H + 2 * EPS
                );
            }
}

module tensioner_slide_spring(level = "top") {
    spring_y = TENSIONER_SPRING_Y;
    carriage_x1 = TENSIONER_X + TENSIONER_CARRIAGE_X_OFFSET
        + TENSIONER_CARRIAGE_W / 2;
    // The coil starts inside the carriage's small round seat and ends just
    // before the fixed right end pocket, so the spring is visibly anchored at
    // both ends of the slide.
    spring_x0 = carriage_x1 - TENSIONER_SPRING_POCKET_DEPTH + 0.20;
    spring_x1 = TENSIONER_BASE_X1 - TENSIONER_BASE_END_W - 0.20;
    spring_z = tensioner_carriage_center_z(level);

    color(COLOR_SPRING)
        compression_spring_x(spring_x0, spring_x1, spring_y, spring_z);
}

module tensioner_adjust_screw(level = "top") {
    screw_y = TENSIONER_ADJ_Y;
    carriage_x0 = TENSIONER_X + TENSIONER_CARRIAGE_X_OFFSET
        - TENSIONER_CARRIAGE_W / 2;
    screw_z = tensioner_carriage_center_z(level);
    screw_tip = carriage_x0 + TENSIONER_ADJ_SCREW_CLEAR;
    rod_length = max(0.25, screw_tip - TENSIONER_BASE_X0 + EPS);

    color("#707985") {
        // A simple cylindrical head stands outside the fixed left end. The
        // modeled rod gets longer as TENSIONER_SCREW_OUT_MM increases: turning
        // the screw outward therefore pushes this level's carriage toward +X.
        cylinder_x(
            TENSIONER_BASE_X0 - TENSIONER_ADJ_HEAD_L,
            screw_y,
            screw_z,
            TENSIONER_ADJ_HEAD_D,
            TENSIONER_ADJ_HEAD_L
        );
        cylinder_x(
            TENSIONER_BASE_X0,
            screw_y,
            screw_z,
            TENSIONER_ADJ_ROD_D,
            rod_length
        );
    }
}

module tensioner_spindle(level = "top") {
    pulley_z = tensioner_level_z(level);
    spindle_z0 = tensioner_carriage_top_z(level) - 0.20;
    spindle_z1 = pulley_z
        + TIMING_PULLEY_W / 2
        + TIMING_FLANGE_T
        + 0.80;

    // Each pulley has its own short round spindle. There is an intentional
    // air gap between the two spindle ends; no rod passes through both levels.
    color(COLOR_SHAFT)
        round_rod_z(
            TENSIONER_X,
            DRIVE_AXIS_Y,
            spindle_z0,
            spindle_z1 - spindle_z0
        );
    tensioner_pulley(level);
}

module cabinet_tensioner_receiver_stage(level = "top") {
    x0 = TENSIONER_BASE_X0;
    x1 = TENSIONER_BASE_X1;
    y1 = TENSIONER_BASE_Y0 + TENSIONER_BASE_D;
    z0 = tensioner_channel_z0(level);

    // These fixed ribs are part of the cabinet, not the moving carriage. The
    // shelf extension catches this level's channel floor at y=y1 and lands in
    // the inside face of the 5 mm back wall. End ribs prevent yaw; the right
    // rib keys the fixed receiver against the cabinet side wall.
    union() {
        translate([x0, y1 - EPS, z0 - EPS])
            cube([
                x1 - x0,
                D - BACK_PANEL_T - y1 + 2 * EPS,
                TENSIONER_CHANNEL_FLOOR_T + EPS
            ]);

        for (x = [x0 + 4.0, x1 - 8.0])
            translate([x, y1 - EPS, z0 - EPS])
                cube([
                    4.0,
                    D - BACK_PANEL_T - y1 + 2 * EPS,
                    TENSIONER_CHANNEL_H + EPS
                ]);

        translate([W - WALL - EPS, y1 - EPS, z0 - EPS])
            cube([
                WALL + 2 * EPS,
                D - BACK_PANEL_T - y1 + 2 * EPS,
                TENSIONER_CHANNEL_H + EPS
            ]);
    }
}

module cabinet_tensioner_receiver(level = "both") {
    if (level == "both") {
        cabinet_tensioner_receiver_stage("bottom");
        cabinet_tensioner_receiver_stage("top");
    } else {
        cabinet_tensioner_receiver_stage(level);
    }
}

module tensioner_slide_stage(level = "top") {
    tensioner_slide_base(level);
    tensioner_slide_carriage(level);
    tensioner_bearing_ring(level);
    tensioner_slide_spring(level);
    tensioner_adjust_screw(level);
    tensioner_spindle(level);
}

module tensioner_slide_assembly() {
    // Two separate stages: upper bus belt and lower bus belt.
    tensioner_slide_stage("bottom");
    tensioner_slide_stage("top");
}

module tensioner_stage_with_receiver(level = "both") {
    cabinet_tensioner_receiver(level);
    if (level == "both")
        tensioner_slide_assembly();
    else
        tensioner_slide_stage(level);
}

module clutch_cabinet_shell() {
    // The legacy cabinet shell also contains the old chain tensioner guides.
    // They are not part of this mechanism, so the clutch preview keeps the
    // primary frame separate and adds the internal panels as visual overlays.
    // Use a closed thin-wall envelope for this mechanism entry.  The legacy
    // frame is intentionally open through front/back for its removable panel,
    // which is useful for the chain model but is not a watertight STL solid.
    union() {
        difference() {
            cube([W, D, H]);
            translate([WALL, WALL, WALL])
                cube([W - 2 * WALL, D - 2 * WALL, H - 2 * WALL]);
        }
        cabinet_tensioner_receiver();
    }
}

module clutch_assembly_shell_context() {
    // Do not use a transparent difference() or broad wall panels here.
    // OpenSCAD triangulates transparent faces into large fan faces, which makes
    // the inspection image look like the mechanism is inside broken glass. A
    // wire-frame cabinet datum is enough to show the front/back orientation;
    // the printable cabinet entry above remains a separate closed shell.
    union() {
        for (x = [0, W - WALL])
            for (y = [0, D - WALL])
                translate([x, y, 0])
                    cube([WALL, WALL, H]);
        for (x = [0, W - WALL])
            for (z = [0, H - WALL])
                translate([x, 0, z])
                    cube([WALL, D, WALL]);
        for (y = [0, D - WALL])
            for (z = [0, H - WALL])
                translate([0, y, z])
                    cube([W, WALL, WALL]);
    }
}

module clutch_partition_with_belt_passages() {
    radial_half = TIMING_BELT_T / 2 + TIMING_BELT_CLEAR;
    passage_half_x = TIMING_PITCH_R + radial_half + 0.45;
    difference() {
        partition_plate();
        for (row = [0:N_ROW - 1])
            for (col = [0:N_COL - 1])
                translate([
                    clutch_col_x(col) - passage_half_x,
                    PARTITION_FRONT_Y - EPS,
                    drawer_belt_z(row) - TIMING_BELT_T / 2 - 0.45
                ])
                    cube([
                        2 * passage_half_x,
                        PARTITION_T + 2 * EPS,
                        TIMING_BELT_T + 0.90
                    ]);
    }
}

module clutch_cabinet_context(include_drawers = true) {
    color(COLOR_CABINET, 0.38) clutch_assembly_shell_context();
    color(COLOR_CABINET, 0.72) {
        // Keep the partition as datum rails in the preview. The full
        // perforated partition is a printable cabinet feature, but its
        // transparent boolean face is not useful for visual inspection.
        bay_grid();
        front_service_cheek();
        cabinet_tensioner_receiver();
    }
    if (include_drawers)
        color(COLOR_DRAWER, 0.22) drawer_ghosts();
}

module power_motor_vertical() {
    // The purchased motor's local +Z output points upward in this assembly.
    translate([MOTOR_X, DRIVE_AXIS_Y, MOTOR_FACE_Z])
        pololu_micro_metal_motor_100_1_hp_6v_body_colored();
    translate([MOTOR_X, DRIVE_AXIS_Y, MOTOR_FACE_Z])
        color("#d6d9dc") d_shaft();
    left_d_axis();
}

module left_d_axis() {
    // Front-left axis: the rod has a D flat and both bus pulleys have matching
    // D bores. The motor output shaft overlaps the lower end of this rod.
    color(COLOR_SHAFT)
        d_rod_z(MOTOR_X, DRIVE_AXIS_Y, LEFT_D_AXIS_Z0, ROD_TOP_Z - LEFT_D_AXIS_Z0);
    for (z = [BUS_BOTTOM_Z, BUS_TOP_Z])
        color(COLOR_TIMING)
            timing_pulley_z(MOTOR_X, DRIVE_AXIS_Y, z, TIMING_TEETH, "d");
    color(COLOR_SHAFT)
        for (z = [BUS_BOTTOM_Z, BUS_TOP_Z])
            translate([MOTOR_X, DRIVE_AXIS_Y, z])
                difference() {
                    cylinder(d = 8.0, h = 1.0, center = true);
                    cylinder(d = ROD_D + 2 * ROD_WALL_CLEAR, h = 1.2, center = true);
                }
}

module right_round_axis() {
    // Front-right boundary: two independent short round spindles, one per
    // belt level. There is deliberately no D flat on either shaft. This
    // boundary appears on the left when the cabinet is viewed from the back.
    tensioner_spindle("bottom");
    tensioner_spindle("top");
}

module tensioner_pulley(level = "top") {
    z = level == "top" ? BUS_TOP_Z : BUS_BOTTOM_Z;
    color(COLOR_TENSIONER)
        timing_pulley_z(TENSIONER_X, DRIVE_AXIS_Y, z, TIMING_TEETH, "round");
}

module tensioner_pulley_top() {
    tensioner_pulley("top");
}

module tensioner_pulley_bottom() {
    tensioner_pulley("bottom");
}

module side_axes() {
    left_d_axis();
    right_round_axis();
}

module all_vertical_axes() {
    // Exact front-view order, left to right:
    //   0       : D drive axis + motor
    //   1..N_COL: one drawer transmission axis per drawer column
    //   N_COL+1: two independent round tensioner spindles carried by two slides
    power_motor_vertical();
    for (i = [0:N_COL - 1])
        vertical_gear_column(clutch_col_x(i), DRIVE_AXIS_Y);
    tensioner_slide_assembly();
}

module power_bus() {
    // Front view: D drive + five drawer transmission columns + the two-level
    // round tensioner boundary. The tensioner stages are included once by
    // all_vertical_axes(); they are not duplicated after the belts.
    all_vertical_axes();

    // One top and one bottom horizontal timing belt.  The column pulleys sit
    // on both straight runs; the far-right pair is the adjustable idler.
    color(COLOR_BELT, 0.15) {
        belt_loop_x(MOTOR_X, TENSIONER_X, DRIVE_AXIS_Y, BUS_BOTTOM_Z);
        belt_loop_x(MOTOR_X, TENSIONER_X, DRIVE_AXIS_Y, BUS_TOP_Z);
    }
}
//#endregion

//#region 公开 API：离合与抽屉取力
module clutch_upper_carrier(col, row, engaged = false, include_screw = false) {
    x = clutch_col_x(col);
    y = DRIVE_AXIS_Y;
    upper_z = clutch_upper_z(row, engaged);
    upper_dog_z = clutch_upper_dog_z(row, engaged);

    // Axis-Y upper gear: its teeth stay in the vertical rack.  A short
    // carrier stem links this wheel to the downward dog face.
    color(COLOR_GEAR)
        spur_gear_y(
            x,
            y,
            upper_z,
            CLUTCH_GEAR_TEETH,
            CLUTCH_PITCH_MM,
            CLUTCH_GEAR_TOOTH_DEPTH,
            CLUTCH_GEAR_T,
            ROD_D + 2 * ROD_CLEARANCE
        );
    color(COLOR_DOG)
        dog_face_z(x, y, upper_dog_z, CLUTCH_DOG_TEETH, false);
    color(COLOR_SHAFT)
        translate([x, y, upper_dog_z + CLUTCH_DOG_T / 2])
            cylinder(d = CLUTCH_HUB_D, h = CLUTCH_CARRIER_STEM_H);

    if (include_screw)
        t_countersunk_screw_z(x, y, clutch_screw_top_z(row, engaged));
}

module clutch_lower_takeoff(col, row) {
    x = clutch_col_x(col);
    y = DRIVE_AXIS_Y;
    fixed_z = clutch_fixed_dog_z(row);
    takeoff_pulley_z = clutch_takeoff_pulley_z(row);

    // Fixed lower dog presents its teeth upward. The timing pulley is a second
    // coaxial layer below it; both layers are on the same vertical (Z) axis.
    color(COLOR_DOG)
        dog_face_z(x, y, fixed_z, CLUTCH_DOG_TEETH, true);
    color(COLOR_TIMING)
        timing_pulley_z(x, y, takeoff_pulley_z, TIMING_TEETH, "round");
    color(COLOR_SHAFT)
        translate([x, y, takeoff_pulley_z - TIMING_PULLEY_W / 2 - 0.25])
            cylinder(
                d = ROD_D,
                h = fixed_z - takeoff_pulley_z
                    + CLUTCH_DOG_T / 2 + TIMING_PULLEY_W / 2 + 0.50
            );
}

module clutch_spring_only(col, row, engaged = false) {
    x = clutch_col_x(col);
    y = DRIVE_AXIS_Y;
    fixed_z = clutch_fixed_dog_z(row);
    upper_dog_z = clutch_upper_dog_z(row, engaged);
    spring_bottom = fixed_z + CLUTCH_DOG_T / 2 + 0.30;
    spring_open_top = upper_dog_z - CLUTCH_DOG_T / 2 - 0.30;
    spring_top = engaged ? spring_bottom + CLUTCH_SPRING_MIN_H : spring_open_top;

    color(COLOR_SPRING)
        compression_spring_z(x, y, spring_bottom, spring_top);
}

module clutch_spring_and_screw(col, row, engaged = false) {
    clutch_spring_only(col, row, engaged);
    x = clutch_col_x(col);
    y = DRIVE_AXIS_Y;
    t_countersunk_screw_z(x, y, clutch_screw_top_z(row, engaged));
}

module clutch_station(col, row, engaged = false, detail = false) {
    clutch_upper_carrier(col, row, engaged, false);
    clutch_lower_takeoff(col, row);
    clutch_spring_and_screw(col, row, engaged);

    if (detail)
        color(COLOR_FORK, 0.12)
            clutch_fork(col, row, engaged);
}

module all_clutches() {
    for (row = [0:N_ROW - 1])
        for (col = [0:N_COL - 1])
            clutch_station(
                col,
                row,
                ENGAGED && col == selected_col() && row == selected_row(),
                false
            );
}

module clutch_fork(col, row, engaged = false) {
    x = clutch_col_x(col);
    y = DRIVE_AXIS_Y - FORK_D / 2;
    upper_gear_top = clutch_upper_z(row, engaged) + CLUTCH_GEAR_OUTER_R;
    z = upper_gear_top + (engaged ? FORK_CONTACT : FORK_CLEAR_OPEN) + FORK_T / 2;
    // The fork is a U-shaped pressure shoe with its opening around the rod.
    color(COLOR_FORK)
        translate([x - FORK_W / 2, y, z - FORK_T / 2])
            difference() {
                cube([FORK_W, FORK_D, FORK_T]);
                translate([FORK_W / 2 - 2.0, -EPS, -EPS])
                    cube([4.0, FORK_D + 2 * EPS, FORK_T + 2 * EPS]);
            }
}

module drawer_front_compound(col, row) {
    x = clutch_col_x(col);
    front_y = FRONT_PULLEY_Y;
    belt_z = drawer_belt_z(row);
    gear_z = drawer_front_gear_z(row);
    color(COLOR_TIMING)
        timing_pulley_z(x, front_y, belt_z, TIMING_TEETH, "round");
    // The upper, larger gear is the pinion that contacts the rack below the drawer.
    color(COLOR_GEAR)
        spur_gear_z(x, front_y, gear_z, FRONT_GEAR_TEETH, CLUTCH_PITCH_MM, FRONT_GEAR_TOOTH_DEPTH, FRONT_GEAR_T);
    color(COLOR_SHAFT)
        translate([x, front_y, belt_z - TIMING_PULLEY_W / 2 - 0.25])
            cylinder(d = CLUTCH_HUB_D, h = gear_z - belt_z + TIMING_PULLEY_W / 2 + FRONT_GEAR_T / 2 + 0.50);
}

module drawer_front_drive(col, row) {
    x = clutch_col_x(col);
    belt_z = drawer_belt_z(row);
    color(COLOR_BELT, 0.14)
        belt_loop_y(x, FRONT_PULLEY_Y, DRIVE_AXIS_Y, belt_z);
    drawer_front_compound(col, row);
    horizontal_drawer_rack(
        x,
        FRONT_PULLEY_Y + 3.5,
        PARTITION_FRONT_Y - 1.5,
        drawer_front_gear_z(row)
    );
}

module drawer_drive() {
    for (row = [0:N_ROW - 1])
        for (col = [0:N_COL - 1]) {
            clutch_lower_takeoff(col, row);
            drawer_front_drive(col, row);
        }
}

// 单件检查入口。它们都使用同一组装坐标，便于把检查过的零件直接放回总装。
module selected_column_part() {
    vertical_gear_column(clutch_col_x(selected_col()), DRIVE_AXIS_Y);
}

module selected_left_d_axis_part() {
    left_d_axis();
}

module selected_vertical_rack_part() {
    vertical_gear_rack(clutch_col_x(selected_col()), DRIVE_AXIS_Y);
}

module selected_idler_part() {
    tensioner_stage_with_receiver();
}

module selected_right_round_axis_part() {
    right_round_axis();
}

module selected_tensioner_slide_part() {
    tensioner_stage_with_receiver();
}

module selected_tensioner_top_stage_part() {
    tensioner_stage_with_receiver("top");
}

module selected_tensioner_bottom_stage_part() {
    tensioner_stage_with_receiver("bottom");
}

module selected_tensioner_bearing_part() {
    tensioner_bearing_ring("bottom");
    tensioner_bearing_ring("top");
}

module selected_tensioner_base_part() {
    tensioner_slide_base("bottom");
    tensioner_slide_base("top");
}

module selected_tensioner_carriage_part() {
    tensioner_slide_carriage("bottom");
    tensioner_slide_carriage("top");
}

module selected_tensioner_spring_part() {
    tensioner_slide_spring("bottom");
    tensioner_slide_spring("top");
}

module selected_tensioner_screw_part() {
    tensioner_adjust_screw("bottom");
    tensioner_adjust_screw("top");
}

module selected_tensioner_receiver_part() {
    cabinet_tensioner_receiver();
}

module selected_upper_clutch_part() {
    clutch_upper_carrier(selected_col(), selected_row(), ENGAGED, false);
}

module selected_upper_spur_part() {
    col = selected_col();
    row = selected_row();
    spur_gear_y(
        clutch_col_x(col),
        DRIVE_AXIS_Y,
        clutch_upper_z(row, ENGAGED),
        CLUTCH_GEAR_TEETH,
        CLUTCH_PITCH_MM,
        CLUTCH_GEAR_TOOTH_DEPTH,
        CLUTCH_GEAR_T,
        ROD_D + 2 * ROD_CLEARANCE
    );
}

module selected_upper_dog_part() {
    col = selected_col();
    row = selected_row();
    dog_face_z(
        clutch_col_x(col),
        DRIVE_AXIS_Y,
        clutch_upper_dog_z(row, ENGAGED),
        CLUTCH_DOG_TEETH,
        false
    );
}

module selected_lower_takeoff_part() {
    clutch_lower_takeoff(selected_col(), selected_row());
}

module selected_lower_dog_part() {
    dog_face_z(
        clutch_col_x(selected_col()),
        DRIVE_AXIS_Y,
        clutch_fixed_dog_z(selected_row()),
        CLUTCH_DOG_TEETH,
        true
    );
}

module selected_rear_pulley_part() {
    timing_pulley_z(
        clutch_col_x(selected_col()),
        DRIVE_AXIS_Y,
        clutch_takeoff_pulley_z(selected_row()),
        TIMING_TEETH,
        "round"
    );
}

module selected_spring_part() {
    clutch_spring_only(selected_col(), selected_row(), ENGAGED);
}

module selected_screw_part() {
    col = selected_col();
    row = selected_row();
    t_countersunk_screw_z(
        clutch_col_x(col),
        DRIVE_AXIS_Y,
        clutch_screw_top_z(row, ENGAGED)
    );
}

module selected_fork_part() {
    clutch_fork(selected_col(), selected_row(), ENGAGED);
}

module selected_drawer_belt_part() {
    col = selected_col();
    row = selected_row();
    color(COLOR_BELT, 0.18)
        belt_loop_y(
            clutch_col_x(col),
            FRONT_PULLEY_Y,
            DRIVE_AXIS_Y,
            drawer_belt_z(row)
        );
}

module selected_front_compound_part() {
    drawer_front_compound(selected_col(), selected_row());
}

module selected_front_pulley_part() {
    timing_pulley_z(
        clutch_col_x(selected_col()),
        FRONT_PULLEY_Y,
        drawer_belt_z(selected_row()),
        TIMING_TEETH,
        "round"
    );
}

module selected_front_gear_part() {
    spur_gear_z(
        clutch_col_x(selected_col()),
        FRONT_PULLEY_Y,
        drawer_front_gear_z(selected_row()),
        FRONT_GEAR_TEETH,
        CLUTCH_PITCH_MM,
        FRONT_GEAR_TOOTH_DEPTH,
        FRONT_GEAR_T
    );
}

module selected_drawer_rack_part() {
    row = selected_row();
    horizontal_drawer_rack(
        clutch_col_x(selected_col()),
        FRONT_PULLEY_Y + 3.5,
        PARTITION_FRONT_Y - 1.5,
        drawer_front_gear_z(row)
    );
}

module clutch_detail() {
    // A selected station is rendered in place, with the fork present.  EXPLODE
    // separates the front/back axis stack without changing the mating datums.
    col = selected_col();
    row = selected_row();
    x = clutch_col_x(col);
    y = DRIVE_AXIS_Y;
    translate([0, CLUTCH_EXPLODE, 0])
        clutch_station(col, row, ENGAGED, true);
    if (CLUTCH_EXPLODE > 0)
        color(COLOR_RACK, 0.45)
            translate([
                x - 1.0,
                y + CLUTCH_EXPLODE - 1.0,
                clutch_upper_open_z(row) - 15
            ])
                cube([2.0, 2.0, 30]);
}
//#endregion

//#region 公开 API：输出入口
if (CLUTCH_PART == "assembly") {
    clutch_cabinet_context();
    power_bus();
    all_clutches();
    for (row = [0:N_ROW - 1])
        for (col = [0:N_COL - 1])
            drawer_front_drive(col, row);
    clutch_fork(selected_col(), selected_row(), ENGAGED);
} else if (CLUTCH_PART == "cabinet") {
    // Export the shell alone as a watertight printed part; internal panels and
    // drawer ghosts are visual context only and intentionally do not enter it.
    color(COLOR_CABINET) clutch_cabinet_shell();
} else if (CLUTCH_PART == "power_bus") {
    power_bus();
} else if (CLUTCH_PART == "all_vertical_axes") {
    all_vertical_axes();
} else if (CLUTCH_PART == "drawer_drive") {
    drawer_drive();
} else if (CLUTCH_PART == "clutch") {
    all_clutches();
} else if (CLUTCH_PART == "clutch_detail") {
    clutch_detail();
} else if (CLUTCH_PART == "motor") {
    power_motor_vertical();
} else if (CLUTCH_PART == "left_d_axis") {
    selected_left_d_axis_part();
} else if (CLUTCH_PART == "right_round_axis") {
    selected_right_round_axis_part();
} else if (CLUTCH_PART == "tensioner_pulley_top") {
    tensioner_pulley_top();
} else if (CLUTCH_PART == "tensioner_pulley_bottom") {
    tensioner_pulley_bottom();
} else if (CLUTCH_PART == "tensioner_slide") {
    selected_tensioner_slide_part();
} else if (CLUTCH_PART == "tensioner_stage_top") {
    selected_tensioner_top_stage_part();
} else if (CLUTCH_PART == "tensioner_stage_bottom") {
    selected_tensioner_bottom_stage_part();
} else if (CLUTCH_PART == "tensioner_bearing") {
    selected_tensioner_bearing_part();
} else if (CLUTCH_PART == "tensioner_base") {
    selected_tensioner_base_part();
} else if (CLUTCH_PART == "tensioner_carriage") {
    selected_tensioner_carriage_part();
} else if (CLUTCH_PART == "tensioner_spring") {
    selected_tensioner_spring_part();
} else if (CLUTCH_PART == "tensioner_screw") {
    selected_tensioner_screw_part();
} else if (CLUTCH_PART == "tensioner_receiver") {
    selected_tensioner_receiver_part();
} else if (CLUTCH_PART == "side_axes") {
    side_axes();
} else if (CLUTCH_PART == "column") {
    selected_column_part();
} else if (CLUTCH_PART == "vertical_rack") {
    selected_vertical_rack_part();
} else if (CLUTCH_PART == "idler") {
    selected_idler_part();
} else if (CLUTCH_PART == "bus_belt") {
    color(COLOR_BELT, 0.15) {
        belt_loop_x(MOTOR_X, TENSIONER_X, DRIVE_AXIS_Y, BUS_BOTTOM_Z);
        belt_loop_x(MOTOR_X, TENSIONER_X, DRIVE_AXIS_Y, BUS_TOP_Z);
    }
} else if (CLUTCH_PART == "upper_clutch") {
    selected_upper_clutch_part();
} else if (CLUTCH_PART == "upper_spur") {
    selected_upper_spur_part();
} else if (CLUTCH_PART == "upper_dog") {
    selected_upper_dog_part();
} else if (CLUTCH_PART == "lower_takeoff") {
    selected_lower_takeoff_part();
} else if (CLUTCH_PART == "lower_dog") {
    selected_lower_dog_part();
} else if (CLUTCH_PART == "rear_pulley") {
    selected_rear_pulley_part();
} else if (CLUTCH_PART == "spring") {
    selected_spring_part();
} else if (CLUTCH_PART == "screw") {
    selected_screw_part();
} else if (CLUTCH_PART == "fork") {
    selected_fork_part();
} else if (CLUTCH_PART == "drawer_belt") {
    selected_drawer_belt_part();
} else if (CLUTCH_PART == "front_compound") {
    selected_front_compound_part();
} else if (CLUTCH_PART == "front_pulley") {
    selected_front_pulley_part();
} else if (CLUTCH_PART == "front_gear") {
    selected_front_gear_part();
} else if (CLUTCH_PART == "drawer_rack") {
    selected_drawer_rack_part();
} else {
    assert(false, str("unknown CLUTCH_PART: ", CLUTCH_PART));
}
//#endregion

//#region 业务逻辑与检查
echo("cabinet_clutch", "W", W, "H", H, "D", D);
echo("drive_axis", "x_motor", MOTOR_X, "y", DRIVE_AXIS_Y, "z_bottom", BUS_BOTTOM_Z, "z_top", BUS_TOP_Z);
echo("vertical_axes", "count", VERTICAL_AXIS_COUNT, "layout", "D-drive + drawer-columns + two short round tensioner spindles");
echo("left_axis", "profile", "D", "d", ROD_D, "pulley_bore", "D");
echo("right_axis", "profile", "round", "d", ROUND_AXIS_D, "pulley_bore", ROUND_BORE_D);
echo("timing", "pitch", TIMING_PITCH_MM, "teeth", TIMING_TEETH, "pitch_r", TIMING_PITCH_R, "outer_d", 2 * TIMING_OUTER_R, "flange_d", TIMING_FLANGE_D);
echo("tensioner", "slides", TENSIONER_SLIDE_COUNT, "axis_min_x", TENSIONER_AXIS_MIN_X, "axis_max_x", TENSIONER_AXIS_MAX_X, "screw_out", TENSIONER_SCREW_OUT_MM, "channel_x", TENSIONER_BASE_X0, TENSIONER_BASE_X1, "bottom_z", tensioner_channel_z0("bottom"), "top_z", tensioner_channel_z0("top"), "channel_h", TENSIONER_CHANNEL_H);
echo("tensioner_bearing", "od", TENSIONER_BEARING_OD, "h", TENSIONER_BEARING_H, "spindle_d", ROUND_AXIS_D, "seat_od", TENSIONER_BEARING_SEAT_OD);
echo("clutch", "open_gap", CLUTCH_OPEN_GAP, "drop", CLUTCH_DROP_MM, "selected", selected_col(), selected_row(), "engaged", ENGAGED);

assert(
    CLUTCH_PART == "assembly"
    || CLUTCH_PART == "cabinet"
    || CLUTCH_PART == "power_bus"
    || CLUTCH_PART == "all_vertical_axes"
    || CLUTCH_PART == "drawer_drive"
    || CLUTCH_PART == "clutch"
    || CLUTCH_PART == "clutch_detail"
    || CLUTCH_PART == "motor"
    || CLUTCH_PART == "left_d_axis"
    || CLUTCH_PART == "right_round_axis"
    || CLUTCH_PART == "tensioner_pulley_top"
    || CLUTCH_PART == "tensioner_pulley_bottom"
    || CLUTCH_PART == "tensioner_slide"
    || CLUTCH_PART == "tensioner_stage_top"
    || CLUTCH_PART == "tensioner_stage_bottom"
    || CLUTCH_PART == "tensioner_bearing"
    || CLUTCH_PART == "tensioner_base"
    || CLUTCH_PART == "tensioner_carriage"
    || CLUTCH_PART == "tensioner_spring"
    || CLUTCH_PART == "tensioner_screw"
    || CLUTCH_PART == "tensioner_receiver"
    || CLUTCH_PART == "side_axes"
    || CLUTCH_PART == "column"
    || CLUTCH_PART == "vertical_rack"
    || CLUTCH_PART == "idler"
    || CLUTCH_PART == "bus_belt"
    || CLUTCH_PART == "upper_clutch"
    || CLUTCH_PART == "upper_spur"
    || CLUTCH_PART == "upper_dog"
    || CLUTCH_PART == "lower_takeoff"
    || CLUTCH_PART == "lower_dog"
    || CLUTCH_PART == "rear_pulley"
    || CLUTCH_PART == "spring"
    || CLUTCH_PART == "screw"
    || CLUTCH_PART == "fork"
    || CLUTCH_PART == "drawer_belt"
    || CLUTCH_PART == "front_compound"
    || CLUTCH_PART == "front_pulley"
    || CLUTCH_PART == "front_gear"
    || CLUTCH_PART == "drawer_rack"
);
assert(abs(CLUTCH_OPEN_GAP - 2 * CLUTCH_DOG_TOOTH_H) < 0.001, "open clutch gap must be two dog tooth heights");
assert(N_COL == 5, "current clutch layout requires five drawer transmission columns");
assert(VERTICAL_AXIS_COUNT == 7, "vertical axis positions must be D drive + 5 drawer axes + one two-level tensioner boundary");
assert(TENSIONER_SLIDE_COUNT == 2, "upper and lower bus belts require two independent tensioner slides");
assert(DRIVE_AXIS_Y > PARTITION_BACK_Y + 1.0, "drive bus must be behind the partition");
assert(DRIVE_AXIS_Y - TIMING_OUTER_R > PARTITION_BACK_Y + 0.50, "rear pulley OD must clear the partition");
assert(DRIVE_AXIS_Y + TIMING_OUTER_R < D - BACK_PANEL_T - 1.0, "rear belt must clear the back panel");
assert(BUS_BOTTOM_Z > WALL + 2.0, "bottom bus pulley must clear the cabinet floor");
assert(BUS_TOP_Z < H - WALL - 1.0, "top bus pulley must clear the cabinet roof");
assert(TENSIONER_TRAVEL_MM > 0, "tensioner travel must be positive");
assert(TENSIONER_SCREW_OUT_MM >= 0 && TENSIONER_SCREW_OUT_MM <= TENSIONER_TRAVEL_MM,
    "tensioner screw adjustment must stay within the defined travel");
assert(TENSIONER_AXIS_MIN_X < TENSIONER_AXIS_MAX_X,
    "tensioner axis travel must have a valid range");
assert(TENSIONER_AXIS_MIN_X - col_center_x(N_COL - 1)
    > TIMING_FLANGE_D + TENSIONER_AXIS_GAP_MM - 0.01,
    "tensioner flange must clear the last drawer-axis flange");
assert(TENSIONER_BASE_X0 - TENSIONER_ADJ_HEAD_L
    > col_center_x(N_COL - 1) + ROD_D / 2 + 0.50,
    "tensioner screw head must clear the last drawer axis");
assert(TENSIONER_BASE_X0 < W - WALL && TENSIONER_BASE_X1 > W - WALL,
    "outboard tensioner receiver must bridge the cabinet right wall");
assert(TENSIONER_BASE_X1 > TENSIONER_AXIS_MAX_X + TIMING_FLANGE_R,
    "tensioner base must retain the full flange at maximum travel");
assert(TENSIONER_BASE_X0 < TENSIONER_AXIS_MIN_X,
    "tensioner base must start before the axis travel");
assert(tensioner_channel_z1("bottom") < tensioner_channel_z0("top"),
    "upper and lower tensioner channels must be separate");
assert(TENSIONER_CHANNEL_H > TENSIONER_CHANNEL_FLOOR_T
    + TENSIONER_GUIDE_CLEAR + TENSIONER_CARRIAGE_T,
    "tensioner carriage must fit below the retaining lips");
assert(TENSIONER_SPRING_MIN_L > 0, "tensioner spring minimum length must be positive");
assert(TENSIONER_BEARING_OD > ROUND_BORE_D, "bearing inner bore must clear the round spindle");
assert(TENSIONER_BEARING_SEAT_OD > TENSIONER_BEARING_OD,
    "printed bearing seat must retain the bearing ring");
assert(TENSIONER_ADJ_Y > TENSIONER_BASE_Y0 + TENSIONER_CHANNEL_WALL_T,
    "adjustment lane must clear the fixed front channel wall");
assert(TENSIONER_SPRING_Y < TENSIONER_BASE_Y0 + TENSIONER_BASE_D - TENSIONER_CHANNEL_WALL_T,
    "spring lane must fit inside the fixed rear channel wall");
assert(ROUND_BORE_D > ROUND_AXIS_D, "round pulley bore must clear the round axis");
assert(TIMING_FLANGE_R > TIMING_OUTER_R, "timing pulley retaining flange must exceed toothed outer circle");
assert(FRONT_PULLEY_Y > 0 && FRONT_PULLEY_Y < PARTITION_FRONT_Y, "front pulley must stay in the drawer bay");
assert(SELECTED_COLUMN >= 0 && SELECTED_COLUMN < N_COL, "SELECTED_COLUMN out of range");
assert(SELECTED_ROW >= 0 && SELECTED_ROW < N_ROW, "SELECTED_ROW out of range");
//#endregion

//#region 方法/工具
// Preview examples:
//   openscad -D 'CLUTCH_PART="assembly"' -o assembly.stl cabinet_clutch.scad
//   openscad -D 'CLUTCH_PART="clutch_detail"' -D 'CLUTCH_EXPLODE=8' -D 'ENGAGED=true' -o detail.stl cabinet_clutch.scad
//   openscad -D 'CLUTCH_PART="power_bus"' -o power_bus.stl cabinet_clutch.scad
//#endregion
