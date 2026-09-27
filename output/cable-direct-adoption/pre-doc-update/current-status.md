# 当前工程状态

> 当前拉索版的完整场景已发布；统一制作包尚未完成。早先38件支座服务修订记录为 `SERVICE_REPAIR_FAIL_OR_STALE`，其中旧压盖导出字节身份失配保留在[历史执行记录](../output/fixed-hardware-audit/service-resumption-evidence.json)及[身份差异诊断](../output/fixed-hardware-audit/service-keeper-identity-diagnostic.json)。本轮从当前源重新建立55打印实例的独立导出证据，没有把旧失配报告改成通过；网格通过仍不等于新切片、全公差或实物验收。

现有送料修订候选为38件，旋转头为10件，见[装配、裁管和五金说明](final-assembly.md)。这48件是未加入下述拉索替换与新增件的基线数量，不能直接作为拉索整机的最终打印清单。当前没有打印、实物装配或发球记录，不能认定“保证一次过”已完成。

拉索扳机整合入口为 `cad/cable-trigger-system.scad`，含护套导向的局部总装为 `cad/cable-complete-review.scad`，见[固定、动作及装配核验](cable-trigger-integration.md)。当前[统一实例清单](cable-assembly-inventory.md)为45送料/拉索打印件加10旋转头打印件；五金和参考组另列后共84项场景资源。网页已改为该版本，旧33件示意和发布文件保留在历史目录；正式切片包仍未同步完成。

[新导出报告](../output/cable-scene-export/20260927T071458613482Z/report.json)的55打印实例均通过边拓扑、精确面积、顶点链接、单连通及CGAL回读；全部84项源身份在执行期间稳定。[清单/原生参数审查](../output/cable-inventory-audit/report.json)、[前端运动验证](../output/cable-scene-web-review/report.json)与[Chrome实际页面检查](../output/cable-scene-export/20260927T071458613482Z/browser-review.json)分别记录不同范围。页面已验证84项加载、满扣20 mm、释放归零，以及切换视角/剖切/显隐保留场景节点。不能把网页动画当作载荷或发球验收。

拉索候选已修正两端M6螺母/垫片叠层、输出金属垫圈捕获、螺钉外通空间和尾线出口，并建立完整名义护套路线。[222项整机几何检查](../output/cable-trigger-system/20260927T065201380834Z/report.json)及[局部护套路由检查](../output/cable-housing-route/20260927T065201352420Z/report.json)记录对应快照通过，执行时源身份稳定；可查看[该快照同源总装渲染](../output/cable-trigger-system/20260927T065201380834Z/rest.png)。后续新增或修改固定结构须重新核对受影响源和检查，不能继承这次通过。

第三弯另已增加可拆护套导向，含实体包边、下托及自身硬止挡，见[导向固定与装拆说明](cable-route-retention.md)。其当前源通过[16类既有服务通道及阳性对照](../output/cable-retention-service/20260927T070337333817Z/report.json)，局部装拆/捕获证据单独记录，未冒充被上述222项覆盖。含导向的入口为 `cad/cable-complete-review.scad`，可直接看[当前机构渲染](../output/cable-route-retention/complete-assembly.png)。护套前两弯及自由段、真实周边避让、实物端套坐深、夹线能力、结构刚度和带载回位仍未闭合，所以不能认定全部固定和机械逻辑已完成实物验收。

[九件新增/替换件的打印摆向评审](cable-print-orientation-review.md)及[首轮离线切片审查](cable-offline-slice-review.md)已完成。四件平面件完成限定特征路径审查，其中输入盖由0.2改为0.1 mm层高，修正三处承面的0.1 mm偏差。输入座M6孔内支撑、关闭支撑后的两处座底悬挑、扳机2.2 mm高出口上方长唇悬空，以及结构件支撑清理和承载仍未闭合。主座3MF两面数值收缩另有逐面/拓扑解释，严格面数身份失败仍保留。不能把切片生成或部分路径审查作为整机制造放行。

后续已将输入座两处座底接到底面，孤立候选的无支撑切片不再出现悬臂警告；0.1 mm层高同时修正定距管承面及止挡螺母窝顶的+0.1 mm偏差，见[候选重切记录](../output/print-review/current-cable/body-seat-candidate/slice-review.json)。正式CAD与网页仍为原版本，候选尚未合入。扳机还检出松线后脱槽/释放扫回夹线风险，正在重做导线捕获；原R60动画也没有计入线芯靠槽内壁后的有效半径变化，不能继续把名义20 mm当作实物精确收线。

[新的直拉诊断候选](../output/cable-input-lip-candidate/README.md)已冻结为`491ded7714…`：固定导线脊承担出线弯曲，球头由两颗M3连接的独立端盖捕获；手指和主轴接口保留。下臂与端盖已实际0.1 mm无支撑切片、无原生警告，三个名义姿态的新增实体对当前局部总装未见相交。新主体的导出网格、受影响工具/止挡/切片及回位载荷仍需后续完成，未合入正式CAD或完整网页，不得把它计入当前55件制作清单。详见[阶段证据](../output/cable-input-lip-candidate/phase-review.json)。

