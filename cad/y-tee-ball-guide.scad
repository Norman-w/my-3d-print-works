// 打印用 Y 三通。单位 mm。FDM / PETG。
// 原点在风机承口止挡中心。+Z 出球。进球支管在 +X，向外朝风机侧，与参考件同为 135°。
// 这个角度还没按实物重测。
// 进球段外径 50，从端口起内径就是 42，插入送料模块出口。
// 弧线管是一整圈实心壁，内径 42。后风从风机孔一直通到出球段。
// 交汇处只留中间一条贴着弧线外壁的挡条，挡住球。这条以外的风路全部敞开。
// 挡条上的加固：椭圆短直径等于弧线宽，长直径是四倍。长轴从弯道圆心穿过边线再向外探出两倍弧线宽，绕着弧线放到出球直管切点。穿出外壳的部分切掉。
// 弯道中心线半径 100，转 45°，弧长大于球径。局部断面保持内径 42。
// 球在弯里同时只转二十多度，进直管时方向已经摆正，不会一头进直管、球身还在斜段里撞壁。
// 外壳：风机承口外径 56 用一段曲率收到出球管外径 47。支管保持外径 50，不再把交汇处撑粗。
// 打印时出球口贴热床。稳定圈和管壁之间留缝，只在贴床一侧用八处两层窄连接，打完掰掉。球路内径不变。

// ===== 分区：导入/依赖 =====

include <parameters.scad>

// ===== 分区：常量/配置 =====

yt_ball_id = 42;
yt_ball_od = barrel_od;
yt_fan_id = 50;
yt_fan_wall = 3;
yt_exit_wall = 2.5;
yt_fan_depth = y_stub_engagement;
yt_air_step = 3;
yt_air_rib_w = 6;            // 交汇处只留这一条。两侧和后面的风路不再收口
yt_rib_ell_minor = yt_air_rib_w;          // 短直径 = 现在这条弧线的宽度
yt_rib_ell_major = 4 * yt_air_rib_w;       // 长直径 = 弧线宽度的四倍
yt_rib_ell_extra = 8;                       // 弧长外围再延长的角度，两端都加
yt_rib_ell_steps = 24;
yt_rho = 100;
yt_z0 = 114;                 // 出球直段切点。和大半径弯一起抬高，球才不探进风机口
yt_turn = 45;
yt_rib_ell_a0 = -yt_turn - 4;              // 弧线上靠近进球的那头
yt_rib_ell_a1 = 0;                         // 出球端放到直管切点，穿出的部分再用外壳切掉
yt_rib_ell_inlet = yt_rho * yt_rib_ell_extra * PI / 180; // 进球方向再延长的长度
yt_rib_inlet_steps = 6;
yt_branch_angle = 135;
yt_branch_l = 64;            // 末端至少 25 mm 是露出的圆柱，用来插入送料口
yt_exit_l = 106;             // 切点上移后缩短直段，出球口高度不变
yt_mouth_chamfer = 0.6;
yt_arc_steps = 12;
yt_shoulder_len = 22;        // 风机承口外径收到出球管，两端斜率归零
yt_bed_ring_width = 18;      // 出球口贴床面，向外加宽的稳定圈
yt_bed_ring_t = 2.4;         // 多层圈，不是单层裙边
yt_bed_ring_proud = 0.4;     // 略高出出球端面，避免和端面共面碎成非流形
yt_bed_ring_gap = 1.6;       // 圈和管壁之间的缝，方便下手拆
yt_bed_ring_tab_n = 8;       // 两层很薄，多留几处才撑得住整件
yt_bed_ring_tab_w = 6;       // 每处连接的周向宽度
yt_bed_ring_tab_t = 0.4;     // 缝里只留两层 0.2 mm，打完能掰掉
yt_bed_ring_tab_bite = 0.45; // 搭进管壁和圈体，避免只相切
yt_bed_ring_chamfer = 0.8;   // 背向热床的外缘倒角
yt_fn = 64;
yt_eps = 0.08;
yt_used_part = is_undef(yt_part) ? "tee" : yt_part;

// ===== 分区：模型/类型 =====

yt_fan_od = yt_fan_id + 2 * yt_fan_wall;
yt_exit_od = yt_ball_id + 2 * yt_exit_wall;
yt_fan_z0 = -yt_fan_depth;
yt_outward = [sin(yt_branch_angle), 0, cos(yt_branch_angle)];

