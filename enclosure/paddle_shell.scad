// SmartPaddle — 分体式球拍壳体
// 正/反面半壳，贴热床面朝下打印，PETG 材质
//
// 用法:
//   HALF = "front"  → 前壳（红色胶皮面，螺丝过孔）
//   HALF = "back"   → 后壳（黑色胶皮面, USB-C, 引导孔）
//   HALF = "both"   → 组装预览

include <parameters.scad>

// ═══ 配置 ═══
USE_BEZIER_PROFILES = true; // false = 传统椭圆 + FL 手柄
// 外部皮肤: OpenSCAD CSG 并集（水密）。实时 STL 合拢仅为预览。
USE_IMPORTED_OUTER = false;
// "front"/"back" = 半壳组装件; "blade_front"|"blade_back"|"handle_front"|"handle_back" = 四零件
HALF = "front";
LOFT_SLICES = USE_BEZIER_PROFILES ? 64 : 150;

// 由 scripts/bezier_to_openscad.py 生成（USE_BEZIER_PROFILES=true 时必须）
include <generated/bezier_geometry.scad>
include <bezier_profile.scad>

$fn = 80;
eps = 0.02;
// 布尔裁剪辅助立方体；尺寸需超过拍体最大延展（Y 约 257 mm）。
BIG = 1000;

// ═══ 工具函数 ═══

function smoothstep(t) = t * t * (3 - 2 * t);

function fl_half_w(t) =
    let(waist_t = 0.32, n = handle_neck_w/2, b = handle_butt_w/2)
    t <= waist_t
        ? n * (1 - 0.06 * sin(t / waist_t * 90))
        : n * 0.94 + (b - n * 0.94) * smoothstep((t - waist_t) / (1 - waist_t));

function blade_hx(y) =
    let(t = (y - blade_ellipse_cy) / blade_ellipse_b)
    abs(t) >= 1 ? 0 : blade_ellipse_a * sqrt(1 - t*t);

function legacy_paddle_hx(y) =
    y >= shoulder_top_y ? blade_hx(y) :
    y >= shoulder_bottom_y ?
        blade_hx(shoulder_top_y) + (handle_neck_w/2 - blade_hx(shoulder_top_y)) *
            smoothstep((y - shoulder_top_y) / (shoulder_bottom_y - shoulder_top_y)) :
    y >= handle_butt_y ? fl_half_w((y - handle_join_y) / (-handle_length)) : 0;

function legacy_half_z_at(y) =
    y >= shoulder_top_y ? blade_half_t :
    y >= shoulder_bottom_y ?
        blade_half_t + (handle_half_t - blade_half_t) *
            smoothstep((y - shoulder_top_y) / (shoulder_bottom_y - shoulder_top_y)) :
    handle_half_t;

function paddle_hx(y) = legacy_paddle_hx(y);

function half_z_at(y) =
    USE_BEZIER_PROFILES ? bezier_half_z_at(y) : legacy_half_z_at(y);

function envelope_hx(y) =
    USE_BEZIER_PROFILES ? bezier_envelope_hx(y) : paddle_hx(y);

function sign(x) = x >= 0 ? 1 : -1;

function screw_position_ok(p) =
    let(x = p[0], y = p[1], hz = half_z_at(y), hx = envelope_hx(y))
    hz > wall_t + 0.3
    && abs(x) < hx - 4
    && y > handle_butt_y + 12
    && y < blade_tip_y - 10;

function screw_in_blade(p) = screw_position_ok(p) && p[1] >= shoulder_bottom_y - 2;

function screw_in_handle(p) = screw_position_ok(p) && p[1] <= shoulder_bottom_y - 10;

// 压电槽必须完全在拍面胶皮区域内（不能越界到肩部/手柄）。
function piezo_in_blade_ok(p) =
    let(x = p[0], y = p[1], hx = envelope_hx(y), r = piezo_disc_d / 2 + 3)
    y >= shoulder_bottom_y - 2
    && y <= blade_tip_y - 12
    && abs(x) + r < hx;
    
// 保持线槽入口在手柄空腔喉部内侧。
function wire_entry_x() =
    max(3, min(tang_half_w - 1,
        handle_neck_w / 2 - wall_t - handle_cavity_inset - 1));

function pin_position_ok(p) =
    let(x = p[0], y = p[1], hz = half_z_at(y), hx = envelope_hx(y))
    hz > wall_t + pin_h + 1.5 && abs(x) < hx - 3;

