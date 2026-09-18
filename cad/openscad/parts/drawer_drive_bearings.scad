// 抽屉底部齿排导向轴承与前端主动轮轴承参考
//
// Mechanical contract
// process: purchased bearing reference; printed seats are fit prototypes
// material: 681 / 1×3×1 and MR63 / 3×6×2 are metal purchase parts
// load_path: drawer mass stays on the cabinet side slides; 681 bearings only
//            remove side/anti-yaw hard contact. The center front 3×6×2
//            bearing is captive in the shelf-integrated stepped seat.
// lubrication: dry PTFE or silicone film on printed rail faces only; never
//              oil the 03C/2GT belts or pack grease into printed dust traps
// units: mm

//#region 常量/配置
DRAWER_GUIDE_681_ID = 1.00;
DRAWER_GUIDE_681_OD = 3.00;
DRAWER_GUIDE_681_W = 1.00;
DRAWER_GUIDE_681_SEAT_D = 3.15;
DRAWER_GUIDE_681_SHAFT_D = 1.15;

DRAWER_PINION_MR63_ID = 3.00;
DRAWER_PINION_MR63_OD = 6.00;
DRAWER_PINION_MR63_W = 2.00;
DRAWER_PINION_MR63_SEAT_D = 6.10;

// The center first article separates the upper drawer pinion from the lower
// timing pulley. The purchased MR63 itself is 3×6×2; the shelf-integrated
// seat is deeper than the bearing only because its lower shoulder retains the
// bearing from the next bay. The remaining 0.40 mm is printed shelf material.
DRAWER_FRONT_TIMING_BEARING_ID = 3.00;
DRAWER_FRONT_TIMING_BEARING_OD = 6.00;
DRAWER_FRONT_TIMING_BEARING_W = 2.00;
DRAWER_FRONT_TIMING_BEARING_SEAT_D = 6.10;
DRAWER_FRONT_TIMING_BEARING_RETAINER_T = is_undef(SHELF_T)
    ? 0.40
    : SHELF_T - DRAWER_FRONT_TIMING_BEARING_W;
DRAWER_FRONT_TIMING_BEARING_RETAINER_BORE_D = 3.40;

DRAWER_DRIVE_BEARING_EPS = is_undef(EPS) ? 0.05 : EPS;
//#endregion

//#region 私有成员
module drawer_drive_bearing_y(id, od, width, x, y, z) {
    // Axis is world +Y, matching the drawer-front pinion and the side-guide
    // rollers. The reference is deliberately a simple annulus; seals and
    // balls are procurement details, not fabricated geometry.
    translate([x, y, z])
        rotate([-90, 0, 0])
            difference() {
                cylinder(d = od, h = width, center = true, $fn = 48);
                cylinder(
                    d = id,
                    h = width + 2 * DRAWER_DRIVE_BEARING_EPS,
                    center = true,
                    $fn = 40
                );
            }
}

module drawer_drive_bearing_x(id, od, width, x, y, z) {
    // Axis is world +X. The bearing is used as a horizontal roller inside
    // the inward-facing C rail; its outer ring reacts to drawer load in Y.
    translate([x, y, z])
        rotate([0, 90, 0])
            difference() {
                cylinder(d = od, h = width, center = true, $fn = 48);
                cylinder(
                    d = id,
                    h = width + 2 * DRAWER_DRIVE_BEARING_EPS,
                    center = true,
                    $fn = 40
                );
            }
}
//#endregion

//#region 公开 API
module drawer_drive_681_bearing_y(x, y, z) {
    drawer_drive_bearing_y(
        DRAWER_GUIDE_681_ID,
        DRAWER_GUIDE_681_OD,
        DRAWER_GUIDE_681_W,
        x,
        y,
        z
    );
}

module drawer_drive_681_bearing_x(x, y, z) {
    drawer_drive_bearing_x(
        DRAWER_GUIDE_681_ID,
        DRAWER_GUIDE_681_OD,
        DRAWER_GUIDE_681_W,
        x,
        y,
        z
    );
}

module drawer_drive_mr63_bearing_y(x, y, z) {
    drawer_drive_bearing_y(
        DRAWER_PINION_MR63_ID,
        DRAWER_PINION_MR63_OD,
        DRAWER_PINION_MR63_W,
        x,
        y,
        z
    );
}

module drawer_drive_front_timing_bearing_y(x, y, z) {
    drawer_drive_bearing_y(
        DRAWER_FRONT_TIMING_BEARING_ID,
        DRAWER_FRONT_TIMING_BEARING_OD,
        DRAWER_FRONT_TIMING_BEARING_W,
        x,
        y,
        z
    );
}

module drawer_drive_bearing_carrier_y(
    x,
    y,
    z,
    od,
    width,
    seat_d
) {
    // A compact printed cheek around an axial bearing. It is not a drawer
    // slide and must not be counted as the drawer's vertical load path.
    difference() {
        translate([x, y, z])
            cube([od, width + 1.0, od], center = true);
        translate([x, y, z])
            rotate([-90, 0, 0])
                cylinder(
                    d = seat_d,
                    h = width + 1.0 + 2 * DRAWER_DRIVE_BEARING_EPS,
                    center = true,
                    $fn = 48
                );
    }
}
//#endregion
