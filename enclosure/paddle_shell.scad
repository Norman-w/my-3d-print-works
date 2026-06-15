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
TIP_LENGTH = 25;  // handle_back_tip 切片长度 (mm), 可由 -D 覆盖
LOFT_SLICES = USE_BEZIER_PROFILES ? 64 : 150;

// 由 scripts/bezier_to_openscad.py 生成（USE_BEZIER_PROFILES=true 时必须）
include <generated/bezier_geometry.scad>
include <bezier_profile.scad>

// 拍柄开孔基准 Y：取贝塞尔实际底部 (BEZIER_Y0) 与参数量级 (handle_butt_y) 二者更深者，
// 再减 handle_extend_y 延伸量，确保 USB-C/按钮/LED 永远从外部切穿。
handle_butt_cut_y = USE_BEZIER_PROFILES
    ? min(handle_butt_y, BEZIER_Y0) - handle_extend_y
    : handle_butt_y;

// 壳体实际外表面 Y (还原延伸量)，用于开孔内段定位。
actual_butt_y = handle_butt_cut_y + handle_extend_y;

$fn = 80;
eps = 0.02;
overcut = 0.5;  // Z=0 截面过切量，确保切槽干净穿透分型面
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

module piezo_pockets(front = true) {
    for (p = piezo_positions) if (piezo_in_blade_ok(p)) {
        x = p[0]; y = p[1];
        hz = half_z_at(y);
        pd = min(piezo_disc_depth, hz - wall_t - 0.3);
        if (pd > 0.2) {
            if (front)
                translate([x, y, -overcut])
                    cylinder(d = piezo_disc_d, h = pd + overcut + eps);
            else
                translate([x, y, -pd - eps])
                    cylinder(d = piezo_disc_d, h = pd + eps + overcut);
        }
    }
}

// ═══ PZT 信号调理电阻耳槽 ═══
//
// 每片 PZT 旁边紧贴一个小矩形槽，容纳:
//   - 1MΩ 并联电阻 (0603 封装, 1.6×0.8mm)
//   - BAT54S 双肖特基钳位二极管 (SOT-23-3, 2.9×2.5mm)
// 总占用 ≈ 5×7mm。耳槽沿 PZT→MCU 汇聚点方向延伸，信号路径最短。
// 耳槽与 PZT 槽内侧有 1mm 重叠以保证两槽连通。
module resistor_ears(front = true) {
    cx = pcb_cavity_center[0];
    hub_y = pcb_cavity_center[1];
    for (p = piezo_positions) if (piezo_in_blade_ok(p)) {
        px = p[0]; py = p[1];
        hz = half_z_at(py);
        ed = min(resistor_ear_d, hz - wall_t - 0.3);
        if (ed > 0.2) {
            dx = cx - px; dy = hub_y - py;
            angle = atan2(dy, dx);
            ear_center_offset = piezo_disc_d / 2 + resistor_ear_l / 2 - 2;
            ear_cx = px + ear_center_offset * cos(angle);
            ear_cy = py + ear_center_offset * sin(angle);
            if (front)
                translate([ear_cx, ear_cy, ed/2])
                    rotate([0, 0, angle])
                        cube([resistor_ear_l, resistor_ear_w, ed + 2*overcut + eps], center = true);
            else
                translate([ear_cx, ear_cy, -ed/2])
                    rotate([0, 0, angle])
                        cube([resistor_ear_l, resistor_ear_w, ed + 2*overcut + eps], center = true);
        }
    }
}

// ═══ 刚性 PCB 嵌入槽 / KiCad 对照背衬源 ═══
//
// 这个 2D 轮廓是 rigid_pcb/tools/mech_geometry.py 中 SCAD_SLOT_POINTS 的机械基准。
//
// 点分类（共 38 点）：
//   - 14 个大陆接壤点：X/Y 从 pcb_cavity_center + pcb_cavity_size 自动推导
//   - 24 个 PZT 码头/尾巴点：固定几何值，独立于大陆区尺寸
// 修改 pcb_cavity_center 或 pcb_cavity_size 后，14 个接壤点自动跟随。
//
// KiCad 中会把同一批点转换为 Edge.Cuts，并在 Dwgs.User 上画背衬对照。

