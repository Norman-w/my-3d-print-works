# 摇臂叉座低梁加宽筛查

**状态：独立强度/空间候选，未替换当前叉座、未切片、未放行打印。** 原[可拆后叉耳](electric-rocker-service-fork-screen.md)固定基座的低梁为 `X=7…10、Z=−18…−7 mm`，侧向受力时只有 3 mm 宽。新[筛查 CAD](../cad/electric-rocker-service-fork-reinforcement-screen.scad)在低梁外侧补 `X=10…14、Y=40…61、Z=−18…−7 mm`，得到局部 7×11 mm 截面；原主壳两颗合壳螺钉的贯通孔和沉头通道仍从新增材料中扣除。后叉耳、摇臂及电机接口没有改动。

[几何报告](../output/electric-rocker-service-fork-reinforcement-screen/review.json)从当前 CAD 导出单连通、封闭的加宽基座，体积由原候选 7352.724 增至 8138.311 mm³。正对照确认确有新增实体；运动件的两个端点控制网格沿 Z 恰好相差 20 mm，送料架 0–20 mm 每 1 mm 的 21 个位置，以及固定件、五金、电机占位、后叉耳和原锚点孔道等共 27 个交叠探针，新增体积没有正体积碰撞。[叠加图](../output/electric-rocker-service-fork-reinforcement-screen/beam-extension-context.png)里绿色为新增材料，蓝色为原基座，棕色为运动送料框。该图只说明局部空间，不是已经装机的电机座。

把原[静态承力假设](../output/electric-rocker-service-fork-screen/load-screen.json)中的 4–5 kgf 卖家推力和整只枢轴反力继续全部压在一条**无孔直梁**上，仅作几何灵敏度比较：新截面的名义竖向弯曲应力为 3.47–4.34 MPa（原 8.11–10.13），同量级 X 向侧载下为 5.46–6.82 MPa（原 29.72–37.15）。这些数字**没有涵盖壳体合缝螺钉孔处的截面削弱、根部圆角/应力集中、打印方向、层间拉伸、动态冲击或实际电机推拉力**，不能用作 PETG 许用应力或安全系数。加宽让下一版承力路径有更好的空间基础，但不能把当前打印件标为一次装配通过。

进一步的[根部截面复核](../output/electric-rocker-service-fork-reinforcement-screen/root-section-screen.json)（[可复算脚本](../analysis/service_fork_root_section_screen.py)、[依赖版本](../analysis/service_fork_section_requirements.txt)）直接剖切两版封闭 STL：在 `Y=45.5 mm` 的直梁中段，截面积确由 **33 增至 77 mm²**；但在螺钉中心后方的 `Y=39.5 mm`，两版截面完全相同，均被螺钉孔分成三块材料区域，其中下侧材料区约 **18.67 mm²**。这说明当前补强只改善中段，**没有改善根部最需要复核的孔旁承力路径**。截面面积和拓扑不能替代三维应力、层间强度或疲劳计算；此补强件继续保持独立候选。

为处理这个根部薄区，后续增加了[合壳孔旁渐变腹板候选](electric-rocker-root-gusset-screen.md)。它改善名义截面积并通过离散空间筛查，但仍未完成三维应力、真实载荷、螺钉承压和 PETG 层间验证，同样不进入当前打印清单。

最终须以同一只 BY141-3 实测载荷、所购底座和活动端接口，把此加宽基座、金属转轴/螺钉、根部与主壳凸台作为整体校核；然后重新跑完整装配、工具入口、X1C/PETG 切片和实物承载验收。此独立筛查未改变当前 49 件制作清单。
