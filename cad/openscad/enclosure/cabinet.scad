// Mechanical contract
// process: FDM
// material: PETG preferred; PLA acceptable for fit prototype
// parting_plane: back face Y = D; shell stays, back panel separates
// opening_direction: back panel pulled toward +Y
// fastener: rear-cavity motor mount uses four downward M3 axes on stepped floor bosses;
//           the removable back panel still uses the side-wall/inset-lid scheme
// seal: none — parts cabinet, not watertight
// print_orientation: shell front (Y=0) on bed; panel outer face down in slicer
// units: mm
// note: drawers not modeled this round; 1 mm bay clearance reserved on 4 sides

//#region 导入/依赖
include <cabinet_motor_mount_params.scad>
include <cabinet_tensioner.scad>
include <cabinet_motor_mount.scad>
//#endregion

//#region 常量/配置
$fa = 8;
$fs = 0.35;

PART = is_undef(PART) ? "assembly" : PART;   // assembly | shell | back_panel
EXPLODE = is_undef(EXPLODE) ? 28 : EXPLODE;
//#endregion

//#region 模型/类型
// 尺寸与格口函数在 cabinet_params.scad；张紧 U 在 cabinet_tensioner.scad。
//#endregion

//#region 私有成员
echo("bay_w", bay_w(), "bay_h", bay_h(), "W", W, "H", H);
echo("drawer_outer", drawer_outer_w(), drawer_outer_h(), "inner_h", drawer_inner_h());
echo("service_h", SERVICE_H, "service_w", SERVICE_W, "rear_cavity", REAR_CAVITY);

module outer_frame() {
    difference() {
        cube([W, D, H]);
        translate([WALL, -EPS, WALL])
            cube([INNER_W, D + 2 * EPS, INNER_H]);
    }
}

module partition_plate() {
    translate([0, PARTITION_FRONT_Y, 0])
        cube([W, PARTITION_T, H]);
}

module bay_grid() {
    for (i = [1:N_COL - 1])
        translate([col_x(i) - DIV_T, 0, GRID_ORIGIN_Z])
            cube([DIV_T, FRONT_NET + EPS, GRID_H + EPS]);
    for (j = [1:N_ROW - 1])
        translate([GRID_ORIGIN_X, 0, row_z(j) - SHELF_T])
            cube([GRID_W + EPS, FRONT_NET + EPS, SHELF_T]);
    translate([GRID_ORIGIN_X, 0, GRID_ORIGIN_Z - SHELF_T])
        cube([GRID_W + EPS, FRONT_NET + EPS, SHELF_T]);
}

module front_service_cheek() {
    translate([WALL - EPS, 0, GRID_ORIGIN_Z])
        cube([SERVICE_W + EPS, FRONT_NET + EPS, GRID_H + EPS]);
}

module back_rabbet() {
    translate([
        WALL - RABBET_W,
        D - RABBET_DEPTH,
        WALL - RABBET_W
    ])
        cube([
            INNER_W + 2 * RABBET_W,
            RABBET_DEPTH + EPS,
            INNER_H + 2 * RABBET_W
        ]);
}

module cabinet_shell() {
    intersection() {
        cube([W, D, H]);
        difference() {
            union() {
                outer_frame();
                partition_plate();
                bay_grid();
                front_service_cheek();
                tensioner_guides();
                cabinet_motor_mount_floor_seats_local();
            }
            back_rabbet();
            tensioner_floor_bore();
            cabinet_motor_mount_floor_pilot_holes_local();
        }
    }
}

module back_panel() {
    cube([PANEL_W, BACK_PANEL_T, PANEL_H]);
}

module drawer_ghosts() {
    for (i = [0:N_COL - 1], j = [0:N_ROW - 1])
        translate([
            col_x(i) + DRAWER_CLEAR,
            0.2,
            row_z(j) + DRAWER_CLEAR
        ])
            cube([
                drawer_outer_w(),
                FRONT_NET - 0.6,
                drawer_outer_h()
            ]);
}

module emit_part(name) {
    if (PART == "assembly" || PART == name)
        children();
}
//#endregion

//#region 公开 API
if (is_undef(CABINET_LIB_ONLY) || !CABINET_LIB_ONLY) {
    emit_part("shell") {
        if (PART == "assembly")
            color("#6f8f9a") cabinet_shell();
        else
            cabinet_shell();
    }

    emit_part("back_panel") {
        translate([PANEL_X, PANEL_Y, PANEL_Z]) {
            if (PART == "assembly")
                translate([0, EXPLODE, 0])
                    color("#c4a574") back_panel();
            else
                back_panel();
        }
    }

    if (PART == "assembly")
        color("#d9ff62", 0.18) drawer_ghosts();
}
//#endregion

//#region 视图层
// 预览用 PART=assembly；打印件只导出 shell / back_panel。柜底含蛇链电机固定座的
// 两条承托/限位基台和四个带柱顶盲孔的实体导向柱。
//#endregion

//#region 业务逻辑
// 格栅只在抽屉区。底仓前脸通宽开口放电器；后仓仍是一个开间。
// 动力电机罩不再挂在背板上；柜底两条一级承托基台承接左右固定座，四个二级实体
// 导向柱套入座子孔，罩体从上方落座，硬弹簧套柱，蘑菇头螺钉从上方拧入柱顶盲孔。
// 左颊板只堵前仓抽屉高度，把回程走廊留在后仓。张紧 U 导肋长在后仓底板。
//#endregion

//#region 方法/工具
// 导出: -D PART='"shell"' / '"back_panel"' / '"assembly"'
//#endregion