// ── 大陆区边界：从 cavity 参数自动推导，最终零硬编码 ──
_ml_x_l = -pcb_cavity_size[0] / 2;                           // 大陆左边界 X (-21)
_ml_x_r =  pcb_cavity_size[0] / 2;                           // 大陆右边界 X (+21)
_ml_y_t =  pcb_cavity_center[1] + pcb_cavity_size[1] / 2;   // 大陆上边界 Y (+24)
_ml_y_b =  pcb_cavity_center[1] - pcb_cavity_size[1] / 2;   // 大陆下边界 Y (-26)

// ── 栈道/尾巴几何常量（独立于大陆区尺寸的设计选择） ──
_gw_corner = 1.61;      // 栈道与大陆底角的内收量，避免锐角应力集中
_gw_bl_w   = 16.75;     // 下栈道外缘 |X|，决定下栈道宽度 = _ml_x_r - _gw_bl_w = 4.25mm
_gw_tl_outer = 19.48;   // 上栈道外缘 |X|，拍头左侧
_gw_tl_inner = 14.75;   // 上栈道内缘 |X|，拍头左侧 (6.25mm 宽)
// PCB 尾巴: 1.27mm×10P 金手指尾插, 深入拍柄空腔避开颈部螺丝 Y=-89
// 尾巴呈"凸"字形: 基部保持 9mm 半宽，末端 10mm 收窄到金手指宽度
_tail_hw        = 3.81;  // 金手指区半宽（对映 tail_connector_pcb_w/2）
_tail_base_hw   = 9.00;  // 尾巴基部半宽（原大陆区延续宽度）
_tail_y         = -102.00; // 尖端 Y（伸入拍柄 13mm，螺丝已过）
_tail_neck_y    = -92.00;  // 收窄转折点 Y（= tail_y + 10mm 金手指区长度）

rigid_pcb_slot_points = [
    // ─ 尾巴 (凸字形: 尖端收窄 10mm → 基部恢复 9mm 半宽) ─
    [ _tail_hw,      _tail_y],                //  0 尾巴右尖（金手指窄区）
    [-_tail_hw,      _tail_y],                //  1 尾巴左尖（金手指窄区）
    [-_tail_hw,      _tail_neck_y],           //  2 窄区→宽区转折（左）
    [-_tail_base_hw, _tail_neck_y],           //  3 宽区起点（左）
    [-_tail_base_hw, _ml_y_b],                //  4 宽区→大陆下缘（左）
    // ─ 左下栈道 → 左侧下 PZT 码头 ─
    [-_gw_bl_w,   _ml_y_b],                   //  3 下栈道入口
    [-29.99, -40.11],                        //  4 码头几何（固定）
    [-28.24, -41.75],                        //  5
    [-35.08, -49.05],                        //  6
    [-41.65, -42.90],                        //  7
    [-34.81, -35.60],                        //  8
    [-33.06, -37.24],                        //  9
    // ─ 大陆左侧边缘 ─
    [_ml_x_l,   _ml_y_b + _gw_corner],       // 10 大陆左下（内收 gw_corner）
    [_ml_x_l,   _ml_y_t],                    // 11 大陆左上
    // ─ 左上栈道 → 左侧上 PZT 码头 ─
    [-_gw_tl_outer, _ml_y_t],                // 12 上栈道外缘
    [-29.66, 35.62],                        // 13 码头几何（固定）
    [-31.62, 34.32],                        // 14
    [-37.17, 42.64],                        // 15
    [-29.68, 47.63],                        // 16
    [-24.13, 39.31],                        // 17
    [-26.15, 37.97],                        // 18
    [-_gw_tl_inner, _ml_y_t],                // 19 上栈道内缘
    // ─ 右上栈道 → 右侧上 PZT 码头 ─
    [ _gw_tl_inner, _ml_y_t],                // 20 上栈道内缘（右）
    [ 26.15, 37.97],                        // 21 码头几何（固定）
    [ 24.13, 39.31],                        // 22
    [ 29.68, 47.63],                        // 23
    [ 37.17, 42.64],                        // 24
    [ 31.62, 34.32],                        // 25
    [ 29.66, 35.62],                        // 26
    [ _gw_tl_outer, _ml_y_t],                // 27 上栈道外缘（右）
    // ─ 大陆右侧边缘 ─
    [_ml_x_r,   _ml_y_t],                    // 28 大陆右上
    [_ml_x_r,   _ml_y_b + _gw_corner],       // 29 大陆右下（内收 gw_corner）
    // ─ 右下栈道 → 右侧下 PZT 码头 ─
    [ 33.06, -37.24],                       // 30 码头几何（固定）
    [ 34.81, -35.60],                       // 31
    [ 41.65, -42.90],                       // 32
    [ 35.08, -49.05],                       // 33
    [ 28.24, -41.75],                       // 34
    [ 29.99, -40.11],                       // 35
    [ _gw_bl_w,        _ml_y_b],             // 36 下栈道入口（右）
    // ─ 尾巴（宽区 → 窄区） ─
    [_tail_base_hw,    _ml_y_b],             // 37 宽区→大陆下缘（右）
    [_tail_base_hw,    _tail_neck_y],        // 38 宽区→转折（右）
    [_tail_hw,         _tail_neck_y],        // 39 窄区→宽区转折（右）
];

