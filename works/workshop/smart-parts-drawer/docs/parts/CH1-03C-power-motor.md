# CH1-03C 动力轮 D 轴电机

## 选型

动力轮采用真实可采购的 Pololu `#1101`：`100:1 Micro Metal Gearmotor HP 6V`，无编码器版本。

- 官方页面：[Pololu 100:1 Micro Metal Gearmotor HP 6V](https://www.pololu.com/product/1101)
- 官方尺寸图：[Micro Metal Gearmotor dimensions](https://www.pololu.com/file/0J949/micro-metal-gearmotor-dimensions.pdf)
- 额定电压：6 V
- 官方输出轴：直径 3 mm、D 形、轴长 9 mm
- 官方减速箱截面：10 × 12 mm
- 官方无编码器本体最大长度：25.6 mm；模型本体按 9 mm 减速箱 + 16.6 mm 电机罐建模
- 电机线缆不包含在模型中，实际产品也需要另配/焊接引线

## 装配方向

模型局部坐标中，减速箱前端面为 `z=0`，D 轴沿 `+Z` 指向动力轮。装进柜体时，电机位于动力轮后侧，轴沿世界 `-Y` 插入 `snake_drive_c()`。

`snake_drive_c()` 是用户定义的“从背面看右下角 / 从正面看左下角”唯一动力位；主动轮为 12T，其他全部导向轮统一为小尺寸 8T 绿色钝齿的 3×6×2 mm 轴承导向轮。

## 文件与预览

- 模型库源文件：`cad/openscad/parts/motor_pololu_micro_metal_100_1_hp_6v.scad`
- 独立入口：`cad/openscad/ch1_03c_power_motor.scad`
- 独立模型库 STL：`output/3d-print/motor-library/ch1_03c_power_motor_pololu_100_1_hp_6v.stl`（保留作尺寸参考，不进入总装配器件树）
- 柜体中已安装的电机 STL：`output/3d-print/cabinet-chain/cabinet_chain_motor.stl`
- 网页预览：`http://127.0.0.1:8876/`

该电机 STL 是采购件的外形/间隙显示件，不要拿去 3D 打印；真正打印的是动力轮和轴承轮。
