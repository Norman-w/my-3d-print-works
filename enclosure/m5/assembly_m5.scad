// SmartPaddle M5 — 尾板开孔包络预览（无电池匣）
include <../parameters.scad>
include <../bezier_profile.scad>
include <parameters_m5.scad>
include <tail_board_cuts_m5.scad>

// ===== 分区：公开 API =====
color([0.2, 0.7, 0.35, 0.75])
    m5_tail_board_interference_cuts();