module rigid_pcb_profile_2d() {
    polygon(points = rigid_pcb_slot_points);
}

module rigid_pcb_cavity(front = true) {
    d = max(pcb_cavity_depth, piezo_trench_d, resistor_ear_d);
    if (front)
        translate([0, 0, d / 2])
            linear_extrude(height = d + 2 * overcut + eps, center = true)
                rigid_pcb_profile_2d();
    else
        translate([0, 0, -d / 2])
            linear_extrude(height = d + 2 * overcut + eps, center = true)
                rigid_pcb_profile_2d();
}

// ═══ 导线通道 ═══

module wire_channels(front = true) {
    cx = pcb_cavity_center[0];  hub_y = pcb_cavity_center[1];
    hub_d = 10;
    td = piezo_trench_d;
    z0 = front ? -overcut : -td - overcut;
    zh = td + 2*overcut + eps;
    for (sx = [-1, 1]) {
        points = [for (p = piezo_positions) if (piezo_in_blade_ok(p) && sign(p[0]) == sx) p];
        if (len(points) > 0) {
            for (p = points) {
                px = p[0]; py = p[1];
                hull() {
                    translate([px, py, z0])
                        cylinder(d = piezo_trench_w, h = zh);
                    translate([cx, hub_y, z0])
                        cylinder(d = piezo_trench_w, h = zh);
                }
            }
        }
    }
    translate([cx, hub_y, z0])
        cylinder(d = hub_d, h = zh);
}

// ═══ 电源通道（拍柄电池 → 甜区 ESP32） ═══

module signal_bus_to_handle(front = true) {
    trench_w = signal_trench_w;
    trench_d = signal_trench_d;
    // 统一 Z 底起点 + 总高度，cube 和 cylinder 共用，避免 hull 渐变
    z0    = front ? -overcut : -trench_d - overcut;
    zh    = trench_d + 2*overcut + eps;
    zcube = z0 + zh / 2;                     // cube center=true 要用中心点
    pcb_left  = pcb_cavity_center[0] - pcb_cavity_size[0] / 2 + 2.5;
    pcb_right = pcb_cavity_center[0] + pcb_cavity_size[0] / 2 - 2.5;
    pcb_y     = pcb_cavity_center[1];
    entry_y_join = shoulder_bottom_y;
    entry_y_deep = shoulder_bottom_y - 20;
    entry_x      = 5;
    for (sx = [-1, 1]) {
        pcb_entry_x = sx > 0 ? pcb_right : pcb_left;
        handle_entry_x = sx * entry_x;
        hull() {
            translate([pcb_entry_x, pcb_y, zcube])
                cube([2, trench_w, zh], center = true);
            translate([handle_entry_x, entry_y_join, z0])
                cylinder(d = trench_w * 1.5, h = zh);
        }
        hull() {
            translate([handle_entry_x, entry_y_join, z0])
                cylinder(d = trench_w * 1.5, h = zh);
            translate([handle_entry_x, entry_y_deep, z0])
                cylinder(d = trench_w * 1.5, h = zh);
        }
    }
}

// ═══ PCB 安装凹槽 ═══

