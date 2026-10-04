# 电子扳机：已选背梁的开关线材固定孔

**状态：两处固定孔已并入当前 49 件清单中的电子扳机背梁；未试印或放行。** 固定背梁上的两个穿孔给焊片后的线材提供扎带固定点，使线束拉力由背梁承担，不直接牵扯开关焊片。[已选背梁网格](../output/electronic-trigger-candidate/beam.stl) · [线材净空 CAD](../cad/electronic-trigger-wire-relief-screen.scad) · [几何报告](../output/electronic-trigger-wire-relief/review.json) · [松开位局部图](../output/electronic-trigger-wire-relief/released.png) · [扣下位局部图](../output/electronic-trigger-wire-relief/pulled.png)。图中的红色线与黄色扎带仍是净空代理。

背板在 `Y=−59…−55 mm`。两个名义 Ø3.0 mm 穿孔中心为 `(X,Z)=(42.5,−13.5)/(48.5,−13.5) mm`，供名义宽 2.5 mm 的扎带穿过；左外缘余壁 2.0 mm、两孔之间余壁 3.0 mm、到指窗上缘最小名义 3.0 mm。预留的导线先从 D3 焊片向 −X 离开，再沿背板左侧向下到两个孔之间的固定点；模型用单线 Ø2 mm、汇束 Ø4 mm 的包络检查邻件，**没有断言真实焊接弯曲半径、绝缘套直径或线材规格**。固定点之后到控制板的线束路径也还没设计。

[几何报告](../output/electronic-trigger-wire-relief/review.json)导出的背梁与当前选件 STL 哈希相同，且为单连通封闭网格；两孔从无孔背梁移去约 56.46 mm³。27 项松开/半扣/扣到底及送料 0/10/20 mm 的导线/扎带与扳机、固定件和运动件名义避让探针均为空，另有 2 项孔确实贯通无孔背梁的正对照。扎带按 [T18R 官方尺寸](https://www.hellermanntyton.com/products/cable-ties-inside-serrated/t18r/111-01230)取 2.5 mm 宽、头部 4.45×4.8×3.7 mm，再以 5.5×5.8×4.7 mm 盒体预留头部净空。真实扎带穿装、锁紧工具、开关焊锡、热缩管、手指握持与长期振动仍未验收。

[X1C/PETG 离线切片](../output/electronic-trigger-wire-relief/slice-review.json)沿现用背梁 X−90° 摆向，0.4 mm 喷嘴、0.2 mm 层高、4 壁、25% 填充、5 mm brim、仅从热床生成树状支撑。约 84.31 g、110 层，原生切片无警告；按实际 3MF 变换核对，两处扎带通孔沿打印高度方向，G-code 中以 0.25 mm 外扩包围盒查到的支撑挤出段均为 0。[盘面图](../output/electronic-trigger-wire-relief/slice-x-minus-90-tree/plate-preview.png)与[3MF](../output/electronic-trigger-wire-relief/slice-x-minus-90-tree/slice-review.3mf)可用于复核。**未发送打印机**；切片不证明真实扎带能穿孔、锁紧后不割伤线材，也不能替代焊点与整机走线验收。
