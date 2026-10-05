// 另一款 Ø41 风机 -> Ø50 Y 三通的直插、旋拧卡口连接件
// 打印姿态：气流轴 +Z，三通插入段朝上，风机卡口朝下/负 Z 侧。
// 这个文件是独立候选，不改写现有 Ø76 风机风嘴。

include <fan-tee-direct-parameters.scad>
include <thread-profile.scad>

part = "connector";
core_id = part == "core34" ? 34.0 :
    part == "core36" ? 36.0 :
    part == "core38" ? 38.0 : 36.0;

function dt_polar(r, a) = [r * cos(a), r * sin(a)];

module dt_outer_profile() {
    union() {
        // 风机卡口外壳：从 Ø48 渐变到主体 Ø50，不在风机端制造硬台阶。
        translate([0, 0, dt_socket_to_body_z0])
            cylinder(
                h=dt_socket_to_body_l,
                d1=dt_fan_socket_outer_d,
                d2=dt_body_outer_d,
                $fn=dt_fn
            );

        // 主体保持 Ø50 名义外包络，给内部风嘴芯留出连续导向段。
        translate([0, 0, dt_socket_to_body_z1])
            cylinder(
                h=dt_body_to_spigot_transition_z0 - dt_socket_to_body_z1,
                d=dt_body_outer_d,
                $fn=dt_fn
            );

        // 进入三通前收缩到有装配间隙的 Ø49.2 首件外径。
        translate([0, 0, dt_body_to_spigot_transition_z0])
            cylinder(
                h=dt_body_to_spigot_transition_l,
                d1=dt_body_outer_d,
                d2=dt_tee_spigot_od,
                $fn=dt_fn
            );

        translate([0, 0, dt_tee_spigot_z0])
            cylinder(
                h=dt_tee_spigot_leadin_z0 - dt_tee_spigot_z0,
                d=dt_tee_spigot_od,
                $fn=dt_fn
            );

        // 三通入口导入倒角；末端不改变内壁 Ø43.2 的基准气道。
        translate([0, 0, dt_tee_spigot_leadin_z0])
            cylinder(
                h=dt_tee_spigot_leadin_l,
                d1=dt_tee_spigot_od,
                d2=dt_tee_spigot_leadin_od,
                $fn=dt_fn
            );
    }
}

module dt_inner_bore() {
    // 风机外壳插入空腔；风机端面之后才进入真正的内风道。
    translate([0, 0, dt_fan_socket_back_z - dt_eps])
        cylinder(
            h=dt_fan_face_z - dt_fan_socket_back_z + 2 * dt_eps,
            d=dt_fan_socket_id,
            $fn=dt_fn
        );

    // 从暂定的风机内径连续扩到 Ø42.4 入口空气通道。
    translate([0, 0, dt_fan_face_z - dt_eps])
        cylinder(
            h=dt_bore_expand_z1 - dt_fan_face_z + 2 * dt_eps,
            d1=dt_fan_outlet_id_assumed,
            d2=dt_air_bore_id,
            $fn=dt_fn
        );

    // 芯子从三通侧装入；Ø42.4 入口段向 Ø40.6 导向/螺纹基孔过渡。
    translate([0, 0, dt_bore_expand_z1 - dt_eps])
        cylinder(
            h=dt_core_seat_z0 - dt_bore_expand_z1 + 2 * dt_eps,
            d=dt_air_bore_id,
            $fn=dt_fn
        );
    translate([0, 0, dt_core_seat_z0 - dt_eps])
        cylinder(
            h=dt_core_seat_l + 2 * dt_eps,
            d=dt_core_seat_id,
            $fn=dt_fn
        );
    translate([0, 0, dt_core_seat_z0 + dt_core_seat_l - dt_eps])
        cylinder(
            h=dt_body_thread_z0 - dt_core_seat_z0 - dt_core_seat_l + 2 * dt_eps,
            d1=dt_core_seat_id,
            d2=dt_core_guide_id,
            $fn=dt_fn
        );
    translate([0, 0, dt_body_thread_z0 - dt_eps])
        cylinder(
            h=dt_bore_to_tee_z0 - dt_body_thread_z0 + 2 * dt_eps,
            d=dt_thread_bore_id,
            $fn=dt_fn
        );

    // 三通插入段内径由“实际打印外径 - 2×3 mm 壁厚”定义。
    translate([0, 0, dt_bore_to_tee_z0 - dt_eps])
        cylinder(
            h=dt_tee_spigot_z1 - dt_bore_to_tee_z0 + 2 * dt_eps,
            d1=dt_core_guide_id,
            d2=dt_tee_spigot_id,
            $fn=dt_fn
        );
}

module dt_body_thread_cut() {
    // 先按公牙轴向牙型生成母沟，再增加轴向配合余量；
    // 与芯子的螺旋相位完全一致，避免只得到环槽或扁片。
    tp_helical_thread(
        dt_body_thread_z0,
        dt_core_thread_l,
        dt_thread_bore_id / 2,
        (dt_body_thread_groove_id - dt_thread_bore_id) / 2,
        dt_core_thread_pitch,
        dt_core_thread_root_width_fraction,
        dt_core_thread_crest_width_fraction,
        dt_core_thread_female_axial_clearance,
        dt_core_thread_slices_per_turn
    );
}