function yt_on_arc(a) = [
    yt_rho * (1 - cos(a)),
    0,
    yt_z0 + yt_rho * sin(a)
];
function yt_arc_points() = [
    for (i = [0:yt_arc_steps]) yt_on_arc(-yt_turn + yt_turn * i / yt_arc_steps)
];
function yt_branch_mouth() = yt_on_arc(-yt_turn) + yt_branch_l * yt_outward;
function yt_clamp(t) = max(0, min(1, t));
function yt_smooth(t) = let(u = yt_clamp(t)) u * u * u * (10 + u * (-15 + 6 * u));
function yt_outer_r(z) = z <= 0 ? yt_fan_od / 2
    : z >= yt_shoulder_len ? yt_exit_od / 2
    : yt_fan_od / 2 + (yt_exit_od / 2 - yt_fan_od / 2) * yt_smooth(z / yt_shoulder_len);
function yt_main_profile() = concat(
    [[0, yt_fan_z0]],
    [[yt_outer_r(yt_fan_z0), yt_fan_z0]],
    [for (i = [1:96]) let(z = yt_fan_z0 + (yt_z0 + yt_exit_l - yt_fan_z0) * i / 96)
        [yt_outer_r(z), z]],
    [[0, yt_z0 + yt_exit_l]]
);

// ===== 分区：私有成员 =====

module yt_pipe(points, radius) {
    for (i = [0:len(points) - 2])
        hull() {
            translate(points[i]) sphere(r=radius, $fn=yt_fn);
            translate(points[i + 1]) sphere(r=radius, $fn=yt_fn);
        }
}

module yt_taper_pipe(points, r0, r1) {
    n = len(points) - 1;
    for (i = [0:n - 1])
        hull() {
            translate(points[i])
                sphere(r=r0 + (r1 - r0) * yt_smooth(i / n), $fn=yt_fn);
            translate(points[i + 1])
                sphere(r=r0 + (r1 - r0) * yt_smooth((i + 1) / n), $fn=yt_fn);
        }
}

module yt_half_space() {
    translate([-180, 0, yt_fan_z0 - 40])
        cube([360, 180, yt_z0 + yt_exit_l - yt_fan_z0 + 80]);
}

module yt_branch_place() {
    translate(yt_on_arc(-yt_turn))
        rotate([0, yt_branch_angle, 0])
            children();
}

module yt_air_rib_block(a) {
    p = yt_on_arc(a);
    ox = -cos(a);
    oz = sin(a);
    tx = sin(a);
    tz = cos(a);
    r_in = yt_ball_id / 2 - 0.8;
    r_out = yt_ball_id / 2 + yt_exit_wall;
    mid = (r_in + r_out) / 2;
    c = p + [ox, 0, oz] * mid;
    multmatrix([
        [ox, 0, tx, c.x],
        [0, 1, 0, c.y],
        [oz, 0, tz, c.z],
        [0, 0, 0, 1]
    ])
        cube([r_out - r_in, yt_air_rib_w, 0.5], center=true);
}

module yt_air_rib_keep() {
    for (i = [0:yt_arc_steps - 1])
        hull() {
            yt_air_rib_block(-yt_turn - 4 + (yt_turn + 4) * i / yt_arc_steps);
            yt_air_rib_block(-yt_turn - 4 + (yt_turn + 4) * (i + 1) / yt_arc_steps);
        }
}

// 椭圆中心在弧线外壁上。局部 x 从弯道圆心指向边线。长半径默认两倍弧线宽，快顶出管子时收到外壳内侧。
function yt_rib_ell_tip_at(a, t) =
    let(ox = -cos(a), oz = sin(a))
        yt_on_arc(a) + [ox, 0, oz] * (yt_ball_id / 2 + t);

function yt_rib_ell_inside(a, t) =
    let(p = yt_rib_ell_tip_at(a, t))
        sqrt(p.x * p.x + p.y * p.y) + 0.5 < yt_outer_r(p.z);

function yt_rib_ell_fit(a, lo, hi, n) =
    n <= 0 ? lo :
    let(mid = (lo + hi) / 2)
        yt_rib_ell_inside(a, mid)
            ? yt_rib_ell_fit(a, mid, hi, n - 1)
            : yt_rib_ell_fit(a, lo, mid, n - 1);

function yt_rib_ell_out(a) =
    let(full = yt_rib_ell_major / 2)
        yt_rib_ell_inside(a, full) ? full : yt_rib_ell_fit(a, 0.3, full, 8);

