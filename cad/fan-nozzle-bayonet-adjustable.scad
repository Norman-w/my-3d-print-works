// 风机卡口 + 连续锥形风道 + 50/48 mm 硬管滑动夹套
//
// 目标：五羊/DOUAES 风机（用户实测外径76、内径71、上下对置锁扣）
// 接入项目现有 50/48 mm 透明硬管，并保留轴向调节空间。
// 打印姿态：本文件的 +Z 方向竖直向上，风机卡口底面贴打印板。
//
// part 可选：
//   "nozzle"       只输出打印件
//   "section"      输出一半剖切的结构审查视图
//   "assembly"     输出风机/硬管包络参考
//   "fan-envelope" 输出风机接口包络
//   "tube-envelope"输出硬管包络
//   "adjustment-view" 输出固定硬管、Y口和风嘴两个调节位置
//   "tip-core34" / "tip-core36" / "tip-core38" / "tip-core40"
//                  输出可拆换风嘴芯
//   "core-fit-section" 输出主件 + Ø40 风嘴芯的剖视装配审查图
//   "core-thread-detail" 输出旋入式螺纹的局部爆炸剖视图
//   "core-taper-section" 输出 Ø34 芯的内部直段—收缩锥—末端直段剖视图
//   "interface-section" 输出“内插段—亚克力管—外套筒—M3夹紧”的剖视说明图
//   "y-tee-interface-section" 输出 Y 三通承口—管端止挡的剖视说明图
//   "fan-body-envelope" / "fan-tabs-envelope" 输出风机参考包络的分件
//   "tube-preview" / "y-tee-preview" 输出交互预览用的局部参考件
//   "m3-clamp-hardware" 输出交互预览用的 M3 参考五金

include <fan-nozzle-parameters.scad>

part = "nozzle";
show_hardware = false;
// part=tip45 用于导出完整 Ø45 主体；默认 nozzle 为 42.5 mm。
// 48 mm 是现有硬管内径，不能在当前 Ø47 外径细喷嘴中作为内径。
fn_tip_id = part == "tip45" ? 45.0 : fn_tip_id_default;
fn_tip_core_seat_id_effective = part == "tip45" ? fn_tip_id : fn_tip_core_seat_id;
fn_tip_core_id = part == "tip-core34" ? 34.0 :
    part == "tip-core36" ? 36.0 :
    part == "tip-core38" ? 38.0 :
    part == "tip-core40" ? 40.0 : fn_tip_core_ids[0];
assert(fn_tip_id > 0 && fn_tip_id < fn_tip_outer_d);
assert(part != "tip-core34" && part != "tip-core36" &&
    part != "tip-core38" && part != "tip-core40" ||
    (fn_tip_core_id > 0 && fn_tip_core_id < fn_tip_core_od));

function fn_polar(r, a) = [r * cos(a), r * sin(a)];

module fn_ring(z, h, od, id) {
    difference() {
        translate([0, 0, z]) cylinder(h=h, d=od, $fn=fn_fn);
        translate([0, 0, z - fn_eps])
            cylinder(h=h + 2 * fn_eps, d=id, $fn=fn_fn);
    }
}

module fn_sector_cut(a0, a1, r0, r1, z, h, n=18) {
    // 用线性挤出做卡口的环向锁止槽，避免 rotate_extrude 的剖面方向歧义。
    translate([0, 0, z])
        linear_extrude(height=h)
            polygon(points=concat(
                [for (i=[0:n]) fn_polar(r0, a0 + (a1-a0) * i/n)],
                [for (i=[n:-1:0]) fn_polar(r1, a0 + (a1-a0) * i/n)]
            ));
}

module fn_spigot_witness_grooves() {
    // 这些浅环槽在透明硬管内可见，标出喷嘴末端实际被硬管覆盖的长程刻度。
    for (overlap=fn_spigot_overlap_marks)
        translate([0, 0, fn_spigot_z0 + fn_spigot_l - overlap])
            cylinder(
                h=fn_spigot_mark_h,
                d=fn_spigot_od + 2 * fn_spigot_mark_radial_depth,
                $fn=fn_fn
            );
}

