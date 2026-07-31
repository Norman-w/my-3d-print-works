// SmartPaddle M5 — 横向滑块 / 锁舌 / 弹簧包络
include <parameters_m5.scad>

// ===== 分区：常量/配置 =====
eps = 0.02;
$fn = 40;

// ===== 分区：公开 API =====

// 滑块 + 一体锁舌（本地位姿：锁定时锁舌伸入匣凹槽）
// travel_x：0 = 锁定，正值 = 向外拨开（远离匣，X+ 侧为拨出方向）
module m5_latch_slider(travel_x = 0) {
    tx = min(max(travel_x, 0), m5_latch_travel_x);
    // 外露拨片（凹陷于壳侧，与圆按键造型区分）
    color([0.85, 0.55, 0.15])
    translate([tx, 0, 0]) {
        // 拨片本体
        hull() {
            translate([1.2, 0, 0])
                cube([2.2, m5_latch_body_y, m5_latch_body_z], center = true);
            translate([2.6, 0, 0])
                cube([1.2, m5_latch_body_y - 2, m5_latch_body_z - 1.5], center = true);
        }
        // 防滑细纹
        for (i = [-2:2])
            translate([3.0, i * 1.6, 0])
                cube([0.5, 0.6, m5_latch_body_z - 2], center = true);
        // 锁舌（伸向 −X，朝向电池匣）
        translate([
            -m5_latch_engagement_x / 2 - 0.2,
            0,
            0
        ])
            hull() {
                cube([m5_latch_engagement_x + 0.6, m5_latch_tongue_y, m5_latch_tongue_z], center = true);
                // 斜导面
                translate([-0.4, -m5_latch_tongue_y / 2 + 0.4, 0])
                    cube([0.4, 0.8, m5_latch_tongue_z - 0.4], center = true);
            }
        // 复位弹簧座孔
        translate([0.5, m5_latch_body_y / 2 - 1, 0])
            rotate([0, 90, 0])
                cylinder(d = m5_return_spring_od + 0.4, h = 1.2, center = true);
    }
}

// 复位弹簧包络
module m5_return_spring_envelope(compressed = true) {
    L = compressed ? m5_return_spring_free * 0.55 : m5_return_spring_free;
    color([0.7, 0.7, 0.75, 0.7])
        rotate([0, 90, 0])
            cylinder(d = m5_return_spring_od, h = L, center = false);
}

// 顶出弹簧包络（仓内 +Y 端）
module m5_eject_spring_envelope(state = "locked") {
    // locked / ejected / free
    L =
        state == "free" ? m5_eject_spring_free :
        state == "ejected" ? m5_eject_spring_free * 0.72 :
        m5_eject_spring_free * 0.45;
    color([0.65, 0.65, 0.7, 0.75])
        rotate([-90, 0, 0])
            cylinder(d = m5_eject_spring_od, h = L, center = false);
}

// 世界坐标放置：滑块在电池匣 X+ 外侧
module m5_latch_placed(travel_x = 0) {
    pocket_y = m5_datum_a_y + m5_cartridge_total_y * 0.42;
    latch_x = m5_cartridge_cx() + m5_sx() * (
        m5_cartridge_outer_x / 2 + m5_latch_engagement_x / 2 + 0.3
    );
    translate([latch_x, pocket_y, 0])
        mirror([m5_mirror_x ? 1 : 0, 0, 0])
            m5_latch_slider(travel_x);
}

module m5_eject_spring_placed(state = "locked") {
    translate([
        m5_cartridge_cx(),
        m5_datum_a_y + m5_housing_bay_depth_y() - 1.5,
        0
    ])
        mirror([0, 1, 0])
            m5_eject_spring_envelope(state);
}
