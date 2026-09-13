// Mechanical contract
// process: assembly visualization — one 12T D-shaft drive sprocket; all other wheels use 3×6×2 bearing seats
// material: sprockets resin/PETG TBD; chain carbon steel 03C; blunt idlers PETG
// parting_plane: n/a for chain; cabinet back face remains Y = D
// opening_direction: n/a
// fastener: back-view upper-right / front-view upper-left power_c() sprocket 3 mm D-shaft; other wheels 3 mm round bearing shaft; tensioner M3 + spring
// seal: n/a
// print_orientation: sprocket hub down; do not 3D-print the chain
// units: mm
// note: 5x5 row-major snake through every bay center; rear-view right return; power at back-view upper right / front-view upper left (power_c()); all wheels are face-flipped; bearings are separate display/purchase geometry

//#region 导入/依赖
QUALITY = is_undef(QUALITY) ? 2 : QUALITY;
PART = is_undef(PART) ? "assembly" : PART;
EXPLODE = is_undef(EXPLODE) ? 48 : EXPLODE;
CHAIN_LIB_ONLY = true;
CABINET_LIB_ONLY = true;
include <cabinet.scad>
include <../ch1_03c_roller_chain.scad>
include <cabinet_chain_path.scad>
use <../parts/ch1_03c_sprocket.scad>
use <../parts/ch1_03c_blunt_idler.scad>
use <../parts/ch1_03c_bearing_visual.scad>
use <../parts/ch1_03c_connecting_link_params.scad>
use <../parts/motor_pololu_micro_metal_100_1_hp_6v.scad>
use <../parts/motor_pololu_mount_cover.scad>
//#endregion

//#region 常量/配置
$fa = 8;
$fs = 0.22;
CHAIN_Y = MOTOR_MOUNT_CHAIN_Y;
CONNECTOR_LINK_INDEX = 20;       // 顶部直线段上的一节；不放在转向轮上
CONNECTOR_HIGHLIGHT = "#ff2fd0";
//#endregion

//#region 模型/类型
// 销轴路径在 cabinet_chain_path.scad；本文件只做后仓装配。
//#endregion

//#region 私有成员
echo("snake_pins", len(snake_pins()), "length_mm", len(snake_pins()) * P);
echo("power", power_c(), "entry", entry_c(), "service_return", drive_c(), "tensioner", ten_path_c(), "ten_z", TEN_Z);

module snake_in_rear() {
    translate([0, CHAIN_Y, 0])
        rotate([90, 0, 0])
            children();
}

module place_xz(c) {
    translate([c[0], CHAIN_Y, c[1]])
        children();
}

module place_geared(c) {
    place_xz(c)
        rotate([90, 0, 0])
            rotate([0, 0, wheel_pose_rot(c[0], c[1])])
                rotate([180, 0, 0])
                    children();
}

module place_power_motor(c) {
    // The flipped power wheel presents its D bore toward +Y. The motor sits behind
    // that face, with local +Z rotated to world -Y so the shaft enters the wheel.
    translate([c[0], CHAIN_Y + HUB_H / 2, c[1]])
        rotate([90, 0, 0])
            children();
}

module place_power_motor_cover(c) {
    translate([c[0], CHAIN_Y, c[1]])
        children();
}

module rear_blunt_idlers() {
    for (c = blunt_centers())
        place_geared(c) ch1_03c_bearing_blunt_idler(BLUNT_TEETH);
}

module rear_bearing_visuals() {
    // 与轴承版齿轮一一对应；背面右上/正面左上 power_c() 动力轮没有轴承，不在此处放置。
    for (c = concat(right_turn_sprockets(), left_turn_sprockets(), [drive_c(), ten_path_c()]))
        place_geared(c) ch1_03c_bearing_visual();
    for (c = blunt_centers())
        place_geared(c) ch1_03c_bearing_visual();
}

module rear_sprockets() {
    // 按用户背面视图：右上（正面左上）power_c() 保留 D 轴动力接口，其余 12T 轮全部改为轴承版。
    place_geared(power_c()) ch1_03c_sprocket(SPROCKET_TEETH);
    for (c = concat(right_turn_sprockets(), left_turn_sprockets(), [drive_c(), ten_path_c()]))
        place_geared(c) ch1_03c_bearing_sprocket(SPROCKET_TEETH);
}

module highlighted_connector() {
    // 接头只替换这两个销位的普通销：链板保持原位，带槽双穿销和夹片
    // 必须共用普通销的中心线，不能再叠加一套外板。
    p0 = snake_pins()[CONNECTOR_LINK_INDEX];
    p1 = snake_pins()[(CONNECTOR_LINK_INDEX + 1) % len(snake_pins())];
    snake_in_rear()
        place_from_to(p0, p1, [0, 0, 1])
            translate([P / 2, 0, 0])
                color(CONNECTOR_HIGHLIGHT) {
                    ch1_03c_connecting_pin_pair();
                    ch1_03c_retaining_clip();
                }
}

