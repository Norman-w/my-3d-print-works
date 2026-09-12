// 柜体背板上的动力电机固定罩接收 boss。
// 本文件假设父文件已通过 cabinet_motor_mount_params.scad 载入共享参数。

//#region 导入/依赖
// 无额外依赖；尺寸与位置来自 cabinet_motor_mount_params.scad。
//#endregion

//#region 私有成员
module local_y_cylinder(d, h, x, z, y0) {
    translate([x, y0 + h, z])
        rotate([90, 0, 0])
            cylinder(d = d, h = h);
}
//#endregion

//#region 公开 API
module cabinet_motor_mount_bosses_local() {
    c = motor_mount_c();
    local_x = c[0] - PANEL_X;
    local_z = c[1] - PANEL_Z;
    difference() {
        union() {
            for (p = MOTOR_MOUNT_BOSS_OFFSETS) {
                local_y_cylinder(
                    MOTOR_MOUNT_BOSS_OD,
                    MOTOR_MOUNT_BOSS_L,
                    local_x + p[0],
                    local_z + p[1],
                    -MOTOR_MOUNT_BOSS_L
                );
                local_y_cylinder(
                    MOTOR_MOUNT_BOSS_PAD_D,
                    MOTOR_MOUNT_BOSS_PAD_H,
                    local_x + p[0],
                    local_z + p[1],
                    -MOTOR_MOUNT_BOSS_PAD_H
                );
            }
        }
        // 嵌件从 boss 的前端压入，后面保留约 1.5 mm 实体承托到背板。
        for (p = MOTOR_MOUNT_BOSS_OFFSETS)
            local_y_cylinder(
                MOTOR_MOUNT_INSERT_D,
                MOTOR_MOUNT_INSERT_L + MOTOR_MOUNT_EPS,
                local_x + p[0],
                local_z + p[1],
                -MOTOR_MOUNT_BOSS_L - MOTOR_MOUNT_EPS
            );
    }
}
//#endregion

//#region 业务逻辑
// 该模块在 cabinet.scad 的 back_panel() 局部坐标内调用：boss 向 −Y 伸入后仓，
// 与固定罩法兰的四个孔面接触；底座盘把螺钉拉力分散到 5 mm 背板。
//#endregion
