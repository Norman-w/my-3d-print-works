# 当前入口后夹：限定数字制造绑定

已将第三工艺候选绑定到当前 `feeder/inlet-rear`。机械 CAD、STL 和完整场景未变；采用“后键端朝打印板、+CAD Y 生长”的摆向，0.2 mm 层高、原 0.35 mm 支撑 XY 间隙。这里只完成数字证据选盘，`manufacturing_release=false`、`physical_acceptance=false`、`sent_to_printer=false`。

[绑定清单](manifest.json) · [实际 3MF](../../current-inlet-process-revision/runs/20260927T110450585847Z/inlet-rear-rear-key-ends-down-supported/slice-review.3mf) · [实际 G-code](../../current-inlet-process-revision/runs/20260927T110450585847Z/inlet-rear-rear-key-ends-down-supported/plate_1.gcode)

## 完成的限定核对

- 当前 STL 与原生 3MF 的 1728 个有向面对应，原生无修复/警告；实际配置、打印板范围、嵌入 G-code 和外存文件已绑定。
- 四段后定位键从首层开始，随后 29 层连续存在，未重现前两候选的上片悬空首道。两个孔、两个绑带槽没有模型封顶。
- 两 M2.5 螺杆、两 M4 螺杆与两 AF7 螺母轴向入位的完整名义体积均不撞模型路径。孔窝内支撑单独记录，先清除再装五金。
- 锚板和两螺母肩台按实际 G-code 先后核对。锚板最长已识别直线无下托段约 4.60631 mm，两端有此前投影承托；M4 肩台最早环弧仅有少量珠体边缘搭接。没有把后打的路径倒算成先前支撑。
- 全部实际支撑的退取投影及原命中逐路径定位，未发现位于支撑起始层底以下的后续障碍。原源曲面 tri90 的起始交叠来自连续 CAD 与打印台阶差异，该区实际支撑/模型非零体积相交对为 0；五处其余模型命中按命令层面为共同边界，其中四处的声明层高比实际 Z 增量多 `0.000001 mm`。

原严格零交叠失败全部保留。这里分类的是起始边界接触及其来源，**不把接触说成始终有正间隙**，也不据数值分离界保证真实 PETG 可以整块轻松拔下。

## 清理与装配衔接

脱离打印板后，模型与支撑的名义分离方向为后定位键伸出方向，即 CAD −Y、朝原打印板方向。接触分离后，沿该方向移走外部支撑；抓持外部支撑，不以细定位键作撬动支点。模型保留完整，不要求先切断它的任何部分。

背梁贴合面、两定位键、两 M2.5 孔、绑带槽、M4 螺母窝及其承面需清屑后再进行背梁预组。轴向通路可容纳名义五金，不代表可以带着支撑用螺钉拉入。操作力、支撑分离、抓持和清理后的实物尺寸仍待正式成品确认。

## 保留的制作和整机限制

锚板短跨、肩台小面积边缘搭接、0.2 mm 支撑顶间隔、同料 PETG 黏连及实际承面质量没有实物证据；其风险没有因选盘消失。0.018900 mm 的局部名义同层路径间距仅用于解释源曲面命中，不作为可保证的制造间隙。Generic PETG / Textured PEI 仍是分析配置；用户仅确认 PETG、PEI、X1C 和 0.4 mm 喷嘴。

采用本盘后，统一索引为 56 实例绑定 42 盘。整机公差、受载失程、回位、夹丝保持和发球性能仍未完成，不能将“有绑定文件”解释成“已经保证一次装成”。

## 证据入口

- [四候选比较与保留失败](../../current-inlet-process-revision/README.md)
- [本候选首道承托](../../current-inlet-process-revision/runs/20260927T110450585847Z/inlet-rear-rear-key-ends-down-supported/underlay-review.md)
- [完整名义五金体积](../../current-inlet-process-revision/runs/20260927T110450585847Z/inlet-rear-rear-key-ends-down-supported/hardware-volume-review.md)
- [起始接触来源](../../current-inlet-process-revision/runs/20260927T110450585847Z/inlet-rear-rear-key-ends-down-supported/initial-compatibility-origin.md)
- [全树命中定位](../../current-inlet-process-revision/runs/20260927T110450585847Z/inlet-rear-rear-key-ends-down-supported/hit-localization.md)
- [只读重建绑定脚本](bind.py)，不切片、不打印。