module pcb_main_cavity(front = true) {
    xy = pcb_cavity_center;
    wh = pcb_cavity_size;
    d  = pcb_cavity_depth;
    if (front)
        translate([xy[0], xy[1], d/2])
            cube([wh[0], wh[1], d + 2*overcut + eps], center = true);
    else
        translate([xy[0], xy[1], -d/2])
            cube([wh[0], wh[1], d + 2*overcut + eps], center = true);
}

// ═══ USB-C 母座两段式台阶开口 ═══
//
// 内圈（壳外可见）：公头大小，穿透 2mm 挡皮。
// 外圈（腔体内）：母座外壳 + 0.5mm，深约 13mm 入腔体。
// 母座从腔体向外推入，外圈容纳母座体，2mm 台阶卡住不脱出。

// ── 辅助：圆角矩形 2D 轮廓 (XZ 平面) ──
module _usb_c_rounded_rect(op_x, op_z, r) {
    hull() {
        for (x = [-1, 1], z = [-1, 1])
            translate([x * (op_x/2 - r), z * (op_z/2 - r)])
                circle(r = r);
    }
}

module usb_c_cutout() {
    // 1. 内圈：穿透挡皮 (handle_butt_cut_y → +wall端)，公头大小
    translate([0, handle_butt_cut_y, usb_c_z])
        rotate([-90, 0, 0])
            linear_extrude(height = handle_extend_y + usb_c_retain_t + eps)
                _usb_c_rounded_rect(usb_c_opening_x, usb_c_opening_z, usb_c_opening_r);

    // 2. 外圈：从挡皮后侧往腔体挖深，母座外壳 + 0.5mm
    socket_start_y = handle_butt_cut_y + handle_extend_y + usb_c_retain_t;
    translate([0, socket_start_y, usb_c_z])
        rotate([-90, 0, 0])
            linear_extrude(height = 7 + eps)
                _usb_c_rounded_rect(usb_c_socket_x, usb_c_socket_z, usb_c_socket_r);

    // 3. 线路板槽：母座右侧 +X 方向，1.6mm 板厚
    //    X: 母座外圈右缘 (+2.0) → +3.6
    //    Y: 母座挡槽 +1mm 起 15.8mm 深
    //    Z: ±6mm (前后壳共享)
    pcb_x  = usb_c_socket_x / 2;                    // PCB X 起点 (母座外圈右缘)
    pcb_dz = 6;                                     // PCB 槽 Z 半高
    pcb_y  = socket_start_y + 1;                    // PCB 槽 Y 起点 (挡槽 + 1mm)
    translate([pcb_x, pcb_y, -pcb_dz])
        cube([1.6, 15.8, pcb_dz * 2]);

    // 4. 元器件/接线空间槽：外圈切完 7mm 后的 Y 位置为起点，高 6mm。
    //    X 贯穿基台全宽，Z 为线路板高 12mm (±6mm)。
    //    用于漏出负载接线通往开关侧，以及线路板正面电子元件空间。
    clr_x  = -(usb_c_socket_x / 2);                 // 基台 X 起点 (母座外圈左侧)
    clr_w  = usb_c_socket_x + 1.6 + 2;              // 基台 X 全宽
    clr_y  = socket_start_y + 7;                    // 外圈 Y 尾端
    translate([clr_x, clr_y, -pcb_dz])
        cube([clr_w, 6, pcb_dz * 2]);

    // 5. 电池线焊点/导线空间槽：第4刀 Y 尾端为起点，直到基台 Y 末端。
    //    X: 从线路板左面 (X=+2.0) 到基台左侧 (X=-2.0)，宽 4mm。
    //    Z: ±6mm。
    //    用于腾出充电板背面电池线焊点及导线位置。
    bat_x = -(usb_c_socket_x / 2);                  // 起点 X (基台左侧)
    bat_w = usb_c_socket_x;                         // 宽 (母座外圈全宽 4mm)
    bat_y = clr_y + 6;                               // Y 起点 (第4刀尾端)
    bat_h = (actual_butt_y + 2 + 19) - bat_y + eps;  // 高 (到基台 Y 末端)
    translate([bat_x, bat_y, -pcb_dz])
        cube([bat_w, bat_h, pcb_dz * 2]);
}

