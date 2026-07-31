// SmartPaddle M5 — 电池匣（匣体 + 尾盖 + 电芯/保护板/触点包络）
include <parameters_m5.scad>

// ===== 分区：常量/配置 =====
eps = 0.02;
$fn = 48;

// ===== 分区：私有成员 =====
module _m5_rounded_box(sx, sy, sz, r = 0.6) {
    rr = min(r, sx/2 - eps, sy/2 - eps, sz/2 - eps);
    minkowski() {
        cube([sx - 2*rr, sy - 2*rr, sz - 2*rr], center = true);
        sphere(r = rr, $fn = 24);
    }
}

module _m5_rail_profile(clear = 0) {
    // 梯形导轨截面（XZ）：宽底、窄顶，防脱
    w0 = m5_rail_w + 2 * clear;
    w1 = m5_rail_w * 0.65 + 2 * clear;
    h  = m5_rail_h + clear;
    polygon([
        [-w0/2, 0], [w0/2, 0], [w1/2, h], [-w1/2, h]
    ]);
}

// ===== 分区：公开 API =====

// 电芯最大实体（含热缩间隙）；轴向 = 局部 +Y（插入方向）
module m5_cell_envelope() {
    d = m5_battery_cell_d + 2 * m5_cell_shrink_clear;
    color([0.15, 0.15, 0.18])
        rotate([-90, 0, 0])
            cylinder(d = d, h = m5_battery_cell_l, center = true);
    // 正极帽示意（朝保护板 / +Y）
    color([0.85, 0.75, 0.25])
        translate([0, m5_battery_cell_l / 2, 0])
            rotate([-90, 0, 0])
                cylinder(d = d * 0.55, h = 0.8, center = false);
}

// 保护板包络（匣内 +Y 端）
module m5_protection_pcb_envelope() {
    color([0.12, 0.45, 0.22])
        cube([m5_prot_pcb_x, m5_prot_pcb_y, m5_prot_pcb_z], center = true);
    // MOS/焊点最高点示意
    color([0.2, 0.2, 0.25])
        translate([0, 0, m5_prot_pcb_z / 2 - 0.6])
            cube([m5_prot_pcb_x * 0.7, m5_prot_pcb_y * 0.8, 1.2], center = true);
}

// 凹陷触点窗（P+ / P−），防止平面金属同时短路两极
module m5_contact_windows() {
    for (sz = [-1, 1])
        translate([0, 0, sz * m5_contact_pitch_z / 2])
            rotate([90, 0, 0])
                cylinder(d = m5_contact_pad_d, h = m5_contact_pad_y + eps, center = false);
}

// 导轨（匣外侧，沿 Y）
module m5_cartridge_rails(clear = 0) {
    rail_len = m5_cartridge_total_y - m5_cartridge_cap_t - 4;
    for (side = [-1, 1]) {
        translate([
            side * (m5_cartridge_outer_x / 2 + clear / 2),
            m5_cartridge_cap_t + 2 + rail_len / 2,
            0
        ])
            cube([
                m5_rail_h + clear,
                rail_len,
                m5_rail_w + 2 * clear
            ], center = true);
    }
    // 非对称键：仅 +Z 侧，阻止 180° 反插
    translate([
        m5_cartridge_outer_x / 2 + clear / 2,
        m5_cartridge_cap_t + 2 + rail_len * 0.35,
        m5_key_offset_z
    ])
        cube([
            m5_rail_h + clear,
            rail_len * 0.7,
            m5_rail_w * 0.8 + 2 * clear
        ], center = true);
}

// 锁舌凹槽（匣 X+ 外侧，锁定时锁舌落入）
module m5_latch_pocket_cut() {
    pocket_y = m5_cartridge_total_y * 0.42;
    translate([
        m5_cartridge_outer_x / 2 - m5_latch_engagement_x / 2 + eps,
        pocket_y,
        0
    ])
        cube([
            m5_latch_engagement_x + 0.4,
            m5_latch_tongue_y + 0.6,
            m5_latch_tongue_z + 0.6
        ], center = true);
    // 斜导角：插入末段推开锁舌
    translate([
        m5_cartridge_outer_x / 2 - 0.2,
        pocket_y - m5_latch_tongue_y / 2 - 1.5,
        0
    ])
        rotate([0, 0, -25])
            cube([2.5, 3.5, m5_latch_tongue_z + 0.6], center = true);
}