module fn_helical_thread_ridge(z0, length, base_r, height, pitch) {
    // 三角牙型的连续螺旋凸棱：用于芯子的外螺纹，也用于主体的内螺纹刀具。
    // 凸棱根部压入基体 0.02 mm，避免只在切平面上接触而留下非流形边。
    translate([0, 0, z0])
        linear_extrude(
            height=length,
            twist=360 * length / pitch,
            slices=ceil(length / pitch * fn_tip_core_thread_slices_per_turn),
            convexity=10
        )
            polygon(points=[
                [base_r - fn_eps, -pitch * 0.32],
                [base_r + height, 0],
                [base_r - fn_eps, pitch * 0.32]
            ]);
}

module fn_tip_core_thread_cut() {
    // 主体内孔基准为 Ø42.5；螺纹槽最高到 Ø43.6，仍保留约 1.7 mm 外壁。
    fn_helical_thread_ridge(
        fn_tip_core_thread_z0,
        fn_tip_core_thread_l,
        fn_tip_id / 2,
        fn_tip_core_thread_groove_id / 2 - fn_tip_id / 2,
        fn_tip_core_thread_pitch
    );
}

module fn_tip_core_thread_ridge() {
    // 芯子外圆基准为 Ø42；外螺纹大径约 Ø43.0。
    fn_helical_thread_ridge(
        fn_tip_core_thread_z0,
        fn_tip_core_thread_l,
        fn_tip_core_od / 2,
        fn_tip_core_thread_height,
        fn_tip_core_thread_pitch
    );
}

module fn_sleeve_inspection_slot() {
    for (overlap=fn_spigot_overlap_marks)
        rotate([0, 0, fn_sleeve_inspection_slot_angle])
            translate([
                fn_sleeve_id/2 - 0.25,
                -fn_sleeve_inspection_slot_w/2,
                fn_spigot_z0 + fn_spigot_l - overlap
                    - fn_sleeve_inspection_window_l/2
            ])
                cube([
                    fn_sleeve_od/2 + 4,
                    fn_sleeve_inspection_slot_w,
                    fn_sleeve_inspection_window_l
                ]);
}

module fn_sleeve_scale_marks() {
    // 外部短刻线与透明管内的长程重叠环槽一一对应。
    for (overlap=fn_spigot_overlap_marks)
        rotate([0, 0, fn_sleeve_scale_angle])
            translate([
                fn_sleeve_od/2 - 0.2,
                -fn_sleeve_scale_mark_w/2,
                fn_spigot_z0 + fn_spigot_l - overlap
                    - fn_sleeve_scale_mark_h/2
            ])
                cube([
                    1.0,
                    fn_sleeve_scale_mark_w,
                    fn_sleeve_scale_mark_h
                ]);
}

module fn_radial_window(angle, z0, z1) {
    // 轴向插入窗：锁扣沿 +Z 插入，再旋转到环向锁止槽。
    rotate([0, 0, angle])
        translate([
            fn_fan_socket_id/2 - 0.65,
            -fn_fan_lug_window_tangential/2,
            z0
        ])
            cube([
                fn_fan_outlet_od/2 + fn_fan_lug_radial + fn_fan_window_outer_clearance
                    - (fn_fan_socket_id/2 - 0.65),
                fn_fan_lug_window_tangential,
                z1-z0
            ]);
}

module fn_bayonet_cuts() {
    for (angle=fn_fan_lug_angles) {
        fn_radial_window(
            angle,
            -fn_eps,
            fn_fan_lug_end_z + fn_fan_bayonet_axial_clearance
        );
        fn_sector_cut(
            angle,
            angle + fn_fan_lock_turn_deg,
            fn_fan_socket_id/2 - 0.65,
            fn_fan_socket_id/2 + fn_fan_lug_radial + fn_fan_lock_radial_clearance,
            fn_fan_lug_start_z - fn_fan_bayonet_axial_clearance,
            fn_fan_lug_axial + 2 * fn_fan_bayonet_axial_clearance
        );
    }
}

