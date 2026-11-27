// ============================================================
// 理疗仪线缆串联保护盒 — 全局参数（v3 功率调速板）
// therapy-cable-inline-box-for-physio
//
// 坐标：盒体/PCB 的 50mm 长边沿 X；线缆沿 Y，二者垂直。
//       旋钮在 X- 端，四位端子在 X+ 端，PCB 元件面朝 +Z。
//       分型面 Z=0 穿过旋钮轴线。
// ============================================================

// ===== 分区：PCB 与安装孔 =====

MODULE_LENGTH       = 50.0;  // 商品图标称，待卡尺复测
MODULE_WIDTH        = 32.0;  // 商品图标称，待卡尺复测
MODULE_PCB_THICK    = 1.6;   // 暂按常见 FR4
MODULE_CLEARANCE    = 0.6;

// PCB 靠旋钮端放置，把 X+ 空间留给端子和两根线的弯折。
MODULE_CENTER_X     = -7.0;
MODULE_CENTER_Y     =  0.0;

// 用户实测：四孔孔径约 3mm，孔心到相邻两边均约 3mm。
MODULE_HOLE_DIAM         = 3.0;
MODULE_HOLE_INSET_X      = 3.0;
MODULE_HOLE_INSET_Y      = 3.0;
MODULE_HOLE_CLEARANCE    = 0.3;
MODULE_HOLES = [
    [MODULE_CENTER_X - (MODULE_LENGTH/2 - MODULE_HOLE_INSET_X),
     MODULE_CENTER_Y - (MODULE_WIDTH/2  - MODULE_HOLE_INSET_Y)],
    [MODULE_CENTER_X - (MODULE_LENGTH/2 - MODULE_HOLE_INSET_X),
     MODULE_CENTER_Y + (MODULE_WIDTH/2  - MODULE_HOLE_INSET_Y)],
    [MODULE_CENTER_X + (MODULE_LENGTH/2 - MODULE_HOLE_INSET_X),
     MODULE_CENTER_Y - (MODULE_WIDTH/2  - MODULE_HOLE_INSET_Y)],
    [MODULE_CENTER_X + (MODULE_LENGTH/2 - MODULE_HOLE_INSET_X),
     MODULE_CENTER_Y + (MODULE_WIDTH/2  - MODULE_HOLE_INSET_Y)]
];

// ===== 分区：旋钮 / 电位器 =====

KNOB_AXIS_ABOVE_PCB = 6.2;   // 用户实测：轴心到 PCB 正面
PCB_TOP_Z           = -KNOB_AXIS_ABOVE_PCB;
PCB_BOTTOM_Z        = PCB_TOP_Z - MODULE_PCB_THICK;
KNOB_AXIS_Y         = MODULE_CENTER_Y;
KNOB_AXIS_Z         = 0.0;

KNOB_THREAD_DIAM    = 6.5;   // 用户实测：固定套筒外螺纹
KNOB_WINDOW_DIAM    = 7.1;   // 螺纹外径 + 打印/装配余量
KNOB_THREAD_LENGTH  = 10.0;  // 自 PCB 旋钮端向外；待实测
KNOB_SHAFT_DIAM     = 6.0;   // 占位值
KNOB_SHAFT_LENGTH   = 8.0;   // 螺纹套筒外继续伸出；占位值
KNOB_CAP_DIAM       = 18.0;  // 占位值，不影响壳体开孔
KNOB_CAP_LENGTH     = 16.0;

POT_BODY_SIZE_X     = 10.0;
POT_BODY_SIZE_Y     = 10.0;
POT_BODY_SIZE_Z     = 10.0;
POT_BODY_CENTER_X_REL = -(MODULE_LENGTH/2 - POT_BODY_SIZE_X/2);

// 用户复核：贴 PCB 的矩形“下巴”，Y=2mm、+Z=1mm；
// 沿旋钮/X- 方向突出不超过 1mm，因此完全位于壳体内腔。
POT_CHIN_WIDTH_Y       = 2.0;
POT_CHIN_HEIGHT_Z      = 1.0;
POT_CHIN_PROTRUSION_X  = 1.0;