// ═══ 充电 PCB 实心基台 (加法实体, 后续挖空放线路板) ═══
//
// USB-C 母座焊接在线路板上, 线路板在母座 +X 方向。
// 从台阶后 2mm 起向 Y+ 深 19mm (台阶1mm + 母座缝1mm)。
// 前后壳各贡献一半, 合壳后形成完整块, 后续挖空容纳充电模块。

module usb_c_pcb_block(front = true) {
    hz = half_z_at(actual_butt_y);   // 拍柄尾端半高
    blk_y = actual_butt_y + 2;       // Y 起点 (台阶 1mm + 母座缝隙 1mm, 往 +Y)

    blk_x = -(usb_c_socket_x / 2);          // X 起点 (母座外圈左侧)
    blk_w = usb_c_socket_x + 1.6 + 2;      // X 宽 (母座 + 板厚 + 2mm 容差)
    if (front) {
        translate([blk_x, blk_y, 0])
            cube([blk_w, 19, hz]);
    } else {
        translate([blk_x, blk_y, -hz])
            cube([blk_w, 19, hz]);
    }
}

// ═══ USB-C 母座左侧夹持固定销 (加法实体) ═══
//
// 从母座外圈左侧 (X=-2.0) 往 X- 方向伸出 1.5mm 宽的销柱。
// Y: 从墙体内侧 (actual_butt_y + 1) 向拍头 +5mm。
// Z: 从分型面向 ±3mm (前后壳各延伸 3mm)。
// 用于辅助夹持固定 USB-C 母座，防止左右窜动。

module usb_c_left_clamp(front = true) {
    clamp_x = -(usb_c_socket_x / 2) - 1.5;   // X 起点 (母座左侧往 X- 1.5mm)
    clamp_y = actual_butt_y + usb_c_retain_t; // Y 起点 (墙体内侧)
    if (front) {
        translate([clamp_x, clamp_y, 0])
            cube([1.5, 5, 3]);
    } else {
        translate([clamp_x, clamp_y, -3])
            cube([1.5, 5, 3]);
    }
}

// ═══ LED 导光柱孔（拍柄底部） ═══
//
// 充电模块位于拍柄底部内腔。两个 TP4056 LED 指示灯 (红/绿)
// 通过导光柱孔通向外部，位于 USB-C 上方。

module led_light_guide_holes() {
    // 红绿共用单孔，位于左上 (X<0, Z>0)，仅在前壳打孔。
    translate([led_charge_x, handle_butt_cut_y, led_charge_z])
        rotate([-90, 0, 0])
            linear_extrude(height = led_hole_depth + eps)
                circle(d = led_hole_d);
}

// ═══ 软开关按钮孔 ═══
//
// 4.5×4.5mm 轻触开关，从分型面 (Z=0) 直接安入。
// 矩形通道 5×5mm 从外壁内侧直通腔体 (~9mm深)。
// 前 3mm 容纳开关塑料体，后 6mm 为立柱+焊爪区。
// 立柱 X=3 Y=5 Z=壳厚，Z 向接到外壳壁面提供结构支撑。
// 开关焊爪从立柱两侧 1mm 间隙伸入内腔。
// P-MOSFET 自锁电路：按下 → 上电 → ESP32 GPIO 拉低自锁。
// 长按 2s → ESP32 释放 GPIO → 关机。

module button_cutout() {
    // 按钮柱通孔: Ø3mm，穿透外壁 (button_wall_t=1mm)
    translate([button_x, handle_butt_cut_y, button_z])
        rotate([-90, 0, 0])
            linear_extrude(height = handle_extend_y + button_wall_t + eps)
                circle(d = button_cap_d);

    // 矩形通道: 5×5mm，从外壁内侧直通腔体 9mm
    // 前 3mm 容纳 4.5×4.5 开关体，后 6mm 为立柱（5mm）+ 焊爪间隙（1mm）
    pocket_start = actual_butt_y + button_wall_t;
    translate([button_x, pocket_start, button_z])
        rotate([-90, 0, 0])
            linear_extrude(height = 9 + eps)
                square([button_pocket_w, button_pocket_w], center = true);
}

// ═══ 按钮立柱（加法实体，接驳到 Z 向外壳壁） ═══
//
// 立柱 X=3 Y=5 Z=壳厚，位于开关体后壁 (pocket_start+3)。
// Z 向从分型面 (0) 直通外壳表面，与壳壁一体化，非悬浮片。
// 开关焊爪从立柱两侧 1mm 间隙 (X方向) 伸入内腔。