module z_half_space(front = true) {
    if (front) {
        // 前部半空间，保留 Z >= 0。
        translate([0, 0, BIG / 2 - eps])
            cube([BIG, BIG, BIG], center = true);
    } else {
        // 后部半空间，保留 Z <= 0。
        translate([0, 0, -BIG / 2 + eps])
            cube([BIG, BIG, BIG], center = true);
    }
}

module bezier_blade_half(front = true) {
    intersection() {
        bezier_blade_solid();
        z_half_space(front);
    }
}

module bezier_handle_half(front = true) {
    intersection() {
        bezier_handle_solid();
        z_half_space(front);
    }
}

// ═══ 圆角矩形 (XZ 平面) ═══

module rounded_rect(w, h, r) {
    rr = min(r, w/2 - eps, h/2 - eps);
    hull()
        for (sx = [-1, 1], sy = [-1, 1])
            translate([sx * (w/2 - rr), sy * (h/2 - rr)])
                circle(r = rr);
}

// ═══ 完整拍体外壳（以 Z=0 为中心） ═══

module paddle_outer() {
    if (USE_BEZIER_PROFILES && USE_IMPORTED_OUTER) {
        import("stl/outer_envelope.stl", convexity = 10);
    } else if (USE_BEZIER_PROFILES) {
        bezier_paddle_outer();
    } else {
        steps = LOFT_SLICES;
        y0 = handle_butt_y;
        y1 = blade_tip_y;
        dh = (y1 - y0) / steps;
        for (i = [0:steps-1]) {
            ym = y0 + (i + 0.5) * dh;
            hx = paddle_hx(ym);
            hz = half_z_at(ym);
            if (hx > 0.05) {
                translate([0, ym, 0])
                rotate([90, 0, 0])
                    linear_extrude(height = dh + eps, center = true) {
                        if (ym >= shoulder_top_y) {
                            scale([hx, hz]) circle(r = 1);
                        } else {
                            rounded_rect(hx * 2, hz * 2, handle_corner_r);
                        }
                    }
            }
        }
    }
}

// ═══ 内部空腔（从外部几何中减去） ═══

module handle_cavity() {
    // 仅手柄中空；拍面保持实心。
    if (USE_BEZIER_PROFILES) {
        bezier_handle_cavity();
    } else {
        steps = 80;
        y0 = handle_butt_y + wall_t;
        y1 = shoulder_top_y + 5;
        dh = (y1 - y0) / steps;
        for (i = [0:steps-1]) {
            ym = y0 + (i + 0.5) * dh;
            outer_hx = paddle_hx(ym);
            outer_hz = half_z_at(ym);
            inner_hx = outer_hx - wall_t - handle_cavity_inset;
            inner_hz = outer_hz - wall_t - handle_cavity_inset;
            if (inner_hx > 0.5 && inner_hz > 0.5) {
                translate([0, ym, 0])
                rotate([90, 0, 0])
                    linear_extrude(height = dh + eps, center = true) {
                        if (ym >= shoulder_top_y) {
                            scale([inner_hx, inner_hz]) circle(r = 1);
                        } else {
                            rounded_rect(inner_hx * 2, inner_hz * 2,
                                max(1.5, handle_corner_r - 1));
                        }
                    }
            }
        }
    }
}

// ═══ 螺丝 Boss（正向圆柱） ═══

module screw_bosses() {
    for (p = screw_positions)
        if (screw_position_ok(p)) {
            x = p[0]; y = p[1];
            hz = half_z_at(y);
            boss_h = hz - wall_t;
            if (boss_h > 1) {
                translate([x, y, 0])
                    cylinder(d = screw_d_boss, h = boss_h, center = false);
            }
        }
}

// 后壳半部 Boss（负 Z 方向）
module screw_bosses_back() {
    for (p = screw_positions)
        if (screw_position_ok(p)) {
            x = p[0]; y = p[1];
            hz = half_z_at(y);
            boss_h = hz - wall_t;
            if (boss_h > 1) {
                translate([x, y, -boss_h])
                    cylinder(d = screw_d_boss, h = boss_h, center = false);
            }
        }
}

// ═══ 螺丝孔 ═══

