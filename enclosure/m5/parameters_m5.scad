// SmartPaddle M5 — 可换电池拍柄专有参数
// 状态标注：MODEL_TARGET / DATASHEET / MEASURED_SAMPLE / VERIFIED_PRINT
// 禁止把商家典型值直接标成 VERIFIED。不得覆盖 M4 parameters.scad。

// ===== 分区：常量/配置 =====

// —— 基准与方向 ——
// M5_DATUM_A：拍柄尾端齐平面，法向 −Y（取自贝塞尔实际平底）
// M5_DATUM_B：对称面 X=0
// M5_DATUM_C：分型面 Z=0
m5_mirror_x = false;              // false = 尾板 X−、电池 X+、滑块 X+ 外侧

// 尾段重构长度（从 DATUM_A 向 +Y）
m5_tail_active_length_y = 70.0;   // MODEL_TARGET

// —— 局部外形加宽/加厚（相对 M4 尾端包络）——
// M4 尾端约 32.9×24.4 外廓 / ~25.9×17.4 内腔，放不下 16+分隔+10 并排与 21 高尾板。
m5_outer_hx_butt      = 20.0;     // MODEL_TARGET：外半宽 → 外宽 40mm
m5_outer_hz_butt      = 15.0;     // MODEL_TARGET：外半厚 → 外厚 30mm
m5_outer_flare_y      = 18.0;     // 从尾面往 +Y 的加宽过渡长度
m5_shell_min_t        = 1.80;     // 普通壳最薄门禁
m5_wall_t             = 2.00;     // MODEL_TARGET：与 M4 wall_t 对齐起点
m5_cavity_inset       = 0.80;     // MODEL_TARGET：尾段略减内缩以让位

// —— 14500 电芯（Vapcell K10 厂商规格，待实测）——
m5_battery_cell_d     = 14.10;    // DATASHEET / TBD 同批最大值
m5_battery_cell_l     = 50.10;    // DATASHEET / TBD
m5_cell_shrink_clear  = 0.35;     // 热缩膜/偏心保护间隙（每侧）

// —— 电池匣 ——
m5_cartridge_outer_x  = 16.00;    // MODEL_TARGET
m5_cartridge_outer_z  = 16.00;    // MODEL_TARGET
m5_cartridge_total_y  = 57.00;    // MODEL_TARGET，期望 55–58
m5_cartridge_wall_t   = 1.20;     // MODEL_TARGET
m5_cartridge_cap_t    = 2.50;     // MODEL_TARGET：齐平尾盖厚度
m5_cartridge_clearance_xy = 0.25; // 每侧，打印样条后修正
m5_rail_clearance     = 0.25;     // 每侧
m5_rail_w             = 2.00;     // 导轨凸台宽
m5_rail_h             = 1.40;     // 导轨凸台高
m5_rail_root_min_t    = 1.50;
m5_key_offset_z       = 2.50;     // 非对称防反插键相对中心偏移

// —— 保护板 / 触点（匣内 +Y 端）——
m5_prot_pcb_y         = 2.40;     // MODEL_TARGET：保护板包络厚度
m5_prot_pcb_x         = 13.50;    // MODEL_TARGET
m5_prot_pcb_z         = 13.50;    // MODEL_TARGET
m5_contact_pad_y      = 0.80;     // 沉金触点窗深度（凹陷）
m5_contact_pad_d      = 4.50;     // 触点窗直径
m5_contact_pitch_z    = 7.00;     // P+ / P− 中心距
m5_contact_working_travel_y = 1.00; // TBD
m5_contact_overtravel_y     = 0.30; // TBD
m5_hard_stop_margin_y = 0.80;     // 塑料硬止挡余量

// —— 固定尾板 ——
// 阶段策略：满截面尾板（pcb-tail）占满拍柄 XZ；合模时板边嵌入内壁环槽。
m5_tail_board_full_section = true; // true=环槽满截面；false=窄侧矩形槽（旧示意）
m5_tail_board_x       = 10.00;    // 窄板示意用；满截面时由 loft 决定
m5_tail_board_z       = 21.00;    // 窄板示意用
m5_tail_board_t       = 1.00;     // 与 pcb-tail 板厚一致
m5_tail_board_slot_clear = 0.30;  // 窄板槽侧间隙
// 环槽：径向嵌入深度与 pcb-tail BOARD_CLEARANCE_MM=-0.50 对齐
m5_tail_board_ring_groove_radial = 0.50;
m5_tail_board_ring_groove_axial_clear = 0.15; // 板厚向每侧
m5_tail_board_y_from_butt = 5.80; // = Type-C 超短体 H，与 generate_outline 一致
m5_divider_min_t      = 1.20;     // 不含局部加强筋

