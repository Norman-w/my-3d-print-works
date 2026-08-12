// ============================================================
// v3 下半壳体 — Z <= 0，分型面穿过旋钮轴和两根线缆。
// - 底面 4×M2 合盖螺丝
// - 4×PCB 罗马柱，适配约 3mm 安装孔
// - 双侧线缆夹齿与导向柱
// ============================================================
include <parameters.scad>
include <utilities.scad>
include <module-holder.scad>
include <cable-gland.scad>
include <cable-strain-relief.scad>

module bottom_half() {
    r_outer = CORNER_RADIUS;
    r_inner = max(r_outer - SIDE_WALL_THICKNESS, 0.5);
    shell_boss_h = BOX_INNER_BOTTOM_H;
    module_boss_h = PCB_BOTTOM_Z + BOX_INNER_BOTTOM_H;

    difference() {
        union() {
            difference() {
                intersection() {
                    translate([BOX_CENTER_X, 0, BOX_CENTER_Z])
                        rounded_rect_prism(
                            BOX_OUTER_LENGTH, BOX_OUTER_WIDTH,
                            BOX_OUTER_HEIGHT, r_outer, center = true);
                    translate([0, 0, -BOX_OUTER_HEIGHT])
                        cube([BOX_OUTER_LENGTH * 2,
                              BOX_OUTER_WIDTH * 2,
                              BOX_OUTER_HEIGHT * 2], center = true);
                }

                intersection() {
                    translate([BOX_CENTER_X, 0, BOX_CENTER_Z])
                        rounded_rect_prism(
                            BOX_INNER_LENGTH, BOX_INNER_WIDTH,
                            BOX_INNER_HEIGHT, r_inner, center = true);
                    translate([0, 0, -BOX_INNER_HEIGHT])
                        cube([BOX_INNER_LENGTH * 2,
                              BOX_INNER_WIDTH * 2,
                              BOX_INNER_HEIGHT * 2], center = true);
                }
            }

            // 合盖四角 Boss：螺丝从底面穿入上壳导孔柱。
            for (bx = BOSS_X_POSITIONS, sy = [-1, 1]) {
                translate([bx, sy * BOSS_Y,
                           -BOX_INNER_BOTTOM_H]) {
                    cylinder(d1 = BOSS_REINFORCE_OD,
                             d2 = BOSS_DIAMETER,
                             h = min(BOSS_REINFORCE_H, shell_boss_h),
                             $fn = 32);
                    if (shell_boss_h > BOSS_REINFORCE_H)
                        translate([0, 0, BOSS_REINFORCE_H])
                            cylinder(d = BOSS_DIAMETER,
                                     h = shell_boss_h - BOSS_REINFORCE_H,
                                     $fn = 32);
                }
            }

            // PCB 四孔支柱：柱顶即 PCB 底面。
            for (p = MODULE_HOLES) {
                translate([p[0], p[1], -BOX_INNER_BOTTOM_H]) {
                    cylinder(d1 = MODULE_BOSS_REINFORCE_OD,
                             d2 = MODULE_BOSS_DIAMETER,
                             h = min(MODULE_BOSS_REINFORCE_H,
                                     module_boss_h), $fn = 32);
                    if (module_boss_h > MODULE_BOSS_REINFORCE_H)
                        translate([0, 0, MODULE_BOSS_REINFORCE_H])
                            cylinder(d = MODULE_BOSS_DIAMETER,
                                     h = module_boss_h
                                         - MODULE_BOSS_REINFORCE_H,
                                     $fn = 32);
                }

                // 定位颈进入约 3mm PCB 孔，在锁螺丝前先消除横向晃动。
                translate([p[0], p[1], PCB_BOTTOM_Z])
                    cylinder(d1 = MODULE_LOCATOR_DIAMETER,
                             d2 = MODULE_LOCATOR_TIP_DIAMETER,
                             h = MODULE_LOCATOR_HEIGHT, $fn = 32);
            }

            cable_clamp_teeth_bottom();
            cable_guide_posts_bottom();
            alignment_lip();
        }

        // 合盖通孔 + 底面沉头。
        for (bx = BOSS_X_POSITIONS, sy = [-1, 1]) {
            translate([bx, sy * BOSS_Y,
                       BOX_OUTER_BOTTOM_Z - 0.1])
                cylinder(d = SCREW_CLEARANCE,
                         h = BOX_INNER_BOTTOM_H + WALL_THICKNESS + 0.3,
                         $fn = 24);
            translate([bx, sy * BOSS_Y,
                       BOX_OUTER_BOTTOM_Z - 0.1])
                cylinder(d1 = SCREW_HEAD_DIAMETER,
                         d2 = SCREW_CLEARANCE,
                         h = WALL_THICKNESS + 0.4, $fn = 32);
        }

        // PCB 螺丝从元件面穿板，锁入底壳支柱。
        for (p = MODULE_HOLES)
            translate([p[0], p[1], -BOX_INNER_BOTTOM_H - 0.1])
                cylinder(d = MODULE_BOSS_PILOT,
                         h = module_boss_h + MODULE_LOCATOR_HEIGHT + 0.2,
                         $fn = 24);

        module_knob_end_cuts();

        for (sy = [-1, 1])
            translate([CABLE_ENTRY_X, sy * BOX_OUTER_WIDTH/2, 0])
                cable_channel_half_bottom();
    }
}

module alignment_lip() {
    lh = ALIGNMENT_LIP_H;
    lw = ALIGNMENT_LIP_W;
    lox = BOX_INNER_LENGTH/2 + lw;
    loy = BOX_INNER_WIDTH/2 + lw;
    lix = BOX_INNER_LENGTH/2 - PRINT_TOLERANCE;
    liy = BOX_INNER_WIDTH/2 - PRINT_TOLERANCE;

    translate([BOX_CENTER_X, 0, 0])
        difference() {
            linear_extrude(height = lh)
                rounded_rect_2d(lox * 2, loy * 2,
                                max(CORNER_RADIUS - SIDE_WALL_THICKNESS + lw,
                                    0.5));
            translate([0, 0, -0.1])
                linear_extrude(height = lh + 0.2)
                    rounded_rect_2d(lix * 2, liy * 2,
                                    max(CORNER_RADIUS - SIDE_WALL_THICKNESS,
                                        0.5));
        }
}
