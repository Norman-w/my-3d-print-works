# 直拉v2正式采用与完整场景同步

本目录记录本轮从冻结候选采用到正式CAD、清单、网页的过程。机械源采用后为 `cad/cable-trigger-input.scad` SHA `e243be6b39956ae2ac28bda58c8f3d92bcf4e9a04b28818d8b37d65dea276d07`；旧权威源和网页保留在 `../cable-direct-pull-v2/pre-adoption/`。`adopt_input.py`是一次性迁移辅助，不应作为日常重建命令重跑，它会覆盖后来增加的父入口内容。

## 已完成

- ci输入固定导向直拉、端球捕获盖、±2 mm调节和等长cr护套路由进入正式源。
- 主系统、导出选择器、85行清单和前端统一新运动合同；精确native合同避免6位有效数字舍入。
- 当前源总装244项检查、85行导出/56打印实例网格与CGAL回读通过，输入四件与冻结v2逐三角坐标集合相同。
- 驱动预算用真实长度反解及变力臂，满20 mm为19.334251925°。±2 mm调节后重新坐实护套、布线及重设输出零位。
- 新端盖9项台架服务顺序检查通过，错误顺序检出实料阻挡。
- 实际Chrome页面加载85项，满扣/释放和相机/剖切切换均保持同一场景及实例；本机LAN回读当前资源字节一致。
- 同源原生CAD渲染已经目视检查；公开页面已更新，旧发布备份保留。

证据入口：

- [当前总装](../cable-trigger-system/20260927T091437982269Z/report.json)
- [当前网格](../cable-scene-export/20260927T091627124663Z/report.json)
- [网页验证](../cable-scene-export/20260927T091627124663Z/browser-review.json)
- [源合同审计](contract-audit.json)
- [候选/正式实体一致性](mesh-parity.json)
- [驱动预算](../cable-actuation-v2/20260927T091604751038Z/review.md)
- [服务补充](service/README.md)
- [原生图](render/20260927T091713271855Z/whole-pulled-reverse.png)

## 下一层工作

局部支撑工艺在 `../cable-direct-pull-v3/` 独立记录；v3是切片工艺候选，不是又一次修改机械实体。统一56件制作计划尚未建立，旧 `scripts/review_cable_slice.py` 默认报告及body/lever计划仍是历史诊断，不可直接当作本版制作入口。

未宣称物理公差、端套坐深、摩擦、夹线、紧固、PETG承载/蠕变、带载回位、单球与旋转已验收。也没有下单、发打印或要求用户打印试片。几何动画与真实运动性能分开。
