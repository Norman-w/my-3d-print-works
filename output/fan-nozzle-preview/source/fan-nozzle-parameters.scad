// 五羊/DOUAES 涡轮风机到 50/48 mm 硬管的参数化风嘴
// 单位：mm；气流方向 +Z；打印时风机卡口朝下、风道竖直。
//
// 机械基准分级：
//   1. 用户实测风机接口：fan_*。
//   2. 项目已有硬管：tube_*，来自 cad/parameters.scad。
//   3. 结构与打印余量：其余 fn_*，仍需首件装配校核。

// ---- 用户实测风机接口 ----
fn_fan_outlet_od = 76.0;
fn_fan_outlet_id = 71.0;
fn_fan_lug_axial = 8.0;
fn_fan_lug_tangential = 7.5;
fn_fan_lug_radial = 2.0;
fn_fan_lug_from_face = 3.0;
fn_fan_lug_count = 2;
fn_fan_lug_angles = [90, 270];

// ---- 风机卡口 ----
// 0.30 mm 径向间隙是 PETG 首件的名义起点，不是实物量规结论。
fn_fan_socket_radial_clearance = 0.30;
fn_fan_socket_id = fn_fan_outlet_od + 2 * fn_fan_socket_radial_clearance;
fn_fan_collar_od = 86.0;
fn_fan_collar_z = 30.0;
// 风机出口面在卡口内部的名义止位位置。
fn_fan_face_z = 24.0;
fn_fan_entry_chamfer_h = 1.2;
fn_fan_lug_window_clearance = 0.8;
fn_fan_lock_turn_deg = 18.0;
fn_fan_lock_radial_clearance = 0.8;
fn_fan_window_outer_clearance = 0.6;
fn_fan_bayonet_axial_clearance = 0.5;

fn_fan_lug_start_z = fn_fan_face_z - fn_fan_lug_from_face - fn_fan_lug_axial;
fn_fan_lug_end_z = fn_fan_face_z - fn_fan_lug_from_face;
fn_fan_lug_window_tangential =
    fn_fan_lug_tangential + fn_fan_lug_window_clearance;

// ---- 连续锥形风道 ----
// 42.5 mm 是项目现有导向内径；主文件另有完整 Ø45 版本，
// 默认件则通过可拆换风嘴芯提供 Ø34 / Ø36 / Ø38 / Ø40 四档。
fn_tip_id_default = 42.5;
fn_cone_z0 = fn_fan_face_z;
fn_cone_z1 = 104.0;
fn_cone_outer_d0 = 82.0;
fn_tip_outer_d = 47.0;
fn_cone_wall_at_throat = (fn_tip_outer_d - fn_tip_id_default) / 2;
function fn_cone_outer_d_at(z) =
    fn_cone_outer_d0 +
        (fn_tip_outer_d - fn_cone_outer_d0) * (z - fn_cone_z0) /
        (fn_cone_z1 - fn_cone_z0);

// 风机卡口外径不能在 z=30 mm 处突然收缩到锥体，改为连续相切过渡。
// 过渡从卡口圆柱顶部开始，到主锥体 z=44 mm 处结束；卡口的
// Ø86 外包络和锁扣区域保持不变，过渡只发生在锁扣之后。
fn_fan_collar_transition_l = 14.0;
fn_fan_collar_transition_z0 = fn_fan_collar_z;
fn_fan_collar_transition_z1 =
    fn_fan_collar_transition_z0 + fn_fan_collar_transition_l;
fn_fan_collar_transition_d1 =
    fn_cone_outer_d_at(fn_fan_collar_transition_z1);
fn_fan_collar_transition_axis_clearance_r = 0.5;
// 起点与卡口竖直外壁相切，终点与主锥体相切；Hermite 曲线的
// 终点导数使用 h11，避免过渡面在接回主锥体前向内凹穿过锥体。
function fn_fan_collar_transition_radius(t) =
    (2 * t * t * t - 3 * t * t + 1) * fn_fan_collar_od / 2 +
    (t * t * t - 2 * t * t + t) * 0 * fn_fan_collar_transition_l +
    (-2 * t * t * t + 3 * t * t) * fn_fan_collar_transition_d1 / 2 +
    (t * t * t - t * t) *
        (fn_tip_outer_d - fn_cone_outer_d0) /
        (2 * (fn_cone_z1 - fn_cone_z0)) * fn_fan_collar_transition_l;

