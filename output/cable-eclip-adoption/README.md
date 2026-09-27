# 标准槽销轴已采用，制作与实物验收未放行

后续制作更新：三个改形件已完成新切片及限定审查，当前为56实例/42板，见[新版制作入口](../current-eclip-manufacturing/README.md)。下文53/3及39板是CAD采用时的冻结阶段记录，不是最新制作状态。

**正式CAD和完整三维场景已更新到HCDG8-30＋原配NETW7轴设计。** 原四M4主机孔、固定导向直拉v2及向虎口扣动保留。新场景为`20260927T153058669616Z`，86显示项含56打印实例；新增卡簧空间参考默认隐藏，不是实际E环实体。

[本次汇总](latest.json) · [机械结论](../../docs/current-mechanical-review.md) · [完整三维场景](http://192.168.7.187:8877/feeder-motion.html?view=system)

## 已完成的实际检查

| 范围 | 本次结果 |
|---|---|
| [CAD迁移](20260927T151752917841Z/cad-review/report.json) | 21项几何等价；12组运动数值、5档护套路由精确匹配；3项越界负控拒绝。基准从采用前源冻结，不从新源自我复制。 |
| [总装](../cable-trigger-system/20260927T152544768903Z/report.json) | 244项名义检查通过；有限姿态及报告列明的连续包络，不是完整公差/承载证明。 |
| [路线](../cable-housing-route/20260927T152611143454Z/report.json)与[驱动](../cable-actuation-v2/20260927T152544767413Z/report.json) | 25项路线检查通过；固定导向长度解及理想传力复算通过。 |
| [86项导出](../cable-scene-export/20260927T153058669616Z/report.json) | 56打印实例拓扑及CGAL回读通过；五金/参考分组只作显示。 |
| [浏览器](../cable-scene-export/20260927T153058669616Z/browser-review.json) | 实际加载86/86；扣动20 mm与释放归零；切视/剖切保留全部实例；空间参考可开关。仅本机访问LAN地址，非另一设备验证。 |
| [制造绑定](20260927T151752917841Z/manufacturing/binding-02/report.json) | 53实例复用39板，3改形未重切、无选定板。38件同字节、14件有向三角面严格同集合、端球盖按+Y3映射后严格同集合并核对实际3MF摆向。 |
| [装配五金](../current-assembly-package/runs/20260927T154004364940Z/README.md) | 45类规格、56打印取件身份；销与随附环各装1件，采购根仅1套。共享四M4原螺母只算一次。 |

![扣住状态的原生CAD渲染](../cable-direct-adoption/render/20260927T152544756846Z/whole-pulled-reverse.png)

[释放图](../cable-direct-adoption/render/20260927T152544756846Z/whole-rest.png) · [扣住图](../cable-direct-adoption/render/20260927T152544756846Z/whole-pulled.png)。这是实际局部送料/拉线CAD；外部风机、三通、人体位置未知，完整网页仅作参考布局。

## 明确修正与保留边界

旧M4轴栓夹紧力经过PETG端座，已改为销头/槽内卡簧轴向保持。两侧M3独立固定主盖；加工POM-C六角套和两内Ø10推力垫替换旧圆套/小孔垫。销从盖侧穿入、背侧套两尾垫并装原配卡簧；实际工具和完全入槽仍须验收。

[独立采用意见](../current-axis-eclip-candidate/engineering-adoption-review.md)解释完全入槽E环与横孔开口销的自由度差异。R10等空间仍是工程接收要求，非厂家精确安装态网格。[工具资料](../current-axis-eclip-reference/tool-followup/README.md)不足以认证工具头进入。

初次整组CGAL融合五金触接面出现非流形警告，保留[失败导出](../cable-scene-export/20260927T152609986811Z/report.json)。最终按真实模块分开导出CGAL销（1436面，单件拓扑通过）与其余Manifold五金，再仅拼接显示三角面；没有压掉警告或把五金组当打印实体。组件构成有源码断言，完整报告记录两份原生来源。

当前仍未完成：新版三件切片与清理审查；实物卡簧/工具/保持载荷；真实加工配合、夹丝抗滑、端套坐深、行程失程、摩擦与带载回位；动态单球及风机/旋转效果。没有采购、打印或要求消耗性试片。CAD采用不等于保证实物“一次过”。

采用前[205文件存档](20260927T151752917841Z/pre-adoption-source.tar.gz)、[SHA清单](20260927T151752917841Z/pre-adoption-sha256.json)与[旧完整状态](20260927T151752917841Z/pre-adoption-docs/current-status.md)保留。历史候选目录中的“未采用”和旧源绑定均属于其冻结时点；不要重新拼接旧候选作为当前CAD。

`adopted=true`、`manufacturing_release=false`、`physical_acceptance=false`。
