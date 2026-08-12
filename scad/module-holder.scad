// ============================================================
// v3 功率调速板 — 端壁开孔与可视化占位
// 坐标：PCB 长边 X，线缆 Y，元件面 +Z，旋钮在 X-。
// ============================================================
include <parameters.scad>

// ===== 分区：端壁避让 =====

// 上下壳各切一半，合盖后组成完整的旋钮螺纹套筒孔。
module module_knob_end_cuts() {
    wall_center_x = BOX_INNER_MIN_X - SIDE_WALL_THICKNESS/2;
    cut_len = SIDE_WALL_THICKNESS + 2.0;

    translate([wall_center_x, KNOB_AXIS_Y, KNOB_AXIS_Z])
        rotate([0, 90, 0])
            cylinder(d = KNOB_WINDOW_DIAM, h = cut_len,
                     center = true, $fn = 48);
}

// ===== 分区：装配占位 =====

module module_placeholder() {
    _pcb_placeholder();
    _potentiometer_placeholder();
    _heatsink_placeholder();
    _terminal_placeholder();
    _capacitor_placeholders();
}

// M2 沉头不得直接压在 PCB 的约 3mm 平孔上；此垫圈把载荷摊平。
// 90°锥座让按总长标注的 M2×5 沉头嵌入，保留足够螺纹咬合。
module module_screw_washer() {
    difference() {
        cylinder(d = MODULE_WASHER_OD, h = MODULE_WASHER_H, $fn = 48);
        translate([0, 0, -0.1])
            cylinder(d = MODULE_WASHER_ID,
                     h = MODULE_WASHER_H + 0.2, $fn = 32);
        translate([0, 0, MODULE_WASHER_H - MODULE_WASHER_CS_DEPTH])
            cylinder(d1 = MODULE_WASHER_ID,
                     d2 = MODULE_WASHER_CS_DIAM,
                     h = MODULE_WASHER_CS_DEPTH + 0.1, $fn = 48);
    }
}

module _pcb_placeholder() {
    color("seagreen")
    difference() {
        translate([MODULE_CENTER_X, MODULE_CENTER_Y,
                   PCB_BOTTOM_Z + MODULE_PCB_THICK/2])
            cube([MODULE_LENGTH, MODULE_WIDTH, MODULE_PCB_THICK],
                 center = true);

        for (p = MODULE_HOLES)
            translate([p[0], p[1], PCB_BOTTOM_Z - 0.1])
                cylinder(d = MODULE_HOLE_DIAM,
                         h = MODULE_PCB_THICK + 0.2, $fn = 24);
    }
}

module _potentiometer_placeholder() {
    board_knob_edge_x = MODULE_CENTER_X - MODULE_LENGTH/2;
    body_center_x = MODULE_CENTER_X + POT_BODY_CENTER_X_REL;

    color("mediumseagreen")
        translate([body_center_x, KNOB_AXIS_Y,
                   PCB_TOP_Z + POT_BODY_SIZE_Z/2])
            cube([POT_BODY_SIZE_X, POT_BODY_SIZE_Y, POT_BODY_SIZE_Z],
                 center = true);

    // 固定螺纹套筒：从 PCB 边向 X- 伸出。
    color("silver")
        translate([board_knob_edge_x - KNOB_THREAD_LENGTH,
                   KNOB_AXIS_Y, KNOB_AXIS_Z])
            rotate([0, 90, 0])
                cylinder(d = KNOB_THREAD_DIAM, h = KNOB_THREAD_LENGTH,
                         $fn = 36);

    color("gray")
        translate([board_knob_edge_x - KNOB_THREAD_LENGTH - KNOB_SHAFT_LENGTH,
                   KNOB_AXIS_Y, KNOB_AXIS_Z])
            rotate([0, 90, 0])
                cylinder(d = KNOB_SHAFT_DIAM, h = KNOB_SHAFT_LENGTH,
                         $fn = 32);

    color("gainsboro")
        translate([board_knob_edge_x - KNOB_THREAD_LENGTH
                   - KNOB_SHAFT_LENGTH - KNOB_CAP_LENGTH,
                   KNOB_AXIS_Y, KNOB_AXIS_Z])
            rotate([0, 90, 0])
                cylinder(d = KNOB_CAP_DIAM, h = KNOB_CAP_LENGTH, $fn = 48);

    // 该下巴沿 X- 仅突出 1mm，停留在内腔中，不需要切穿端壁。
    color("silver")
        translate([board_knob_edge_x - POT_CHIN_PROTRUSION_X,
                   KNOB_AXIS_Y - POT_CHIN_WIDTH_Y/2, PCB_TOP_Z])
            cube([POT_CHIN_PROTRUSION_X,
                  POT_CHIN_WIDTH_Y, POT_CHIN_HEIGHT_Z]);
}

module _heatsink_placeholder() {
    base_z = PCB_TOP_Z;
    fin_h = HEATSINK_HEIGHT - HEATSINK_BASE_HEIGHT;
    fin_pitch = HEATSINK_SIZE_Y / HEATSINK_FIN_COUNT;

    color("silver") {
        translate([HEATSINK_CENTER_X, HEATSINK_CENTER_Y,
                   base_z + HEATSINK_BASE_HEIGHT/2])
            cube([HEATSINK_SIZE_X, HEATSINK_SIZE_Y,
                  HEATSINK_BASE_HEIGHT], center = true);

        for (i = [0 : HEATSINK_FIN_COUNT - 1]) {
            fy = HEATSINK_CENTER_Y - HEATSINK_SIZE_Y/2
                 + fin_pitch/2 + i * fin_pitch;
            translate([HEATSINK_CENTER_X, fy,
                       base_z + HEATSINK_BASE_HEIGHT + fin_h/2])
                cube([HEATSINK_SIZE_X, HEATSINK_FIN_THICK, fin_h],
                     center = true);
        }
    }
}

module _terminal_placeholder() {
    color("royalblue")
        translate([MODULE_CENTER_X + TERMINAL_CENTER_X_REL,
                   MODULE_CENTER_Y,
                   PCB_TOP_Z + TERMINAL_HEIGHT/2])
            cube([TERMINAL_SIZE_X, TERMINAL_SIZE_Y, TERMINAL_HEIGHT],
                 center = true);
}

module _capacitor_placeholders() {
    color("black")
    for (cy = CAP_Y_POSITIONS)
        translate([MODULE_CENTER_X + CAP_CENTER_X_REL,
                   MODULE_CENTER_Y + cy, PCB_TOP_Z])
            cylinder(d = CAP_DIAMETER, h = CAP_HEIGHT, $fn = 32);
}
