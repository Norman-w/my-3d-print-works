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

module rounded_pad_xy(w, d, h, r, x, y0, z0) {
    // Rounded rectangular pad in the cabinet floor's XY plane.  The x
    // argument is the pad centre; y0 is its front edge in the legacy source
    // frame.  It is intentionally a continuous rail, not four floating disks.
    translate([x, y0, z0])
        hull() {
            for (dx = [-w / 2 + r, w / 2 - r], dy = [r, d - r])
                translate([dx, dy, 0])
                    cylinder(r = r, h = h);
        }
}

module motor_mount_spring_coil(x, y) {
    // Preview-only purchased spring.  It is coaxial with the hollow guide
    // post and starts just above the printed collar on the moving Omega seat.
    translate([x, y, MOTOR_MOUNT_SPRING_START_Z])
        linear_extrude(
            height = MOTOR_MOUNT_SPRING_FREE_L,
            twist = 360 * 6,
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
    // The shaft points downward through the post.  The two-stage head is a
    // simple printable visual of the large mushroom head that compresses the
    // stiff spring; it is not claimed to be a thread model.
    shaft_z0 = MOTOR_MOUNT_BOSS_STAGE1_Z0 - MOTOR_MOUNT_EPS;
    head_z = MOTOR_MOUNT_SCREW_HEAD_Z;
    translate([x, y, shaft_z0])
        cylinder(
            d = MOTOR_MOUNT_SCREW_SHAFT_D,
            h = head_z + MOTOR_MOUNT_SCREW_HEAD_H - shaft_z0
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
    rail_y0 = floor_y - MOTOR_MOUNT_BOSS_STAGE1_RAIL_L / 2;
    difference() {
        union() {
            for (offset_x = MOTOR_MOUNT_FLOOR_SEAT_OFFSETS_X)
                rounded_pad_xy(
                    MOTOR_MOUNT_BOSS_STAGE1_RAIL_W,
                    MOTOR_MOUNT_BOSS_STAGE1_RAIL_L,
                    MOTOR_MOUNT_BOSS_STAGE1_H,
                    MOTOR_MOUNT_BOSS_STAGE1_RAIL_R,
                    c[0] + offset_x,
                    rail_y0,
                    MOTOR_MOUNT_BOSS_STAGE1_Z0
                );
            // Each fixing hole has its own hollow 20 mm guide.  The guides
            // rise from the first step and keep the spring and screw coaxial
            // while the Omega seat is pressed down.
            for (offset_x = MOTOR_MOUNT_FLOOR_SEAT_OFFSETS_X)
                for (y_offset = MOTOR_MOUNT_OMEGA_SEAT_FASTENER_OFFSETS_Y)
                    local_z_cylinder(
                        MOTOR_MOUNT_BOSS_GUIDE_OD,
                        MOTOR_MOUNT_BOSS_GUIDE_H,
                        c[0] + offset_x,
                        floor_y + y_offset,
                        MOTOR_MOUNT_BOSS_STAGE1_TOP_Z
                    );
        }
        // The continuous rails fuse into the cabinet floor and all four
        // concentric bores pass through both steps and the 3.2 mm floor.  The
        // underside can receive an M3 nut or heat-set insert.
        for (offset_x = MOTOR_MOUNT_FLOOR_SEAT_OFFSETS_X)
            for (y_offset = MOTOR_MOUNT_OMEGA_SEAT_FASTENER_OFFSETS_Y)
                local_z_cylinder(
                    MOTOR_MOUNT_BOSS_GUIDE_BORE_D,
                    MOTOR_MOUNT_BOSS_STAGE1_H
                        + MOTOR_MOUNT_BOSS_GUIDE_H
                        + 2 * MOTOR_MOUNT_EPS,
                    c[0] + offset_x,
                    floor_y + y_offset,
                    MOTOR_MOUNT_BOSS_STAGE1_Z0 - MOTOR_MOUNT_EPS
                );
    }
}

module cabinet_motor_mount_floor_bores_local() {
    // The cabinet floor is a solid part of outer_frame().  Keep this cut
    // separate from the boss module so the four guide bores remain open
    // after the bosses are fused into that floor.
    c = motor_mount_c();
    floor_y = MOTOR_MOUNT_CHAIN_Y
        + MOTOR_MOUNT_OMEGA_SEAT_CENTER_Y_LOCAL;
    for (offset_x = MOTOR_MOUNT_FLOOR_SEAT_OFFSETS_X)
        for (y_offset = MOTOR_MOUNT_OMEGA_SEAT_FASTENER_OFFSETS_Y)
            local_z_cylinder(
                MOTOR_MOUNT_BOSS_GUIDE_BORE_D,
                MOTOR_MOUNT_BOSS_STAGE1_H
                    + MOTOR_MOUNT_BOSS_GUIDE_H
                    + 2 * MOTOR_MOUNT_EPS,
                c[0] + offset_x,
                floor_y + y_offset,
                MOTOR_MOUNT_BOSS_STAGE1_Z0 - MOTOR_MOUNT_EPS
            );
}

module cabinet_motor_mount_spring_hardware_local() {
    c = motor_mount_c();
    floor_y = MOTOR_MOUNT_CHAIN_Y
        + MOTOR_MOUNT_OMEGA_SEAT_CENTER_Y_LOCAL;
    for (offset_x = MOTOR_MOUNT_FLOOR_SEAT_OFFSETS_X)
        for (y_offset = MOTOR_MOUNT_OMEGA_SEAT_FASTENER_OFFSETS_Y) {
            x = c[0] + offset_x;
            y = floor_y + y_offset;
            motor_mount_spring_coil(x, y);
            motor_mount_mushroom_screw(x, y);
        }
}
//#endregion

//#region 业务逻辑
// 该模块在 cabinet.scad 的 cabinet_shell() 局部坐标内调用：两条连续的
// 一级台阶导轨从柜底长出，四个空心二级导向柱对应 Ω 套的四个孔。旧 Z
// 是当前世界 Y；固定螺钉从上方沿世界 -Y 下压弹簧，Ω 套从上方沿导向柱落座。
// cabinet_motor_mount_spring_hardware_local() 只在链条总装配中显示采购件
// 弹簧和螺钉，不把它们并入柜体打印 STL。
//#endregion
