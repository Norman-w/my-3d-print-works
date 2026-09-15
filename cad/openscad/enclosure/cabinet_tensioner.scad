// 后仓底部张紧 U：导槽、弹簧口袋、M3 螺栓孔。父文件需已 include cabinet_params。

//#region 导入/依赖
// 由 cabinet.scad include；节距只在本文件复一份，避免和链条参数二次赋值。
//#endregion

//#region 常量/配置
TEN_P = 4.7625;
TEN_WALL_CLEAR = 0.40;
TEN_TRAVEL = MOTOR_MOUNT_SLIDE_STROKE; // 电机/罩体沿旧 Z 的可调下压行程
TEN_RIB_T = 3.2;
TEN_RIB_GAP = 16.0;              // 两肋夹住链条，轴沿 Y
TEN_SLOT_W = 3.4;                // 3 mm 轴滑动间隙
TEN_SPRING_L = 14.0;
TEN_SPRING_D = 6.0;
TEN_BOLT_D = 3.2;
TEN_BOLT_HEAD_D = 5.6;
TEN_BOLT_HEAD_H = 2.4;
TEN_WELL_PAD = 4.0;
//#endregion

//#region 模型/类型
function ten_pitch_r() = TEN_P / (2 * sin(15));

function ten_outer_r() = ten_pitch_r() + 0.38 * TEN_P;

function ten_return_x() = WALL + ten_outer_r() + TEN_WALL_CLEAR;

function tensioner_c() = [
    ten_return_x() + ten_pitch_r(),
    is_undef(TEN_Z) ? WALL + ten_outer_r() + 1.2 : TEN_Z
];

function tensioner_slot_h() = TEN_TRAVEL + ten_pitch_r() * 2 + 2.0;

function tensioner_chain_y() = PARTITION_BACK_Y + 12;
//#endregion

//#region 私有成员
module tensioner_rib_blank() {
    c = tensioner_c();
    h = tensioner_slot_h() + TEN_WELL_PAD;
    translate([
        c[0] - ten_outer_r() - TEN_WELL_PAD,
        0,
        WALL - EPS
    ])
        cube([
            2 * ten_outer_r() + 2 * TEN_WELL_PAD,
            TEN_RIB_T,
            h
        ]);
}

module tensioner_slot_cut() {
    c = tensioner_c();
    translate([
        c[0] - TEN_SLOT_W / 2,
        -EPS,
        c[1] - ten_pitch_r() - TEN_TRAVEL / 2
    ])
        cube([
            TEN_SLOT_W,
            TEN_RIB_T + 2 * EPS,
            tensioner_slot_h()
        ]);
}

module tensioner_rib() {
    difference() {
        tensioner_rib_blank();
        tensioner_slot_cut();
    }
}

module tensioner_spring_coil() {
    c = tensioner_c();
    translate([c[0], tensioner_chain_y(), WALL + 1.6])
        linear_extrude(height = TEN_SPRING_L, twist = 360 * 6, slices = 48)
            translate([TEN_SPRING_D / 2 - 0.55, 0])
                circle(d = 1.1);
}

module tensioner_bolt_solid() {
    c = tensioner_c();
    translate([c[0], tensioner_chain_y(), 0]) {
        cylinder(d = TEN_BOLT_HEAD_D, h = TEN_BOLT_HEAD_H);
        cylinder(d = TEN_BOLT_D, h = WALL + TEN_SPRING_L + 8);
    }
}
//#endregion

//#region 公开 API
module tensioner_guides() {
    y0 = tensioner_chain_y() - TEN_RIB_GAP / 2 - TEN_RIB_T;
    y1 = tensioner_chain_y() + TEN_RIB_GAP / 2;
    translate([0, y0, 0]) tensioner_rib();
    translate([0, y1, 0]) tensioner_rib();
}

module tensioner_floor_bore() {
    c = tensioner_c();
    translate([c[0], tensioner_chain_y(), -EPS])
        cylinder(d = TEN_BOLT_D + 0.2, h = WALL + 2 * EPS);
}

module tensioner_hardware() {
    tensioner_spring_coil();
    tensioner_bolt_solid();
}
//#endregion

//#region 视图层
// guides / floor_bore 并进柜壳；spring / bolt 只在装配预览。
//#endregion

//#region 业务逻辑
// 弹簧/调节螺杆把现在的电机—固定罩滑台沿旧 Z 向下压；旧 Z 经总装配适配
// 为世界 +Y，向下调节就是世界 -Y。链条额定位置由 TEN_Z 给出。
//#endregion

//#region 方法/工具
// 由 cabinet.scad / cabinet_chain.scad include，不单独打开。
//#endregion