module yt_rib_ell_section(a) {
    p = yt_on_arc(a);
    ox = -cos(a);
    oz = sin(a);
    tx = sin(a);
    tz = cos(a);
    c = p + [ox, 0, oz] * (yt_ball_id / 2);
    reach = yt_rib_ell_major / 2;
    n = 24;
    multmatrix([
        [ox, 0, tx, c.x],
        [0, 1, 0, c.y],
        [oz, 0, tz, c.z],
        [0, 0, 0, 1]
    ])
        linear_extrude(0.45, center=true)
            polygon([
                for (i = [0:n - 1]) [
                    reach * cos(360 * i / n),
                    yt_rib_ell_minor / 2 * sin(360 * i / n)
                ]
            ]);
}

function yt_rib_inlet_dir() =
    [-sin(yt_rib_ell_a0), 0, -cos(yt_rib_ell_a0)];

function yt_rib_inlet_u() =
    [-cos(yt_rib_ell_a0), 0, sin(yt_rib_ell_a0)];

function yt_rib_inlet_center(s) =
    yt_on_arc(yt_rib_ell_a0) + yt_rib_inlet_dir() * s + yt_rib_inlet_u() * (yt_ball_id / 2);

function yt_rib_pt_inside(p) =
    sqrt(p.x * p.x + p.y * p.y) + 0.5 < yt_outer_r(p.z);

function yt_rib_inlet_tip(s, t) =
    yt_rib_inlet_center(s) + yt_rib_inlet_u() * t;

function yt_rib_inlet_fit(s, lo, hi, n) =
    n <= 0 ? lo :
    let(mid = (lo + hi) / 2)
        yt_rib_pt_inside(yt_rib_inlet_tip(s, mid))
            ? yt_rib_inlet_fit(s, mid, hi, n - 1)
            : yt_rib_inlet_fit(s, lo, mid, n - 1);

function yt_rib_inlet_out(s) =
    let(full = yt_rib_ell_major / 2)
        yt_rib_pt_inside(yt_rib_inlet_tip(s, full)) ? full
            : yt_rib_inlet_fit(s, 0.3, full, 8);

module yt_rib_inlet_section(s) {
    c = yt_rib_inlet_center(s);
    u = yt_rib_inlet_u();
    d = yt_rib_inlet_dir();
    reach = yt_rib_inlet_out(s);
    n = 24;
    multmatrix([
        [u.x, 0, d.x, c.x],
        [u.y, 1, d.y, c.y],
        [u.z, 0, d.z, c.z],
        [0, 0, 0, 1]
    ])
        linear_extrude(0.45, center=true)
            polygon([
                for (i = [0:n - 1]) [
                    reach * cos(360 * i / n),
                    yt_rib_ell_minor / 2 * sin(360 * i / n)
                ]
            ]);
}

module yt_rib_rein_raw() {
    for (i = [0:yt_rib_ell_steps - 1])
        hull() {
            yt_rib_ell_section(yt_rib_ell_a0 + (yt_rib_ell_a1 - yt_rib_ell_a0) * i / yt_rib_ell_steps);
            yt_rib_ell_section(yt_rib_ell_a0 + (yt_rib_ell_a1 - yt_rib_ell_a0) * (i + 1) / yt_rib_ell_steps);
        }
    for (i = [0:yt_rib_inlet_steps - 1])
        hull() {
            yt_rib_inlet_section(yt_rib_ell_inlet * i / yt_rib_inlet_steps);
            yt_rib_inlet_section(yt_rib_ell_inlet * (i + 1) / yt_rib_inlet_steps);
        }
}

module yt_tube_envelope() {
    yt_main_shell();
    yt_taper_pipe(yt_arc_points(), yt_ball_od / 2, yt_exit_od / 2);
    yt_branch_place()
        cylinder(h=yt_branch_l, d=yt_ball_od, $fn=yt_fn);
}

module yt_rib_rein() {
    intersection() {
        yt_rib_rein_raw();
        yt_tube_envelope();
    }
}

// ===== 分区：公开 API =====

module yt_main_shell() {
    rotate_extrude(convexity=4, $fn=yt_fn)
        polygon(yt_main_profile());
}

