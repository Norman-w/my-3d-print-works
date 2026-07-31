// SmartPaddle M5 — 真实拍柄尾段合壳挖仓（可导出预览网格）
include <../parameters.scad>
include <../bezier_profile.scad>
include <parameters_m5.scad>
use <battery_cartridge_m5.scad>
use <latch_m5.scad>

// ===== 分区：常量/配置 =====
PART = "tail_coupon";
ASSEMBLY_STATE = "cartridge_locked";
$fn = 32;
eps = 0.08;
BIG = 500;
actual_butt_y = BEZIER_Y0;
TAIL_LEN = m5_tail_active_length_y;
LOFT_STEPS = 22;

m5_echo_feasibility();

function _dy(s) =
    s == "removed" ? -48 :
    s == "ejected" || s == "latch_pressed" ? -m5_eject_travel_y : 0;
function _lx(s) =
    s == "latch_pressed" || s == "ejected" || s == "removed" ? m5_latch_travel_x : 0;

function _flare_t(y) =
    let(d = y - actual_butt_y)
    d <= 0 ? 1 : d >= m5_outer_flare_y ? 0 : 1 - d / m5_outer_flare_y;

function _hx(y) =
    let(t = _flare_t(y), b = bezier_envelope_hx(y))
    b + (m5_outer_hx_butt - b) * t;

function _hz(y) =
    let(t = _flare_t(y), b = bezier_half_z_at(y))
    b + (m5_outer_hz_butt - b) * t;

// ===== 分区：私有成员 =====
module _xz(hx, hz, r = 3.0) {
    rr = min(r, hx - 0.25, hz - 0.25);
    hull()
        for (sx = [-1, 1], sz = [-1, 1])
            translate([sx * (hx - rr), sz * (hz - rr)])
                circle(r = rr);
}

module _loft(y0, y1, steps, inset = 0) {
    dh = (y1 - y0) / steps;
    for (i = [0:steps - 1]) {
        ya = y0 + i * dh;
        yb = y0 + (i + 1) * dh;
        hxa = _hx(ya) - inset;
        hza = _hz(ya) - inset;
        hxb = _hx(yb) - inset;
        hzb = _hz(yb) - inset;
        if (hxa > 0.8 && hza > 0.8 && hxb > 0.8 && hzb > 0.8)
            hull() {
                translate([0, ya, 0])
                    rotate([90, 0, 0])
                        linear_extrude(height = eps)
                            _xz(hxa, hza);
                translate([0, yb, 0])
                    rotate([90, 0, 0])
                        linear_extrude(height = eps)
                            _xz(hxb, hzb);
            }
    }
}

module m5_shell_hollow() {
    difference() {
        _loft(actual_butt_y - 0.2, actual_butt_y + TAIL_LEN, LOFT_STEPS, 0);
        _loft(
            actual_butt_y + 1.2,
            actual_butt_y + TAIL_LEN - 1.2,
            LOFT_STEPS - 2,
            m5_wall_t + m5_cavity_inset
        );
    }
}

module m5_tail_board_ring_groove_cut() {
    // 满截面尾板环槽：在板平面把内腔局部加大 radial，合模后板边卡进凹槽
    y_c = actual_butt_y + m5_tail_board_y_from_butt;
    half_y = m5_tail_board_t / 2 + m5_tail_board_ring_groove_axial_clear;
    cavity_inset = m5_wall_t + m5_cavity_inset;
    groove_inset = cavity_inset - m5_tail_board_ring_groove_radial;
    assert(groove_inset > 0.5, "ring groove eats through outer wall");
    _loft(y_c - half_y, y_c + half_y, 6, groove_inset);
}

module m5_feature_cuts() {
    // 电池仓
    translate([
        m5_cartridge_cx(),
        actual_butt_y + m5_housing_bay_depth_y() / 2,
        0
    ])
        cube([
            m5_cartridge_outer_x + 2 * m5_cartridge_clearance_xy,
            m5_housing_bay_depth_y() + 2,
            m5_cartridge_outer_z + 2 * m5_cartridge_clearance_xy
        ], center = true);

