// SmartPaddle M5 — 拍柄尾段：环槽卡满截面尾板（无电池匣）
include <../parameters.scad>
include <../bezier_profile.scad>
include <parameters_m5.scad>
include <tail_board_cuts_m5.scad>

// ===== 分区：常量/配置 =====
PART = "tail_coupon";
$fn = 32;
eps = 0.08;
BIG = 500;
actual_butt_y = BEZIER_Y0;
TAIL_LEN = m5_tail_active_length_y;
LOFT_STEPS = 22;

m5_echo_feasibility();

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
    y_c = actual_butt_y + m5_tail_board_y_from_butt;
    half_y = m5_tail_board_t / 2 + m5_tail_board_ring_groove_axial_clear;
    cavity_inset = m5_wall_t + m5_cavity_inset;
    groove_inset = cavity_inset - m5_tail_board_ring_groove_radial;
    assert(groove_inset > 0.5, "ring groove eats through outer wall");
    _loft(y_c - half_y, y_c + half_y, 6, groove_inset);
}

module m5_feature_cuts() {
    m5_tail_board_interference_cuts();
    if (m5_tail_board_full_section)
        m5_tail_board_ring_groove_cut();
    translate([0, actual_butt_y - 2.5, 0])
        cube([2 * m5_outer_hx_butt + 4, 4, 2 * m5_outer_hz_butt + 4], center = true);
}

module m5_handle_united() {
    difference() {
        m5_shell_hollow();
        m5_feature_cuts();
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

// ===== 分区：公开 API =====
if (PART == "tail_coupon") m5_handle_united();
else if (PART == "handle_front") m5_handle_half(true);
else if (PART == "handle_back") m5_handle_half(false);
else if (PART == "board_cuts_only") m5_tail_board_interference_cuts();

echo(str("M5 PART=", PART, " buttY=", actual_butt_y));