module fn_outer_profile() {
    union() {
        // 风机卡口与主锥体使用一个连续外轮廓：保留 Ø86 卡口包络，
        // 再用相切肩部接回主锥体，避免 z=30 处出现环形平台或端面拼接。
        fn_fan_collar_cone_outer();

        // 伸入硬管的细喷嘴。
        translate([0, 0, fn_spigot_z0])
            cylinder(h=fn_spigot_l, d=fn_spigot_od, $fn=fn_fn);

        // 外套筒根部到套筒本体使用一个连续外轮廓：Hermite 过渡与主锥体、
        // 套筒外壁两端相切，并与主锥体重叠 20 mm，避免边缘连接和重复端面。
        fn_sleeve_transition_outer();

        fn_clamp_ears();
        fn_sleeve_scale_marks();
    }
}

module fn_fan_collar_cone_outer() {
    // 这是完整的“卡口圆柱 + 相切过渡 + 主锥体”旋转实体，
    // 不是三个只靠边缘接触的独立圆柱。过渡末端与原主锥体
    // 在 z=44 mm 处相切，且整个过渡始终位于主锥体外侧。
    rotate_extrude($fn=fn_fn)
        polygon(points=concat(
            [
                [fn_fan_collar_transition_axis_clearance_r, 0],
                [fn_fan_collar_od/2, 0],
                [fn_fan_collar_od/2, fn_fan_collar_transition_z0]
            ],
            [for (i=[1:24])
                [
                    fn_fan_collar_transition_radius(i/24),
                    fn_fan_collar_transition_z0 +
                        fn_fan_collar_transition_l * i/24
                ]],
            [for (i=[1:24])
                [
                    fn_cone_outer_d_at(
                        fn_fan_collar_transition_z1 +
                            (fn_cone_z1 - fn_fan_collar_transition_z1) * i/24
                    ) / 2,
                    fn_fan_collar_transition_z1 +
                        (fn_cone_z1 - fn_fan_collar_transition_z1) * i/24
                ]],
            [[fn_fan_collar_transition_axis_clearance_r, fn_cone_z1]]
        ));
}

module fn_sleeve_transition_outer() {
    // 旋转挤出的是完整的“过渡 + 外套筒”实体，后续再由
    // fn_inner_profile/fn_sleeve_clearance_space 切出风道和管子间隙；
    // 因此根部保留整圈材料，且 z=94 没有两个独立端面重叠。
    rotate_extrude($fn=fn_fn)
        polygon(points=concat(
            [[fn_sleeve_transition_axis_clearance_r, fn_sleeve_transition_z0]],
            [for (i=[0:24])
                [
                    fn_sleeve_transition_radius(i/24),
                    fn_sleeve_transition_z0 + fn_sleeve_transition_l * i/24
                ]],
            [
                [fn_sleeve_od/2, fn_sleeve_z0 + fn_sleeve_l],
                [fn_sleeve_transition_axis_clearance_r, fn_sleeve_z0 + fn_sleeve_l]
            ]
        ));
}

module fn_sleeve_clearance_space() {
    // 套筒的内腔必须是“中心内插段之外的环形间隙”。
    // 不能用一个完整的 Ø50.8 圆柱直接切除，否则会把 Ø47 内插段也切掉。
    if (fn_sleeve_z0 < fn_spigot_z0)
        translate([0, 0, fn_sleeve_z0 - fn_eps])
            cylinder(
                h=fn_spigot_z0 - fn_sleeve_z0 + 2 * fn_eps,
                d=fn_sleeve_id,
                $fn=fn_fn
            );

