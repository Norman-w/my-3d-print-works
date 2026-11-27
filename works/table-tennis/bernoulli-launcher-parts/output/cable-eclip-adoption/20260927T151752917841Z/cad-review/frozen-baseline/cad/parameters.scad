// 单位：mm。用户提供的接口尺寸与待实测的样机候选参数明确分开。
// 该文件是几何尺寸的唯一来源；修改后必须重新校核并导出。

// 用户提供；未以实物量规复核。
barrel_id = 48;
barrel_od = 50;
hose_id = 50;
hose_od = 55;

// 以下是工程校核包络，不是对用户实际球径的声明。
ball_min_d = 40;
ball_max_d = 41;
guide_id = 42.5;
guide_od = 47;
guide_start_z = -80;
guide_length = 104;
transition_length = 18;
feed_socket_od = 49.4;
feed_socket_length = 28;
y_stub_od = 50;
y_stub_engagement = 25;
barrel_engagement = 25;
interface_radial_clearance = 0.25;

// 待运动校核的双挡指候选几何。
finger_tip_radius = 2.5;
finger_closed_center_r = 21;
finger_open_center_r = 26;
gate_spacing = 28.5;
gate_overlap_fraction = 0.20;
cam_stroke = 20;
guide_clearance_budget = 0.25;
// 容纳槽/销孔名义游隙后的设计包络；并非实测的制造或受力误差。
gate_position_budget = 1.0;

// 外壳、旁通与可拆装接口。
body_id = 64;
body_wall = 3;
body_flange = 9;
split_gasket_thickness = 1;
fastener_d = 3.4;
nut_af = 5.8;
nut_depth = 2.6;
radial_print_clearance = 0.25;
axial_print_clearance = 0.3;

// 摩擦头候选；零接触位置不能被宣传为已验证的无旋球。
spin_guide_id = 42.5;
spin_body_wall = 3;
spin_pad_width = 12;
spin_pad_length = 22;
spin_pad_thickness = 1;
spin_adjustment_travel = 2.5;
spin_contact_length = 30;
spin_angle = 0;

$fn = 72;
