// SmartPaddle M5 — 尾板干涉包络预览（无电池匣）
include <parameters_m5.scad>
include <tail_board_cuts_m5.scad>

// ===== 分区：常量/配置 =====
$fn = 40;

// ===== 分区：公开 API =====
module m5_interface_envelopes_placed() {
    color([0.15, 0.65, 0.35, 0.55])
        m5_tail_board_interference_cuts();
}
