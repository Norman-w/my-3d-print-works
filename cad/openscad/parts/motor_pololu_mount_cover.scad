// Mechanical contract
// process: FDM; PETG/nylon recommended for the printed sleeve and fixing seats
// material: printed motor-fit Ω clamp; mating motor is purchased Pololu #1101
// parting_plane: n/a; one printed clamp, open at the lower Ω mouth and at both axial ends
// opening_direction: motor slides through the sleeve along local Y; fixing seats face local -Z
// fastener: four M3 screws through local-Z holes in the two bottom seats into blind floor-boss pilots; the Ø5 floor Boss posts rise 12 mm through the Ø5.8 seat holes
// seal: n/a; rear electrical tabs remain open
// print_orientation: rotate as needed in the slicer; source axis follows the assembly datum
// units: mm
// note: the clamp follows the motor's rounded rectangular 10×12 mm envelope;
//       the bottom profile is two short outward seats, not two hanging legs;
//       each seat carries two holes for the four circular floor Boss posts.

//#region 导入/依赖
include <../enclosure/cabinet_motor_mount_params.scad>
include <motor_pololu_micro_metal_100_1_hp_6v.scad>
//#endregion

//#region 常量/配置
$fa = 8;
$fs = 0.22;
//#endregion

//#region 模型/类型
// 固定套局部原点为蛇形主动轮轴中心；局部 X/Z 是电机横截面，局部 Y 是电机轴向。
// 在柜体装配中局部 -Z 直接是柜底方向；下方是座子而不是腿。
//#endregion

//#region 私有成员
module rounded_prism_xz(w, h, len, r, y0) {
    hull() {
        for (x = [-w / 2 + r, w / 2 - r], z = [-h / 2 + r, h / 2 - r])
            translate([x, y0 + len, z])
                rotate([90, 0, 0])
                    cylinder(r = r, h = len);
    }
}

module motor_mount_local_z_cylinder(d, h, x, y, z0) {
    translate([x, y, z0])
        cylinder(d = d, h = h);
}

module motor_mount_rounded_prism_xy(w, d, h, r, x0, y0, z0) {
    translate([x0, y0, z0])
        hull() {
            for (x = [-w / 2 + r, w / 2 - r], y = [r, d - r])
                translate([x, y, 0])
                    cylinder(r = r, h = h);
        }
}

module omega_mouth_cut() {
    mouth_z = MOTOR_MOUNT_OMEGA_MOUTH_SIGN < 0
        ? -MOTOR_MOUNT_OMEGA_OUTER_H / 2 - MOTOR_MOUNT_EPS
        : MOTOR_MOUNT_OMEGA_INNER_H / 2 - MOTOR_MOUNT_EPS;
    translate([
        -MOTOR_MOUNT_OMEGA_MOUTH_W / 2,
        MOTOR_MOUNT_COVER_FRONT_Y_LOCAL - MOTOR_MOUNT_EPS,
        mouth_z
    ])
        cube([
            MOTOR_MOUNT_OMEGA_MOUTH_W,
            MOTOR_MOUNT_OMEGA_BODY_L + 2 * MOTOR_MOUNT_EPS,
            MOTOR_MOUNT_OMEGA_OUTER_H / 2 - MOTOR_MOUNT_OMEGA_INNER_H / 2
                + 2 * MOTOR_MOUNT_EPS
        ]);
}

module omega_sleeve_shell() {
    difference() {
        rounded_prism_xz(
            MOTOR_MOUNT_OMEGA_OUTER_W,
            MOTOR_MOUNT_OMEGA_OUTER_H,
            MOTOR_MOUNT_OMEGA_BODY_L,
            MOTOR_MOUNT_OMEGA_OUTER_R,
            MOTOR_MOUNT_COVER_FRONT_Y_LOCAL
        );
        // Rounded rectangular bore follows the 10×12 mm gearbox and clears
        // the smaller 10×10 mm can without turning the sleeve into a tube.
        rounded_prism_xz(
            MOTOR_MOUNT_OMEGA_INNER_W,
            MOTOR_MOUNT_OMEGA_INNER_H,
            MOTOR_MOUNT_OMEGA_BODY_L + 2 * MOTOR_MOUNT_EPS,
            MOTOR_MOUNT_OMEGA_INNER_R,
            MOTOR_MOUNT_COVER_FRONT_Y_LOCAL - MOTOR_MOUNT_EPS
        );
        // Remove the entire lower span of the outer sleeve.  The cut reaches
        // both rounded side transitions, so the motor underside is genuinely
        // open and cannot leave a thin bridge between the two seats.
        omega_mouth_cut();
    }
}

