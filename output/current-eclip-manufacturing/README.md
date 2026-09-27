# 新版拉线输入件：切片与装配入口

新版主体、扳机和盖板已重新切片并完成下列限定数字检查。当前共 **56 个打印实例、42 张打印板、45 类五金规格**；制作与实物验收仍未放行。

- [当前打印清单](20260927T161537157301Z/manufacturing/manifest.json)：53 个实例沿用已核对的 39 板，三件新版各占一板。
- [三件选择依据及报告](20260927T161537157301Z/review-index.json)
- [当前五金与取件表](../current-assembly-package/runs/20260927T164103218111Z/README.md)
- [完整装配顺序](../../docs/current-assembly.md)及[固定与机械逻辑](../../docs/current-mechanical-review.md)

## 这次修正

主体的背板在所选摆向下离打印板 3 mm，原来的两处螺母窝支撑没有托住背板。本次补上背板支撑，并检查实际生成的前序支撑路径。

盖板原摆向在轴根产生 0.45 mm 径向悬边。本次翻转为小轴孔一面朝打印板，让孔径向上扩大，并为两个浅方窝增加支撑。这两项是打印工艺修正，没有改动正式 CAD 尺寸或四颗主固定螺钉的位置。

| 零件 | 当前切片 | 装五金前的清理 |
|---|---|---|
| 输入主体 | [3MF](../current-eclip-slices/20260927T155752390241Z/cable-input-body/slice-review.3mf) | 从开敞背面清背板支撑，再清两浅螺母窝。 |
| 扳机 | [3MF](../current-eclip-slices/20260927T155733716437Z/cable-input-lever/slice-review.3mf) | 清两浅窝；独立首层残料随 Brim 清床。 |
| 主盖 | [3MF](../current-eclip-slices/20260927T160923352541Z/cable-input-cover/slice-review.3mf) | 小轴孔面朝床；清两浅方窝，独立首层残料随 Brim 清床。 |

## 已检查的范围

当前 STL 的全部有向三角面与实际原生 3MF 对应；G-code、配置和摆向都有文件散列绑定。所列轴孔、六角套窝、球端和钢丝姿态的名义线珠净空已经核对；支撑的前序承托与反打印生长方向的退出路径见[支撑审查](../current-eclip-support-review/README.md)。实际 PETG 剥离力、下垂和承面质量没有经过实物验收。

止挡螺母报告中的原始接触旗标保留。[独立复核](../current-eclip-slices-review/stop-nut-audit/report.json)将其定位到预期轴向承面，未发现同尺寸螺母的径向插入冲突。报告中的 0.019 mm 是名义线珠接触位置差，不是要求用户测量的精度，也不能替代实际坐实后的止挡校准。

所用配置为 X1C、0.4 mm 喷嘴、Generic PETG、Textured PEI；用户已确认 PETG/PEI，但具体耗材与 PEI 表面类型仍属于工艺假设。主体冻结调用记录有一句旧的“两处支撑”说明；实际 enforcer、原生 3MF 和最终审查均为背板加两浅窝共三处，以实际产物为准。

## 仍未验证

轴销卡簧的真实安装与保持载荷、POM 套和打印件配合、夹线抗滑、护套坐深、摩擦及带载回位、止挡误差，以及实际单球送料与旋转效果仍待正式总成验证。没有新增消耗性试片，也没有发送打印或采购。

`manufacturing_release=false`、`physical_acceptance=false`、`sent_to_printer=false`、`goal_complete=false`。数字文件完整不构成“一次装配必过”的保证。
