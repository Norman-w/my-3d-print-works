// 中心纯永磁离合选择指磁力靴
//
// The shoe is a printed, non-magnetic carrier for two nominal Ø2 mm magnets.
// M_engage and M_release are deliberately separated along the selector tangent
// by GT2_ACTUATOR_TRIGGER_SPACING_MM (12 mm). The two pockets have a square
// and triangular raised assembly mark respectively. Low N/S labels are also
// embossed beside the pockets so the selected magnet polarity is traceable
// during first-article assembly.

//#region 导入/依赖
include <ch1_03c_gt2_clutch_pair_params.scad>
//#endregion

//#region 常量/配置
CENTER_SELECTOR_SHOE_W = 17.50;
CENTER_SELECTOR_SHOE_D = 5.60;
// The trigger face stays at the frozen 0.40 mm gap below the male rotor, but
// the shoe must pass above the input rotary-bearing blocks.  A 2.00 mm body
// leaves 0.20 mm clearance over their top datum while retaining the frozen
// 1.80 mm blind magnet pocket and its 0.20 mm printed floor.
CENTER_SELECTOR_SHOE_H = 2.00;
CENTER_SELECTOR_SHOE_POCKET_RIM_D = 2.80;
CENTER_SELECTOR_SHOE_POCKET_RIM_H = 0.35;
CENTER_SELECTOR_SHOE_MARK_H = 0.30;
CENTER_SELECTOR_SHOE_POLARITY_MARK_SIZE = 1.10;
CENTER_SELECTOR_SHOE_POLARITY_MARK_H = 0.22;
//#endregion

//#region 公开 API
module center_clutch_selector_shoe() {
    pocket_z0 = CENTER_SELECTOR_SHOE_H / 2
        - GT2_MAGNET_POCKET_H;
    difference() {
        union() {
            translate([
                -CENTER_SELECTOR_SHOE_W / 2,
                -CENTER_SELECTOR_SHOE_D / 2,
                -CENTER_SELECTOR_SHOE_H / 2
            ])
                cube([
                    CENTER_SELECTOR_SHOE_W,
                    CENTER_SELECTOR_SHOE_D,
                    CENTER_SELECTOR_SHOE_H
                ]);
            for (x = [
                -GT2_ACTUATOR_TRIGGER_SPACING_MM / 2,
                GT2_ACTUATOR_TRIGGER_SPACING_MM / 2
            ])
                translate([x, 0, CENTER_SELECTOR_SHOE_H / 2])
                    difference() {
                        cylinder(
                            d = CENTER_SELECTOR_SHOE_POCKET_RIM_D,
                            h = CENTER_SELECTOR_SHOE_POCKET_RIM_H,
                            $fn = 48
                        );
                        translate([0, 0, -GT2_EPS])
                            cylinder(
                                d = GT2_MAGNET_POCKET_D,
                                h = CENTER_SELECTOR_SHOE_POCKET_RIM_H
                                    + 2 * GT2_EPS,
                                $fn = 48
                            );
                    }
        }
        for (x = [
            -GT2_ACTUATOR_TRIGGER_SPACING_MM / 2,
            GT2_ACTUATOR_TRIGGER_SPACING_MM / 2
        ])
            translate([x, 0, pocket_z0])
                cylinder(
                    d = GT2_MAGNET_POCKET_D,
                    h = GT2_MAGNET_POCKET_H + 2 * GT2_EPS,
                    $fn = 48
                );
    }

    // M_engage is the square-marked/N-marked pocket; M_release is the
    // triangular/S-marked pocket. The actual magnet faces are installed to
    // match the center rotor's mating polarity during first-article setup.
    translate([
        -GT2_ACTUATOR_TRIGGER_SPACING_MM / 2 - 0.60,
        -1.65,
        CENTER_SELECTOR_SHOE_H / 2
    ])
        cube([1.20, 1.20, CENTER_SELECTOR_SHOE_MARK_H]);
    translate([
        GT2_ACTUATOR_TRIGGER_SPACING_MM / 2,
        -1.65,
        CENTER_SELECTOR_SHOE_H / 2
    ])
        cylinder(
            r = 0.72,
            h = CENTER_SELECTOR_SHOE_MARK_H,
            $fn = 3
        );

    for (entry = [
        [-GT2_ACTUATOR_TRIGGER_SPACING_MM / 2, "N"],
        [GT2_ACTUATOR_TRIGGER_SPACING_MM / 2, "S"]
    ])
        translate([
            entry[0],
            1.35,
            CENTER_SELECTOR_SHOE_H / 2
        ])
            linear_extrude(height = CENTER_SELECTOR_SHOE_POLARITY_MARK_H)
                text(
                    entry[1],
                    size = CENTER_SELECTOR_SHOE_POLARITY_MARK_SIZE,
                    halign = "center",
                    valign = "center"
                );
}
//#endregion

//#region 业务校验
assert(abs(GT2_ACTUATOR_TRIGGER_SPACING_MM - 12.0) < 0.001,
    "selector magnetic shoe spacing is frozen at 12 mm");
assert(GT2_MAGNET_POCKET_D >= GT2_MAGNET_NOMINAL_D,
    "selector shoe pocket must fit the nominal magnet");
assert(GT2_MAGNET_POCKET_H < CENTER_SELECTOR_SHOE_H,
    "selector shoe pocket must remain blind");
//#endregion
