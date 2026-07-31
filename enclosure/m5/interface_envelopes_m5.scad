// SmartPaddle M5 — 尾板 / USB / 按键 / LED / 线束 / 手指禁布包络（半透明占位）
include <parameters_m5.scad>

// ===== 分区：常量/配置 =====
eps = 0.02;
$fn = 40;

// ===== 分区：公开 API =====

// 尾板：板厚沿 X，板面在 YZ
module m5_tail_board_envelope() {
    color([0.15, 0.55, 0.25, 0.85])
        cube([m5_tail_board_t, m5_tail_board_x, m5_tail_board_z], center = true);
}

module m5_wire_harness_envelope() {
    color([0.2, 0.8, 0.4, 0.35])
        hull() {
            sphere(r = 2.0);
            translate([0, 30, 0]) sphere(r = 2.0);
        }
}

module m5_finger_grip_envelope() {
    color([1, 0.6, 0.3, 0.18])
        translate([0, -6, 0])
            cube([14, 10, 14], center = true);
}

module m5_fixed_contacts_envelope() {
    color([0.85, 0.7, 0.2, 0.8])
        for (sz = [-1, 1])
            translate([0, 0, sz * m5_contact_pitch_z / 2])
                rotate([90, 0, 0])
                    cylinder(d = 3.2, h = 5, center = true);
}

// 世界坐标：整组接口包络
module m5_interface_envelopes_placed(show_usb_plug = false) {
    board_y = m5_datum_a_y + 6;
    translate([m5_board_cx(), board_y, 0])
        m5_tail_board_envelope();

    // UI：尾端面外侧（−Y）
    translate([m5_board_cx(), m5_datum_a_y - 0.5, 0]) {
        color([0.3, 0.3, 0.35, 0.85])
            translate([0, -4, 0])
                cube([m5_usb_socket_x, 8, m5_usb_socket_z], center = true);
        if (show_usb_plug)
            color([0.55, 0.55, 0.6, 0.4])
                translate([0, -12, 0])
                    cube([m5_usb_opening_x + 1, 12, m5_usb_opening_z + 1], center = true);
        color([0.9, 0.9, 0.95, 0.85])
            translate([m5_sx() * -3.2, -2, 0])
                rotate([90, 0, 0])
                    cylinder(d = m5_button_cap_d, h = 3, center = false);
        color([1, 0.25, 0.25, 0.85])
            translate([0, -2, 5])
                rotate([90, 0, 0])
                    cylinder(d = m5_led_charge_d, h = 2.5, center = false);
        color([0.2, 0.75, 1, 0.85])
            translate([0, -2, -5])
                rotate([90, 0, 0])
                    cylinder(d = m5_led_rgb_d, h = 2.5, center = false);
    }

    translate([m5_board_cx(), board_y + 10, 0])
        m5_wire_harness_envelope();

    translate([
        m5_cartridge_cx(),
        m5_datum_a_y + m5_housing_bay_depth_y() - 3,
        0
    ])
        m5_fixed_contacts_envelope();

    translate([m5_cartridge_cx(), m5_datum_a_y - 1, 0])
        m5_finger_grip_envelope();
}
