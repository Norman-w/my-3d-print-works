// CH1 03C 传动离合轴承 — 独立模型库/采购件显示入口

//#region 导入/依赖
include <parts/ch1_03c_extended_link_params.scad>
//#endregion

//#region 常量/配置
PART = is_undef(PART) ? "bearing" : PART;
//#endregion

//#region 公开 API
if (PART == "bearing")
    ch1_03c_clutch_bearing_visual();
else if (PART == "assembly")
    ch1_03c_extended_link_reference();
//#endregion

//#region 业务逻辑
// 轴承为 3×6×2 mm MR63 尺寸，轴向沿 +Y，与平台座孔一致。
//#endregion
