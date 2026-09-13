// CH1 03C 加长连接节双穿销 — 独立模型库入口

//#region 导入/依赖
include <parts/ch1_03c_extended_link_params.scad>
//#endregion

//#region 常量/配置
PART = is_undef(PART) ? "pin" : PART;
//#endregion

//#region 公开 API
if (PART == "pin")
    ch1_03c_extended_connecting_pin_pair();
else if (PART == "assembly")
    ch1_03c_extended_link_reference();
//#endregion

//#region 业务逻辑
// 固定端面到第一道夹片槽 6.42 mm；两夹片内侧净距 10 mm；总销长 17.50 mm。
//#endregion
