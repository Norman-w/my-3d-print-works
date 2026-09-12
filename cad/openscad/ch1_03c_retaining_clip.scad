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
// 夹片为按 03C 节距布局的双 C 耳结构；具体钢片厚度/展开形状需按实物 CL 件复核。
//#endregion