// 匣体外壳（空腔减去电芯仓，含尾盖一体预览时可拆）
module m5_cartridge_body_solid() {
    difference() {
        // 外轮廓
        translate([0, m5_cartridge_total_y / 2, 0])
            _m5_rounded_box(
                m5_cartridge_outer_x,
                m5_cartridge_total_y,
                m5_cartridge_outer_z,
                0.8
            );
        // 电芯仓（轴向 +Y）
        cell_cavity_y = m5_battery_cell_l + 1.0;
        translate([
            0,
            m5_cartridge_cap_t + cell_cavity_y / 2,
            0
        ])
            rotate([-90, 0, 0])
                cylinder(
                    d = m5_battery_cell_d + 2 * m5_cell_shrink_clear + 0.4,
                    h = cell_cavity_y + eps,
                    center = true
                );
        // 保护板仓
        translate([
            0,
            m5_cartridge_total_y - m5_prot_pcb_y / 2 - 0.4,
            0
        ])
            cube([
                m5_prot_pcb_x + 0.4,
                m5_prot_pcb_y + 0.4,
                m5_prot_pcb_z + 0.4
            ], center = true);
        // 内端触点窗（朝 +Y 开口，凹陷）
        translate([0, m5_cartridge_total_y + eps, 0])
            m5_contact_windows();
        // 锁舌凹槽 + 斜导角
        m5_latch_pocket_cut();
        // 排液微孔（尾盖内侧，不穿向触点）
        for (sx = [-1, 1])
            translate([sx * 4, m5_cartridge_cap_t + 1.5, -m5_cartridge_outer_z / 2 + 0.2])
                cylinder(d = m5_drain_min_d, h = 2.5, center = false);
    }
    m5_cartridge_rails(0);
}

// 齐平尾盖（可拆分打印件）
module m5_cartridge_cap_solid() {
    difference() {
        translate([0, m5_cartridge_cap_t / 2, 0])
            _m5_rounded_box(
                m5_cartridge_outer_x - 0.1,
                m5_cartridge_cap_t,
                m5_cartridge_outer_z - 0.1,
                0.5
            );
        // 浅抓取纹
        for (i = [-2:2])
            translate([0, 0.4, i * 2.2])
                rotate([0, 90, 0])
                    cylinder(d = 0.7, h = m5_cartridge_outer_x * 0.7, center = true);
    }
}

// 完整电池匣装配（本地位姿：尾盖在 Y=0，插入方向 +Y）
module m5_battery_cartridge(show_internals = true) {
    color([0.25, 0.55, 0.85])
        m5_cartridge_body_solid();
    color([0.18, 0.42, 0.72])
        m5_cartridge_cap_solid();
    if (show_internals) {
        // 电芯中心
        translate([
            0,
            m5_cartridge_cap_t + m5_battery_cell_l / 2 + 0.3,
            0
        ])
            m5_cell_envelope();
        // 保护板
        translate([
            0,
            m5_cartridge_total_y - m5_prot_pcb_y / 2 - 0.5,
            0
        ])
            m5_protection_pcb_envelope();
        // 触点镀金示意（凹陷面）
        color([0.9, 0.75, 0.2])
            for (sz = [-1, 1])
                translate([
                    0,
                    m5_cartridge_total_y - m5_contact_pad_y / 2,
                    sz * m5_contact_pitch_z / 2
                ])
                    cube([m5_contact_pad_d * 0.7, m5_contact_pad_y, m5_contact_pad_d * 0.7], center = true);
    }
}

// 世界坐标：相对 DATUM，cartridge_dy = 0 锁定，负值向 −Y 拔出
module m5_battery_cartridge_placed(cartridge_dy = 0, show_internals = true) {
    translate([
        m5_cartridge_cx(),
        m5_cartridge_locked_y0() + cartridge_dy,
        0
    ])
        mirror([m5_mirror_x ? 1 : 0, 0, 0])
            m5_battery_cartridge(show_internals);
}
