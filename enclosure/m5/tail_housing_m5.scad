// SmartPaddle M5 — 尾段固定壳：电池仓 / 尾板槽 / 导轨 / 滑块通道 / 排液
include <parameters_m5.scad>
use <battery_cartridge_m5.scad>
use <latch_m5.scad>

// ===== 分区：常量/配置 =====
eps = 0.02;
$fn = 48;

// ===== 分区：私有成员 =====
module _m5_outer_profile(hx, hz, r = 3.5) {
    rr = min(r, hx - eps, hz - eps);
    hull()
        for (sx = [-1, 1], sz = [-1, 1])
            translate([sx * (hx - rr), sz * (hz - rr)])
                circle(r = rr);
}

function _m5_flare_t(y) =
    let(dy = y - m5_datum_a_y)
    dy <= 0 ? 1 :
    dy >= m5_outer_flare_y ? 0 :
    1 - (dy / m5_outer_flare_y);

// 相对 M4 的局部加宽插值（仅用目标外包络，不依赖贝塞尔切片）
function _m5_hx_at(y) =
    let(t = _m5_flare_t(y),
        hx_far = 13.5)  // 过渡末端约接近 M4 腰部
    hx_far + (m5_outer_hx_butt - hx_far) * t;

function _m5_hz_at(y) =
    let(t = _m5_flare_t(y),
        hz_far = 11.2)
    hz_far + (m5_outer_hz_butt - hz_far) * t;

module _m5_loft_solid(y0, y1, steps = 28, inset = 0) {
    dh = (y1 - y0) / steps;
    for (i = [0:steps - 1]) {
        y_a = y0 + i * dh;
        y_b = y0 + (i + 1) * dh;
        hx_a = _m5_hx_at(y_a) - inset;
        hz_a = _m5_hz_at(y_a) - inset;
        hx_b = _m5_hx_at(y_b) - inset;
        hz_b = _m5_hz_at(y_b) - inset;
        if (hx_a > 0.5 && hz_a > 0.5 && hx_b > 0.5 && hz_b > 0.5)
            hull() {
                translate([0, y_a, 0])
                    rotate([90, 0, 0])
                        linear_extrude(height = eps)
                            _m5_outer_profile(hx_a, hz_a);
                translate([0, y_b, 0])
                    rotate([90, 0, 0])
                        linear_extrude(height = eps)
                            _m5_outer_profile(hx_b, hz_b);
            }
    }
}

// ===== 分区：公开 API =====

module m5_tail_outer_solid() {
    y0 = m5_datum_a_y - 0.5;
    y1 = m5_datum_a_y + m5_tail_active_length_y;
    _m5_loft_solid(y0, y1, 32, 0);
}

module m5_battery_bay_cut() {
    // 电池仓全行程空腔（含间隙）
    cx = m5_cartridge_cx();
    w = m5_cartridge_outer_x + 2 * m5_cartridge_clearance_xy;
    h = m5_cartridge_outer_z + 2 * m5_cartridge_clearance_xy;
    depth = m5_housing_bay_depth_y() + 1;
    translate([cx, m5_datum_a_y + depth / 2 - 0.5, 0])
        cube([w, depth + 1, h], center = true);
    // 入口略倒角
    translate([cx, m5_datum_a_y - 0.2, 0])
        cube([w + 0.6, 2, h + 0.6], center = true);
}

module m5_board_slot_cut() {
    if (m5_tail_board_full_section) {
        // 满截面环槽：板面在 XZ，厚沿 Y；局部加大内腔形成卡槽
        y_c = m5_datum_a_y + m5_tail_board_y_from_butt;
        half_y = m5_tail_board_t / 2 + m5_tail_board_ring_groove_axial_clear;
        cavity_inset = m5_wall_t + m5_cavity_inset;
        groove_inset = cavity_inset - m5_tail_board_ring_groove_radial;
        _m5_loft_solid(y_c - half_y, y_c + half_y, 8, groove_inset);
    } else {
        cx = m5_board_cx();
        // 窄板槽：板厚沿 X，板面在 YZ
        slot_x = m5_tail_board_t + 2 * m5_tail_board_slot_clear;
        slot_y = 14;
        slot_z = m5_tail_board_z + 2 * m5_tail_board_slot_clear;
        translate([cx, m5_datum_a_y + 6, 0])
            cube([slot_x, slot_y, slot_z], center = true);
        translate([cx + m5_sx() * (-2.5), m5_datum_a_y + 7, 0])
            cube([4, 12, slot_z - 2], center = true);
    }
}

module m5_divider_wall() {
    translate([
        m5_divider_cx(),
        m5_datum_a_y + m5_housing_bay_depth_y() / 2,
        0
    ])
        cube([
            m5_divider_min_t,
            m5_housing_bay_depth_y() - 1,
            2 * m5_inner_hz() - 1
        ], center = true);
}

