// Mechanical contract
// process: assembly visualization — sprockets resin-printable; chain purchased 03C steel
// material: sprockets TBD resin/PETG; chain carbon steel SKU 单排03C-1X210L
// parting_plane: n/a
// opening_direction: n/a
// fastener: sprocket 3 mm D-shaft + M2 on flat; chain riveted pins (visualization)
// seal: n/a
// print_orientation: sprocket hub down, indicator on +Z; do not 3D-print the chain
// units: mm
// source: docs/parts/CH1-03C-roller-chain.md
// note: 1x left / 2x right, center distance 200 mm; 102-link even closed wrap

//#region 导入/依赖
use <ch1_03c_roller_chain.scad>
use <parts/ch1_03c_sprocket.scad>
include <parts/ch1_03c_sprocket_params.scad>
//#endregion

//#region 常量/配置
$fa = 8;
$fs = 0.22;

PART = "assembly";               // assembly | sprocket_1x | sprocket_2x | plates | rollers | pins
CENTER_DISTANCE = 200;
TANGENT_PITCHES = 42;
LEFT_WRAP_PITCHES = 6;
RIGHT_WRAP_PITCHES = 12;
N_LEFT = 12;
N_RIGHT = 24;
eps = 0.05;
//#endregion

//#region 模型/类型
function polar_xy(c, r, a) = [c[0] + r * cos(a), c[1] + r * sin(a), 0];

function lerp_open(a, b, n) = [
    for (j = [1:n - 1]) a + (j / n) * (b - a)
];

function wrap_cw_open(c, r, n_teeth, steps, start_a) = [
    for (k = [1:steps]) polar_xy(c, r, start_a - k * 360 / n_teeth)
];
//#endregion

//#region 私有成员
R_LEFT = sprocket_pitch_r(N_LEFT);
R_RIGHT = sprocket_pitch_r(N_RIGHT);
ALPHA = asin((R_RIGHT - R_LEFT) / CENTER_DISTANCE);
LEFT_ROT = 90 + ALPHA;
RIGHT_ROT = 90 + ALPHA;

left_center = [0, 0, 0];
right_center = [CENTER_DISTANCE, 0, 0];
left_upper = polar_xy(left_center, R_LEFT, LEFT_ROT);
right_upper = polar_xy(right_center, R_RIGHT, RIGHT_ROT);
left_lower = polar_xy(
    left_center, R_LEFT, LEFT_ROT - LEFT_WRAP_PITCHES * 360 / N_LEFT
);
right_lower = polar_xy(
    right_center, R_RIGHT, RIGHT_ROT - RIGHT_WRAP_PITCHES * 360 / N_RIGHT
);

drive_pins = concat(
    [left_upper],
    lerp_open(left_upper, right_upper, TANGENT_PITCHES),
    [right_upper],
    wrap_cw_open(right_center, R_RIGHT, N_RIGHT, RIGHT_WRAP_PITCHES, RIGHT_ROT),
    lerp_open(right_lower, left_lower, TANGENT_PITCHES),
    [left_lower],
    wrap_cw_open(
        left_center,
        R_LEFT,
        N_LEFT,
        LEFT_WRAP_PITCHES - 1,
        LEFT_ROT - LEFT_WRAP_PITCHES * 360 / N_LEFT
    )
);

module emit_drive(name) {
    if (PART == "assembly" || PART == name) children();
}

module drive_sprocket_1x() {
    rotate(LEFT_ROT)
        ch1_03c_sprocket(N_LEFT);
}

module drive_sprocket_2x() {
    translate(right_center)
        rotate(RIGHT_ROT)
            ch1_03c_sprocket(N_RIGHT);
}
//#endregion

//#region 公开 API
assert(len(drive_pins) % 2 == 0, "drive pin count must be even");
assert(len(drive_pins) == 102, str("expected 102 pins, got ", len(drive_pins)));

emit_drive("sprocket_1x") {
    if (PART == "assembly") color("#5b9fd6") drive_sprocket_1x();
    else drive_sprocket_1x();
}
emit_drive("sprocket_2x") {
    if (PART == "assembly") color("#e0c07a") drive_sprocket_2x();
    else drive_sprocket_2x();
}
emit_drive("plates") {
    if (PART == "assembly") color("#8A919C") plates_on_path(drive_pins);
    else plates_on_path(drive_pins);
}
emit_drive("rollers") {
    if (PART == "assembly") color("#E8EDF2") rollers_on_path(drive_pins);
    else rollers_on_path(drive_pins);
}
emit_drive("pins") {
    if (PART == "assembly") color("#B08D57") pins_on_path(drive_pins);
    else pins_on_path(drive_pins);
}
//#endregion

//#region 业务逻辑
// 外切公切线倾角 ALPHA；切段 42 节、1x 包角 6 节、2x 包角 12 节，合计 102。
// 保持中心距 200 mm，切段边长略短于 P（约 0.12%），只用于可视化，不是张紧计算。
// 链轮旋转使 0 号齿对准上切点，滚子落在节圆座孔。
//#endregion

//#region 方法/工具
// 导出: -D PART='"plates"' / '"rollers"' / '"pins"' / '"sprocket_1x"' / '"sprocket_2x"'
//#endregion
