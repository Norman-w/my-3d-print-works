# 当前工程状态

正式CAD与完整三维场景已采用固定导向直拉v2，当前快照为`20260927T091627124663Z`。已完成数字采用和场景同步，制作包与实物验收尚未放行。

当前主轴选型收敛到[MISUMI HCDG8-30＋原配NETW7 E型卡簧＋两尾垫](../output/current-axis-eclip-candidate/README.md)。厂家L段与槽尺寸已有明确公差；新隔离模型完成152对声明空间关系、完整转子的连续名义净空及路线检查。标准槽销取消中央锁母预紧和手弯开口销；实际卡簧安装后轮廓、入槽/工具、头根参考尺寸及受载仍开放。正式场景和打印包仍对应原L15轴系，没有把隔离候选写成已采用。

[开口销分支](../output/current-axis-pin-retention/README.md)保留条件检查历史；其绕横孔轴滚转尚无可达范围证明，原薄盘不能仅凭初始弯脚方向视为运行中恒定，未证明实际碰撞，已取消优先整合标记。

原L15轴的锁紧力经PETG端座，旧L27贯穿管又与背梁碰撞；[肩轴与杯垫片分支](../output/current-axis-offset-candidate/README.md)虽已形成金属闭合，[安装扭矩/夹力窗](../output/current-axis-offset-candidate/locking-load/README.md)仍未闭合，现保留为比较记录。标准销候选减少了这一装配变量，仍不等于可靠回位：[21组自重预算](../output/current-return-budget/moving-mass/README.md)已经量化，[测力判据工具](../output/current-return-budget/measurement-assessment/README.md)当前真实记录仍为0条。

最初[DIN471槽销来源筛选](../output/current-axis-circlip-reference/README.md)未找到完整配套；后续[HCDG8-30厂家资料](../output/current-axis-circlip-reference/alternate-supplier/README.md)提供了更明确的实际订购型号，它配E型No.7环，与DIN471不同。[OCHIAI ETW-7](../output/current-axis-eclip-reference/ring/ochiai-etw/README.md)的推荐槽径与本销不重合，未直接替换原配NETW7。E型候选使用自己的原生检查，没有继承横孔销报告。

送料基线38个实例中替换背梁/滑架，新增8个拉线实例；送料46件加旋转头10件，共56个打印实例（55 PETG、1 TPU95A HF）。五金和参考显示组另列，场景共85项。数量与身份见[统一清单](cable-assembly-inventory.md)，不能使用旧33、38或55件的历史打印清单拼接制作。

## 本版完成

- 替换旧收线包绕机构，端球由螺钉盖捕获，固定导向承担钢芯转弯；入口名义5 mm、±2 mm装配调节消除了早期端口碰撞。
- 扳机向虎口勾扣，满20 mm收线对应19.334251925°，指端近向11.918827663 mm；扳机、端盖、金属和钢芯共用同一非线性长度解。
- [244项当前总装几何检查](../output/cable-trigger-system/20260927T091437982269Z/report.json)通过；[85项当前源导出](../output/cable-scene-export/20260927T091627124663Z/report.json)与56打印实例严格网格/CGAL回读通过。
- [驱动预算](../output/cable-actuation-v2/20260927T091604751038Z/report.json)已更新：目录弹簧理想指力4.958～13.627 N，未包含真实摩擦。整根线芯名义中心线路径包含护套内部分，只作几何预算，不作裁长。
- [当前机械复核](current-mechanical-review.md)明确条件性的18.4214～20 mm功能区间，并把拉索失程、止挡零位及72边形接触延迟计入设置问题；没有把条件误差箱当成已证明的打印精度。
- [止挡区间计算](../output/current-stop-contract/README.md)已同时限制输入和输出的0～20 mm检查域；实际失程及终点误差未知时不输出装配设置。公共架[有限压条接触](../output/current-joint-tolerance/frame-finite-contact/README.md)和[载体/壳体轴承共同约束](../output/current-joint-tolerance/carrier-body-coupling/README.md)补齐局部连续界，完整共同公差域仍未证明。
- [回位预算](../output/current-return-budget/README.md)给出逐位置正余力条件，显式计入重力和外载；零位名义弹簧力2.975 N，真实摩擦和手持姿态下余量仍未知。
- [当前65个送料实例的有限气路](../output/current-airway-review/README.md)在全行程保持连通，覆盖Z−124至133内部截面；不是压降、流量或最终发球能力证明。
- [统一装配入口](current-assembly.md)串起送料、拉索及旋转头，明确共享四长栓拆装须同时承托输入和背梁、输出专用保持垫圈不可省略、长余尾不能装入后运行。29阶段依赖覆盖56打印实例；这是顺序审查，不是所有真实抓持/工具路径通过。
- [整套五金与取件表](../output/current-assembly-package/runs/20260927T124252819653Z/README.md)合并44类规格，移除旧四短栓/旧位置垫片，保留四原螺母一次，套件及其子件分开计数。工作档55打印，保持档另装1叉、1螺钉及1垫片；不把两档全量相加。定距管新增有公差的SPMSS目录候选，实时配置/供货未确认；轴套、垫片、库存与扭矩未因此落实。
- [拉索中段导向自身拆装](../output/current-route-service-review/README.md)确认指定前提下弧盖退出50 mm、下托先降8 mm再后抽100 mm的连续刚性路径。长距离直下确实会撞输出固定桥；四导向安装螺钉拆除后须分别外部承托。没有将该结果扩成整基座、柔线或工具实物验收。
- [主轴夹紧复核](../output/current-axis-clamp-review/README.md)确认L15管两端仍串有打印端座，与侧柱构成公差敏感的并行闭合，不能当作独立金属限压。[原贯穿式浮动通轴候选](../output/current-axis-through-candidate/README.md)后续查出轴头与背梁碰撞；[沉孔肩轴候选](../output/current-axis-shoulder-candidate/README.md)已作修订和限定检查，仍须完成肩端垫片、径向保持及侧柱受力；正式模型未改。
- [四挡指共同轴向界](../output/current-joint-tolerance/half-shell-axial-coupling/README.md)在限定贴合/导向子域内收紧至0.78343 mm；径向和真实球心横向包络仍未闭合，不是整机公差已通过。
- [Chrome实际页面](../output/cable-scene-export/20260927T091627124663Z/browser-review.json)加载85项，扣动/释放正确，切换视角及剖切保留原场景节点。本机访问LAN地址已核对服务文件身份，不冒充另一设备验收。

