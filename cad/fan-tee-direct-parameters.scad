// 另一款风机 -> Y 三通直插连接件
// 单位：mm；气流方向 +Z；风机卡口在 -Z 侧，三通直插段在 +Z 侧。
//
// 已知实测输入：
//   - 新风机出风口外径 Ø41；两侧对置 L 形卡口槽
//   - 轴向反向槽总长 18.5；转向弧长约 20；槽宽约 7 / 6.5
//   - Y 三通承口名义内径 Ø50
//
// 仍需实测：新风机出风口内径、L 槽相对端面的精确基准、三通真实止挡深度。

// ---- 风机外部卡口 ----
dt_fan_outlet_od = 41.0;
// 未提供风机内径；35 mm 只是候选气道参数，首件前应替换为实测值。
dt_fan_outlet_id_assumed = 35.0;
dt_fan_socket_radial_clearance = 0.45;
dt_fan_socket_id =
    dt_fan_outlet_od + 2 * dt_fan_socket_radial_clearance;
dt_fan_socket_outer_d = 48.0;

// 风机 L 形槽：以风机出风端面为 z=0，反向延伸位于 z<0。
dt_fan_bayonet_count = 2;
dt_fan_bayonet_angles = [0, 180];
dt_fan_bayonet_axial_back_l = 18.5;
dt_fan_bayonet_turn_start_back = 7.0;
dt_fan_bayonet_turn_arc_l = 20.0;
dt_fan_bayonet_axial_slot_w = 7.0;
dt_fan_bayonet_turn_slot_w = 6.5;
dt_fan_bayonet_turn_angle_deg =
    dt_fan_bayonet_turn_arc_l / (PI * dt_fan_outlet_od) * 360;
// 圆饼凸起直径比两段槽宽各留约 0.25 mm 以上的名义余量。
dt_fan_bayonet_button_d = 6.0;
dt_fan_bayonet_button_radial_h = 1.60;
dt_fan_bayonet_button_embed = 0.80;
dt_fan_socket_back_z = -dt_fan_bayonet_axial_back_l;
dt_fan_face_z = 0.0;
dt_fan_bayonet_button_z = -dt_fan_bayonet_turn_start_back;

// ---- 三通直插段 ----
dt_tee_bore_id = 50.0;
// Ø50 是三通名义内径；FDM 首件默认给每侧 0.40 mm 径向装配间隙。
// 如果量到的是可用实测内径，可只改 dt_tee_bore_id；不要在切片器中缩放。
dt_tee_fit_radial_clearance = 0.40;
dt_tee_spigot_od =
    dt_tee_bore_id - 2 * dt_tee_fit_radial_clearance;
dt_wall = 3.0;
dt_tee_spigot_id = dt_tee_spigot_od - 2 * dt_wall;
dt_tee_spigot_l = 25.0;
dt_tee_spigot_z1 = 80.0;
dt_tee_spigot_z0 = dt_tee_spigot_z1 - dt_tee_spigot_l;
dt_tee_spigot_leadin_l = 2.0;
dt_tee_spigot_leadin_z0 = dt_tee_spigot_z1 - dt_tee_spigot_leadin_l;
dt_tee_spigot_leadin_od = dt_tee_spigot_od - 1.0;

// 连接件主体外径按 Ø50 名义包络；风机端用 Ø48 外径渐变接入。
dt_body_outer_d = 50.0;
dt_socket_to_body_l = 30.0;
dt_socket_to_body_z0 = dt_fan_socket_back_z;
dt_socket_to_body_z1 = dt_socket_to_body_z0 + dt_socket_to_body_l;
dt_body_to_spigot_transition_l = 4.0;
dt_body_to_spigot_transition_z0 =
    dt_tee_spigot_z0 - dt_body_to_spigot_transition_l;

// ---- 连续内风道 ----
// 三通侧是风嘴芯的装入方向。芯子全长保持 Ø40 导向外径，
// 从 Ø42.4 导入段进入 Ø40.6 导向/螺纹基孔；不设置无法通过导向孔的外法兰。
dt_bore_expand_z1 = 30.0;
dt_air_bore_id = 42.4;
dt_core_seat_id = 42.4;
dt_core_guide_id = 40.6;
dt_thread_bore_id = dt_core_guide_id;

// ---- 可替换、旋入式出风口芯 ----
// 芯子从三通侧插入；主体内螺纹与芯子外螺纹啮合，4 mm/圈改变伸出量。
dt_core_od = 40.0;
dt_core_ids = [34.0, 36.0, 38.0];
// 外径为 Ø40 时，入口粗直段不能也做成 Ø40，否则该段壁厚为零。
// 统一采用 Ø38 粗直段，随后收缩到 Ø34/36/38 的可替换出口。
dt_core_inlet_id = 38.0;
dt_core_mount_l = 22.0;
dt_core_taper_l = 15.0;
dt_core_exit_l = 8.0;
dt_core_l = dt_core_mount_l + dt_core_taper_l + dt_core_exit_l;
// 取消原先 Ø42 后端法兰：它大于 Ø40.6 导向孔，从三通侧装入时会被卡住。
// 芯子从局部 z=0 开始就是 Ø40 连续导向外径，前 4 mm 留作无螺纹起牙导向。
dt_core_flange_od = dt_core_od;
dt_core_flange_l = 0.0;
dt_core_thread_lead_l = 4.0;
dt_core_thread_rel_z0 = dt_core_thread_lead_l;
dt_core_thread_l = 16.0;
dt_core_thread_pitch = 4.0;
dt_core_thread_height = 0.90;
dt_core_thread_major_od =
    dt_core_od + 2 * dt_core_thread_height;