    if (max(fn_sleeve_z0, fn_spigot_z0) <
        min(fn_sleeve_z0 + fn_sleeve_l, fn_spigot_z0 + fn_spigot_l))
        translate([
            0,
            0,
            max(fn_sleeve_z0, fn_spigot_z0) - fn_eps
        ])
            difference() {
                cylinder(
                    h=min(fn_sleeve_z0 + fn_sleeve_l, fn_spigot_z0 + fn_spigot_l)
                        - max(fn_sleeve_z0, fn_spigot_z0) + 2 * fn_eps,
                    d=fn_sleeve_id,
                    $fn=fn_fn
                );
                translate([0, 0, -fn_eps])
                    cylinder(
                        h=min(fn_sleeve_z0 + fn_sleeve_l, fn_spigot_z0 + fn_spigot_l)
                            - max(fn_sleeve_z0, fn_spigot_z0) + 4 * fn_eps,
                        d=fn_spigot_od + 2 * fn_eps,
                        $fn=fn_fn
                    );
            }

    if (fn_sleeve_z0 + fn_sleeve_l > fn_spigot_z0 + fn_spigot_l)
        translate([
            0,
            0,
            fn_spigot_z0 + fn_spigot_l - fn_eps
        ])
            cylinder(
                h=fn_sleeve_z0 + fn_sleeve_l - fn_spigot_z0 - fn_spigot_l
                    + 2 * fn_eps,
                d=fn_sleeve_id,
                $fn=fn_fn
            );
}

module fn_inner_profile() {
    union() {
        // 入口倒角：帮助风机端面插入，不改变锁止位置。
        translate([0, 0, -fn_eps])
            cylinder(
                h=fn_fan_entry_chamfer_h + fn_eps,
                d1=fn_fan_socket_id + 2 * fn_fan_entry_chamfer_h,
                d2=fn_fan_socket_id,
                $fn=fn_fn
            );
        translate([0, 0, fn_fan_entry_chamfer_h-fn_eps])
            cylinder(
                h=fn_fan_face_z-fn_fan_entry_chamfer_h+2*fn_eps,
                d=fn_fan_socket_id,
                $fn=fn_fn
            );

        // 风机出口面后方的连续收缩段；最后 2 mm 留出芯子入口外肩的座位。
        translate([0, 0, fn_cone_z0-fn_eps])
            cylinder(
                h=fn_tip_core_seat_z0-fn_cone_z0+2*fn_eps,
                d1=fn_fan_outlet_id + 0.4,
                d2=fn_tip_core_seat_id_effective,
                $fn=fn_fn
            );
        translate([0, 0, fn_tip_core_seat_z0-fn_eps])
            cylinder(
                h=fn_tip_core_seat_l+2*fn_eps,
                d=fn_tip_core_seat_id_effective,
                $fn=fn_fn
            );

        // 细喷嘴内孔与硬管内孔同轴连通。
        translate([0, 0, fn_spigot_z0-fn_eps])
            cylinder(h=fn_spigot_l+2*fn_eps, d=fn_tip_id, $fn=fn_fn);

        // 硬管外侧滑入夹套的环形空间；中心细喷嘴由 fn_sleeve_clearance_space 保留。
        fn_sleeve_clearance_space();

        fn_spigot_witness_grooves();
        if (part != "tip45") fn_tip_core_thread_cut();
        fn_sleeve_split_cut();
        fn_sleeve_inspection_slot();
        fn_clamp_fastener_cuts();
    }
}

module fn_sleeve_split_cut() {
    // 仅切套筒壁，不贯穿中心喷嘴；底部留 4 mm 环形桥，增强根部强度。
    translate([
        fn_sleeve_id/2 - 0.25,
        -fn_sleeve_split_gap/2,
        fn_sleeve_split_start
    ])
        cube([
            fn_sleeve_od/2 + 4,
            fn_sleeve_split_gap,
            fn_sleeve_z0 + fn_sleeve_l - fn_sleeve_split_start + fn_eps
        ]);
}

module fn_y_cylinder(x, y, z, h, d) {
    translate([x, y, z])
        rotate([90, 0, 0])
            cylinder(h=h, d=d, center=true, $fn=fn_fn);
}

