// Mechanical contract
// process: FDM
// material: PETG preferred; PLA acceptable for fit prototype
// parting_plane: back face Y = D; shell stays, back panel separates
// opening_direction: back panel pulled toward +Y
// fastener: deferred — inset lid with screws on the side walls; no mid-span bosses
// seal: none — parts cabinet, not watertight
// print_orientation: shell front (Y=0) on bed; panel outer face down in slicer
// units: mm
// note: drawers not modeled this round; 1 mm bay clearance reserved on 4 sides

//#region 导入/依赖
include <cabinet_params.scad>
//#endregion

//#region 常量/配置
$fa = 8;
$fs = 0.35;

PART = "assembly";               // assembly | shell | back_panel
EXPLODE = 28;
//#endregion

//#region 模型/类型
// 尺寸与格口函数在 cabinet_params.scad。
//#endregion

//#region 私有成员
echo("bay_w", bay_w(), "bay_h", bay_h());
echo("drawer_outer", drawer_outer_w(), drawer_outer_h(), "inner_h", drawer_inner_h());
echo("rear_cavity", REAR_CAVITY, "fastener", "side screws later, no bosses");

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
        translate([col_x(i) - DIV_T, 0, WALL - EPS])
            cube([DIV_T, FRONT_NET + EPS, INNER_H + 2 * EPS]);
    for (j = [1:N_ROW - 1])
        translate([WALL - EPS, 0, row_z(j) - SHELF_T])
            cube([INNER_W + 2 * EPS, FRONT_NET + EPS, SHELF_T]);
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
            }
            back_rabbet();
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
//#endregion

//#region 视图层
// 预览用 PART=assembly；打印件只导出 shell / back_panel。
//#endregion

//#region 业务逻辑
// 前脸开口、隔板、层板和立板一次成型。后仓留空给链轮，中部不设 Boss。
// 背板只坐后口止口；侧边螺丝和内嵌后盖下一轮再做。
//#endregion

//#region 方法/工具
// 导出: -D PART='"shell"' / '"back_panel"' / '"assembly"'
//#endregion
