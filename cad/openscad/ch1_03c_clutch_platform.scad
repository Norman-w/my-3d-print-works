// CH1 03C 传动离合轴承平台 — 独立模型库/打印入口

//#region 导入/依赖
include <parts/ch1_03c_extended_link_params.scad>
//#endregion

//#region 常量/配置
PART = is_undef(PART) ? "platform" : PART;
//#endregion

//#region 公开 API
if (PART == "platform")
    ch1_03c_clutch_platform();
else if (PART == "assembly")
    ch1_03c_extended_link_reference();
//#endregion

//#region 业务逻辑
// 平台沿 Y 厚 3 mm，挂在两根加长销上；下方中心座压入已购买的 3×6×2 mm 轴承。
//#endregion
