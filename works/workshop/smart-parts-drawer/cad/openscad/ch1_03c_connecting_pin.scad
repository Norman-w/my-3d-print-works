// CH1 03C 连接节双穿销 — 独立模型库入口

//#region 导入/依赖
include <parts/ch1_03c_connecting_link_params.scad>
//#endregion

//#region 常量/配置
PART = is_undef(PART) ? "pin" : PART;
//#endregion

//#region 公开 API
if (PART == "pin")
    ch1_03c_connecting_pin_pair();
else if (PART == "assembly")
    ch1_03c_connecting_link_reference();
//#endregion

//#region 业务逻辑
// 双销中心距为 4.7625 mm；销身 Ø1.62 mm、总长 6.9 mm，末端带夹片槽。
//#endregion
