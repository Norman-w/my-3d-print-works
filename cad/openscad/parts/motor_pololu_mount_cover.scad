// Mechanical contract
// process: FDM; PETG/nylon recommended for the cover and printed boss receiver
// material: printed motor cover; mating motor is purchased Pololu #1101
// parting_plane: open front faces the power wheel; cover removes toward +Y/back panel
// opening_direction: slide the cover along +Y after removing four M3 screws
// fastener: four M3 screws into 4.6 mm heat-set-insert pockets in the back-panel bosses
// seal: n/a; cable exit is an open rear slot
// print_orientation: rotate as needed in the slicer; the source axis is Y, not a claimed bed orientation
// units: mm
// note: the cover cavity is a clearance cage for a 10 x 12 mm gearbox and 10 x 10 mm motor body;
//       it is a structural retainer, not a motor replacement or a sealed enclosure.

//#region 导入/依赖
include <../enclosure/cabinet_motor_mount_params.scad>
include <motor_pololu_micro_metal_100_1_hp_6v.scad>
//#endregion

//#region 常量/配置
$fa = 8;
$fs = 0.22;
//#endregion

//#region 模型/类型
// 固定罩局部原点为动力轮轴中心；X/Z 为罩体截面，Y 向后仓/背板方向增加。
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

module local_y_cylinder(d, h, x, z, y0) {
    translate([x, y0 + h, z])
        rotate([90, 0, 0])
            cylinder(d = d, h = h);
}

module local_y_slot(d, h, x, z, slot, y0) {
    // Elongate the fastener clearance in local Z.  In the canonical web
    // world this is the vertical +Y direction after the legacy adapter, so
    // the cover can move down against the spring without losing the four
    // back-panel screw references.
    hull() {
        local_y_cylinder(d, h, x, z - slot / 2, y0);
        local_y_cylinder(d, h, x, z + slot / 2, y0);
    }
}

module cover_shell() {
    rear_wall_front =
        MOTOR_MOUNT_COVER_BODY_REAR_Y_LOCAL - MOTOR_MOUNT_COVER_REAR_WALL_T;
    difference() {
        rounded_prism_xz(
            MOTOR_MOUNT_COVER_OUTER_W,
            MOTOR_MOUNT_COVER_OUTER_H,
            MOTOR_MOUNT_COVER_BODY_L,
            MOTOR_MOUNT_COVER_OUTER_R,
            MOTOR_MOUNT_COVER_FRONT_Y_LOCAL
        );
        // 前端开口，后侧留下 2 mm 罩底；两侧留出 2 mm 电机装配间隙。
        rounded_prism_xz(
            MOTOR_MOUNT_COVER_INNER_W,
            MOTOR_MOUNT_COVER_INNER_H,
            MOTOR_MOUNT_COVER_BODY_L
                - MOTOR_MOUNT_COVER_REAR_WALL_T
                + MOTOR_MOUNT_EPS,
            MOTOR_MOUNT_COVER_INNER_R,
            MOTOR_MOUNT_COVER_FRONT_Y_LOCAL - MOTOR_MOUNT_EPS
        );
        // Pololu 后端电气片/引线的出线槽，不封死电机后端。
        translate([
            -MOTOR_MOUNT_COVER_CABLE_SLOT_W / 2,
            rear_wall_front - MOTOR_MOUNT_EPS,
            -MOTOR_MOUNT_COVER_CABLE_SLOT_H / 2
        ])
            cube([
                MOTOR_MOUNT_COVER_CABLE_SLOT_W,
                MOTOR_MOUNT_COVER_REAR_WALL_T + 2 * MOTOR_MOUNT_EPS,
                MOTOR_MOUNT_COVER_CABLE_SLOT_H
            ]);
    }
}

module cover_flange() {
    difference() {
        rounded_prism_xz(
            MOTOR_MOUNT_COVER_FLANGE_W,
            MOTOR_MOUNT_COVER_FLANGE_H,
            MOTOR_MOUNT_COVER_FLANGE_T + MOTOR_MOUNT_COVER_OVERLAP,
            MOTOR_MOUNT_COVER_OUTER_R,
            MOTOR_MOUNT_COVER_FLANGE_FRONT_Y_LOCAL
        );
        for (p = MOTOR_MOUNT_BOSS_OFFSETS) {
            local_y_slot(
                MOTOR_MOUNT_SCREW_CLEAR_D,
                MOTOR_MOUNT_COVER_FLANGE_T + 2 * MOTOR_MOUNT_EPS,
                p[0],
                p[1],
                MOTOR_MOUNT_SLIDE_STROKE,
                MOTOR_MOUNT_COVER_FLANGE_FRONT_Y_LOCAL - MOTOR_MOUNT_EPS
            );
            local_y_slot(
                MOTOR_MOUNT_SCREW_HEAD_D,
                MOTOR_MOUNT_SCREW_HEAD_H + MOTOR_MOUNT_EPS,
                p[0],
                p[1],
                MOTOR_MOUNT_SLIDE_STROKE,
                MOTOR_MOUNT_COVER_FLANGE_FRONT_Y_LOCAL - MOTOR_MOUNT_EPS
            );
        }
    }
}
//#endregion

//#region 公开 API
module ch1_03c_power_motor_cover() {
    union() {
        cover_shell();
        cover_flange();
    }
}

module ch1_03c_power_motor_cover_colored() {
    color("#56616d") ch1_03c_power_motor_cover();
}
//#endregion

//#region 业务逻辑
// 罩体前缘与动力轮后表面保持 0.5 mm 轴向间隙；内腔 14×16 mm 包络覆盖 10×12 mm 减速箱。
// 四个法兰孔与 cabinet_motor_mount_bosses_local() 同一组 ±10 / ±10.5 mm 坐标。
//#endregion

//#region 方法/工具
// 独立入口见 cad/openscad/ch1_03c_power_motor_cover.scad。
//#endregion
