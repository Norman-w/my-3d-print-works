// 03C 轴承装配显示件：不是打印齿轮的一部分，而是独立的采购件几何。
// Mechanical contract
// process: assembly visualization / purchased bearing reference
// material: steel bearing with dark seal reference
// fastener: 3 mm round shaft through the 3×6×2 mm bearing
// units: mm

//#region 导入/依赖
include <ch1_03c_sprocket_params.scad>
//#endregion

//#region 常量/配置
$fa = is_undef($fa) ? 10 : $fa;
$fs = is_undef($fs) ? 0.18 : $fs;
//#endregion

//#region 模型/类型
module bearing_annulus(od, id, h) {
    difference() {
        cylinder(d = od, h = h, center = true);
        cylinder(d = id, h = h + 0.04, center = true);
    }
}
//#endregion

//#region 公开 API
module ch1_03c_bearing_visual() {
    // 外圈、内圈和两侧密封盖分层建模，让网页装配中能看出“轴承 + 齿轮”。
    union() {
        bearing_annulus(BEARING_OD, 4.55, BEARING_B);
        bearing_annulus(4.15, BEARING_ID, BEARING_B);
        for (z = [-BEARING_B / 2 + 0.09, BEARING_B / 2 - 0.09])
            translate([0, 0, z])
                bearing_annulus(BEARING_OD - 0.28, BEARING_ID + 0.22, 0.12);
    }
}
//#endregion

//#region 业务逻辑
// 该文件只提供装配显示几何；实际轴承由用户购买，不与塑料齿轮 STL 合并打印。
//#endregion