module m5_rail_grooves_cut() {
    // 壳体导轨槽（与匣轨配对）
    rail_len = m5_cartridge_total_y + m5_eject_travel_y - 2;
    cx = m5_cartridge_cx();
    for (side = [-1, 1]) {
        translate([
            cx + side * (m5_cartridge_outer_x / 2 + m5_rail_clearance),
            m5_datum_a_y + 3 + rail_len / 2,
            0
        ])
            rotate([90, 0, 90])
                linear_extrude(height = rail_len, center = true)
                    offset(delta = m5_rail_clearance)
                        square([m5_rail_w + 0.2, m5_rail_h + 0.2], center = true);
    }
    // 防反插键槽
    translate([
        cx + m5_sx() * (m5_cartridge_outer_x / 2 + m5_rail_clearance),
        m5_datum_a_y + 3 + rail_len * 0.35,
        m5_sx() * m5_key_offset_z
    ])
        cube([m5_rail_h + 0.5, rail_len * 0.7, m5_rail_w], center = true);
}

module m5_latch_channel_cut() {
    pocket_y = m5_datum_a_y + m5_cartridge_total_y * 0.42;
    latch_x = m5_cartridge_cx() + m5_sx() * (
        m5_cartridge_outer_x / 2 + m5_latch_travel_x + 2.5
    );
    // 滑块通道
    translate([latch_x, pocket_y, 0])
        cube([
            m5_latch_travel_x + 6,
            m5_latch_body_y + 1.5,
            m5_latch_body_z + 1.5
        ], center = true);
    // 外露拨片凹槽（防误触）
    translate([
        m5_sx() * (m5_outer_hx_butt - 1.2),
        pocket_y,
        0
    ])
        cube([3.5, m5_latch_body_y + 2, m5_latch_body_z + 2], center = true);
}

module m5_drain_cuts() {
    // 仓底排液 → 外界，不穿电子仓
    cx = m5_cartridge_cx();
    for (sy = [8, 20, 35])
        translate([cx, m5_datum_a_y + sy, -m5_inner_hz() + 0.5])
            rotate([90, 0, 0])
                cylinder(d = m5_drain_min_d, h = 4, center = false);
}

module m5_contact_seat() {
    // 内端触点座 + 硬止挡
    translate([
        m5_cartridge_cx(),
        m5_datum_a_y + m5_housing_bay_depth_y() - 1.2,
        0
    ]) {
        cube([m5_cartridge_outer_x - 1, 2.4, m5_cartridge_outer_z - 1], center = true);
        // 硬止挡肩
        translate([0, -1.5, 0])
            cube([m5_cartridge_outer_x - 2, 1.2, m5_cartridge_outer_z - 2], center = true);
    }
}

module m5_usb_opening_cut() {
    translate([m5_board_cx(), m5_datum_a_y - 0.5, 0])
        rotate([90, 0, 0])
            linear_extrude(height = 4)
                offset(r = 0.4)
                    square([m5_usb_opening_x, m5_usb_opening_z], center = true);
}

module m5_button_opening_cut() {
    translate([
        m5_board_cx() + m5_sx() * (-3.5),
        m5_datum_a_y - 0.5,
        0
    ])
        rotate([90, 0, 0])
            cylinder(d = m5_button_cap_d + 0.4, h = 4, center = false);
}

module m5_led_opening_cuts() {
    for (sz = [5, -5])
        translate([m5_board_cx(), m5_datum_a_y - 0.5, sz])
            rotate([90, 0, 0])
                cylinder(d = m5_led_charge_d + 0.3, h = 4, center = false);
}

// 尾段壳体（外壳 − 仓/槽 + 分隔墙/触点座）
module m5_tail_housing(alpha = 1) {
    color([0.75, 0.78, 0.82, alpha])
    union() {
        difference() {
            m5_tail_outer_solid();
            // 内腔
            _m5_loft_solid(
                m5_datum_a_y + 0.2,
                m5_datum_a_y + m5_tail_active_length_y - 1,
                28,
                m5_wall_t + m5_cavity_inset
            );
            m5_battery_bay_cut();
            m5_board_slot_cut();
            m5_rail_grooves_cut();
            m5_latch_channel_cut();
            m5_drain_cuts();
            m5_usb_opening_cut();
            m5_button_opening_cut();
            m5_led_opening_cuts();
            // 尾端开放面（电池入口）
            translate([0, m5_datum_a_y - 2, 0])
                cube([2 * m5_outer_hx_butt + 4, 4, 2 * m5_outer_hz_butt + 4], center = true);
        }
        m5_divider_wall();
        m5_contact_seat();
    }
}

// 前后半壳预览（分型面切开）
module m5_tail_housing_half(front = true, alpha = 0.55) {
    intersection() {
        m5_tail_housing(alpha);
        translate([0, 0, front ? 500 : -500])
            cube([2000, 2000, 1000], center = true);
    }
}
