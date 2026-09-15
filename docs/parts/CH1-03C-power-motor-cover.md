# CH1-03C 动力轮电机固定罩

## 结构方案

固定罩采用后侧开口的 U 形笼罩，内腔包住 Pololu #1101 电机的 10×12 mm 减速箱，前端与动力轮后表面留 0.5 mm 间隙。罩体后法兰有四个 M3 通孔和螺钉头沉孔。

可拆背板内侧增加四根 Ø8 mm boss 柱，底部用 Ø14×1.6 mm 圆盘把载荷分散到背板；每根 boss 预留 Ø4.6×5 mm 的 M3 热熔螺母位。安装顺序是：先把 M3 铜螺母装入背板 boss，再把电机套进罩体，从罩体前侧四角拧入 M3 螺钉。

受力路径：电机/罩体 → 后法兰 → M3 螺钉 → 热熔螺母 → 背板 boss → 背板。电机引线从罩后方 8×4 mm 槽穿出。

## 关键假设

- 工艺按 FDM PETG/尼龙首版设计；材料、层高和壁数仍需按实际打印机验证。
- 紧固件默认 M3 螺钉 + 外径约 4.6 mm、长度 5 mm 的热熔铜螺母；没有嵌件时可把 boss 孔改为 M3 自攻螺钉导向孔。
- 背板是可拆件，固定罩沿 +Y 方向拆出；没有跨越背板分型面的倒扣。
- 固定罩和 boss 是打印件；电机、螺钉、热熔螺母仍是采购件。

## 文件

- 固定罩源文件：`cad/openscad/parts/motor_pololu_mount_cover.scad`
- 固定罩独立入口：`cad/openscad/ch1_03c_power_motor_cover.scad`
- 独立打印 STL：`output/3d-print/motor-mount/ch1_03c_power_motor_cover.stl`（保留作单件打印/适配检查，不进入总装配器件树）
- 柜体定位固定罩 STL：`output/3d-print/cabinet-chain/cabinet_chain_motor_cover.stl`
- 含接收 boss 的背板 STL：`output/3d-print/cabinet/cabinet_back_panel.stl`
- 共享位置/尺寸：`cad/openscad/enclosure/cabinet_motor_mount_params.scad`
- 网页模型库：[http://127.0.0.1:8765/](http://127.0.0.1:8765/)

固定罩不是密封件；切片时需确认悬垂、螺钉头沉孔、热熔螺母压入方向和实际背板装配间隙。