查看[固定与动作说明](cable-trigger-integration.md)或[本版原生总装效果图](../output/cable-direct-adoption/render/20260927T091713271855Z/whole-pulled-reverse.png)。完整场景仍可切换送料、扳机、旋转头和总览视角，显示/加载独立；未丢弃其他模型。

新增[有限半管中的球心共同包络](../output/current-joint-tolerance/ball-center-coupling/README.md)：名义内半径条件下横向界1.37071 mm，内半径+0.25 mm条件预算下1.62295 mm。[球心与挡指共同复核](../output/current-joint-tolerance/gate-ball-joint-review/README.md)得到前/后By条件界0.69703/0.67995 mm；若同一共同域Bx≤1 mm，静态门距仍有正余量，放行为u>18.59671 mm。Bx共同界仍未证明，这不是实际止挡设置或完整双球功能通过。

[同一销轴的螺母与V座约束](../output/current-joint-tolerance/common-radial-closure/README.md)补入了实际螺母腔对倾斜的限制。在螺纹同轴、螺母就位及V面保持接触的名义分支，局部Y=10.5截面的特定投影界为0.372776 mm；它还没有与共同凸轮姿态、真实配合误差合并，不能当作Bx或完整单球验收结果。

[真实凸轮中面交点](../output/current-joint-tolerance/common-cam-intersection/README.md)已进一步求得载体局部Y*=9.52136～11.47865；整个斜截面仍在有限肩段内，远端条件余量至少1.97849 mm。径向残项的相关消元和实际共同零位尚未完成；宽外包超标不等于可实现碰撞，不据此直接改孔。

## 制作与物理边界

已建立[当前56件制作索引](current-manufacturing.md)，合计56实例绑定42张限定审查板，无未绑定实例。入口后夹采用[后键朝下的第三候选](../output/current-manufacturing/inlet-process/README.md)，替换原待审工艺；其他55实例的模型、材料和选盘未改变。选盘只连接当前几何与有明确边界的数字证据，不等于制作质量或实物放行。

[四候选比较](../output/current-inlet-process-revision/README.md)保留前两版后键悬空首道及第四版起始交叠的失败。第三候选已用自己的路径补齐四键起底、完整五金体积和逐先后底面承托；全树命中未出现更低的退出障碍，源曲面与打印台阶差异、声明层高与实际Z增量差异已逐行分类，原严格失败未删除。锚板4.60631 mm直跨、肩台少量边缘搭接、支撑分离和承面质量限制保留。机械CAD和完整场景未改。

输入座、拉臂、球头盖已采用实际0.1 mm局部manual支撑，主盖0.1 mm无支撑。[首层残料分类](../output/cable-direct-pull-v3/first-layer-island-review/report.json)确认3个额外小岛位于实体外，与Brim一道清床，其余支撑在原开口内。名义清理路径已有依据，真实PETG分离力和承面质量未验证；不能沿用旧0.2 mm自动树支撑配置。见[四件当前工艺绑定](../output/current-manufacturing/input-process/README.md)。统一索引已经建立，制作放行仍未完成。

四孔固定、捕获结构与张紧线芯传力已具名义几何依据；实际打印尺寸、支撑清理、钢芯/护套摩擦、端套坐深、夹线强度、紧固、PETG蠕变及带载回位仍未实测。前两护套自由弯与未知风机/三通/人体空间不作完整实装保证。

正常点射仍依赖球就绪、完整扣动及离球后释放。新版整机公差预算和风机气动余量未全部闭合，不能据动画或网格宣称“一次过”、单球性能或旋转效果。当前没有打印、实物装配或发球记录，也没有把试片成本转交用户。

## 入口和历史

- 局部完整机构：`cad/cable-complete-review.scad`；输入：`cad/cable-trigger-input.scad`；送料：`cad/launcher-final-assembly.scad`；旋转头：`cad/spin-head.scad`。
- [局域网完整场景](http://192.168.7.187:8877/feeder-motion.html?view=system)，服务继续由既有launchd维护。
- [采用前状态原文](../output/cable-direct-adoption/pre-doc-update/current-status.md)保留此前失败及分阶段证据；其“当前”仅针对旧快照。
- 原包绕回程夹线、v1调节碰撞、不同支撑候选失败均保留，不覆盖为通过。冻结v2四件与本版的[实体一致性](../output/cable-direct-adoption/mesh-parity.json)已核对。

`manufacturing_release=false`、`physical_acceptance=false`；“保证一次过”的目标仍在进行。
