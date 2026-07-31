// SmartPaddle M5 — 满截面自研尾板参数（无电池匣）
// 充电/USB/按键/LED 均在 pcb-tail；外壳只做环槽卡板 + Step6 干涉开孔。

// ===== 分区：常量/配置 =====

m5_mirror_x = false;

m5_tail_active_length_y = 70.0;

m5_outer_hx_butt      = 20.0;
m5_outer_hz_butt      = 15.0;
m5_outer_flare_y      = 18.0;
m5_shell_min_t        = 1.80;
m5_wall_t             = 2.00;
m5_cavity_inset       = 0.80;

// —— 满截面尾板环槽 ——
m5_tail_board_full_section = true;
m5_tail_board_t       = 1.00;
m5_tail_board_ring_groove_radial = 0.50;
m5_tail_board_ring_groove_axial_clear = 0.15;
m5_tail_board_y_from_butt = 5.80; // = Type-C H，与 generate_outline 一致

// UI 开孔间隙（Step6 / tail_board_cuts 使用；具体 XY 来自 KiCad）
m5_button_hole_over   = 0.50;
m5_led_hole_over      = 0.40;
m5_usb_clear          = 0.35;

// —— 派生 ——
m5_datum_a_y = is_undef(BEZIER_Y0) ? -178.0962 : BEZIER_Y0;

function m5_sx() = m5_mirror_x ? -1 : 1;
function m5_inner_hx() = m5_outer_hx_butt - m5_wall_t - m5_cavity_inset;
function m5_inner_hz() = m5_outer_hz_butt - m5_wall_t - m5_cavity_inset;

// ===== 分区：公开 API =====
module m5_echo_feasibility() {
    echo("=== M5 (full-section tail board, no battery cartridge) ===");
    echo(str("DATUM_A Y=", m5_datum_a_y));
    echo(str("outer ", 2*m5_outer_hx_butt, "×", 2*m5_outer_hz_butt));
    echo(str("inner ", 2*m5_inner_hx(), "×", 2*m5_inner_hz()));
    echo(str("board Y_from_butt=", m5_tail_board_y_from_butt, " t=", m5_tail_board_t));
}
