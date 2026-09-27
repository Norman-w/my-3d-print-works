// 运动/空间研究模型；没有实体凸轮、传动支架、接口或紧固件。
// 不得把该模型导出的实体当作可制造整机或已经工作的机构。
include <parameters.scad>

stroke_fraction = 0;
section_view = true;
show_reference_balls = true;
ball_d = ball_max_d;
study_part = "assembly";

eps = 0.02;
guide_end_z = guide_start_z + guide_length;
closing_end = (1 - gate_overlap_fraction) / 2;
opening_start = 1 - closing_end;

function clamp(v, lo, hi) = min(hi, max(lo, v));
function gate_r(rear, t) = rear
    ? finger_open_center_r - (finger_open_center_r - finger_closed_center_r)
        * clamp(t / closing_end, 0, 1)
    : finger_closed_center_r + (finger_open_center_r - finger_closed_center_r)
        * clamp((t - opening_start) / closing_end, 0, 1);
function parked_offset(d) = sqrt(pow(d/2 + finger_tip_radius, 2)
    - pow(finger_closed_center_r, 2));

assert(guide_id > ball_max_d, "球径包络超过导向孔");
assert(guide_od > guide_id && body_id > guide_od, "导向与壳腔尺寸不成立");
assert(stroke_fraction >= 0 && stroke_fraction <= 1);

module keep_section() {
    if (section_view)
        intersection() {
            children();
            translate([-100, 0, -150]) cube([200, 100, 300]);
        }
    else children();
}

module radial_hole(z) {
    translate([-60, 0, z]) rotate([0, 90, 0])
        cylinder(h=120, r=finger_tip_radius + radial_print_clearance);
}

module guide() {
    difference() {
        translate([0, 0, guide_start_z]) cylinder(h=guide_length, d=guide_od);
        translate([0, 0, guide_start_z-eps]) cylinder(h=guide_length+2*eps, d=guide_id);
        radial_hole(0);
        radial_hole(-gate_spacing);
    }
}

module outer_envelope() {
    // 只有壳体包络，端部故意开放：不暗示已有通风入口、封闭侧腔或固定结构。
    difference() {
        translate([0, 0, guide_start_z])
            cylinder(h=guide_length, d=body_id+2*body_wall);
        translate([0, 0, guide_start_z-eps])
            cylinder(h=guide_length+2*eps, d=body_id);
        radial_hole(0);
        radial_hole(-gate_spacing);
    }
}

module finger_pair(z, rear) {
    r = gate_r(rear, stroke_fraction);
    for (side=[-1,1])
        translate([side*r, 0, z]) {
            sphere(r=finger_tip_radius);
            rotate([0, side*90, 0]) cylinder(h=21, r=finger_tip_radius);
        }
}

module reference_balls() {
    // 仅为前挡关闭时的理想同轴静止球位；不是运动解或风力模拟。
    z0 = -parked_offset(ball_d);
    for (z=[z0, z0-ball_d]) translate([0, 0, z]) sphere(d=ball_d);
}

module assembly() {
    color([0.62,0.66,0.70]) keep_section() outer_envelope();
    color([0.12,0.56,0.76]) keep_section() guide();
    color([0.95,0.42,0.12]) keep_section() finger_pair(0, false);
    color([0.20,0.72,0.43]) keep_section() finger_pair(-gate_spacing, true);
    if (show_reference_balls)
        color([0.96,0.91,0.63]) keep_section() reference_balls();
}

if (study_part == "assembly") assembly();
else if (study_part == "guide") guide();
else assert(false, "未知研究模型部件");
