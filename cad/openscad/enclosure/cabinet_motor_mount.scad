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
//#endregion

//#region 公开 API
module cabinet_motor_mount_floor_seats_local() {
    c = motor_mount_c();
    floor_y = MOTOR_MOUNT_CHAIN_Y
        + MOTOR_MOUNT_OMEGA_SEAT_CENTER_Y_LOCAL;
    difference() {
        union() {
            for (offset_x = MOTOR_MOUNT_FLOOR_SEAT_OFFSETS_X)
                for (y_offset = MOTOR_MOUNT_OMEGA_SEAT_FASTENER_OFFSETS_Y)
                    local_z_cylinder(
                        MOTOR_MOUNT_FLOOR_SEAT_D,
                        MOTOR_MOUNT_FLOOR_SEAT_H,
                        c[0] + offset_x,
                        floor_y + y_offset,
                        WALL - MOTOR_MOUNT_EPS
                    );
        }
        // The vertical bore is the actual world-Y fixing reference.  It
        // passes through the printed floor seat and the 3.2 mm cabinet floor;
        // the underside can receive an M3 nut or heat-set insert.
        for (offset_x = MOTOR_MOUNT_FLOOR_SEAT_OFFSETS_X)
            for (y_offset = MOTOR_MOUNT_OMEGA_SEAT_FASTENER_OFFSETS_Y)
                local_z_cylinder(
                    MOTOR_MOUNT_FLOOR_BORE_D,
                    MOTOR_MOUNT_FLOOR_SEAT_H + WALL + 2 * MOTOR_MOUNT_EPS,
                    c[0] + offset_x,
                    floor_y + y_offset,
                    -MOTOR_MOUNT_EPS
                );
    }
}
//#endregion

//#region 业务逻辑
// 该模块在 cabinet.scad 的 cabinet_shell() 局部坐标内调用：两块圆形接收座
// 直接坐在柜底，四个孔的轴线沿旧 Z / 世界 Y；Ω 套底部的左右固定座从上方落到这里。
//#endregion