module yt_bed_ring_tab() {
    r_wall = yt_exit_od / 2;
    r0 = r_wall - yt_bed_ring_tab_bite;
    ri = r_wall + yt_bed_ring_gap;
    r1 = ri + yt_bed_ring_tab_bite;
    half = yt_bed_ring_tab_w / 2;
    over = 0.15;
    root = 0.3;
    span = root + yt_bed_ring_tab_t + over;
    difference() {
        intersection() {
            difference() {
                translate([0, 0, -root])
                    cylinder(h=span, r=r1, $fn=yt_fn);
                translate([0, 0, -root - yt_eps])
                    cylinder(h=span + 2 * yt_eps, r=r0, $fn=yt_fn);
            }
            translate([0, 0, -root - yt_eps])
                linear_extrude(span + 2 * yt_eps)
                    polygon([[0, -0.2], [r1 + 1, -half], [r1 + 1, half], [0, 0.2]]);
        }
        translate([0, 0, -root - yt_eps])
            difference() {
                cylinder(h=root + yt_eps, r=ri - 0.05, $fn=yt_fn);
                translate([0, 0, -yt_eps])
                    cylinder(h=root + 3 * yt_eps, r=r_wall + 0.05, $fn=yt_fn);
            }
        translate([0, 0, yt_bed_ring_tab_t])
            difference() {
                cylinder(h=over + yt_eps, r=ri - 0.05, $fn=yt_fn);
                translate([0, 0, -yt_eps])
                    cylinder(h=over + 3 * yt_eps, r=r_wall + 0.05, $fn=yt_fn);
            }
        translate([0, 0, yt_bed_ring_tab_t])
            cylinder(h=over + yt_eps, r=r_wall - 0.05, $fn=yt_fn);
    }
}

module yt_bed_ring() {
    z1 = yt_z0 + yt_exit_l;
    ro = yt_exit_od / 2 + yt_bed_ring_width;
    ri = yt_exit_od / 2 + yt_bed_ring_gap;
    face = yt_bed_ring_t + yt_bed_ring_proud;
    translate([0, 0, z1 - yt_bed_ring_t])
        rotate_extrude(convexity=2, $fn=yt_fn)
            polygon([
                [ri, 0],
                [ro - yt_bed_ring_chamfer, 0],
                [ro, yt_bed_ring_chamfer],
                [ro, face],
                [ri, face]
            ]);
    translate([0, 0, z1 + yt_bed_ring_proud - yt_bed_ring_tab_t])
        for (i = [0:yt_bed_ring_tab_n - 1])
            rotate([0, 0, i * 360 / yt_bed_ring_tab_n])
                yt_bed_ring_tab();
}

module yt_outer() {
    yt_main_shell();
    yt_taper_pipe(yt_arc_points(), yt_ball_od / 2, yt_exit_od / 2);
    yt_branch_place()
        cylinder(h=yt_branch_l, d=yt_ball_od, $fn=yt_fn);
    yt_rib_rein();
    yt_bed_ring();
}

module yt_rear_air() {
    difference() {
        translate([0, 0, yt_air_step - yt_eps])
            cylinder(h=yt_z0 - yt_air_step + 2 * yt_eps, d=yt_ball_id, $fn=yt_fn);
        yt_air_rib_keep();
        yt_rib_rein();
    }
}

module yt_bore() {
    translate([0, 0, yt_fan_z0 - yt_eps])
        cylinder(h=yt_fan_depth + yt_eps, d=yt_fan_id, $fn=yt_fn);
    translate([0, 0, -yt_eps])
        cylinder(h=yt_air_step + 2 * yt_eps, d1=yt_fan_id, d2=yt_ball_id, $fn=yt_fn);
    yt_rear_air();
    yt_pipe(concat(yt_arc_points(), [[0, 0, yt_z0 + yt_exit_l]]), yt_ball_id / 2);
    yt_branch_place()
        translate([0, 0, -yt_eps])
            cylinder(h=yt_branch_l + 1, d=yt_ball_id, $fn=yt_fn);
    yt_branch_place()
        translate([0, 0, yt_branch_l - yt_mouth_chamfer])
            cylinder(h=yt_mouth_chamfer + 1,
                d1=yt_ball_id, d2=yt_ball_id + 2 * yt_mouth_chamfer, $fn=yt_fn);
}

module yt_tee() {
    difference() {
        yt_outer();
        yt_bore();
    }
}

// ===== 分区：视图层 =====

module yt_section() {
    difference() {
        yt_tee();
        yt_half_space();
    }
}

// ===== 分区：业务逻辑 =====

