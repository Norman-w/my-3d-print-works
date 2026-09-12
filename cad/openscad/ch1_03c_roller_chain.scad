// Mechanical contract
// process: purchased carbon-steel roller chain (CAD envelope, not FDM)
// material: 03C carbon steel (Taobao SKU 单排03C-1X210L长1米)
// parting_plane: n/a
// opening_direction: n/a
// fastener: riveted pins (visualization only)
// seal: n/a
// print_orientation: n/a — do not 3D-print this SKU
// units: mm
// source: docs/parts/CH1-03C-roller-chain.md

//#region 导入/依赖
include <ch1_03c_params.scad>
//#endregion

//#region 常量/配置
$fa = 8;
$fs = 0.22;

PART = "assembly";   // assembly | plates | rollers | pins
MODE = "loop";       // loop | straight
LINKS = 20;          // 预览节数；完整 SKU 为 210，勿直接整圈 CGAL
assert(LINKS % 2 == 0, "LINKS must be even so inner/outer plates close");
//#endregion

//#region 模型/类型
function unit(v) = norm(v) < 1e-9 ? [0, 0, 1] : v / norm(v);

function loop_radius() = (P / 2) / sin(180 / LINKS);

function pin_count() = MODE == "loop" ? LINKS : LINKS + 1;

function pin_axis_vec() = MODE == "loop" ? [0, 0, 1] : [0, 1, 0];

function pin_pos(i) =
    MODE == "loop"
        ? [
              loop_radius() * cos(i * 360 / LINKS),
              loop_radius() * sin(i * 360 / LINKS),
              0
          ]
        : [i * P, 0, 0];
//#endregion

//#region 私有成员
module place_from_to(p0, p1, axis_y) {
    x = unit(p1 - p0);
    z = unit(cross(x, unit(axis_y)));
    y = unit(cross(z, x));
    multmatrix([
        [x[0], y[0], z[0], p0[0]],
        [x[1], y[1], z[1], p0[1]],
        [x[2], y[2], z[2], p0[2]],
        [0, 0, 0, 1]
    ]) children();
}

module plate_profile(hole_d) {
    difference() {
        offset(r = -fillet)
            offset(r = fillet)
                union() {
                    circle(d = h2);
                    translate([P, 0]) circle(d = h2);
                    translate([0, -waist / 2]) square([P, waist]);
                }
        circle(d = hole_d);
        translate([P, 0]) circle(d = hole_d);
    }
}

module chain_plate(hole_d) {
    rotate([90, 0, 0])
        linear_extrude(height = T, convexity = 8)
            plate_profile(hole_d);
}

module inner_plates() {
    translate([0, inner_width / 2 + T, 0])
        chain_plate(journal_od + clearance);
    translate([0, -inner_width / 2, 0])
        chain_plate(journal_od + clearance);
}

module outer_plates() {
    translate([0, inner_width / 2 + 2 * T, 0])
        chain_plate(d2 + clearance);
    translate([0, -(inner_width / 2 + T), 0])
        chain_plate(d2 + clearance);
}

module hardware_along_y(od, id, length) {
    translate([0, -length / 2, 0])
        rotate([-90, 0, 0])
            difference() {
                cylinder(d = od, h = length);
                if (id > 0)
                    translate([0, 0, -eps])
                        cylinder(d = id, h = length + 2 * eps);
            }
}

module pin_solid() {
    translate([0, -outer_face, 0])
        rotate([-90, 0, 0]) {
            cylinder(d = d2, h = plate_stack);
            translate([0, 0, -rivet_h])
                cylinder(d = rivet_d, h = rivet_h);
            translate([0, 0, plate_stack])
                cylinder(d = rivet_d, h = rivet_h);
        }
}

module place_at_pin(i) {
    axis = pin_axis_vec();
    if (MODE != "loop" && i == LINKS)
        place_from_to(pin_pos(i - 1), pin_pos(i), axis)
            translate([P, 0, 0]) children();
    else
        place_from_to(pin_pos(i), pin_pos((i + 1) % pin_count()), axis)
            children();
}

module bushing_solid() {
    hardware_along_y(journal_od, d2 + clearance, inner_width + 2 * T);
}

module roller_solid() {
    bushing_solid();
    hardware_along_y(d1, journal_od + clearance, visible_bush_len);
}

module plates_all() {
    axis = pin_axis_vec();
    for (i = [0:LINKS - 1]) {
        p0 = pin_pos(i);
        p1 = pin_pos((i + 1) % pin_count());
        place_from_to(p0, p1, axis) {
            if (i % 2 == 0) outer_plates();
            else inner_plates();
        }
    }
}

module rollers_all() {
    for (i = [0:pin_count() - 1]) place_at_pin(i) roller_solid();
}

module pins_all() {
    for (i = [0:pin_count() - 1])
        place_at_pin(i) pin_solid();
}

module emit(name) {
    if (PART == "assembly" || PART == name) children();
}

module plates_on_path(pins) {
    n = len(pins);
    assert(n >= 4 && n % 2 == 0, "pin path must have even count");
    axis = [0, 0, 1];
    for (i = [0:n - 1])
        place_from_to(pins[i], pins[(i + 1) % n], axis) {
            if (i % 2 == 0) outer_plates();
            else inner_plates();
        }
}

module rollers_on_path(pins) {
    n = len(pins);
    axis = [0, 0, 1];
    for (i = [0:n - 1])
        place_from_to(pins[i], pins[(i + 1) % n], axis)
            roller_solid();
}

module pins_on_path(pins) {
    n = len(pins);
    axis = [0, 0, 1];
    for (i = [0:n - 1])
        place_from_to(pins[i], pins[(i + 1) % n], axis)
            pin_solid();
}

module chain_on_path(pins) {
    plates_on_path(pins);
    rollers_on_path(pins);
    pins_on_path(pins);
}
//#endregion

//#region 公开 API
module ch1_03c_chain() {
    emit("plates") {
        if (PART == "assembly") color("#8A919C") plates_all();
        else plates_all();
    }
    emit("rollers") {
        if (PART == "assembly") color("#E8EDF2") rollers_all();
        else rollers_all();
    }
    emit("pins") {
        if (PART == "assembly") color("#B08D57") pins_all();
        else pins_all();
    }
}

ch1_03c_chain();
//#endregion

//#region 业务逻辑
// 内外链节交替；闭环时 LINKS 必须为偶数。销轴沿局部 Y，节距沿局部 X。
//#endregion

//#region 方法/工具
// 导出用 -D PART='"plates"' 等覆盖 PART；完整 210 节请在装配体里用路径实例化，不要一次性 CGAL。
//#endregion
