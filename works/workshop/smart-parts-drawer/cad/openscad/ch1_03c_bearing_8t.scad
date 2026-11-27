// Mechanical contract
// process: rigid resin/SLA-DLP first; FDM requires calibrated bearing-seat clearance
// material: to be confirmed; this is a low-load printed translator/idler
// parting_plane: n/a (single printed disc with chain-guide flanges)
// opening_direction: n/a
// fastener: 3 mm round shaft through a 3×6×2 mm bearing; no D-flat or set screw
// seal: n/a
// print_orientation: flange face down; axis = +Z (tooth profile in XY)
// units: mm
// source: parts/ch1_03c_blunt_idler.scad + parts/ch1_03c_sprocket_params.scad

//#region 导入/依赖
// 只引入 8T 原始轮廓和参数，不让库文件额外输出一颗普通惰轮。
BLUNT_LIB_ONLY = true;
include <parts/ch1_03c_blunt_idler.scad>
//#endregion

//#region 常量/配置
$fa = 8;
$fs = 0.22;

TEETH = 8;
//#endregion

//#region 公开 API
rotate([180, 0, 0])
    ch1_03c_bearing_blunt_idler(TEETH);
//#endregion

//#region 业务逻辑
// 保留原 8T 钝齿和两侧挡圈；中心改为从 +Z 装入的 6.05 mm 轴承座，输出按装配要求正反面翻转。
// 3×6×2 轴承在 8T 齿根内仍保留约 1.8 mm 径向材料，适合本低负载用途。
//#endregion