module screw_holes_clearance() {
    for (p = screw_positions)
        if (screw_position_ok(p)) {
        x = p[0]; y = p[1];
        hz = half_z_at(y);
        // 间隙孔，从分型面到锥体底部
        cone_h = 1.8;  // M2 沉头螺丝帽厚度
        cone_top = hz - plug_recess_depth;
        translate([x, y, -eps])
            cylinder(d = screw_d_clearance, h = cone_top - cone_h + eps);
        // 锥形沉头：宽口在硅胶塞坑底面，向内收窄。
        translate([x, y, cone_top - cone_h])
            cylinder(d1 = screw_d_clearance, d2 = screw_head_d, h = cone_h + eps);
        }
}

module screw_holes_clearance_blade() {
    for (p = screw_positions)
        if (screw_in_blade(p)) {
        x = p[0]; y = p[1];
        hz = half_z_at(y);
        // 间隙孔，从分型面到锥体底部
        cone_h = 1.8;  // M2 沉头螺丝帽厚度
        translate([x, y, -eps])
            cylinder(d = screw_d_clearance, h = hz - cone_h + eps);
        // 锥形沉头：宽口在外表面，向内收窄。
        translate([x, y, hz - cone_h])
            cylinder(d1 = screw_d_clearance, d2 = screw_head_d, h = cone_h + eps);
        }
}

// 落在拍面鬓角内的手柄螺丝：拍面部件需要开通孔让螺丝穿过。
//（拍面多边形经鬓角延伸至 y≈-103，覆盖部分手柄螺丝位。）
module blade_pass_through_for_handle_screws() {
    for (p = screw_positions)
        if (screw_in_handle(p) && screw_position_ok(p)
            && abs(p[0]) < envelope_hx(p[1]) - 3) {
        x = p[0]; y = p[1];
        hz = half_z_at(y);
        // 螺杆间隙过孔：从拍面穿过到达手柄。
        translate([x, y, -eps])
            cylinder(d = screw_d_clearance, h = hz + eps);
        }
}

module screw_holes_pilot() {
    for (p = screw_positions)
        if (screw_position_ok(p)) {
        x = p[0]; y = p[1];
        hz = half_z_at(y);
        // 从分型面向内钻约 60% 壁厚的引导孔
        drill_h = (hz - wall_t) * 0.7;
        translate([x, y, -drill_h])
            cylinder(d = screw_d_pilot, h = drill_h + eps);
        }
}

// ═══ 硅胶塞凹坑（外壳外侧） ═══

module plug_recesses() {
    for (p = screw_positions)
        if (screw_position_ok(p)) {
        x = p[0]; y = p[1];
        hz = half_z_at(y);
        translate([x, y, hz - plug_recess_depth + eps])
            cylinder(d = plug_recess_d, h = plug_recess_depth + eps);
        }
}

// ═══ 压电传感器凹槽 ═══

module piezo_pockets() {
    for (p = piezo_positions) if (piezo_in_blade_ok(p)) {
        x = p[0]; y = p[1];
        hz = half_z_at(y);
        pd = min(piezo_disc_depth, hz - wall_t - 0.3);
        if (pd > 0.2) {
            // 从分型面向壳体内挖出压电片凹槽
            translate([x, y, -eps])
                cylinder(d = piezo_disc_d, h = pd + eps);
        }
    }
}

// ═══ 导线通道 ═══

module wire_channels() {
    // 将压电片导线成对汇聚引入手柄内腔：
    // 右侧（正 X）→ +cx，左侧（负 X）→ -cx。
    // 汇聚点深入手柄区域，确保线槽跨越拍面-手柄连接边界连续。
    entry_y = shoulder_bottom_y + 2;
    cx = wire_entry_x();
    for (sx = [-1, 1]) {
        // 同侧压电片汇聚到同一个人口点。
        points = [for (p = piezo_positions) if (piezo_in_blade_ok(p) && sign(p[0]) == sx) p];
        if (len(points) > 0) {
            for (p = points) {
                px = p[0]; py = p[1];
                // 从压电片到汇聚点的线槽
                hull() {
                    translate([px, py, -eps])
                        cylinder(d = piezo_trench_w, h = piezo_trench_d + eps);
                    translate([sx * cx, entry_y, -eps])
                        cylinder(d = piezo_trench_w, h = piezo_trench_d + eps);
                }
            }
            // 从汇聚点继续延伸到手柄内腔
            hull() {
                translate([sx * cx, entry_y, -eps])
                    cylinder(d = piezo_trench_w, h = piezo_trench_d + eps);
                translate([sx * cx, shoulder_bottom_y - 20, -eps])
                    cylinder(d = piezo_trench_w, h = piezo_trench_d + eps);
            }
        }
    }
}