    // 尾板：满截面环槽，或旧窄矩形槽
    if (m5_tail_board_full_section)
        m5_tail_board_ring_groove_cut();
    else
        translate([m5_board_cx(), actual_butt_y + 7, 0])
            cube([
                m5_tail_board_t + 2 * m5_tail_board_slot_clear,
                15,
                m5_tail_board_z + 2 * m5_tail_board_slot_clear
            ], center = true);

    // 滑扣通道（勿切穿整壳）
    pocket_y = actual_butt_y + m5_cartridge_total_y * 0.42;
    translate([
        m5_cartridge_cx() + m5_sx() * (m5_cartridge_outer_x / 2 + 3.2),
        pocket_y,
        0
    ])
        cube([6.5, m5_latch_body_y + 1.2, m5_latch_body_z + 1.2], center = true);

    // 尾端面 UI 开口
    translate([m5_board_cx(), actual_butt_y - 0.5, 0])
        rotate([90, 0, 0])
            linear_extrude(4)
                offset(r = 0.3)
                    square([m5_usb_opening_x, m5_usb_opening_z], center = true);

    translate([m5_board_cx() + m5_sx() * (-3.2), actual_butt_y - 0.5, 0])
        rotate([90, 0, 0])
            cylinder(d = m5_button_cap_d + 0.3, h = 4);

    // 拍尾清口（只切端面外延，不吞掉整段）
    translate([0, actual_butt_y - 2.5, 0])
        cube([2 * m5_outer_hx_butt + 4, 4, 2 * m5_outer_hz_butt + 4], center = true);
}

module m5_internals_add() {
    translate([m5_divider_cx(), actual_butt_y + m5_housing_bay_depth_y() / 2, 0])
        cube([m5_divider_min_t, m5_housing_bay_depth_y() - 3, m5_tail_board_z - 2], center = true);

    translate([m5_cartridge_cx(), actual_butt_y + m5_housing_bay_depth_y() - 1.6, 0])
        cube([m5_cartridge_outer_x - 2, 2.6, m5_cartridge_outer_z - 2], center = true);
}

module m5_handle_united() {
    union() {
        difference() {
            m5_shell_hollow();
            m5_feature_cuts();
        }
        m5_internals_add();
    }
}

module m5_z_half(front = true) {
    if (front)
        translate([0, 0, BIG / 2 - eps]) cube([BIG, BIG, BIG], center = true);
    else
        translate([0, 0, -BIG / 2 + eps]) cube([BIG, BIG, BIG], center = true);
}

module m5_handle_half(front = true) {
    intersection() {
        m5_handle_united();
        m5_z_half(front);
    }
}

module m5_assembly_preview(state = ASSEMBLY_STATE) {
    color([0.75, 0.79, 0.84, 0.45]) m5_handle_united();
    if (state != "removed")
        m5_battery_cartridge_placed(_dy(state), true);
    m5_latch_placed(_lx(state));
    color([0.15, 0.55, 0.28])
        translate([m5_board_cx(), actual_butt_y + 7, 0])
            cube([m5_tail_board_t, m5_tail_board_x, m5_tail_board_z], center = true);
}

// ===== 分区：公开 API =====
if (PART == "assembly_preview") m5_assembly_preview(ASSEMBLY_STATE);
else if (PART == "tail_coupon") m5_handle_united();
else if (PART == "handle_front") m5_handle_half(true);
else if (PART == "handle_back") m5_handle_half(false);
else if (PART == "cartridge_world") m5_battery_cartridge_placed(0, true);
else if (PART == "latch_world") m5_latch_placed(0);

echo(str("M5 PART=", PART, " buttY=", actual_butt_y));