// 细喷嘴伸入 48 mm 内径硬管；0.50 mm 径向名义间隙。
fn_tube_id = 48.0;
fn_tube_od = 50.0;
fn_spigot_radial_clearance = 0.50;
fn_spigot_od = fn_tube_id - 2 * fn_spigot_radial_clearance;
// 长程版：保留至少 25 mm 插入量时，提供约 60 mm 的轴向调节余量。
fn_spigot_l = 100.0;
fn_spigot_z0 = fn_cone_z1;
// 细喷嘴插入硬管的可视刻线；四档对应不同的 Y 口距离。
fn_spigot_overlap_marks = [25.0, 45.0, 65.0, 85.0];
fn_spigot_overlap_mark_zs =
    [for (overlap=fn_spigot_overlap_marks)
        fn_spigot_z0 + fn_spigot_l - overlap];
fn_spigot_mark_h = 1.0;
fn_spigot_mark_radial_depth = 0.35;

// 交互装配预览的固定参考：名义 65 mm 重叠、首切 130 mm 管子。
// 管子在预览中作为局部 STL，从 z=0 开始；装配 frame 再把它放到 139 mm。
fn_preview_nominal_overlap = 65.0;
fn_preview_tube_l = 130.0;
fn_preview_tube_start_z = fn_spigot_z0 + fn_spigot_l - fn_preview_nominal_overlap;
fn_preview_y_frame_z = fn_preview_tube_start_z + fn_preview_tube_l;

// ---- Y/斜三通交互预览参考 ----
// 工程样品图显示：主管是直通的横向管路，斜支管从交汇处向上偏出；
// 这里仍保留局部 +Z 主管坐标，交互预览再把整套装配转成样品姿态。
// 外部轮廓、真实止位和角度仍未量测；45° 是按样品外观采用的参考角度，
// 不是最终加工尺寸。预览 frame 位于硬管端面/承口止位，局部承口向下延伸。
fn_y_tee_outer_d = 56.0;
fn_y_tee_bore_id = fn_tube_id;
fn_y_tee_socket_id = fn_tube_od + 1.0;
fn_y_tee_socket_l = 25.0;
fn_y_tee_main_up_l = 78.0;
fn_y_tee_branch_start_z = 28.0;
fn_y_tee_branch_l = 78.0;
fn_y_tee_branch_angle = 45.0;
fn_y_tee_port_lip_l = 6.0;
fn_y_tee_port_lip_d = 60.0;

// 可拆换风嘴芯：默认不装芯时为 Ø42.5；当前提供 Ø34 / Ø36 / Ø38 / Ø40。
// 芯子是“外径恒定的导向筒 + 内部收缩锥”的 cartridge：
//   - 外径恒定，负责在主体内孔中同轴导向，避免外部锥面造成晃动；
//   - 风道入口先保持一段 Ø40 直径，再逐渐收缩到目标末端口径；
//   - 入口外肩靠主体台阶定位，入口后用粗牙内外螺纹旋入锁紧；
//   - 螺纹只锁风嘴芯，外套管的 M3 夹紧位仍是另一条独立接口。
fn_tip_core_od = 42.0;
fn_tip_core_l = 102.0;
fn_tip_core_z0 = fn_spigot_z0 - 2.0;
fn_tip_core_flange_od = 43.2;
fn_tip_core_flange_l = 2.0;
fn_tip_core_inlet_id = 40.0;
fn_tip_core_mount_l = 24.0;
fn_tip_core_taper_l = 70.0;
fn_tip_core_exit_l = 8.0;
fn_tip_core_ids = [34.0, 36.0, 38.0, 40.0];

// 风嘴芯采用适合 FDM 的粗牙旋入式锁紧，不再使用 C 形卡环。
// 芯子从主体出口/硬管侧插入，先让入口外肩进入座位，再旋转推进；
// 3 个导程提供可感知的轴向锁紧，同时给 PETG 留出可打印间隙。
fn_tip_core_thread_z0 = fn_spigot_z0;
fn_tip_core_thread_l = 12.0;
fn_tip_core_thread_pitch = 4.0;
fn_tip_core_thread_height = 0.50;
fn_tip_core_thread_groove_id = 43.60;
fn_tip_core_thread_clearance =
    (fn_tip_core_thread_groove_id - (fn_tip_core_od + 2 * fn_tip_core_thread_height)) / 2;
