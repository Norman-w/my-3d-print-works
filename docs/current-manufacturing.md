# 当前往复电机版制作状态

[当前电动版实例清单](electric-assembly-inventory.json)包含 39 个送料结构实例（左 Y 盖、运动弹簧间隔套及固定背梁各替换一次，另增电子扳机杠杆）及 10 个旋转头实例（含正常工作时不安装的保持叉）。这 49 个是当前已定义结构件，不是完整电动机构的最终打印件数。

两件光电替换件已有[旧几何/切片记录](optical-home-candidate.md)；本版从滑架去掉手扣指环，保留原右止挡肩外侧 1 mm，并在无拉索基线中通过[71 项名义几何复核](../output/electric-feeder/review.json)，新增探针覆盖滑架两端的左右止挡肩及旧指环切除区。电子扳机的替换背梁与独立杠杆通过[79 项局部探针](../output/electronic-trigger-candidate/review.json)及[16 项当前总装替换/扫掠探针](../output/electric-trigger-integration/review.json)，两件均重新生成 X1C/PETG 离线切片；同版整机渲染显示原背梁未叠装。[一体输出横头候选](electric-output-crosshead-screen.md)也有自己的替换送料框 STL、3MF 和 G-code，但不在当前 49 件清单内，摇臂销保持和槽壁强度未验证。[可拆后叉耳候选](electric-rocker-service-fork-screen.md)的基座和后叉耳通过名义装配路径筛查并生成了 X1C/PETG 离线切片，关键螺母窝/定位键袋/轴孔未被支撑填入；[承力筛查](../output/electric-rocker-service-fork-screen/load-screen.json)另指出低梁打印层方向与定位键/M3 孔接触次序的未决风险，尚未打印或证明 PETG 接合面承力。以上检查不等于已经校核电机座、杆端接头、整机受力、开关导通或实物安装。当前仍无**完整的电机座、双向传动总成及其正式取件表/摆盘**。因此 manufacturing_release=false、physical_acceptance=false，不发送打印机。

原拉索版的 56 件/42 板、53 件复用及三件重切记录移作[历史制作资料](history/current-manufacturing-cable-2026-09-30.md)。其中拉索输入四件、输出盖、第三弯导向三件、替换的背梁/滑架和拉索专用五金均不能进入电动版。原料仍按 X1C、0.4 mm、PETG/旋转头 TPU 95A HF 候选处理；实际新件的摆盘和切片须等电机接口定型后再重新绑定，不以浪费材料打印试片为前置条件。