// ═══ USB-C 开口 ═══

module usb_c_cutout() {
    // 在拍柄底部，沿 +Y 方向向内切。
    translate([0, handle_butt_y, -usb_c_h/2])
        rotate([-90, 0, 0])
            linear_extrude(height = usb_c_depth + eps)
                square([usb_c_w, usb_c_h], center = true);
}

// ═══ LED 导光柱孔（拍柄底部） ═══

led_filament_d = 2.0;     // 1.75mm 透明耗材丝导光用的孔
led_filament_depth = 8;    // 钻入底部壁面的深度

module led_light_guide_hole() {
    // 置于 USB-C 上方，在拍柄底部端面。
    translate([0, handle_butt_y, usb_c_h/2 + 2.5])
        rotate([-90, 0, 0])
            linear_extrude(height = led_filament_depth + eps)
                circle(d = led_filament_d);
}

// ═══ 定位销 & 定位孔 ═══

module alignment_pins() {
    for (p = pin_positions)
        if (pin_position_ok(p)) {
        x = p[0]; y = p[1];
        hz = half_z_at(y);
        if (hz > wall_t + pin_h + 1) {
            translate([x, y, 0])
                cylinder(d = pin_d, h = pin_h);
        }
        }
}

module alignment_sockets() {
    for (p = pin_positions)
        if (pin_position_ok(p)) {
        x = p[0]; y = p[1];
        hz = half_z_at(y);
        if (hz > wall_t + pin_h + 1) {
            translate([x, y, -eps])
                cylinder(d = pin_d + pin_socket_clearance * 2, h = pin_h + 1);
        }
        }
}

// ═══ 拍面内部加强筋 ═══

module blade_ribs() {
    for (y = [shoulder_top_y + rib_spacing : rib_spacing : blade_tip_y - 15]) {
        hx = paddle_hx(y) - wall_t - 3;
        hz = half_z_at(y) - wall_t - blade_inner_floor;
        if (hx > 3 && hz > 0.3) {
            translate([0, y, wall_t])
            rotate([90, 0, 0])
                linear_extrude(height = rib_t, center = true)
                    scale([hx, hz])
                        circle(r = 1);
        }
    }
}

module outer_skin_front() {
    if (USE_BEZIER_PROFILES) {
        union() {
            bezier_blade_half(true);
            bezier_handle_half(true);
        }
    } else {
        intersection() {
            paddle_outer();
            z_half_space(true);
        }
    }
}

module outer_skin_back() {
    if (USE_BEZIER_PROFILES) {
        union() {
            bezier_blade_half(false);
            bezier_handle_half(false);
        }
    } else {
        intersection() {
            paddle_outer();
            z_half_space(false);
        }
    }
}

// ═══ 通用螺丝 Boss 立柱（带末端扩展） ═══
// h: 总高度。前后 boss 均使用 direction=+1。
// 扩展端（宽头）在远端——前壳在外部壁面，后壳在分型面。
module screw_boss_column(h, direction) {
    flare_h = 1.2;
    flare_d = 7;
    shaft_d = 6;
    if (h > 0.3) {
        union() {
            // 从起始点向内的直杆
            if (h > flare_h) {
                translate([0, 0, direction * 0.01])
                    cylinder(d = shaft_d, h = h - flare_h, center = false);
            }
            // 末端的扩展
            hull() {
                translate([0, 0, direction * (h - flare_h)])
                    cylinder(d = shaft_d, h = 0.02, center = false);
                translate([0, 0, direction * (h - 0.01)])
                    cylinder(d = flare_d, h = 0.02, center = false);
            }
        }
    }
}

// ═══ 四个可打印零件（拍面/拍柄 × 前/后） ═══

module blade_front_part() {
    module _cutouts() {
        screw_holes_clearance_blade();
        blade_pass_through_for_handle_screws();
        piezo_pockets();
        wire_channels();
    }
    difference() {
        union() {
            bezier_blade_half(true);
            blade_ribs();
        }
        _cutouts();
    }
    for (p = pin_positions)
        if (pin_position_ok(p) && p[1] > shoulder_bottom_y) {
            let(x = p[0], y = p[1], hz = half_z_at(y))
            if (hz > wall_t + pin_h + 1)
                translate([x, y, 0])
                    cylinder(d = pin_d, h = pin_h);
        }
}

