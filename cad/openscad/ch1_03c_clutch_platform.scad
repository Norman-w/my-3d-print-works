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
// 平台主体沿 Y 厚 5.0 mm，前后各有 0.8 mm 对称加强筋；轴承中心下移到 z=-2.0，
// 从下方沿 +Z 压入 681（1×3×1 mm），再由独立承托环锁住。
//#endregion