module button_retention_column(front = true) {
    pocket_start = actual_butt_y + button_wall_t;
    hz = half_z_at(actual_butt_y);   // 拍柄尾端半高
    col_y = pocket_start + 3;        // 立柱 Y 起点 (开关体槽后壁)
    col_x = button_x - 1.5;          // 立柱 X 起點 (3mm 宽居中)

    if (front) {
        // 前壳: Z=0 → +hz，立柱接到前壳外壁
        translate([col_x, col_y, 0])
            cube([3, 5, hz]);
    } else {
        // 后壳: Z=-hz → 0，立柱接到后壳外壁
        translate([col_x, col_y, -hz])
            cube([3, 5, hz]);
    }
}

// ═══ 软开关电路元件槽 ═══
//
// 容纳 AO3401 P-MOSFET + 1N4148×2 + 100kΩ 电阻 (死虫焊)。
// 位于按钮內侧旁。

module soft_power_circuit_cavity() {
    // 放在按钮孔内侧壁上（后壳侧），容纳贴片元件。
    translate([button_x + 5, handle_butt_cut_y + 2, button_z - 3])
        rotate([90, 0, 0])
            cube([soft_power_cavity_w, soft_power_cavity_l, soft_power_cavity_d + eps], center = true);
}

// ═══ 用户交互 LED 导光孔 (WS2812-2020) ═══
//
// WS2812-2020 智能 RGB LED（1.6×1.6mm），位于按钮左侧。
// 状态指示灯：蓝闪配网 / 绿常亮AP / 红闪低电量 / 紫闪OTA。
// LED 贴在拍柄底部内壁，焊线引出到 PCB 区域侧。

module ws2812_led_hole() {
    translate([ws2812_led_x, handle_butt_cut_y, ws2812_led_z])
        rotate([-90, 0, 0])
            linear_extrude(height = ws2812_led_hole_depth + eps)
                circle(d = ws2812_led_hole_d);
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
        piezo_pockets(front = true);
        rigid_pcb_cavity(front = true);
        pcb_main_cavity(front = true);
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
        piezo_pockets(front = false);
        rigid_pcb_cavity(front = false);
        pcb_main_cavity(front = false);
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
            // 充电 PCB 实心基台 (放在 union 内，受 usb_c_cutout 减法作用)
            usb_c_pcb_block(front = true);
            // USB-C 左侧夹持固定销
            usb_c_left_clamp(front = true);
        }
        rigid_pcb_cavity(front = true);
        pcb_main_cavity(front = true);
        screw_holes_clearance();
        plug_recesses();
        usb_c_cutout();
        led_light_guide_holes();
        button_cutout();
    }
    // 加固立柱：从开关槽后壁接到 Z 向外壳
    button_retention_column(front = true);
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
            // 充电 PCB 实心基台 (放在 union 内，受 usb_c_cutout 减法作用)
            usb_c_pcb_block(front = false);
            // USB-C 左侧夹持固定销
            usb_c_left_clamp(front = false);
        }
        rigid_pcb_cavity(front = false);
        pcb_main_cavity(front = false);
        screw_holes_pilot();
        usb_c_cutout();
        button_cutout();
        ws2812_led_hole();
        soft_power_circuit_cavity();
    }
    // 加固立柱：从开关槽后壁接到 Z 向外壳
    button_retention_column(front = false);
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
} else if (HALF == "handle_back_tip") {
    // 拍柄后壳尾部切片，用于快速打印验证装配。
    // 长度由 TIP_LENGTH 变量控制，默认 25mm。
    intersection() {
        handle_back_part();
        translate([-BIG, handle_butt_cut_y, -BIG])
            cube([BIG*2, TIP_LENGTH, BIG*2]);
    }
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
echo(str("Total height: ", blade_tip_y - handle_butt_cut_y, "mm"));
echo(str("Blade: ", blade_width, "mm wide × ", blade_core_t, "mm thick"));
echo(str("Handle: ", handle_thickness, "mm thick, butt Y=", handle_butt_y));
echo(str("Half: ", HALF));
echo(str("Screws: ", len(screw_positions), "× M2"));