module dt_bayonet_buttons() {
    // 两个对置的圆饼凸起，直径 6 mm；安装时沿风机 L 槽轴向进入，
    // 到 z=-7 mm 的转向段后顺时针旋拧锁止。凸起根部嵌入壁厚，
    // 不依靠一条薄边或角点接触。
    for (angle=dt_fan_bayonet_angles)
        rotate([0, 0, angle])
            translate([
                dt_fan_socket_id / 2 - dt_fan_bayonet_button_radial_h,
                0,
                dt_fan_bayonet_button_z
            ])
                rotate([0, 90, 0])
                    cylinder(
                        h=dt_fan_bayonet_button_radial_h +
                            dt_fan_bayonet_button_embed,
                        d=dt_fan_bayonet_button_d,
                        $fn=48
                    );
}

module dt_connector() {
    // 先切出气道和主体内螺纹，再补回真正的圆饼卡口凸起；
    // 这样凸起会保留在内腔，而不是被空腔布尔切掉。
    union() {
        difference() {
            dt_outer_profile();
            union() {
                dt_inner_bore();
                dt_body_thread_cut();
            }
        }
        dt_bayonet_buttons();
    }
}

module dt_core_thread_ridge() {
    // 真实轴向平顶梯形公牙：根宽、斜牙侧、平顶，不是薄的径向切向片。
    tp_helical_thread(
        dt_core_thread_rel_z0,
        dt_core_thread_l,
        dt_core_od / 2,
        dt_core_thread_height,
        dt_core_thread_pitch,
        dt_core_thread_root_width_fraction,
        dt_core_thread_crest_width_fraction,
        0,
        dt_core_thread_slices_per_turn
    );
}

module dt_core(core_id=core_id) {
    difference() {
        union() {
            // 芯子全长都是 Ø40 导向外径；不再有无法穿过 Ø40.6 孔的后端法兰。
            cylinder(h=dt_core_l, d=dt_core_od, $fn=dt_fn);
            dt_core_thread_ridge();
        }

        if (core_id >= dt_core_inlet_id) {
            translate([0, 0, -dt_eps])
                cylinder(h=dt_core_l + 2 * dt_eps, d=core_id, $fn=dt_fn);
        } else {
            translate([0, 0, -dt_eps])
                cylinder(
                    h=dt_core_mount_l + dt_eps,
                    d=dt_core_inlet_id,
                    $fn=dt_fn
                );
            translate([0, 0, dt_core_mount_l - dt_eps])
                cylinder(
                    h=dt_core_taper_l + 2 * dt_eps,
                    d1=dt_core_inlet_id,
                    d2=core_id,
                    $fn=dt_fn
                );
            translate([
                0,
                0,
                dt_core_mount_l + dt_core_taper_l - dt_eps
            ])
                cylinder(
                    h=dt_core_exit_l + 2 * dt_eps,
                    d=core_id,
                    $fn=dt_fn
                );
        }
    }
}

// ---- 以下模块只用于几何审查，不属于打印件 ----
module dt_fan_reference() {
    color([0.55, 0.58, 0.62, 0.45])
        translate([0, 0, dt_fan_socket_back_z])
            cylinder(h=dt_reference_fan_l, d=dt_fan_outlet_od, $fn=dt_fn);
}

module dt_tee_socket_reference() {
    color([0.90, 0.68, 0.10, 0.26])
        translate([0, 0, dt_tee_spigot_z0])
            difference() {
                cylinder(h=dt_tee_spigot_l, d=dt_reference_tee_outer_d, $fn=dt_fn);
                translate([0, 0, -dt_eps])
                    cylinder(
                        h=dt_tee_spigot_l + 2 * dt_eps,
                        d=dt_tee_bore_id,
                        $fn=dt_fn
                    );
            }
}

module dt_assembly() {
    color([0.12, 0.42, 0.90, 1.0]) dt_connector();
    dt_fan_reference();
    dt_tee_socket_reference();
    color([0.20, 0.80, 0.24, 0.92])
        translate([0, 0, dt_core_nominal_z0])
            dt_core(36);
}

module dt_section() {
    intersection() {
        union() {
            color([0.12, 0.42, 0.90, 1.0]) dt_connector();
            dt_fan_reference();
            dt_tee_socket_reference();
            color([0.20, 0.80, 0.24, 0.92])
                translate([0, 0, dt_core_nominal_z0])
                    dt_core(36);
        }
        translate([-100, 0, dt_fan_socket_back_z - 2])
            cube([200, 100, dt_tee_spigot_z1 - dt_fan_socket_back_z + 4]);
    }
}

module dt_bayonet_detail() {
    intersection() {
        union() {
            color([0.12, 0.42, 0.90, 1.0]) dt_connector();
            dt_fan_reference();
        }
        // 保留半截剖面，让内壁圆饼凸起和风机外圆的相对位置可见。
        translate([-100, 0, dt_fan_socket_back_z - 2])
            cube([200, 100, 28]);
    }
}

module dt_core_thread_detail() {
    intersection() {
        union() {
            color([0.12, 0.42, 0.90, 1.0]) dt_connector();
            color([0.20, 0.80, 0.24, 0.95])
                translate([0, 0, dt_core_nominal_z0])
                    dt_core(36);
        }
        translate([-100, 0, dt_body_thread_z0 - 8])
            cube([200, 100, dt_core_thread_l + 16]);
    }
}

if (part == "connector") dt_connector();
else if (part == "core34" || part == "core36" || part == "core38") dt_core();
else if (part == "assembly") dt_assembly();
else if (part == "section") dt_section();
else if (part == "bayonet-detail") dt_bayonet_detail();
else if (part == "core-thread-detail") dt_core_thread_detail();
else if (part == "fan-reference") dt_fan_reference();
else if (part == "tee-reference") dt_tee_socket_reference();
else assert(false, "Unknown part selector");
