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
// 固定头内侧面到第一道夹片槽中心 6.42 mm；两夹片内侧净距 10 mm；
// 销杆有效长 17.50 mm，固定头外伸后独立 STL 总包络 17.90 mm。
//#endregion