module pins_on_path_without_connector(pins) {
    // 从普通销集合中拿掉接头占用的两个销位，由 highlighted_connector() 补回带槽销。
    n = len(pins);
    axis = [0, 0, 1];
    connector_b = (CONNECTOR_LINK_INDEX + 1) % n;
    for (i = [0:n - 1])
        if (i != CONNECTOR_LINK_INDEX && i != connector_b)
            place_from_to(pins[i], pins[(i + 1) % n], axis)
                pin_solid();
}

module bay_center_dots() {
    for (i = [0:N_COL - 1], j = [0:N_ROW - 1])
        translate([col_center_x(i), CHAIN_Y, row_center_z(j)])
            sphere(d = 2.2);
}

module emit_chain(name) {
    if (PART == "assembly" || PART == name)
        children();
}
//#endregion

//#region 公开 API
if (PART == "power_check") {
    // Diagnostic close-up only: the motor shaft enters the flipped D-shaft power wheel.
    color("#e07a3d") place_geared(power_c())
        ch1_03c_sprocket(SPROCKET_TEETH);
    place_power_motor(power_c())
        pololu_micro_metal_motor_100_1_hp_6v_colored();
    color("#56616d", 0.28)
        place_power_motor_cover(power_c())
            ch1_03c_power_motor_cover();
}

if (PART == "assembly") {
    %cabinet_shell();
    %drawer_ghosts();
    color("#ff4d4d", 0.9) bay_center_dots();
    color("#c9a227", 0.85) tensioner_hardware();
}

emit_chain("plates") {
    if (PART == "assembly") color("#8A919C") snake_in_rear() plates_on_path(snake_pins());
    else snake_in_rear() plates_on_path(snake_pins());
}
emit_chain("rollers") {
    if (PART == "assembly") color("#E8EDF2") snake_in_rear() rollers_on_path(snake_pins());
    else snake_in_rear() rollers_on_path(snake_pins());
}
emit_chain("pins") {
    if (PART == "assembly") color("#B08D57") snake_in_rear() pins_on_path_without_connector(snake_pins());
    else snake_in_rear() pins_on_path_without_connector(snake_pins());
}
emit_chain("sprockets") {
    if (PART == "assembly") {
        color("#e07a3d") place_geared(power_c())
            ch1_03c_sprocket(SPROCKET_TEETH);
        color("#d4a017") place_geared(ten_path_c())
            ch1_03c_bearing_sprocket(SPROCKET_TEETH);
        color("#5b9fd6") {
            for (c = concat(right_turn_sprockets(), left_turn_sprockets(), [drive_c()]))
                place_geared(c) ch1_03c_bearing_sprocket(SPROCKET_TEETH);
        }
    } else {
        rear_sprockets();
    }
}
emit_chain("idlers") {
    if (PART == "assembly") color("#7dcc4a") rear_blunt_idlers();
    else rear_blunt_idlers();
}
emit_chain("bearings") {
    if (PART == "assembly") color("#b9c2ca") rear_bearing_visuals();
    else rear_bearing_visuals();
}
emit_chain("motor") {
    if (PART == "assembly")
        place_power_motor(power_c())
            pololu_micro_metal_motor_100_1_hp_6v_colored();
    else
        place_power_motor(power_c())
            pololu_micro_metal_motor_100_1_hp_6v();
}
emit_chain("motor_cover") {
    if (PART == "assembly")
        color("#56616d", 0.92)
            place_power_motor_cover(power_c())
                ch1_03c_power_motor_cover();
    else
        place_power_motor_cover(power_c())
            ch1_03c_power_motor_cover();
}
emit_chain("connector") {
    highlighted_connector();
}
//#endregion

//#region 视图层
// 预览用 PART=assembly；power_check 仅用于近距离确认动力轮、电机轴和固定罩的相对位置。
// 链条外购件分 plates / rollers / pins 导出。
//#endregion

//#region 业务逻辑
// 闭环按真实节距闭合；底端张紧轮吃掉余量。长于 210L×1 m SKU，只做后仓走线可视化。
// 红点是每格矩形中心；水平段节圆线必须穿过这些点。
// 橙色 power_c() 背面右上/正面左上 12T 保留 D 轴动力接口，并在轮后接入真实 Pololu 1101 电机模型与固定罩；
// 下方 service_return、入口、金色张紧、蓝色转向和绿色 8T 平移轮均为轴承版，并显示独立的 3×6×2 轴承。
// 所有轮子安装面翻转 180°。
// 高亮 CONNECTOR_LINK_INDEX 节为 03C 连接节：该节普通双销被带槽双穿销替换，
// 链板保持原位，再卡上右端敞口圆弧夹片；网页运动预览会把它与链条一起带着走。
//#endregion

//#region 方法/工具
// 导出: -D PART='"plates"' / '"rollers"' / '"pins"' / '"sprockets"' / '"idlers"' / '"bearings"' / '"motor"' / '"connector"'
// 检查视图: -D PART='"power_check"'。
//#endregion
