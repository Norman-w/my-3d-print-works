// ============================================================
// 理疗仪线缆串联保护盒 — 主入口（v3 功率调速板）
// therapy-cable-inline-box-for-physio
//
// 用法：
//   预览装配：   VISUAL=true  , RENDER="assembly"
//   导出下半：   VISUAL=false , RENDER="bottom"   → openscad -o stl/bottom-half.stl
//   导出上半：   VISUAL=false , RENDER="top"      → openscad -o stl/top-half.stl
// ============================================================
include <parameters.scad>
include <utilities.scad>
include <module-holder.scad>
include <cable-gland.scad>
include <cable-strain-relief.scad>
include <ventilation.scad>
include <bottom-half.scad>
include <top-half.scad>

// ===== 分区：常量/配置 =====
RENDER = "assembly";  // "bottom" | "top" | "assembly" | "flat"
ASSEMBLY_GAP = 18;

// ===== 分区：公开 API =====
if (RENDER == "bottom") {
    bottom_half();
} else if (RENDER == "top") {
    top_half();
} else if (RENDER == "flat") {
    translate([0, -BOX_OUTER_WIDTH / 2 - 5, 0])
        bottom_half();
    translate([0,  BOX_OUTER_WIDTH / 2 + 5, 0])
        rotate([180, 0, 0])
            top_half();

    // 四个 PCB 螺丝承压垫圈排在两半壳之间，不增加平放包围盒。
    for (wx = [-12, -4, 4, 12])
        translate([wx, 0, 0])
            module_screw_washer();
} else {
    assembly_view();
}

module assembly_view() {
    if (VISUAL) {
        color("ivory")
        translate([0, 0, -ASSEMBLY_GAP / 2])
            bottom_half();

        color("lightblue", 0.45)
        translate([0, 0, +ASSEMBLY_GAP / 2])
            top_half();

        module_placeholder();

        color("dimgray")
        for (sy = [-1, 1]) {
            translate([CABLE_ENTRY_X,
                       sy * (BOX_OUTER_WIDTH / 2
                             + GLAND_OUTER_EXTEND + 10), 0])
            rotate([90, 0, 0])
                cylinder(d = CABLE_DIAMETER, h = 25,
                         center = true, $fn = 32);
        }
    } else {
        bottom_half();
    }
}