该候选本体随后已由同源原样CGAL导出通过严格网格核对，Manifold失败留档。两新件的分面、球窝、线口及真实六角螺母包络已完成限定路径检查。不过[调节器移动检查](../output/cable-input-lip-candidate/adjuster-travel/20260927T083207056075Z/report.json)又确认：名义0.2 mm轴向间隔不足，M6金属端前移0.5/1 mm时与固定导向分别有约2.49/6.63 mm³真实相交。因此该候选仍需修正入口直段和调节余量，不能将局部运动/切片通过写成可制作定版。

后续[直拉 v2 候选](../output/cable-direct-pull-v2/README.md)已把入口改为名义5 mm直段、±2 mm装配调节，并建立等长护套路线。局部原生运动/捕获检查、总装三姿态×三设置、16类路线服务通道、主体及拉臂实际0.1 mm无支撑切片均已有分范围证据。后侧螺母窝顶桥接、实际导向接触/摩擦、供应件坐深及正式CAD/场景采用仍未完成；不能把无切片警告或这些有限数字检查写成整机放行。原55件网页仍未更新，新的离线[完整送料与拉线装配图](../output/cable-direct-pull-v2/render/whole-pulled-reverse.png)单独标注候选身份和范围。

## 本次修订

- 公共架新增两条独立Y压条、两端顶丝和锁母，配套修改两支座与两导向盖；四套挡指载体Y压条保留。原公共架固定0.4 mm间隙不再是唯一选择。
- 入口使用22 mm宽分体外夹、刚性双支架与背梁背板，共3个打印件。软管套接仍为28 mm；名义3 mm柔衬适应钢丝外表面，外侧新孔供20 mm织带卸载。结构装入及名义五金检查与实物夹压分别记录。
- 导向盖采用M3×20安装螺钉；左支座重新贯通原安装孔，避免螺钉末端撞到后加的弹簧筋。四个载体Y外盖增加安装螺钉头部让位。
- 原主壳、V定位挡指、肩销压块、回位弹簧接口和出口捕获座保留。已有严格网格、CGAL回读、总装相交及打印件两两检查记录须按各自源身份读取；旧33件总报告不覆盖本轮38件修订。
- 旋转头10件及其五金不变；摩擦垫为TPU95A HF，38＋10基线中的其余47个打印件用PETG。加入拉索替换/新增件后，当前统一清单为54个PETG实例和1个TPU实例。外缝封口用SCS2700 LM，管口外包用Scotch70。

2026-09-27只读核对发现，现存[送料报告](../output/launcher-final/report.json)记录的是**33个实例**，[送料切片报告](../output/print-review/final-feeder/report.json)记录的是**33个实例、20类几何和20个采用板**。两报告中的 `analysis/launcher_final_assembly.py`、`cad/launcher-final-assembly.scad` SHA256均与当前文件不同；报告中的PASS属于旧快照，不能读作38件已通过。旧33件/20板证据另保留在 `output/print-review/final-feeder/baseline33/`。

38件修订的切片**计划**覆盖24类几何：8类改件待上游冻结并通过后重切，16类仅在当前STL、原切片输入和配置全部满足身份条件时才能复用。实际板数和采用清单以新审查完成后的报告为准，目前不声明“38件24板已完成”。旧调用记录不能改写成新切片。[旋转头切片](../output/print-review/final-spin/report.json)是独立10件记录，也不能补足送料或拉索新增件的检查。

## 尚未完成的实物与全误差认证

新增公共架Y调节已关闭明确的可调结构缺口。[轨姿态界](frame-y-guide-bound.md)给出接触域成立时的条件比较；[旧整机误差报告](final-gate-error-bound.md)明确标为33件历史基线。新版整机±1 mm总误差预算仍未认证，轨姿态条件界不能代替它。

真实打印配合、支撑清理后的表面、V座/M2预紧保持、PETG承压与蠕变、柔衬材质、钢丝软管夹压/抗拔、气密及带载弹簧回位均未实物验收。取消桥箍型号依赖不等于已测得软管摩擦或密封能力。

正常点射的工作条件是球已到位、完整扣动、离球后完整回位。静态单球腔与后挡隔球证据不能代替动态进球和推进测试；空按、半程回扣属于额外防误操作要求，未强行加入三重联锁。风机额定与新增模块气动余量不能从21/42 V历史经历推导。

以上边界不要求用户先耗材打印试片。数字候选、浏览器预览与离线切片均不是首机实物验收。

## 文件与局域网

送料修订入口为`cad/launcher-final-assembly.scad`，旋转头为`cad/spin-head.scad`，拉索整合候选为`cad/cable-trigger-system.scad`。`output/launcher-final`中现存报告仍属上述33件快照；目前没有覆盖这些入口的统一已发布制作包。不要遍历整个output目录打印历史件与诊断相交体。

[局域网地址](http://192.168.7.187:8877/)由当前macOS登录会话的launchd维持。发布脚本核对源、报告、STL与下载包的身份；服务使用no-store防止浏览器继续显示旧版。服务文件和访问记录在`output/preview-service/lan-verification.json`；本机经LAN IP访问不冒充第二台设备验证。