// —— 锁止 / 顶出 ——
m5_latch_travel_x     = 1.80;     // MODEL_TARGET 1.5–2.0；尾端面横向拨动
m5_latch_engagement_x = 1.00;     // MODEL_TARGET 0.8–1.2
// 锁扣外露位置：拍尾端面（Y−），禁止放在左右握持边（掌根易误触）
m5_latch_on_butt_face = true;
m5_latch_body_y       = 10.00;    // 滑块本体沿 Y 长度
m5_latch_body_z       = 6.00;     // 滑块本体沿 Z 高度
m5_latch_tongue_y     = 5.00;     // 锁舌沿 Y
m5_latch_tongue_z     = 3.00;     // 锁舌沿 Z
m5_eject_travel_y     = 4.00;     // MODEL_TARGET 3–5
m5_eject_spring_od    = 5.00;     // MODEL_TARGET 顶出弹簧外径
m5_eject_spring_free  = 12.00;    // MODEL_TARGET 自由长
m5_return_spring_od   = 3.50;     // 复位弹簧外径
m5_return_spring_free = 8.00;

// —— 用户界面（固定在尾板侧，相对尾板中心）——
m5_usb_opening_x      = 2.90;     // 公头开口窄边（板厚向）
m5_usb_opening_z      = 8.50;     // 公头开口宽边
m5_usb_socket_x       = 4.00;
m5_usb_socket_z       = 10.00;
m5_button_cap_d       = 3.00;
m5_led_charge_d       = 2.00;
m5_led_rgb_d          = 2.00;
m5_wire_min_bend_r    = 3.00;
m5_drain_min_d        = 1.20;
m5_tpu_pad_preload    = 0.20;

// —— 派生：基准与中心线 ——
// 实际平底由 include 的 profiles 提供；无 profiles 时回退参数值。
m5_datum_a_y = is_undef(BEZIER_Y0) ? -178.0962 : BEZIER_Y0;

function m5_sx() = m5_mirror_x ? -1 : 1;

// 内腔可用半宽/半厚（尾端加宽后）
function m5_inner_hx() = m5_outer_hx_butt - m5_wall_t - m5_cavity_inset;
function m5_inner_hz() = m5_outer_hz_butt - m5_wall_t - m5_cavity_inset;

// X 向布局：分隔墙中心、尾板中心、电池匣中心（未镜像）
function m5_required_x() =
    m5_tail_board_x + m5_divider_min_t + m5_cartridge_outer_x;

function m5_layout_half_span() = m5_required_x() / 2;

function m5_divider_cx_raw() =
    -m5_layout_half_span() + m5_tail_board_x + m5_divider_min_t / 2;

function m5_board_cx_raw() =
    m5_divider_cx_raw() - m5_divider_min_t / 2 - m5_tail_board_x / 2;

function m5_cartridge_cx_raw() =
    m5_divider_cx_raw() + m5_divider_min_t / 2 + m5_cartridge_outer_x / 2;

function m5_divider_cx()   = m5_sx() * m5_divider_cx_raw();
function m5_board_cx()     = m5_sx() * m5_board_cx_raw();
function m5_cartridge_cx() = m5_sx() * m5_cartridge_cx_raw();

// 电池匣锁定时：尾盖外表面齐 DATUM_A
function m5_cartridge_locked_y0() = m5_datum_a_y;
function m5_cartridge_locked_y1() = m5_datum_a_y + m5_cartridge_total_y;

function m5_housing_bay_depth_y() =
    m5_cartridge_total_y + m5_eject_travel_y + m5_hard_stop_margin_y;

// 可行性余量（尾端面）
function m5_x_margin() = 2 * m5_inner_hx() - m5_required_x();
function m5_z_margin_battery() =
    2 * m5_inner_hz() - m5_cartridge_outer_z - 2 * m5_cartridge_clearance_xy;
function m5_z_margin_board() =
    2 * m5_inner_hz() - m5_tail_board_z - 2 * m5_tail_board_slot_clear;

// ===== 分区：公开 API（回显门禁）=====
module m5_echo_feasibility() {
    echo("=== M5 feasibility (DATUM_A butt) ===");
    echo(str("DATUM_A Y=", m5_datum_a_y));
    echo(str("outer ", 2*m5_outer_hx_butt, "×", 2*m5_outer_hz_butt));
    echo(str("inner ", 2*m5_inner_hx(), "×", 2*m5_inner_hz()));
    echo(str("required_x=", m5_required_x(), "  x_margin=", m5_x_margin()));
    echo(str("z_margin_battery=", m5_z_margin_battery()));
    echo(str("z_margin_board=", m5_z_margin_board()));
    echo(str("board_cx=", m5_board_cx(), "  cartridge_cx=", m5_cartridge_cx()));
    assert(m5_x_margin() >= 0, "M5 x_margin < 0 — widen outer or shrink packs");
    assert(m5_z_margin_battery() >= 0, "M5 z_margin_battery < 0");
    assert(m5_z_margin_board() >= 0, "M5 z_margin_board < 0 — thicken outer");
}
