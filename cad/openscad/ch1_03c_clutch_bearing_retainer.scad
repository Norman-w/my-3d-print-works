// CH1 03C 681 离合轴承下承托环 — 独立模型库/打印入口

//#region 导入/依赖
include <parts/ch1_03c_extended_link_params.scad>
//#endregion

//#region 常量/配置
PART = is_undef(PART) ? "retainer" : PART;
//#endregion

//#region 公开 API
if (PART == "retainer")
    ch1_03c_clutch_bearing_retainer();
else if (PART == "assembly")
    ch1_03c_extended_link_reference();
//#endregion

//#region 业务逻辑
// 轴承从平台下方装入后，承托环用压配或少量胶固定；轴向沿世界 Z。
//#endregion