module blade_back_part() {
    module _cutouts() {
        // 贯穿螺丝孔：略过分型面，确保干净打通。
        for (p = screw_positions)
            if (screw_in_blade(p)) {
                let(x = p[0], y = p[1], hz = half_z_at(y))
                translate([x, y, -hz - eps])
                    cylinder(d = screw_d_pilot, h = hz + 2 * eps);
            }
        blade_pass_through_for_handle_screws();
        piezo_pockets();
        wire_channels();
    }
    difference() {
        union() {
            bezier_blade_half(false);
            blade_ribs();
            for (p = screw_positions)
                if (screw_in_blade(p)) {
                    let(x = p[0], y = p[1], hz = half_z_at(y), boss_h = hz - wall_t)
                    if (boss_h > 0.2)
                        translate([x, y, -boss_h])
                            cylinder(d = screw_d_boss, h = boss_h);
                }
        }
        _cutouts();
    }
    for (p = pin_positions)
        if (pin_position_ok(p) && p[1] > shoulder_bottom_y) {
            let(x = p[0], y = p[1], hz = half_z_at(y))
            if (hz > wall_t + pin_h + 1)
                translate([x, y, -eps])
                    cylinder(d = pin_d + pin_socket_clearance * 2, h = pin_h + 1);
        }
}

module handle_front_part() {
    difference() {
        union() {
            // 先挖空壳体，再加 boss 立柱，避免空腔把 boss 切掉。
            difference() {
                bezier_handle_half(true);
                handle_cavity();
            }
            for (p = screw_positions)
                if (screw_in_handle(p)) {
                    let(x = p[0], y = p[1], hz = half_z_at(y), boss_h = hz - wall_t - 3)
                    if (boss_h > 0.5)
                    translate([x, y, 0])
                        screw_boss_column(boss_h, 1);
                }
        }
        wire_channels();
        screw_holes_clearance();
        plug_recesses();
        led_light_guide_hole();
    }
}

module handle_back_part() {
    difference() {
        union() {
            difference() {
                bezier_handle_half(false);
                handle_cavity();
            }
            for (p = screw_positions)
                if (screw_in_handle(p)) {
                    let(x = p[0], y = p[1], hz = half_z_at(y), boss_h = hz - wall_t)
                    translate([x, y, -boss_h])
                        cylinder(d = screw_d_boss, h = boss_h);
                }
        }
        wire_channels();
        screw_holes_pilot();
        usb_c_cutout();
    }
}

// ═══ 组装半壳（拍面 + 拍柄，同侧 Z 分割） ═══

module front_half() {
    union() {
        blade_front_part();
        handle_front_part();
    }
}

module back_half() {
    union() {
        blade_back_part();
        handle_back_part();
    }
}

// ═══ 渲染 ═══

if (HALF == "front") {
    front_half();
} else if (HALF == "back") {
    back_half();
} else if (HALF == "blade_front") {
    blade_front_part();
} else if (HALF == "blade_back") {
    blade_back_part();
} else if (HALF == "handle_front") {
    handle_front_part();
} else if (HALF == "handle_back") {
    handle_back_part();
} else if (HALF == "both") {
    %front_half();
    back_half();
} else if (HALF == "four") {
    translate([-5, 0, 0]) blade_front_part();
    translate([5, 0, 0]) blade_back_part();
    translate([-5, 120, 0]) handle_front_part();
    translate([5, 120, 0]) handle_back_part();
}

echo(str("=== SmartPaddle Shell ==="));
echo(str("Profile: ", USE_IMPORTED_OUTER ? "Live outer STL (Three.js)" :
    USE_BEZIER_PROFILES ? "bezier SCAD loft" : "legacy ellipse"));
echo(str("Loft slices: ", LOFT_SLICES));
echo(str("Total height: ", blade_tip_y - handle_butt_y, "mm"));
echo(str("Blade: ", blade_width, "mm wide × ", blade_core_t, "mm thick"));
echo(str("Handle: ", handle_length, "mm FL, ", handle_neck_w, "→", handle_butt_w, "mm"));
echo(str("Half: ", HALF));
echo(str("Screws: ", len(screw_positions), "× M2"));