// ===== 分区：主要元件占位（用于净空和散热孔定位） =====

HEATSINK_CENTER_X_REL = 0.0;   // 相对 PCB 板心，待实测
HEATSINK_CENTER_Y_REL = 0.0;
HEATSINK_SIZE_X       = 24.0;
HEATSINK_SIZE_Y       = 30.0;
HEATSINK_HEIGHT       = 16.0;
HEATSINK_BASE_HEIGHT  = 3.0;
HEATSINK_FIN_COUNT    = 8;
HEATSINK_FIN_THICK    = 1.2;
HEATSINK_CENTER_X     = MODULE_CENTER_X + HEATSINK_CENTER_X_REL;
HEATSINK_CENTER_Y     = MODULE_CENTER_Y + HEATSINK_CENTER_Y_REL;

TERMINAL_CENTER_X_REL = 21.0;
TERMINAL_SIZE_X       = 8.0;
TERMINAL_SIZE_Y       = 30.0;
TERMINAL_HEIGHT       = 11.0;

CAP_CENTER_X_REL      = 17.0;
CAP_DIAMETER          = 8.0;
CAP_HEIGHT            = 17.0;
CAP_Y_POSITIONS       = [-9.5, 0, 9.5];

// ===== 分区：壳体 =====

// 下腔容纳 PCB 轴线偏置、板厚及 3mm 焊点余量；上腔容纳散热片/电容。
// 只把接线端（X+）加长 12mm；旋钮端内壁仍固定在 X=-34mm。
BOX_BASE_INNER_LENGTH = 68.0;
BOX_TERMINAL_EXTENSION = 12.0;
BOX_INNER_LENGTH      = BOX_BASE_INNER_LENGTH + BOX_TERMINAL_EXTENSION;
BOX_INNER_WIDTH       = 44.0;
BOX_INNER_BOTTOM_H    = 10.8;
BOX_INNER_TOP_H       = 14.0;  // 当前最高元件占位仍需实测确认
BOX_INNER_HEIGHT      = BOX_INNER_BOTTOM_H + BOX_INNER_TOP_H;
BOX_CENTER_X          = BOX_TERMINAL_EXTENSION / 2;
BOX_INNER_MIN_X       = BOX_CENTER_X - BOX_INNER_LENGTH / 2;
BOX_INNER_MAX_X       = BOX_CENTER_X + BOX_INNER_LENGTH / 2;

WALL_THICKNESS        = 1.6;  // 顶板 / 底板
SIDE_WALL_THICKNESS   = 2.4;  // 四周外扩，给合盖 Boss 斜坡留足外侧肉厚
BOX_OUTER_LENGTH      = BOX_INNER_LENGTH + SIDE_WALL_THICKNESS * 2;
BOX_OUTER_WIDTH       = BOX_INNER_WIDTH  + SIDE_WALL_THICKNESS * 2;
BOX_OUTER_HEIGHT      = BOX_INNER_HEIGHT + WALL_THICKNESS * 2;
BOX_CENTER_Z          = (BOX_INNER_TOP_H - BOX_INNER_BOTTOM_H) / 2;
BOX_OUTER_TOP_Z       = BOX_INNER_TOP_H + WALL_THICKNESS;
BOX_OUTER_BOTTOM_Z    = -BOX_INNER_BOTTOM_H - WALL_THICKNESS;

CORNER_RADIUS         = 4.0;

// ===== 分区：合盖螺丝（从底面拧入） =====

BOSS_DIAMETER         = 5.0;
BOSS_PILOT_HOLE       = 1.7;
BOSS_REINFORCE_OD     = 7.5;
BOSS_REINFORCE_H      = 2.5;
BOSS_END_INSET_X      = 3.0;
BOSS_X_POSITIONS      = [BOX_INNER_MIN_X + BOSS_END_INSET_X,
                         BOX_INNER_MAX_X - BOSS_END_INSET_X];