module fn_y_hex(x, y, z, h, af) {
    translate([x, y, z])
        rotate([90, 0, 0])
            cylinder(h=h, r=af/sqrt(3), center=true, $fn=6);
}

module fn_clamp_ears() {
    // 耳朵位于 +X 侧，螺丝沿 Y 方向；不会改变风道截面。
    translate([
        fn_sleeve_od/2 - 1,
        fn_sleeve_split_gap/2,
        fn_clamp_z - fn_clamp_ear_h/2
    ])
        cube([fn_clamp_ear_w, fn_clamp_ear_d, fn_clamp_ear_h]);
    translate([
        fn_sleeve_od/2 - 1,
        -fn_sleeve_split_gap/2 - fn_clamp_ear_d,
        fn_clamp_z - fn_clamp_ear_h/2
    ])
        cube([fn_clamp_ear_w, fn_clamp_ear_d, fn_clamp_ear_h]);
}

module fn_clamp_fastener_cuts() {
    // 通孔、正侧螺钉头沉孔、负侧 M3 螺母六角槽。
    fn_y_cylinder(
        fn_clamp_bolt_x, 0, fn_clamp_z,
        2 * (fn_clamp_ear_d + fn_sleeve_split_gap/2 + fn_eps),
        fn_clamp_clearance_d
    );
    fn_y_cylinder(
        fn_clamp_bolt_x,
        fn_sleeve_split_gap/2 + fn_clamp_ear_d - fn_clamp_head_depth/2,
        fn_clamp_z,
        fn_clamp_head_depth + fn_eps,
        fn_clamp_head_d
    );
    fn_y_hex(
        fn_clamp_bolt_x,
        -fn_sleeve_split_gap/2 - fn_clamp_ear_d + fn_clamp_nut_depth/2,
        fn_clamp_z,
        fn_clamp_nut_depth + fn_eps,
        fn_clamp_nut_af
    );
}

module fn_tip_core(core_id=fn_tip_core_id) {
    // 可拆换风嘴芯：外径恒定 42 mm，入口有 43.2 mm 外肩，
    // 内部为 Ø40 直段 -> 收缩锥 -> 目标细口径直段。
    // 入口外肩顶在主体内台阶上；入口后靠外螺纹旋入主体内螺纹锁紧。
    difference() {
        union() {
            translate([0, 0, fn_tip_core_z0])
                cylinder(
                    h=fn_tip_core_flange_l,
                    d=fn_tip_core_flange_od,
                    $fn=fn_fn
                );
            translate([0, 0, fn_tip_core_z0 + fn_tip_core_flange_l])
                cylinder(
                    h=fn_tip_core_l - fn_tip_core_flange_l,
                    d=fn_tip_core_od,
                    $fn=fn_fn
                );
            fn_tip_core_thread_ridge();
        }

        if (core_id >= fn_tip_core_inlet_id) {
            // Ø40 是粗段的同径特例；合并成一次完整切孔，避免重合
            // cylinder 的布尔边在 OpenSCAD 中形成非流形边。
            translate([0, 0, fn_tip_core_z0-fn_eps])
                cylinder(
                    h=fn_tip_core_l+2*fn_eps,
                    d=core_id,
                    $fn=fn_fn
                );
        } else {
            // 入口外肩之后保持一段不变的粗内径，承担导流和安装长度。
            translate([0, 0, fn_tip_core_z0-fn_eps])
                cylinder(
                    h=fn_tip_core_mount_l+fn_eps,
                    d=fn_tip_core_inlet_id,
                    $fn=fn_fn
                );
            // 只在内部做锥形收缩，外部导向直径不变。
            translate([0, 0, fn_tip_core_z0+fn_tip_core_mount_l-fn_eps])
                cylinder(
                    h=fn_tip_core_taper_l+2*fn_eps,
                    d1=fn_tip_core_inlet_id,
                    d2=core_id,
                    $fn=fn_fn
                );
            // 末端保留短直段，避免锥面直接切到出口边缘。
            translate([
                0,
                0,
                fn_tip_core_z0 + fn_tip_core_mount_l + fn_tip_core_taper_l - fn_eps
            ])
                cylinder(
                    h=fn_tip_core_exit_l+2*fn_eps,
                    d=core_id,
                    $fn=fn_fn
                );
        }

        // 出口端两处对置的内侧驱动缺口：硬管退开后可用薄片工具/尖嘴钳
        // 插入缺口旋入或旋出芯子；缺口不依赖主体外壁上的螺丝。
        for (angle=[0, 180])
            rotate([0, 0, angle])
                translate([
                    core_id/2-0.10,
                    -1.5,
                    fn_tip_core_z0+fn_tip_core_l-4.0
                ])
                    cube([
                        fn_tip_core_od/2 - core_id/2 + 1.60,
                        3.0,
                        4.0+fn_eps
                    ]);
    }
}

