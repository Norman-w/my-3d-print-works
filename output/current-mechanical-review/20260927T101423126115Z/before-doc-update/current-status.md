# 当前工程状态

正式CAD与完整三维场景已采用固定导向直拉v2，当前快照为`20260927T091627124663Z`。已完成数字采用和场景同步，制作包与实物验收尚未放行。

送料基线38个实例中替换背梁/滑架，新增8个拉线实例；送料46件加旋转头10件，共56个打印实例（55 PETG、1 TPU95A HF）。五金和参考显示组另列，场景共85项。数量与身份见[统一清单](cable-assembly-inventory.md)，不能使用旧33、38或55件的历史打印清单拼接制作。

## 本版完成

- 替换旧收线包绕机构，端球由螺钉盖捕获，固定导向承担钢芯转弯；入口名义5 mm、±2 mm装配调节消除了早期端口碰撞。
- 扳机向虎口勾扣，满20 mm收线对应19.334251925°，指端近向11.918827663 mm；扳机、端盖、金属和钢芯共用同一非线性长度解。
- [244项当前总装几何检查](../output/cable-trigger-system/20260927T091437982269Z/report.json)通过；[85项当前源导出](../output/cable-scene-export/20260927T091627124663Z/report.json)与56打印实例严格网格/CGAL回读通过。
- [驱动预算](../output/cable-actuation-v2/20260927T091604751038Z/report.json)已更新：目录弹簧理想指力4.958～13.627 N，未包含真实摩擦。裸芯总长和路线只作几何预算，不作裁长。
- [Chrome实际页面](../output/cable-scene-export/20260927T091627124663Z/browser-review.json)加载85项，扣动/释放正确，切换视角及剖切保留原场景节点。本机访问LAN地址已核对服务文件身份，不冒充另一设备验收。

查看[固定与动作说明](cable-trigger-integration.md)或[本版原生总装效果图](../output/cable-direct-adoption/render/20260927T091713271855Z/whole-pulled-reverse.png)。完整场景仍可切换送料、扳机、旋转头和总览视角，显示/加载独立；未丢弃其他模型。

## 制作与物理边界

已建立[当前56件制作索引](current-manufacturing.md)，逐件绑定当前STL、实际3MF/G-code或明确待处理项，按盘核对数量。旧送料23件、旋转头10件和拉线10件有复用绑定；另13个送料实例已用当前几何重切8盘，其中12实例完成报告所列限定检查，入口后夹整树拆除顺序仍待审。合计55实例绑定41张限定审查板，1实例/1板单列候选。完整状态以索引为准，不把历史33件/20板报告补写成新版通过。

输入座、拉臂、球头盖已采用实际0.1 mm局部manual支撑，主盖0.1 mm无支撑。[首层残料分类](../output/cable-direct-pull-v3/first-layer-island-review/report.json)确认3个额外小岛位于实体外，与Brim一道清床，其余支撑在原开口内。名义清理路径已有依据，真实PETG分离力和承面质量未验证；不能沿用旧0.2 mm自动树支撑配置。见[四件当前工艺绑定](../output/current-manufacturing/input-process/README.md)。统一索引已经建立，制作放行仍未完成。

四孔固定、捕获结构与张紧线芯传力已具名义几何依据；实际打印尺寸、支撑清理、钢芯/护套摩擦、端套坐深、夹线强度、紧固、PETG蠕变及带载回位仍未实测。前两护套自由弯与未知风机/三通/人体空间不作完整实装保证。

正常点射仍依赖球就绪、完整扣动及离球后释放。新版整机公差预算和风机气动余量未全部闭合，不能据动画或网格宣称“一次过”、单球性能或旋转效果。当前没有打印、实物装配或发球记录，也没有把试片成本转交用户。

## 入口和历史

- 局部完整机构：`cad/cable-complete-review.scad`；输入：`cad/cable-trigger-input.scad`；送料：`cad/launcher-final-assembly.scad`；旋转头：`cad/spin-head.scad`。
- [局域网完整场景](http://192.168.7.187:8877/feeder-motion.html?view=system)，服务继续由既有launchd维护。
- [采用前状态原文](../output/cable-direct-adoption/pre-doc-update/current-status.md)保留此前失败及分阶段证据；其“当前”仅针对旧快照。
- 原包绕回程夹线、v1调节碰撞、不同支撑候选失败均保留，不覆盖为通过。冻结v2四件与本版的[实体一致性](../output/cable-direct-adoption/mesh-parity.json)已核对。

`manufacturing_release=false`、`physical_acceptance=false`；“保证一次过”的目标仍在进行。