fn_tip_core_thread_turns = fn_tip_core_thread_l / fn_tip_core_thread_pitch;
fn_tip_core_thread_slices_per_turn = 32;

// 芯子入口外肩对应的主体内台阶：芯子总长 102 mm，外肩占前 2 mm，
// 后面的 Ø42 外导向段到达主体出口 z=204 mm。
fn_tip_core_seat_z0 = fn_tip_core_z0;
fn_tip_core_seat_l = fn_tip_core_flange_l;
fn_tip_core_seat_id = 43.5;

// 套在硬管外侧的滑动夹套；0.40 mm 径向名义间隙。
fn_sleeve_radial_clearance = 0.40;
fn_sleeve_id = fn_tube_od + 2 * fn_sleeve_radial_clearance;
fn_sleeve_wall = 3.40;
fn_sleeve_od = fn_sleeve_id + 2 * fn_sleeve_wall;
fn_sleeve_z0 = 94.0;
fn_sleeve_l = 104.0;
// 外套筒根部不能只在锥体上“角对角”相交；用 20 mm 连续锥形根部把
// 主锥体外壁过渡到外套筒外径，保证整圈实体承力，并避免打印悬空台阶。
fn_sleeve_transition_l = 20.0;
fn_sleeve_transition_z0 = fn_sleeve_z0 - fn_sleeve_transition_l;
fn_sleeve_transition_d0 = fn_cone_outer_d_at(fn_sleeve_transition_z0);
// 旋转挤出轮廓不直接碰 Z 轴，避免 STL 在轴心生成退化三角形；
// 后续风道布尔会切掉这条极小的中心避让。
fn_sleeve_transition_axis_clearance_r = 0.5;
// 过渡曲面在主锥体端与主锥体相切，在套筒端与竖直外壁相切。
// 用 Hermite 曲线而不是两段硬圆锥，避免产生可见的变坡环线。
function fn_sleeve_transition_radius(t) =
    (2 * t * t * t - 3 * t * t + 1) * fn_sleeve_transition_d0 / 2 +
    (t * t * t - 2 * t * t + t) *
        (fn_tip_outer_d - fn_cone_outer_d0) /
        (2 * (fn_cone_z1 - fn_cone_z0)) * fn_sleeve_transition_l +
    (-2 * t * t * t + 3 * t * t) * fn_sleeve_od / 2;
fn_sleeve_split_gap = 2.0;
fn_sleeve_split_start = fn_sleeve_z0 + 4.0;
// 四个短检查窗露出透明硬管的边缘；窗口与夹紧耳相反，窗口之间保留环带。
fn_sleeve_inspection_slot_angle = 180;
fn_sleeve_inspection_slot_w = 4.0;
fn_sleeve_inspection_window_l = 8.0;
fn_sleeve_scale_angle = 135;
fn_sleeve_scale_mark_w = 6.0;
fn_sleeve_scale_mark_h = 1.0;

// 一个 M3 横向夹紧位；放在最远 25 mm 插入位置之后，四个刻度都能夹到管子。
// 只锁紧管子，不承担风机卡口的主拉力。
fn_clamp_z = 190.0;
fn_clamp_ear_w = 9.0;
fn_clamp_ear_d = 5.0;
fn_clamp_ear_h = 14.0;
fn_clamp_bolt_x = fn_sleeve_od / 2 + 3.0;
fn_clamp_clearance_d = 3.4;
fn_clamp_head_d = 6.0;
fn_clamp_head_depth = 2.4;
fn_clamp_nut_af = 5.8;
fn_clamp_nut_depth = 2.6;

// ---- 打印 / 几何审查 ----
fn_wall_min = 2.0;
fn_eps = 0.02;
fn_fn = 96;

