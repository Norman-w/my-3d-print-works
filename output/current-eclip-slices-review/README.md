# 新版 Eclip 输入机构：实际切片路径审查

三个新件共五个工艺对照已读完。来源和G-code均以每份artifact-review的SHA锁定；没有改CAD、重新切片或发送打印。所有检查仍是离线路径层级。

| 零件/候选 | 模型进入要求金属/线芯包络的命令数 | 关键结果 |
|---|---:|---|
| cable-input-body / negative-control-original-two-enforcers | 0 | body_through_axis 净径下界8.26676 mm；背板支撑投影0.00/4415.95 mm² |
| cable-input-body / body-full-backplate-support-candidate | 0 | body_through_axis 净径下界8.26676 mm；背板支撑投影4377.13/4415.95 mm² |
| cable-input-lever / lever-current-slice | 0 |  |
| cable-input-cover / negative-control-cover-minus-Z-ring | 0 | cover_main_axis 净径下界8.25144 mm；cover_root_relief 净径下界9.16643 mm |
| cable-input-cover / cover-plus-Z-pocket-support-candidate | 0 | cover_main_axis 净径下界8.26692 mm；cover_root_relief 净径下界9.16674 mm |

- 主体原两enforcer对新增背板底面没有支撑；补全背板后的投影明显改善。原无支撑候选作为失败对照保留，不可凭两M3支撑或native warning为空推整块背板可打印。
- 原盖−Z摆放在2.7→2.8 mm有0.45 mm径向悬边，无支撑。沿圆周缺下承路径19.7168 mm不是桥接跨度；独立近距图和距离界在cover-step目录。+Z摆放消去此环形下表面，改为核验两M3方窝顶的支撑。
- 杠杆使用当前固定导向直拉公式、完整旋转30°AF12 POM六角，而非旧圆形或旧−28.8导向公式。球Ø5和钢芯Ø1.5近端12 mm在u0/10/20/22均对命令线珠留正余量；四点不是连续运动证明。
- 螺母窝/方窝内生成的支撑真实占用装配空间，须在五金装配前从打印床一侧清理。投影覆盖和有入口不等于已经证明支撑可拆净、孔不受伤或底面合格。
- 推力面单列PETG源面与实际路径投影；没有把六角孔内的独立POM件虚构成PETG实体，也没有把0.5 mm转子名义浮动等同于整根销的捕获浮动。

脚本：`analysis/cable_eclip_axis_slice_review.py`；复跑单件：

```sh
/Applications/FreeCAD.app/Contents/Resources/bin/python analysis/cable_eclip_axis_slice_review.py --folder output/current-eclip-slices/20260927T160923352541Z/cable-input-cover --output output/current-eclip-slices-review/20260927T160923352541Z/cable-input-cover
```

自测覆盖当前非线性4姿态、完整六角、零厚承面接触和反向盖法向手性。所有JSON和图像路径及SHA见summary.json及逐件report.json。没有强度、实际清理或首机功能放行。