module fn_nozzle() {
    difference() {
        fn_outer_profile();
        union() {
            fn_inner_profile();
            fn_bayonet_cuts();
        }
    }
}

module fn_fan_envelope() {
    fn_fan_body_envelope();
    fn_fan_tabs_envelope();
}

module fn_fan_body_envelope() {
    // 风机是参考包络，不属于打印件；锁扣用两条凸台表示。
    color([0.55, 0.58, 0.62, 0.45])
        cylinder(h=fn_fan_face_z, d=fn_fan_outlet_od, $fn=fn_fn);
}

module fn_fan_tabs_envelope() {
    for (angle=fn_fan_lug_angles)
        rotate([0, 0, angle])
            translate([
                fn_fan_outlet_od/2 - fn_fan_lug_radial,
                -fn_fan_lug_tangential/2,
                fn_fan_lug_start_z
            ])
                color([0.85, 0.35, 0.15, 0.75])
                    cube([
                        fn_fan_lug_radial,
                        fn_fan_lug_tangential,
                        fn_fan_lug_axial
                    ]);
}

module fn_tube_envelope(start_z=fn_sleeve_z0 - 35, length=100) {
    color([0.20, 0.70, 0.85, 0.28])
        translate([0, 0, start_z])
            difference() {
                cylinder(h=length, d=fn_tube_od, $fn=fn_fn);
                translate([0, 0, -fn_eps])
                    cylinder(h=length+2*fn_eps, d=fn_tube_id, $fn=fn_fn);
            }
}

module fn_tube_preview_local() {
    // 交互装配预览的局部管件：原点在管子靠风嘴一端。
    fn_tube_envelope(0, fn_preview_tube_l);
}

module fn_m3_clamp_hardware() {
    // 仅用于交互装配说明：M3 螺杆、圆柱头和六角螺母的名义包络。
    color([0.20, 0.24, 0.30, 1.0]) {
        fn_y_cylinder(fn_clamp_bolt_x, 0, fn_clamp_z, 18, 2.8);
        fn_y_cylinder(fn_clamp_bolt_x, 8.0, fn_clamp_z, 3.0, 5.5);
        fn_y_hex(fn_clamp_bolt_x, -8.0, fn_clamp_z, 3.2, fn_clamp_nut_af);
    }
}

module fn_y_tee_branch(z0, angle, length, d) {
    // 分支沿 +X 方向偏转；局部原点在与主管轴线的交汇中心。
    translate([0, 0, z0])
        rotate([0, angle, 0])
            cylinder(h=length, d=d, $fn=fn_fn);
}

module fn_y_tee_outer() {
    union() {
        // 下承口从 frame 向下延伸，硬管末端在 frame 处顶到内止位。
        translate([0, 0, -fn_y_tee_socket_l])
            cylinder(
                h=fn_y_tee_socket_l + fn_y_tee_main_up_l,
                d=fn_y_tee_outer_d,
                $fn=fn_fn
            );
        fn_y_tee_branch(
            fn_y_tee_branch_start_z,
            fn_y_tee_branch_angle,
            fn_y_tee_branch_l,
            fn_y_tee_outer_d
        );