assert(yt_ball_od == 50, "进球段外径应为 50");
assert(yt_ball_id == 42, "球道路径内径应为 42");
assert(yt_fan_id == 50, "风机口内径应为 50");
assert(yt_ball_id > ball_max_d, "42 mm 轨道必须大于球径包络");
assert(yt_rho > yt_ball_id / 2, "弯道半径必须大于气道半径，断面才不会自交");
assert(yt_rho * yt_turn * PI / 180 > ball_max_d * 1.5,
    "弯道弧长至少要有球径的 1.5 倍，球才不会横跨整个拐弯");
assert(ball_max_d / yt_rho * 180 / PI < 30, "球在弯道里同时转过的角度应小于 30 度");
assert(yt_air_rib_w >= 4 && yt_air_rib_w <= 8, "交汇处只留中间一条，不要收成风口");
assert(yt_rib_ell_minor == yt_air_rib_w, "椭圆短直径就是弧线宽度");
assert(yt_rib_ell_major == 4 * yt_air_rib_w, "椭圆长直径是弧线宽度的四倍");
assert(yt_rib_ell_major / 2 == 2 * yt_air_rib_w, "过边线的距离是弧线宽度的两倍");
assert(yt_rib_ell_a1 == 0, "出球端放到直管切点，多出去的由外壳切掉");
assert(yt_rib_ell_out(-40) > yt_rib_ell_major / 2 - 0.05,
    "交汇处长轴保持两倍弧线宽");
assert(yt_rib_pt_inside(yt_rib_inlet_tip(yt_rib_ell_inlet, yt_rib_inlet_out(yt_rib_ell_inlet))),
    "进球端延长不要顶出管子");
assert(yt_on_arc(-yt_turn).z - ball_max_d / 2 > yt_air_step,
    "球在弯道入口应完全离开风机收口");
assert(yt_branch_mouth().z - (yt_ball_od / 2) * sin(yt_turn) >= yt_fan_z0,
    "进球口不能低于风机端面，否则整件超高");
assert(yt_branch_l > y_stub_engagement, "进球直段要留出插入长度");
assert(yt_exit_wall >= 2, "出球段壁厚至少 2 mm");
assert(yt_exit_od / 2 - yt_bed_ring_tab_bite - yt_ball_id / 2 >= 1.5,
    "稳定圈连接搭进管壁后，出球段剩余壁厚至少 1.5 mm");
assert(yt_bed_ring_tab_n == 8, "稳定圈留八处连接");
assert(yt_bed_ring_tab_n * yt_bed_ring_tab_w < PI * yt_exit_od * 0.5,
    "连接加起来不能把缝封上");
assert(yt_bed_ring_tab_w <= 8, "每处连接不要太宽");
assert(yt_bed_ring_tab_t == 0.4, "缝里的连接只留两层");
assert(yt_bed_ring_gap >= 1.2, "稳定圈和管壁之间要留得下刀");
assert(yt_bed_ring_t > yt_bed_ring_tab_t + 0.8, "连接上方要留出敞开的缝");
assert(yt_bed_ring_width >= 12, "稳定圈径向宽度至少 12 mm");
assert(yt_branch_mouth().x > yt_exit_od / 2 + yt_ball_od / 2 + 2,
    "进球端口要伸出出球管，才插得进送料口");
assert(yt_branch_l - (yt_exit_od / 2 + yt_ball_od / 2 - yt_on_arc(-yt_turn).x) / sin(yt_branch_angle)
    >= y_stub_engagement, "露出的圆柱插入段至少要有 25 mm");
for (t = [0:5:yt_branch_l]) {
    p = yt_on_arc(-yt_turn) + t * yt_outward;
    if (p.z - ball_max_d / 2 < yt_air_step)
        assert(p.x > yt_fan_id / 2 + ball_max_d / 2 + 1,
            "球在进球段上不能跨进风机口");
}
echo(yt_fan_od=yt_fan_od);
echo(yt_exit_od=yt_exit_od);
echo(yt_branch_join=yt_on_arc(-yt_turn));
echo(yt_arc_len=yt_rho * yt_turn * PI / 180);
echo(yt_air_rib_w=yt_air_rib_w);
echo(yt_muzzle_z=yt_z0 + yt_exit_l);

// ===== 分区：方法/工具 =====

if (yt_used_part == "tee") {
    yt_tee();
} else if (yt_used_part == "section") {
    yt_section();
} else {
    assert(false, "未知零件选择");
}
