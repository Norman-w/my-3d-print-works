// CH1 03C 加长销双固定弹片/夹片 — 独立模型库入口

//#region 导入/依赖
include <parts/ch1_03c_extended_link_params.scad>
//#endregion

//#region 常量/配置
PART = is_undef(PART) ? "clips" : PART;
//#endregion

//#region 公开 API
if (PART == "clips")
    ch1_03c_extended_retaining_clips();
else if (PART == "assembly")
    ch1_03c_extended_link_reference();
//#endregion

//#region 业务逻辑
// 两只右端敞口的双销圆弧弹片分别锁在第一/第二道销槽；每只夹片的两根销位
// 都保留贴槽圆弧，模型保持与加长销相同的装配坐标，夹片内侧之间留 10 mm 净空间。
//#endregion
