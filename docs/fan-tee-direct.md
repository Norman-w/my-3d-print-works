# Ø41 风机到 Y 三通直插连接件候选

这是与现有 Ø76 风机风嘴并行的另一款风机接口候选，不改写原透明管外套方案。

## 当前接口契约

- 气流轴为 `+Z`；风机卡口在 `-Z` 侧，三通直插段在 `+Z` 侧。
- 新风机出风口外径：`Ø41 mm`。
- 风机外侧两处对置 L 形槽：反向轴向总长 `18.5 mm`，转向弧长约 `20 mm`，槽宽约 `7 / 6.5 mm`。
- 连接件内壁使用两个对置的 `Ø6 mm` 圆饼凸起；凸起根部嵌入壁厚，不靠薄边或角点承力。
- 三通承口按名义内径 `Ø50 mm` 建模。FDM 首件默认给每侧 `0.40 mm` 径向间隙，因此实际插入段外径为 `Ø49.2 mm`，不是未经修正的 Ø50.0 mm 过盈件。
- 插入段壁厚保持 `3.0 mm`，对应内径约 `Ø43.2 mm`；插入长度暂定 `25 mm`，需要按三通实物止挡修正。
- 风机内径未提供，当前气道入口暂定 `Ø35 mm`，只是参数化候选，不是实测结论。

## 可替换出风口芯

主体内壁在三通侧先由 `Ø42.4 mm` 入口平顺过渡到 `Ø40.6 mm` 导向/螺纹基孔；芯子全长保持 `Ø40 mm`，从三通侧插入并旋入，不再设置会卡在导向孔处的外法兰。芯子入口粗直段内径 `Ø38 mm`（保留约 1 mm 壁厚），外螺纹大径约 `Ø41.8 mm`，螺距 `4 mm`，有效啮合长度 `16 mm`；前 `4 mm` 为无螺纹导向段，主体内槽最大约 `Ø42.8 mm`，螺纹冠部相对入口 `Ø42.4 mm` 保留约 `0.30 mm` 径向导入余量。牙型先按轴向宽根—斜牙侧—平顶定义，再由同一螺旋相位生成母沟并加入轴向配合余量；不再用薄片扭转近似。每旋转一圈，理论轴向位置变化 `4 mm`；当前名义装配下，芯子末端约伸过三通插入段 `13 mm`，参数调节范围暂取约 `±8 mm`。不增加额外防松结构，是否使用螺纹胶留给实物装配决定。

当前候选芯内径为 `Ø34 / Ø36 / Ø38 mm`。由于外径只有 `Ø40 mm`，暂不提供壁厚为零的 Ø40 芯；如实测气道和强度需要，可另行扩大芯子外径或取消该档。

## 当前输出

- [统一风机接口交互预览入口](/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/fan-nozzle-preview/index.html)
- [主连接件 SCAD](/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/fan-tee-direct-bayonet.scad)
- [参数文件](/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/fan-tee-direct-parameters.scad)
- [主连接件 STL](/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/fan-tee-direct/fan-tee-direct-connector.stl)
- [Ø34 芯 STL](/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/fan-tee-direct/fan-tee-direct-core34.stl)
- [Ø36 芯 STL](/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/fan-tee-direct/fan-tee-direct-core36.stl)
- [Ø38 芯 STL](/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/fan-tee-direct/fan-tee-direct-core38.stl)
- [尺寸报告](/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/fan-tee-direct/report.json)

预览选择器：`connector`、`core34`、`core36`、`core38`、`assembly`、`section`、`bayonet-detail`、`core-thread-detail`。

## 仍需确认

打印前必须实测新风机内径、L 槽开口相对出风端面的轴向位置与顺/逆时针方向，以及三通实际可用内径和止挡深度。当前 CAD、STL 和渲染只能证明参数化几何候选，不能证明风机卡口扭矩、拔脱力、打印螺纹寿命或气动性能。
