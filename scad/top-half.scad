// ============================================================
// v3 上半壳体 — Z >= 0
// - 旋钮 / 双线缆半孔
// - 散热片上方排气槽 + 两侧进气槽
// - 四角导孔柱承接底面合盖螺丝
// ============================================================
include <parameters.scad>
include <utilities.scad>
include <module-holder.scad>
include <cable-gland.scad>
include <cable-strain-relief.scad>
include <ventilation.scad>

module top_half() {
    difference() {
        union() {
            _top_shell_with_alignment_groove();
            cable_clamp_teeth_top();

            // 四角导孔柱从分型面连续接到上盖顶板，承接底面螺丝。
            for (bx = BOSS_X_POSITIONS, sy = [-1, 1]) {
                translate([bx, sy * BOSS_Y, 0])
                    difference() {
                        union() {
                            cylinder(d1 = BOSS_DIAMETER,
                                     d2 = BOSS_REINFORCE_OD,
                                     h = min(BOSS_REINFORCE_H,
                                             TOP_CLOSURE_BOSS_H),
                                     $fn = 32);
                            if (TOP_CLOSURE_BOSS_H > BOSS_REINFORCE_H)
                                translate([0, 0, BOSS_REINFORCE_H])
                                    cylinder(d = BOSS_REINFORCE_OD,
                                             h = TOP_CLOSURE_BOSS_H
                                                 - BOSS_REINFORCE_H,
                                             $fn = 32);
                        }
                        translate([0, 0, -0.1])
                            cylinder(d = BOSS_PILOT_HOLE,
                                     h = TOP_CLOSURE_BOSS_H + 0.2,
                                     $fn = 24);
                    }
            }
        }

        module_knob_end_cuts();
        top_vent_cuts();
        side_vent_cuts();

        for (sy = [-1, 1])
            translate([CABLE_ENTRY_X, sy * BOX_OUTER_WIDTH/2, 0])
                cable_channel_half_top();
    }
}

module _top_shell_with_alignment_groove() {
    r_outer = CORNER_RADIUS;
    r_inner = max(r_outer - SIDE_WALL_THICKNESS, 0.5);

    difference() {
        intersection() {
            translate([BOX_CENTER_X, 0, BOX_CENTER_Z])
                rounded_rect_prism(
                    BOX_OUTER_LENGTH, BOX_OUTER_WIDTH, BOX_OUTER_HEIGHT,
                    r_outer, center = true);
            translate([0, 0, BOX_OUTER_HEIGHT])
                cube([BOX_OUTER_LENGTH * 2, BOX_OUTER_WIDTH * 2,
                      BOX_OUTER_HEIGHT * 2], center = true);
        }

        intersection() {
            translate([BOX_CENTER_X, 0, BOX_CENTER_Z])
                rounded_rect_prism(
                    BOX_INNER_LENGTH, BOX_INNER_WIDTH, BOX_INNER_HEIGHT,
                    r_inner, center = true);
            translate([0, 0, BOX_INNER_HEIGHT])
                cube([BOX_INNER_LENGTH * 2, BOX_INNER_WIDTH * 2,
                      BOX_INNER_HEIGHT * 2], center = true);
        }

        alignment_groove();
    }
}

module alignment_groove() {
    gh = ALIGNMENT_LIP_H + 0.3;
    gox = BOX_INNER_LENGTH/2 + ALIGNMENT_LIP_W + PRINT_TOLERANCE;
    goy = BOX_INNER_WIDTH/2 + ALIGNMENT_LIP_W + PRINT_TOLERANCE;
    gix = BOX_INNER_LENGTH/2 - PRINT_TOLERANCE;
    giy = BOX_INNER_WIDTH/2 - PRINT_TOLERANCE;

    translate([BOX_CENTER_X, 0, 0])
        difference() {
            linear_extrude(height = gh)
                rounded_rect_2d(gox * 2, goy * 2,
                                max(CORNER_RADIUS - SIDE_WALL_THICKNESS
                                    + ALIGNMENT_LIP_W, 0.5));
            translate([0, 0, -0.1])
                linear_extrude(height = gh + 0.2)
                    rounded_rect_2d(gix * 2, giy * 2,
                                    max(CORNER_RADIUS - SIDE_WALL_THICKNESS,
                                        0.5));
        }
}
