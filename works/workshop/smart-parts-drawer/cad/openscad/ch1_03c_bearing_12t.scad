// Mechanical contract
// process: rigid resin/SLA-DLP first; FDM requires calibrated bearing-seat clearance
// material: to be confirmed; this is a low-load printed idler, not a steel sprocket
// parting_plane: n/a (single printed gear with integral hub)
// opening_direction: n/a
// fastener: 3 mm round shaft through a 3×6×2 mm bearing; no D-flat or set screw
// seal: n/a
// print_orientation: hub face down; axis = +Z (tooth profile in XY)
// units: mm
// source: parts/ch1_03c_sprocket.scad + parts/ch1_03c_sprocket_params.scad

//#region 导入/依赖
include <parts/ch1_03c_sprocket_params.scad>
use <parts/ch1_03c_sprocket.scad>
//#endregion

//#region 常量/配置
$fa = 8;
$fs = 0.22;

TEETH = 12;
//#endregion

//#region 公开 API
rotate([180, 0, 0])
    ch1_03c_bearing_sprocket(TEETH);
//#endregion

//#region 业务逻辑
// 与原 12T D 轴版共用尖齿链轮轮廓和 12 mm 轮毂；中心改为从 +Z 装入的 6.05 mm 轴承座，输出按装配要求正反面翻转。
// 轴承外圈由打印件压配，底部台阶承托；轴向由两侧链板/轴肩约束。
//#endregion
