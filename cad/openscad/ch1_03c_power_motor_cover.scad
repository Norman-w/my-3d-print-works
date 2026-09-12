// Pololu #1101 D 轴电机固定罩，独立模型库/打印入口。

//#region 导入/依赖
use <parts/motor_pololu_mount_cover.scad>
//#endregion

//#region 常量/配置
PART = is_undef(PART) ? "cover" : PART;
//#endregion

//#region 公开 API
if (PART == "cover")
    ch1_03c_power_motor_cover();
//#endregion
