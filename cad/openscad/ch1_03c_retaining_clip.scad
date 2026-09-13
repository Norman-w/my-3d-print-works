// CH1 03C 连接节固定弹片/夹片 — 独立模型库入口

//#region 导入/依赖
include <parts/ch1_03c_connecting_link_params.scad>
//#endregion

//#region 常量/配置
PART = is_undef(PART) ? "clip" : PART;
//#endregion

//#region 公开 API
if (PART == "clip")
    ch1_03c_retaining_clip();
else if (PART == "assembly")
    ch1_03c_connecting_link_reference();
//#endregion

//#region 业务逻辑
// 夹片为右端敞口的双销圆弧弹片：两根穿销位置各有一段贴合销槽的圆弧，
// 中间由上下两条收腰弹臂连接。独立 STL 已按装配坐标输出，打印时绕 X 轴铺平。
//#endregion