module omega_mount_seat(x, seat_w) {
    union() {
        difference() {
            // A horizontal seat is visible as the outward underscore in the
            // rear profile.  Its fastener axis is local/world Z, not local Y.
            // The holes are clearance for the cabinet guide posts;
            // the M3 screw remains on the same axis through each hole.
            motor_mount_rounded_prism_xy(
                seat_w,
                MOTOR_MOUNT_OMEGA_SEAT_L,
                MOTOR_MOUNT_OMEGA_SEAT_T,
                MOTOR_MOUNT_OMEGA_SEAT_R,
                x,
                MOTOR_MOUNT_OMEGA_SEAT_FRONT_Y_LOCAL,
                MOTOR_MOUNT_OMEGA_SEAT_BOTTOM_Z
            );
            for (y_offset = MOTOR_MOUNT_OMEGA_SEAT_FASTENER_OFFSETS_Y)
                motor_mount_local_z_cylinder(
                    MOTOR_MOUNT_OMEGA_SEAT_GUIDE_HOLE_D,
                    MOTOR_MOUNT_OMEGA_SEAT_T + 2 * MOTOR_MOUNT_EPS,
                    x,
                    MOTOR_MOUNT_OMEGA_SEAT_CENTER_Y_LOCAL + y_offset,
                    MOTOR_MOUNT_OMEGA_SEAT_BOTTOM_Z - MOTOR_MOUNT_EPS
                );
        }
        // A short annular collar gives the hard spring a positive seat above
        // the moving tab while the cabinet post remains inside it.
        for (y_offset = MOTOR_MOUNT_OMEGA_SEAT_FASTENER_OFFSETS_Y)
            difference() {
                motor_mount_local_z_cylinder(
                    MOTOR_MOUNT_OMEGA_SPRING_SEAT_OD,
                    MOTOR_MOUNT_OMEGA_SPRING_SEAT_H,
                    x,
                    MOTOR_MOUNT_OMEGA_SEAT_CENTER_Y_LOCAL + y_offset,
                    MOTOR_MOUNT_OMEGA_SEAT_TOP_Z
                );
                motor_mount_local_z_cylinder(
                    MOTOR_MOUNT_OMEGA_SEAT_GUIDE_HOLE_D,
                    MOTOR_MOUNT_OMEGA_SPRING_SEAT_H + 2 * MOTOR_MOUNT_EPS,
                    x,
                    MOTOR_MOUNT_OMEGA_SEAT_CENTER_Y_LOCAL + y_offset,
                    MOTOR_MOUNT_OMEGA_SEAT_TOP_Z - MOTOR_MOUNT_EPS
                );
            }
    }
}

module omega_mount_seats() {
    // The X− seat is the compact one required by the corrected motor datum;
    // the X+ seat retains the original wider reaction arm.
    omega_mount_seat(
        -MOTOR_MOUNT_OMEGA_LEFT_SEAT_CENTER_X,
        MOTOR_MOUNT_OMEGA_LEFT_SEAT_W
    );
    omega_mount_seat(
        MOTOR_MOUNT_OMEGA_SEAT_CENTER_X,
        MOTOR_MOUNT_OMEGA_SEAT_W
    );
}
//#endregion

//#region 公开 API
module ch1_03c_power_motor_cover() {
    union() {
        omega_sleeve_shell();
        omega_mount_seats();
    }
}

module ch1_03c_power_motor_cover_colored() {
    color("#56616d") ch1_03c_power_motor_cover();
}
//#endregion

//#region 业务逻辑
// Ω 套前端与主动轮后表面仍保持 MOTOR_MOUNT_WHEEL_BACK_GAP；包络贴合电机，
// 不改变主动轮、D 轴和电机轴心；左右两个下向固定座承接螺钉拉力和弹簧预紧反力。
// 轴向贯通的夹套只承受夹持和反扭矩，座子上的孔轴线沿世界 Z 向下固定。
//#endregion

//#region 方法/工具
assert(MOTOR_MOUNT_OMEGA_INNER_W >= MOTOR_MOUNT_OMEGA_MOTOR_W
    + 2 * MOTOR_MOUNT_OMEGA_CLEAR - MOTOR_MOUNT_EPS,
    "omega sleeve must clear the gearbox width");
assert(MOTOR_MOUNT_OMEGA_INNER_H >= MOTOR_MOUNT_OMEGA_MOTOR_H
    + 2 * MOTOR_MOUNT_OMEGA_CLEAR - MOTOR_MOUNT_EPS,
    "omega sleeve must clear the gearbox height");
assert(MOTOR_MOUNT_OMEGA_SEAT_GUIDE_HOLE_D
        > MOTOR_MOUNT_BOSS_GUIDE_OD + 0.60,
    "omega mounting seats must clear the cabinet guide posts");
assert(MOTOR_MOUNT_OMEGA_SEAT_L > MOTOR_MOUNT_SCREW_HEAD_D,
    "omega mounting seats must contain a usable front/rear fastener span");
assert(MOTOR_MOUNT_OMEGA_LEFT_SEAT_W > MOTOR_MOUNT_SCREW_HEAD_D,
    "X-minus omega mounting seat must contain the fastener head");
assert(MOTOR_MOUNT_OMEGA_SPRING_SEAT_OD
        > MOTOR_MOUNT_SPRING_OD,
    "omega spring collars must support the spring");
//#endregion
