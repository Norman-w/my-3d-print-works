// Pololu 100:1 Micro Metal Gearmotor HP 6V, no encoder (item #1101).
// Standalone model-library entry; the motor is a purchased part and is not for printing.

//#region 导入/依赖
use <parts/motor_pololu_micro_metal_100_1_hp_6v.scad>
//#endregion

//#region 常量/配置
PART = is_undef(PART) ? "motor" : PART;
//#endregion

//#region 模型/类型
// local origin is the output-shaft root / gearbox front face; output axis is +Z.
//#endregion

//#region 公开 API
if (PART == "motor")
    pololu_micro_metal_motor_100_1_hp_6v_colored();
//#endregion

//#region 业务逻辑
// Official mechanical reference: 10 x 12 mm gearbox section, 9 mm gearbox length,
// 3 mm D shaft x 9 mm, 25.6 mm maximum motor/gearbox body length.
//#endregion
