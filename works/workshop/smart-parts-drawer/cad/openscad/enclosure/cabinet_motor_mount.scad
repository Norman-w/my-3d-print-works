// 柜体底部的蛇形动力电机 Ω 形固定座接收面。
// 本文件假设父文件已通过 cabinet_motor_mount_params.scad 载入共享参数。

//#region 导入/依赖
// 无额外依赖；尺寸与位置来自 cabinet_motor_mount_params.scad。
//#endregion

//#region 私有成员
module local_z_cylinder(d, h, x, y, z0) {
    translate([x, y, z0])
        cylinder(d = d, h = h);
}

module motor_mount_spring_coil(x, y) {
    // Preview-only purchased spring.  It is coaxial with the solid Ø5 guide
    // post and is shown at the installed/preloaded length, not its 14 mm free
    // length.  The real spring remains a purchased part.
    translate([x, y, MOTOR_MOUNT_SPRING_START_Z])
        linear_extrude(
            height = MOTOR_MOUNT_SPRING_INSTALLED_L,
            twist = 360 * 3,
            slices = 48
        )
            translate([
                MOTOR_MOUNT_SPRING_OD / 2
                    - MOTOR_MOUNT_SPRING_WIRE_D / 2,
                0
            ])
                circle(d = MOTOR_MOUNT_SPRING_WIRE_D);
}

module motor_mount_mushroom_screw(x, y) {
    // The shaft points downward into the blind pilot in the post.  The two-stage head is a
    // simple printable visual of the large mushroom head that compresses the
    // stiff spring; it is not claimed to be a thread model.
    shaft_z0 = MOTOR_MOUNT_BOSS_PILOT_BOTTOM_Z - MOTOR_MOUNT_EPS;
    head_z = MOTOR_MOUNT_SCREW_HEAD_Z;
    translate([x, y, shaft_z0])
        cylinder(
            d = MOTOR_MOUNT_SCREW_SHAFT_D,
            h = head_z - shaft_z0 + MOTOR_MOUNT_EPS
        );
    translate([x, y, head_z])
        hull() {
            cylinder(d = MOTOR_MOUNT_SCREW_HEAD_D * 0.78, h = 0.65);
            translate([0, 0, MOTOR_MOUNT_SCREW_HEAD_H - 0.65])
                cylinder(d = MOTOR_MOUNT_SCREW_HEAD_D, h = 0.65);
        }
}
//#endregion

//#region 公开 API
module cabinet_motor_mount_floor_seats_local() {
    c = motor_mount_c();
    floor_y = MOTOR_MOUNT_CHAIN_Y
        + MOTOR_MOUNT_OMEGA_SEAT_CENTER_Y_LOCAL;
    union() {
        // Four independent circular root bosses fuse into the cabinet floor.
        // They are deliberately not a pair of long rails: each Ω-seat hole
        // has its own load path and its own coaxial M3 pilot.
        for (spec = MOTOR_MOUNT_FLOOR_SEAT_SPECS)
            for (y_offset = MOTOR_MOUNT_OMEGA_SEAT_FASTENER_OFFSETS_Y)
                local_z_cylinder(
                    spec[1],
                    MOTOR_MOUNT_BOSS_STAGE1_H,
                    c[0] + spec[0],
                    floor_y + y_offset,
                    MOTOR_MOUNT_BOSS_STAGE1_Z0
                );
        // Each fixing point continues as a solid Ø5 guide post.  The moving
        // Ω seat's Ø5.8 hole slides over it; the post section above the base
        // shoulder is exactly 12 mm high.
        for (spec = MOTOR_MOUNT_FLOOR_SEAT_SPECS)
            for (y_offset = MOTOR_MOUNT_OMEGA_SEAT_FASTENER_OFFSETS_Y)
                local_z_cylinder(
                    MOTOR_MOUNT_BOSS_GUIDE_OD,
                    MOTOR_MOUNT_BOSS_GUIDE_H,
                    c[0] + spec[0],
                    floor_y + y_offset,
                    MOTOR_MOUNT_BOSS_STAGE1_TOP_Z
                );
    }
}

module cabinet_motor_mount_floor_pilot_holes_local() {
    // These are blind M3 tapping pilots.  They open at the post top but stop
    // above the circular base shoulder and cabinet floor, so a screw threads into the boss
    // instead of falling through the box.
    c = motor_mount_c();
    floor_y = MOTOR_MOUNT_CHAIN_Y
        + MOTOR_MOUNT_OMEGA_SEAT_CENTER_Y_LOCAL;
    for (spec = MOTOR_MOUNT_FLOOR_SEAT_SPECS)
        for (y_offset = MOTOR_MOUNT_OMEGA_SEAT_FASTENER_OFFSETS_Y)
            local_z_cylinder(
                MOTOR_MOUNT_BOSS_PILOT_D,
                MOTOR_MOUNT_BOSS_PILOT_DEPTH + 2 * MOTOR_MOUNT_EPS,
                c[0] + spec[0],
                floor_y + y_offset,
                MOTOR_MOUNT_BOSS_PILOT_BOTTOM_Z - MOTOR_MOUNT_EPS
            );
}

// Legacy API name retained for external preview scripts; this is no longer a
// through-bore and now delegates to the blind pilot-hole cut.
module cabinet_motor_mount_floor_bores_local() {
    cabinet_motor_mount_floor_pilot_holes_local();
}

module cabinet_motor_mount_spring_hardware_local() {
    c = motor_mount_c();
    floor_y = MOTOR_MOUNT_CHAIN_Y
        + MOTOR_MOUNT_OMEGA_SEAT_CENTER_Y_LOCAL;
    for (spec = MOTOR_MOUNT_FLOOR_SEAT_SPECS)
        for (y_offset = MOTOR_MOUNT_OMEGA_SEAT_FASTENER_OFFSETS_Y) {
            x = c[0] + spec[0];
            y = floor_y + y_offset;
            motor_mount_spring_coil(x, y);
            motor_mount_mushroom_screw(x, y);
        }
}
//#endregion

//#region 业务逻辑
// 该模块在 cabinet.scad 的 cabinet_shell() 局部坐标内调用：四个独立的
// 圆形一级根部基台从柜底长出，四个 Ø5 实体二级导向柱对应 Ω 套四个孔。
// 座子从上方套入导向柱并由根部基台托住；弹簧套在柱外，M3 固定螺钉从
// 上方沿世界 -Z 进入柱顶盲孔。
// cabinet_motor_mount_spring_hardware_local() 只在链条总装配中显示采购件
// 弹簧和螺钉，不把它们并入柜体打印 STL。
//#endregion