        // 仅为预览突出三个开口的端面，不代表原机真实法兰。
        translate([0, 0, fn_y_tee_main_up_l - fn_y_tee_port_lip_l])
            cylinder(h=fn_y_tee_port_lip_l, d=fn_y_tee_port_lip_d, $fn=fn_fn);
        translate([0, 0, fn_y_tee_branch_start_z])
            rotate([0, fn_y_tee_branch_angle, 0])
                cylinder(h=fn_y_tee_port_lip_l, d=fn_y_tee_port_lip_d, $fn=fn_fn);
        translate([0, 0, -fn_y_tee_socket_l])
            cylinder(h=fn_y_tee_port_lip_l, d=fn_y_tee_port_lip_d, $fn=fn_fn);
    }
}

module fn_y_tee_inner() {
    union() {
        // 管子 OD50 插入承口；上到止位后收回到连续 ID48 风道。
        translate([0, 0, -fn_y_tee_socket_l - fn_eps])
            cylinder(
                h=fn_y_tee_socket_l + fn_eps,
                d=fn_y_tee_socket_id,
                $fn=fn_fn
            );
        translate([0, 0, -fn_eps])
            cylinder(
                h=fn_y_tee_main_up_l + 2 * fn_eps,
                d=fn_y_tee_bore_id,
                $fn=fn_fn
            );
        fn_y_tee_branch(
            fn_y_tee_branch_start_z - fn_eps,
            fn_y_tee_branch_angle,
            fn_y_tee_branch_l + 2 * fn_eps,
            fn_y_tee_bore_id
        );
    }
}

module fn_y_tee_preview_local() {
    // 按工程样品图保留“直通主管 + 上扬斜支管 + 三个承口”的关系。
    // 外部包络、真实止位和壁厚仍未测量；这是交互装配参考体，不是打印件。
    color([0.90, 0.68, 0.10, 0.76])
        difference() {
            fn_y_tee_outer();
            fn_y_tee_inner();
        }
}

module fn_y_mouth_preview_local() {
    // 旧选择器保留兼容性，但现在输出完整的 Y/斜三通参考体。
    fn_y_tee_preview_local();
}

module fn_section() {
    intersection() {
        fn_nozzle();
        translate([-100, -100, -1]) cube([100, 200, fn_sleeve_z0+fn_sleeve_l+2]);
    }
}

module fn_core_fit_section() {
    // 仅用于确认入口外肩、恒定外径导向、内部收缩锥和旋入式螺纹；不作为打印件导出。
    intersection() {
        union() {
            color([0.18, 0.50, 0.78, 1.0]) fn_nozzle();
            color([0.20, 0.80, 0.24, 0.90]) fn_tip_core(40);
        }
        translate([-100, -100, -1])
            cube([100, 200, fn_sleeve_z0+fn_sleeve_l+2]);
    }
}

module fn_core_thread_detail() {
    // 螺纹局部爆炸审查图：主体保留一半剖面，另一个 Ø40 芯沿 +X 拉出，
    // 让内螺纹槽、芯子外螺纹和入口外肩的锁紧关系同时可见。
    intersection() {
        union() {
            intersection() {
                color([0.18, 0.50, 0.78, 1.0]) fn_nozzle();
                translate([-100, -100, fn_tip_core_thread_z0-8])
                    cube([100, 200, fn_tip_core_thread_l+16]);
            }
            intersection() {
                color([0.20, 0.80, 0.24, 0.92]) fn_tip_core(40);
                translate([-100, -100, fn_tip_core_thread_z0-8])
                    cube([100, 200, fn_tip_core_thread_l+16]);
            }
            color([0.20, 0.80, 0.24, 0.96])
                translate([34, 0, 0])
                    fn_tip_core(40);
        }
        translate([-100, -100, fn_tip_core_thread_z0-8])
            cube([240, 200, fn_tip_core_thread_l+16]);
    }
}

