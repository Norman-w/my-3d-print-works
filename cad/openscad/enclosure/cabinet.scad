// Mechanical contract
// process: FDM
// material: PETG preferred; PLA acceptable for fit prototype
// parting_plane: back face Y = D; shell stays, back panel separates
// opening_direction: back panel pulled toward +Y
// fastener: M3 socket cap from panel outside into heat-set inserts at boss tips
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
echo("rear_cavity", REAR_CAVITY, "boss_h", BOSS_H, "bosses", len(boss_points()));
echo("rib_rule", "inward only; pads only on interior bosses");

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

module boss_rib() {
    hull() {
        translate([BOSS_R - 0.2, RIB_H * 0.92, 0])
            cube([0.4, 0.4, RIB_T], center = true);
        translate([BOSS_R - 0.2, 0.2, 0])
            cube([0.4, 0.4, RIB_T], center = true);
        translate([BOSS_R + RIB_L, 0.2, 0])
            cube([0.4, 0.4, RIB_T], center = true);
    }
}

module boss_solid(angles, with_pad) {
    union() {
        if (with_pad)
            translate([0, -EPS, 0])
                rotate([-90, 0, 0])
                    cylinder(d = BOSS_PAD_D, h = BOSS_PAD_H + EPS);
        rotate([-90, 0, 0])
            cylinder(d = BOSS_OD, h = BOSS_H);
        for (a = angles)
            rotate([0, a, 0])
                boss_rib();
    }
}

module all_bosses() {
    pts = boss_points();
    angs = boss_rib_angles();
    for (i = [0:len(pts) - 1])
        translate([pts[i][0], PARTITION_BACK_Y, pts[i][1]])
            boss_solid(angs[i], boss_has_pad(i));
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

module boss_fastener_cuts() {
    for (p = boss_points())
        translate([p[0], PARTITION_BACK_Y, p[1]]) {
            translate([0, BOSS_FLOOR, 0])
                rotate([-90, 0, 0])
                    cylinder(
                        d = BOSS_HOLLOW_D,
                        h = BOSS_H - BOSS_FLOOR - INSERT_DEPTH - 1
                    );
            translate([0, BOSS_H - INSERT_DEPTH, 0])
                rotate([-90, 0, 0])
                    cylinder(d = INSERT_D, h = INSERT_DEPTH + EPS);
            translate([0, BOSS_H - 0.8, 0])
                rotate([-90, 0, 0])
                    cylinder(d1 = INSERT_D, d2 = INSERT_D + 1.6, h = 0.8 + EPS);
        }
}

module cabinet_shell() {
    intersection() {
        cube([W, D, H]);
        difference() {
            union() {
                outer_frame();
                partition_plate();
                bay_grid();
                all_bosses();
            }
            back_rabbet();
            boss_fastener_cuts();
        }
    }
}

module panel_fastener_cuts() {
    for (p = boss_points()) {
        hx = p[0] - PANEL_X;
        hz = p[1] - PANEL_Z;
        translate([hx, -EPS, hz])
            rotate([-90, 0, 0])
                cylinder(d = SCREW_CLEAR_D, h = BACK_PANEL_T + 2 * EPS);
        translate([hx, BACK_PANEL_T - CBORE_H, hz])
            rotate([-90, 0, 0])
                cylinder(d = CBORE_D, h = CBORE_H + EPS);
    }
}

module back_panel() {
    difference() {
        cube([PANEL_W, BACK_PANEL_T, PANEL_H]);
        panel_fastener_cuts();
    }
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
// 前脸开口、隔板、层板和立板一次成型。后仓只有 Boss 和加强筋，给链轮留空。
// 四角与上下边中点 Boss 贴外框承力；两颗内柱落在立板/层板交叉背后。
// 背板坐进止口，沉孔从外侧进；拧紧时止口是压紧止挡，Boss 短 0.4 mm。
//#endregion

//#region 方法/工具
// 导出: -D PART='"shell"' / '"back_panel"' / '"assembly"'
//#endregion