// 先定轴向牙型，再用同相位螺旋生成公牙/母沟。
// 根宽约 72% 牙距、平顶约 28% 牙距，避免尖针状或薄片状牙型。
dt_core_thread_root_width_fraction = 0.72;
dt_core_thread_crest_width_fraction = 0.28;
dt_core_thread_female_axial_clearance = 0.18;
dt_body_thread_z0 = 52.0;
dt_body_thread_groove_id = 42.8;
dt_body_thread_radial_clearance =
    (dt_body_thread_groove_id - dt_core_thread_major_od) / 2;
dt_core_nominal_z0 =
    dt_body_thread_z0 - dt_core_thread_rel_z0;
// 这段 Ø42.4 不是法兰座，而是从大气道到 Ø40.6 导向孔的入口过渡段。
dt_core_seat_z0 = dt_core_nominal_z0;
dt_core_seat_l = 2.0;
dt_bore_to_tee_z0 = dt_body_thread_z0 + dt_core_thread_l;
dt_core_adjustment_range = 8.0;
dt_core_thread_slices_per_turn = 64;

// ---- 打印 / 预览 ----
dt_eps = 0.02;
dt_fn = 96;
dt_reference_fan_l = dt_fan_bayonet_axial_back_l;
dt_reference_tee_outer_d = 60.0;

function dt_inner_bore_d_at(z) =
    z <= dt_bore_expand_z1
        ? dt_fan_outlet_id_assumed +
            (dt_air_bore_id - dt_fan_outlet_id_assumed) *
            (z - dt_fan_face_z) /
            (dt_bore_expand_z1 - dt_fan_face_z)
        : z <= dt_core_seat_z0
            ? dt_air_bore_id
            : z <= dt_core_seat_z0 + dt_core_seat_l
                ? dt_core_seat_id
                : z <= dt_body_thread_z0
                    ? dt_core_seat_id +
                        (dt_core_guide_id - dt_core_seat_id) *
                        (z - dt_core_seat_z0 - dt_core_seat_l) /
                        (dt_body_thread_z0 - dt_core_seat_z0 - dt_core_seat_l)
                    : z <= dt_bore_to_tee_z0
                        ? dt_thread_bore_id
                        : dt_thread_bore_id +
                            (dt_tee_spigot_id - dt_thread_bore_id) *
                            (z - dt_bore_to_tee_z0) /
                            (dt_tee_spigot_z1 - dt_bore_to_tee_z0);

assert(dt_fan_outlet_od > 0);
assert(dt_fan_outlet_id_assumed > 0);
assert(dt_fan_outlet_id_assumed < dt_fan_outlet_od);
assert(dt_fan_socket_id > dt_fan_outlet_od);
assert(dt_fan_socket_outer_d > dt_fan_socket_id + 2 * 2.0);
assert(dt_fan_bayonet_count == len(dt_fan_bayonet_angles));
assert(dt_fan_bayonet_axial_back_l > dt_fan_bayonet_turn_start_back);
assert(dt_fan_bayonet_turn_arc_l > 0);
assert(dt_fan_bayonet_axial_slot_w > dt_fan_bayonet_button_d);
assert(dt_fan_bayonet_turn_slot_w > dt_fan_bayonet_button_d);
assert(dt_fan_bayonet_button_radial_h > 0);
assert(dt_tee_bore_id > 2 * dt_tee_fit_radial_clearance);
assert(dt_tee_spigot_od < dt_tee_bore_id);
assert(dt_tee_spigot_od > dt_tee_spigot_id + 2 * dt_wall - 0.001);
assert(dt_tee_spigot_l > 0);
assert(dt_tee_spigot_z0 > dt_socket_to_body_z1);
assert(dt_tee_spigot_leadin_l > 0 && dt_tee_spigot_leadin_l < dt_tee_spigot_l);
assert(dt_air_bore_id >= dt_core_seat_id);
assert(dt_core_seat_id > dt_core_od);
assert(dt_core_guide_id > dt_core_od);
assert(dt_body_thread_groove_id > dt_thread_bore_id);
assert(dt_body_thread_groove_id > dt_core_thread_major_od);
assert(dt_body_thread_radial_clearance >= 0.15);
assert(dt_body_thread_z0 > dt_bore_expand_z1);
assert(dt_body_thread_z0 + dt_core_thread_l < dt_tee_spigot_z1);
assert(dt_core_thread_lead_l > 0);
assert(dt_core_flange_l == 0);
assert(dt_core_flange_od == dt_core_od);
assert(dt_core_seat_z0 == dt_core_nominal_z0);
assert(dt_core_nominal_z0 + dt_core_thread_rel_z0 == dt_body_thread_z0);
assert(dt_core_od < dt_core_guide_id);
assert(dt_core_seat_id > dt_core_od);
assert(dt_core_mount_l + dt_core_taper_l + dt_core_exit_l == dt_core_l);
assert(dt_core_thread_rel_z0 + dt_core_thread_l < dt_core_l);
assert(dt_core_thread_pitch >= 3.0 && dt_core_thread_pitch <= 5.0);
assert(dt_core_thread_height >= 0.50 && dt_core_thread_height <= 1.20);
assert(dt_core_thread_root_width_fraction > dt_core_thread_crest_width_fraction);
assert(dt_core_thread_crest_width_fraction > 0);
assert(dt_core_thread_female_axial_clearance >= 0.10);
assert(dt_core_adjustment_range >= dt_core_thread_pitch);
assert(dt_tee_spigot_z1 < 256.0);
