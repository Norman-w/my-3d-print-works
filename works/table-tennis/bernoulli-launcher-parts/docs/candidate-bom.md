> 历史设计子报告：当前33件送料总装、材料、裁管安排和装配数量已由 [本版统一装配说明](final-assembly.md) 接替。本文旧数量和未集成状态保留用于追溯，不作为当前制作清单。

# 当前候选零件与五金清单

**更新入口：**已集成的新送料总成按[联合候选清单](integrated-feeder-assembly.md)核对，为17种几何、27个打印实例。以下仍保留旧送料基线与现有旋转头，不能将两份送料清单相加或混用。

**供设计核对，尚未形成制造发布清单。** 基线加本轮旋转头修改共17种几何、21件；点射新X导向及先前Y调隙/分缝修订仍单列，不能把此表视作新点射总成的完整清单。柔性垫和对侧导向块的材料另定，不全部按PETG制造。

## 基线及旋转头几何

| 编号 | 名称 | 数量 | 材料状态 | 源文件及导出选择 |
|---|---|---:|---|---|
| P01 | 送料壳体右半 | 1 | PETG（用户确认，打印方向未冻结） | `cad/feeder-body.scad` / `body_part="positive_half"` |
| P02 | 送料壳体左半 | 1 | PETG（用户确认，打印方向未冻结） | `cad/feeder-body.scad` / `body_part="negative_half"` |
| P03 | 右固定支座 | 1 | PETG（用户确认，打印方向未冻结） | `cad/feeder-supports.scad` / `support_part="right_support"` |
| P04 | 左固定支座含弹簧连接 | 1 | PETG（用户确认，打印方向未冻结） | `cad/feeder-supports.scad` / `support_part="left_support"` |
| P05 | 轴向导向盖 | 2 | PETG（用户确认，打印方向未冻结） | `cad/feeder-supports.scad` / `support_part="cap"` |
| P06 | 凸轮架与指环 | 1 | PETG（用户确认，打印方向未冻结） | `cad/feeder-supports.scad` / `support_part="carriage"` |
| P07 | 挡指载体 | 4 | PETG（用户确认，打印方向未冻结） | `cad/feeder-supports.scad` / `support_part="finger"` |
| P08 | 旋转头主体 | 1 | PETG（用户确认，打印方向未冻结） | `cad/spin-head.scad` / `part="body"` |
| P09 | 旋转头浮动载体 | 1 | PETG（用户确认，打印方向未冻结） | `cad/spin-head.scad` / `part="carriage"` |
| P10 | 柔性摩擦垫 | 1 | 材料/硬度未选 | `cad/spin-head.scad` / `part="pad"` |
| P11 | 摩擦垫压条 | 1 | PETG（用户确认，打印方向未冻结） | `cad/spin-head.scad` / `part="pad-keeper"` |
| P12 | 对侧导向块 | 1 | 低摩擦材料待定 | `cad/spin-head.scad` / `part="opposite-guide"` |
| P13 | 旋转头外盖 | 1 | PETG（用户确认，打印方向未冻结） | `cad/spin-head.scad` / `part="cover"` |
| P14 | 弹簧座导向笼 | 1 | PETG（用户确认，打印方向未冻结） | `cad/spin-head.scad` / `part="spring-cage"` |
| P15 | 旋转头弹簧座 | 1 | PETG（用户确认，打印方向未冻结） | `cad/spin-head.scad` / `part="spring-seat"` |
| P16 | 旋转头主动拉帽 | 1 | PETG（用户确认，打印方向未冻结） | `cad/spin-head.scad` / `part="pull-cap"` |
| P17 | 旋转头退出保持块 | 1 | PETG（用户确认，打印方向未冻结） | `cad/spin-head.scad` / `part="hold-fork"` |

挡指载体同一源件装四处；原导向盖镜像装左右。STL保留装配坐标，未批准整套打印方向。新增保持块只在退出档安装，不叠加在工作档运动件上。

## 金属件尺寸候选

| 编号 | 规格 | 数量 | 用途与未核事项 |
|---|---|---:|---|
| H01 | M3×12 圆柱头内六角螺钉 | 22 | 壳体8、支座4、导向盖4、旋转头6；实际头型和长度待核件 |
| H02 | M3×8 圆柱头内六角螺钉 | 2 | 旋转头对侧导向块 |
| H03 | M3×10 90°沉头螺钉 | 2 | 软垫压条；不是圆柱沉孔螺钉 |
| H04 | M3 六角螺母 | 32 | 壳体8、支座4、盖4、随动销4、旋转头12；包括主动退出新增2颗，不含点射X导向替代件 |
| H05 | M3 平垫片，当前厚0.5/外径7 | 8 | 四颗支座螺钉和四颗导向盖螺钉；不能任意加到肩销下 |
| H06 | D4×12 肩螺钉，M3螺纹长7 | 4 | 几何候选 norelem 07534-04X12，不能仅按D4名称替换 |
| H07 | M4×16 圆柱头内六角螺钉 | 1 | 旋转头夹管 |
| H08 | M4×25 手拧螺钉 | 1 | 旋转头预压；当前头部外包络Ø14×6 |
| H09 | M4 六角螺母 | 3 | 夹管1、预压固定1、外锁定1；外锁定扳手入口尚未验证 |
| H10 | M3×45 圆柱头内六角螺钉 | 1 | 上导柱贯穿拉杆，旋转头主动拉回 |
| H11 | M3×16 圆柱头内六角螺钉 | 1 | 旋转头保持块固定 |

肩螺钉依据和装配栈见[机构说明](feeder-mechanism.md)。新增拉杆/保持块的载荷路径及装配顺序见[旋转头说明](spin-head.md)。保持块可加防丢软绳，穿绳耳已建模。未进行采购。

## 点射X导向替代件

[本轮X导向](feeder-cam-guide-revision.md)替换上表P03右支座，另加压条及盖板各1件；新增M3×16螺钉4、M3螺母6、M3平垫片4。既有Y向可调压条仍需保留。独立STL在`output/feeder-cam-guide-revision/`，此处不把不同修订直接累加为完整装配清单。

## 尚待完成的必要件

| 编号 | 名称 | 数量 | 状态 |
|---|---|---:|---|
| U01 | 送料回位弹簧及两端挂接件 | 1 | 无球/有球/卡滞的行程力未测，未选自由长、初拉力、刚度、最大伸长及钩头 |
| U02 | 旋转头压缩弹簧 | 1 | 已按 Lee Spring LC 016DE 10M 目录初选：OD7.92、L0=20.65、线径0.41、固高约2.84、k=0.14 N/mm；CAD支承空间9.75–19 mm已检查，实际弹簧力、摩擦效果和采购尚未确认。见spin-spring-selection.md |
| U03 | 分缝定位和密封材料 | 待定 | 槽形、定位配合及PETG相容材料待定；不能插平垫撑开壳体 |
| U04 | 软管和硬管短节的固定/密封件 | 待定 | 已确认硬管插三通、软管套硬管；模块入口箍紧、出口独立固定/密封及支承未定，见docs/interface-contract.md |
| U05 | 修订抗滚转导向所需零件 | 待定 | 右公共架X主导向支座替换P03，新增压条/盖板各1、M3×16×4、M3螺母×6、M3垫圈×4；与既有径向载体Y调隙件联合使用，未计入基线17种/21件。见feeder-cam-guide-revision.md；完整误差仍开放。 |

上述项目仍属于完整方案；不能删除后把剩余零件称为整套完成。[弹簧目录初选](spin-spring-selection.md)不等于实际摩擦力已确认。JSON同源记录位于`docs/candidate-bom.json`。