module fn_core_taper_section(core_id=34) {
    // 只显示芯子的一半，突出外径恒定、入口粗直段、内部收缩锥和出口直段。
    intersection() {
        color([0.20, 0.80, 0.24, 1.0]) fn_tip_core(core_id);
        translate([-100, -100, fn_tip_core_z0-1])
            cube([100, 200, fn_tip_core_l+2]);
    }
}

module fn_interface_section() {
    // 仅用于装配说明，不是打印件：沿管轴的纵向剖面保留 +Y 半侧，
    // 让“外套筒—亚克力管壁—内插段”三层关系直接可见。
    // 蓝色=打印件；青色=亚克力管；风机卡口锁扣包络仍由 fn_nozzle() 的卡槽体现。
    intersection() {
        union() {
            color([0.12, 0.42, 0.90, 1.0])
                fn_nozzle();
            color([0.05, 0.72, 0.86, 1.0])
                fn_tube_envelope(fn_sleeve_z0 - 24, 104);
        }
        translate([-100, 0, fn_sleeve_z0 - 10])
            cube([200, 100, 90]);
    }
}

module fn_y_tee_interface_section() {
    // Y 三通承口局部剖视：黄色为三通，青色为 OD50 管子；管端在 z=0
    // 顶到承口内肩，内腔从承口 Ø51 收回到连续 Ø48 风道。
    intersection() {
        union() {
            color([0.90, 0.68, 0.10, 1.0])
                difference() {
                    fn_y_tee_outer();
                    fn_y_tee_inner();
                }
            color([0.05, 0.72, 0.86, 1.0])
                fn_tube_envelope(-55, 55);
        }
        translate([-100, -100, -30])
            cube([100, 200, 110]);
    }
}

module fn_assembly() {
    color([0.18, 0.50, 0.78, 1.0]) fn_nozzle();
    fn_fan_envelope();
    fn_tube_envelope();
}

module fn_adjustment_view() {
    // 固定透明硬管和 Y 口，分别显示风嘴的近端/远端位置。
    // 这只是审查视图，不是打印件；真实 Y 口位置仍需实测替换。
    fn_tube_envelope(fn_sleeve_z0 - 35, 160);
    translate([0, 0, fn_sleeve_z0 - 35 + 160])
        fn_y_tee_preview_local();
    color([0.12, 0.42, 0.90, 0.92]) fn_nozzle();
    color([0.95, 0.42, 0.12, 0.34])
        translate([0, 0, 20]) fn_nozzle();
    color([0.20, 0.80, 0.24, 0.85])
        translate([0, 0, 0]) fn_tip_core(40);
}

if (part == "nozzle" || part == "tip45") fn_nozzle();
else if (part == "tip-core34" || part == "tip-core36" ||
    part == "tip-core38" || part == "tip-core40") fn_tip_core();
else if (part == "section") fn_section();
else if (part == "assembly") fn_assembly();
else if (part == "fan-envelope") fn_fan_envelope();
else if (part == "fan-body-envelope") fn_fan_body_envelope();
else if (part == "fan-tabs-envelope") fn_fan_tabs_envelope();
else if (part == "tube-envelope") fn_tube_envelope();
else if (part == "tube-preview") fn_tube_preview_local();
else if (part == "y-tee-preview") fn_y_tee_preview_local();
else if (part == "y-mouth-preview") fn_y_mouth_preview_local();
else if (part == "m3-clamp-hardware") fn_m3_clamp_hardware();
else if (part == "adjustment-view") fn_adjustment_view();
else if (part == "core-fit-section") fn_core_fit_section();
else if (part == "core-thread-detail") fn_core_thread_detail();
else if (part == "core-taper-section") fn_core_taper_section();
else if (part == "interface-section") fn_interface_section();
else if (part == "y-tee-interface-section") fn_y_tee_interface_section();
else assert(false, "Unknown part selector");