assert(fn_fan_socket_id > fn_fan_outlet_od);
assert(fn_fan_collar_od > fn_fan_socket_id + 2 * fn_wall_min);
assert(fn_fan_lug_start_z > 0);
assert(fn_fan_lug_end_z < fn_fan_collar_z);
assert(fn_fan_lug_window_tangential > fn_fan_lug_tangential);
assert(fn_fan_lock_turn_deg > 5 && fn_fan_lock_turn_deg < 35);
assert(fn_tip_id_default > 0 && fn_tip_id_default < fn_tip_outer_d);
assert(fn_spigot_od < fn_tube_id);
assert(fn_preview_nominal_overlap >= min(fn_spigot_overlap_marks));
assert(fn_preview_nominal_overlap <= max(fn_spigot_overlap_marks));
assert(fn_preview_tube_l > fn_spigot_l);
assert(fn_y_tee_outer_d > fn_y_tee_socket_id);
assert(fn_y_tee_socket_id > fn_tube_od);
assert(fn_y_tee_bore_id < fn_y_tee_socket_id);
assert(fn_y_tee_socket_l > 0 && fn_y_tee_socket_l <= fn_preview_tube_l);
assert(fn_y_tee_main_up_l > fn_y_tee_branch_start_z);
assert(fn_y_tee_branch_l > 0);
assert(fn_y_tee_branch_angle > 20 && fn_y_tee_branch_angle < 70);
assert(fn_tip_core_od < fn_tip_id_default);
assert(fn_tip_core_flange_od > fn_tip_core_od);
assert(fn_tip_core_flange_od < fn_tip_core_seat_id);
assert(fn_tip_core_flange_l > 0 && fn_tip_core_flange_l < fn_tip_core_l);
assert(fn_tip_core_inlet_id < fn_tip_core_od);
assert(fn_tip_core_mount_l > fn_tip_core_flange_l);
assert(fn_tip_core_mount_l + fn_tip_core_taper_l + fn_tip_core_exit_l == fn_tip_core_l);
assert(fn_tip_core_thread_z0 == fn_spigot_z0);
assert(fn_tip_core_thread_l > 0 && fn_tip_core_thread_l < fn_tip_core_l - fn_tip_core_flange_l);
assert(fn_tip_core_thread_pitch >= 3.0 && fn_tip_core_thread_pitch <= 5.0);
assert(fn_tip_core_thread_turns >= 2.0 && fn_tip_core_thread_turns <= 4.0);
assert(fn_tip_core_thread_height >= 0.35 && fn_tip_core_thread_height <= 0.80);
assert(fn_tip_core_thread_groove_id > fn_tip_core_od + 2 * fn_tip_core_thread_height);
assert((fn_tip_outer_d - fn_tip_core_thread_groove_id) / 2 >= 1.50);
assert(fn_tip_core_thread_clearance >= 0.20 && fn_tip_core_thread_clearance <= 0.45);
assert(fn_tip_core_thread_z0 + fn_tip_core_thread_l <= fn_tip_core_z0 + fn_tip_core_l);
assert(fn_tip_core_seat_z0 == fn_tip_core_z0);
assert(fn_tip_core_seat_z0 + fn_tip_core_seat_l == fn_spigot_z0);
assert(fn_sleeve_inspection_window_l > 0);
assert(min(fn_spigot_overlap_mark_zs) >= fn_sleeve_z0);
assert(max(fn_spigot_overlap_mark_zs) <=
    fn_sleeve_z0 + fn_sleeve_l);
assert(fn_sleeve_id > fn_tube_od);
assert(fn_sleeve_od > fn_sleeve_id + 2 * fn_wall_min);
assert(fn_sleeve_transition_l >= 8.0);
assert(fn_sleeve_transition_z0 > fn_cone_z0);
assert(fn_sleeve_transition_z0 < fn_sleeve_z0);
assert(fn_sleeve_transition_d0 > fn_tip_outer_d);
assert(fn_sleeve_transition_d0 >= fn_sleeve_od);
assert(fn_sleeve_transition_axis_clearance_r > 0);
assert(fn_fan_collar_transition_l >= 8.0);
assert(fn_fan_collar_transition_z1 > fn_fan_collar_transition_z0);
assert(fn_fan_collar_transition_z1 < fn_cone_z1);
assert(fn_fan_collar_transition_d1 < fn_fan_collar_od);
assert(fn_fan_collar_transition_d1 > fn_tip_outer_d);
assert(fn_fan_collar_transition_axis_clearance_r > 0);
assert(fn_sleeve_split_gap >= 1.2 && fn_sleeve_split_gap <= 3.0);
assert(fn_clamp_z > fn_sleeve_z0 && fn_clamp_z < fn_sleeve_z0 + fn_sleeve_l);