BOSS_Y                = 19.0;
// 从分型面一直长到上盖内表面，并伸入顶板 0.3mm，确保实体相交。
TOP_CLOSURE_BOSS_H    = BOX_INNER_TOP_H + 0.3;
SCREW_CLEARANCE       = 2.3;
SCREW_HEAD_DIAMETER   = 5.0;
SCREW_HEAD_DEPTH      = 1.8;

// ===== 分区：PCB 四孔罗马柱（4×M2×5mm 沉头螺丝 + 承压垫圈） =====

MODULE_BOSS_DIAMETER     = 7.0;
MODULE_BOSS_PILOT        = 1.7;  // M2 螺丝直接攻入打印件
MODULE_BOSS_REINFORCE_OD = 9.0;
MODULE_BOSS_REINFORCE_H  = 1.5;
// 约 3mm PCB 孔转 M2：2.8mm 定位颈留 0.2mm 直径配合间隙。
// 颈高比 1.6mm PCB 薄 0.2mm，确保上方垫圈压 PCB 而不是顶在定位颈上。
MODULE_LOCATOR_DIAMETER  = 2.8;
MODULE_LOCATOR_TIP_DIAMETER = 2.6;
MODULE_LOCATOR_HEIGHT    = MODULE_PCB_THICK - 0.2;
MODULE_WASHER_OD         = 6.0;
MODULE_WASHER_ID         = 2.3;
MODULE_WASHER_H          = 1.3;
MODULE_WASHER_CS_DIAM    = 4.4;  // 兼容常见 M2 90°沉头，留打印余量
MODULE_WASHER_CS_DEPTH   = (MODULE_WASHER_CS_DIAM - MODULE_WASHER_ID) / 2;

// ===== 分区：双线缆（沿 Y，相对两侧进线） =====

CABLE_DIAMETER        = 5.0;   // 沿用旧线缆暂定值，待复测
CABLE_STRIP_LENGTH    = 18.0;
CABLE_ENTRY_END_GAP_X = 11.0;  // 保持出线中心到 X+ 内壁的原有余量
CABLE_ENTRY_X         = BOX_INNER_MAX_X - CABLE_ENTRY_END_GAP_X;
GLAND_HOLE_DIAM       = 5.4;
GLAND_WALL_EXTRA      = 1.5;
GLAND_OUTER_EXTEND    = 0.0;

// 线缆限位柱不负责压紧，只限制横向乱跑；夹紧由上下交错夹齿完成。
GUIDE_POST_DIAMETER        = 3.5;
GUIDE_POST_CABLE_CLEARANCE = 0.8;
GUIDE_POST_INNER_GAP       = CABLE_DIAMETER + GUIDE_POST_CABLE_CLEARANCE;
GUIDE_POST_CENTER_OFFSET   = (GUIDE_POST_INNER_GAP
                              + GUIDE_POST_DIAMETER) / 2;

// ===== 分区：散热孔 =====

ENABLE_TOP_VENTS      = true;
TOP_VENT_COUNT        = 7;
TOP_VENT_SLOT_LENGTH  = 22.0;  // 沿散热鳍片/X 方向
TOP_VENT_SLOT_WIDTH   = 1.8;
TOP_VENT_SLOT_PITCH   = 3.6;

// 侧槽增强自然对流，但降低防汗/防液体能力；湿润环境可设为 false。
ENABLE_SIDE_VENTS     = true;
SIDE_VENT_COUNT       = 3;
SIDE_VENT_SLOT_LENGTH = 20.0;  // 沿 X
SIDE_VENT_SLOT_HEIGHT = 1.5;
SIDE_VENT_Z_FIRST     = 3.5;
SIDE_VENT_Z_PITCH     = 3.0;

// ===== 分区：装配 / 打印 =====

ALIGNMENT_LIP_H       = 0.8;
ALIGNMENT_LIP_W       = 0.8;
PRINT_TOLERANCE       = 0.2;

VISUAL = false;
$fn = 64;
