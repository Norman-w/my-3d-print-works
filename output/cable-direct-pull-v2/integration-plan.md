# 直拉 v2 正式集成契约清单

**只读审查；不是采用记录或通过报告。** 正式 CAD、网页、公共脚本均未修改，本轮未重跑几何、切片或发布。

## 总体约束

保留当前送料工作行程 20 mm、原挡指时序、弹簧端点与统一坐标。改变输入端角度—收线量关系、端球位置与钢芯路线；新增终端上盖。止挡 16–22 mm 为独立输入校准预算，整机工作仍为 0–20 mm；不可把 u22 样本接到整机 t1.1。v2 delta±2 为装配调节，零位需重设并锁紧；先显示 delta0 静态配置。

检查时独立候选 SHA256：`f76a83eeb95644bd3c856922b31da749cc47c083d688d271116f946493994588`；仍标 DIAGNOSTIC_V2_UNVALIDATED，可能继续变化。该候选已用 C=[−24,0,2]、R60 固定导向、5 mm 名义直入段；不得采用上一候选 C=[−28.8,0,2] 的数字。正式采用时以最后冻结源回读为准。

## 最小计数变化

新增 `feeder/cable-input-terminal-cap` 1 件。若 2 个 M3x8 螺钉和 2 个 SW5.5/H2.4 螺母纳入原移动五金组：输入打印件 3→4，新增打印件 7→8，送料打印 45→46，总打印 55→56，模型行 84→85；spin10、purchased23、reference6 不变。BOM 必须明确新增 4 个五金实体，不能以模型行数替代采购数量。

## 精确修改映射

### source-contract

定位：`cad/cable-trigger-input.scad:29-51 ci_stop_setting/ci_theta_max/ci_angle/ci_spec`；`cad/cable-trigger-input.scad:85-96 stop fields and part_selectors`；`output/cable-direct-pull-v2/candidate.scad:45-74 cdp_delta/cdp_phi/cdp_path_length/cdp_angle/cdp_effective_arm/cdp_stop_tip`；`output/cable-direct-pull-v2/candidate.scad:336-354 cdp_direct_contract`

**当前假设：** 正式 ci_angle(u)=u/60；theta_max=20/60；球端旧45°。v2为独立cdp_*，目前只有direct_contract，没有现有依赖所需的完整ci_spec函数。

**最小一致修改：** 采用冻结v2到正式源时保留public ci_*接口与完整ci_spec兼容键，新增明确law discriminator、导向圆心/半径/端球零位/轴向直入段/求逆域、delta设定与预算、cap规格。ci_angle统一反解L(a)-L(0)=u；ci_stop_tip调用该函数。radius_cable不能再作为收线恒定力臂，宜改名/保留兼容并注明含义。导向半径和端球臂半径分别命名。合同数值来自正式源码回读，不能直接抄取报告中6位小数替代精密参数。

**验收范围：** 确认所有ci_spec消费者所需键存在；用冻结源码u=0/10/20/22和delta=-2/0/2的数值证据对照。22仅为独立输入端调节/验证，不驱动送料超20。

### scene-adapter

定位：`cad/cable-scene-export.scad:31-35 cse_route_wire`；`cad/cable-scene-export.scad:50-66 cse_item`；`cad/cable-scene-export.scad:78-85 contract`

**当前假设：** 只导出body/lever/cover三输入打印件；lever/hardware/wire使用20*t；静态route芯减去ci_cable(0)。

**最小一致修改：** 新增cse_part=input-terminal-cap，调用ci_terminal_cap(u)；现有移动五金一次包含两M3螺钉和两螺母。20*t改读取正式ci_spec.stroke或单一源函数；仍保持送料20。核验固定route芯和动态input芯在ferrule mouth/固定prefix的分界连续且不重叠；新动态线从端球B→切点T→固定导向弧→轴向prefix→护套口生成。

**验收范围：** 每新增打印实例单连通/精确面/闭网/CGAL回读；t0图形及0/10/20动态端点对照CAD。同一零位装配坐标输出，不能为前端单独移STL。

### catalogue

定位：`docs/cable-assembly-inventory.json:15 baseline.added_printed_instances`；`docs/cable-assembly-inventory.json:18 counts`；`docs/cable-assembly-inventory.json:64-292 scene_contract.ci`；`docs/cable-assembly-inventory.json:2539-2590 input-lever/input-cover rows`；`docs/cable-assembly-inventory.json:3134-3162 input-hardware-moving row`；`docs/cable-assembly-inventory.json:3360-3380 cable-core-input row`；`docs/cable-assembly-inventory.md:65 contract explanation`

**当前假设：** 84行、打印55、送料45、新增7；两个trigger-rotate记录radians_per_t=-1/3；input-wire rest45/end90；打印输入件3个。

**最小一致修改：** 新增feeder/cable-input-terminal-cap printed行，source与definitions使用统一adapter。最小归并方案：两颗M3x8+两颗SW5.5/H2.4螺母放入已有moving-hardware组，采购BOM仍记录实际4件数量。改两旧旋转行+新cap为同一非线性law引用，不保留radians_per_t作为新法。input-wire移除arc_rest_angle_deg/end_angle_deg，换路径law引用；scene_contract重读。更新source_sha256、part_selectors、名称和说明。

**验收范围：** 期望85模型行，printed56=feeder46+spin10，purchased23/reference6，added8，input printed4；如果另拆五金行须按实际新增行重算，不能同时重复纳入原group。输出报告计数与清单计数一致。

### motion-law

定位：`web/cable-scene-kinematics.mjs:15-23 cableContracts`；`web/cable-scene-kinematics.mjs:50-56 triggerPose`；`web/cable-scene-kinematics.mjs:59-75 rigidPose`；`web/cable-scene-kinematics.mjs:88-101 inputCorePoints`

**当前假设：** triggerPose与rigidPose分别用u/R、radians_per_t*t，inputCorePoints按45°圆弧起点推进；这些公式相互一致但只适用旧机构。

**最小一致修改：** 增加单一inputKinematics(u,ci)返回a/phi/B/T/L/有效力臂；triggerPose、rigidPose及inputCorePoints共用。JS使用源参数的解析L+有界二分反解；必须拒绝未知law，不静默退旧。端球零位[0,60,2]由合同读，rigidPose角=-a绕CAD+Y；动态移动杆/端盖/金属同角。球端→切点直线、导向圆弧和固定prefix共用同一解；求逆单调与域界断言。旧law只供明确旧snapshot或law版本。

**验收范围：** 和正式SCAD数字样本比较0/4/10/20（22限诊断），角度/端点/线长误差显式量化。a不线性插值。缺law/缺参数/越界/未知schema负例应失败。

### ui-graph-and-control

定位：`web/feeder-motion.mjs:96 isShell`；`web/feeder-motion.mjs:118-139 applyCableMotion`；`web/feeder-motion.mjs:142-165 updatePose`；`web/feeder-motion.mjs:255-267 snapshot branch`；`web/feeder-motion-kinematics.mjs:12 STROKE;103-114 cyclePose`；`web/feeder-motion.html:29 stroke placeholder`；`web/scene-assets.mjs generic catalogue loading`

**当前假设：** 新cap未进入isShell；detail仍写收线圆弧；cyclePose固定输出20，UI没有止挡或delta设置控制。

**最小一致修改：** 保留一个scene graph及CAD→world映射；新cap按清单自动加载、列表显隐、随扳机同步，并纳入透明/剖视选择。detail改“扳机转过…，通过固定导向拉动滑架…”。初始12mm占位改合同加载中或动态来源。cyclePose的20与挡指时序保留，先断言ci.stroke=co.stroke=motion_schema.stroke_mm=20；不增未验证设置控件。明确当前静态设置stop20/delta0。旧悬空overlay仍禁用，spin非stroke仍静止，视角只切相机。

**验收范围：** 真实浏览器u0/中途/20与返回检查cap/杆/五金quaternion和线芯端点；切视角/显隐/按需加载后sceneIdentity和instanceID不重建，所有85项可达。近端手指world-X，松手反向。图示不宣称摩擦/承载仿真。

### system-collision-coverage

定位：`cad/cable-trigger-system.scad:30-50 ct_fixed_printed/ct_moving_printed/ct_show`；`cad/cable-trigger-system.scad:52-102 ct_probe_geometry`；`cad/cable-trigger-system.scad:118-120 input selectors`；`analysis/cable_trigger_system.py:131 parts;136-143 pose/jobs;162 scope`

**当前假设：** 动态并集只有ci_lever，无新terminal-cap；parts列表6件。input-host/input-output/input-motion/spring-added均可能漏掉cap。

**最小一致修改：** 在moving printed、show、input selector和以上相关探针加入cap；fixed并集不纳入cap。输入moving五金自动含cap紧固件但不得重复球端/钢芯。新增7th part导出。把新候选必要的球端捕获、线芯终端出口、导向/止挡检查接入正式验证，不只依赖旧input-motion。更新scope不再笼统称Current38件。

**验收范围：** 全运动检查t0..1含新增cap与五金；正控仍需失败预期命中。独立输入u22配套stop22，不传整机ct_t=1.1绕过assert；当前全机工作域还是0..20。

### route-delta-and-service

定位：`cad/cable-housing-route.scad:17-23 cr_input_port/cr_vertices;91-93 cr_wire`；`cad/cable-service-contract.scad:7 cs_stop_setting;25 range;60 cs_input_stop_tools;83 cs_input_module_pose`；`cad/cable-route-retention.scad:172 host ci_hardware`；`analysis/cable_housing_route.py:81 dynamic input hardware`；`cad/cable-service-review.scad; analysis/cable_service_review.py; analysis/cable_retention_service.py`

**当前假设：** 路由从ci_spec.adjuster_overall_x等取得端点，服务完整输入模块未含terminal-cap。stop工具默认20，范围16..22。

**最小一致修改：** 新delta只移动adjuster/ferrule及出口，不移动固定锁母/垫圈。ci_spec所有实际入口/出口字段一致带delta；cr_input_port必须跟随。web默认delta0固定路由，若以后显示调节必须重建route并复验，不能只移动螺杆。服务module加入cap及新五金；增加拆cap的轴向螺钉/扳手和cap移出路径前置条件，不能把原主cover移除证明当新cap服务证明。stop工具使用新ci_stop_tip及同一个设置。

**验收范围：** 新件改变障碍后重跑本地route/service；delta边界可利用v2专项证据但须检查同正式源码身份。当前图形中无delta滑块时不声称可实时调。真实坐深仍未知，不由出口CAD代替。

### length-and-force-budget

定位：`analysis/cable_actuation_budget.py:38-54 theta/Rtheta/force ratio`；`analysis/cable_actuation_budget.py:71-91 regex anchor/wrapped length`；`analysis/cable_actuation_budget.py:111 force_interpretation`；`docs/cable-route-review.md:64`；`docs/cable-trigger-integration.md:91`

**当前假设：** 旧裸芯包绕47.1238898由60*pi/4推导，不是字面常量；当前总长960.632和7.251余量来自旧路径。力比R/(r*cosθ)不适用新机构。

**最小一致修改：** 改为实际L(a)-L(0)=u；输入完整外端口至端球长度用固定prefix+导向弧+切线段，避免同时重复计入route端部与input段。输出减少u，总长和应恒定。手指水平理想力比dL/da/(r*cos a)，用新effective_arm或独立导数核验。移除a=45-ci_angle正则。旧文档数字保留为已过时历史，新增当前源预算；不得当剪线尺寸。

**验收范围：** 独立差分dL/da对有效力臂；0..20输入增量+输出减量守恒；delta±2重新定义零位后takeup保持、绝对线长预算按实际端口变。仍限定理想力，无法证明真实回位。

### slice-adoption

定位：`scripts/review_cable_slice.py:47-60 PLAN/DIAGNOSTIC_PLAN`；`scripts/review_cable_slice.py:95-104 selectors`；`scripts/review_cable_slice.py:185-199 flags/gates`；`analysis/cable_direct_pull_slice_review.py:source SHA and feature ROI`

**当前假设：** 正式body/lever仍.2旧plan；新terminal-cap仅DIAGNOSTIC_PLAN并用cil_terminal_cap，正式export不能选此项。旧新候选路径报告为独立491ded源，不能转名当正式。

**最小一致修改：** 在正式采用且源检查完成后将terminal-cap加入PLAN，selector=正式ci_terminal_cap，保留独立旧诊断计划历史；新lever/body层高和支撑按新实路径结论更新，不能只改名字。v2 body/fairlead已变，需当前源实际切片；新cap/lever若严格证明有向几何完全等同旧候选可引用形状证据但仍要正式产物链身份。审查脚本source/ROI从新合同回读，不硬套旧hash。

**验收范围：** 正式export报告→新4件actual3MF→artifact映射/面数或受界规范化解释→路径层位/孔槽/支撑/禁区。新体积支撑可清理性不得用nativewarning空代替。不开打印、不要求耗材试片。

### publishing

定位：`scripts/build_feeder_motion.py:16 WEB_FILES;52 hardcoded48;56 snapshot;67-74 scene/trigger fields`；`scripts/publish_cable_scene.py:40-48 report/inventory guard;91 render copy;105 manifest;136 text;148 stable guard`

**当前假设：** legacy builder会发布baseline33/48项并带旧trigger描述。current publisher正确原样传scene_contract，但硬拷旧output/cable-route-retention/complete-assembly.png，首页写圆弧收线。

**最小一致修改：** v2不运行legacy builder；若保留工具，显式标历史并阻止覆盖current snapshot。current publisher接受fresh inventory/export，新增law无需每行特判；render应来自fresh source身份render报告并校验hash，不继续复制旧PNG。改首页动作描述。新manifest和web_sources/source_sha保真，先stage验证再发布，manifest最后替换，保留备份/不重启服务。

**验收范围：** 发布receipt与HTTP实际返回所有85 mesh/JS/manifest/render hash一致；浏览器控台无错误，实际图形与controls同步；旧截图/旧验收不能冒称新版本。

### tests-and-documents

定位：`output/cable-scene-web-review/test-kinematics.mjs:23-53 old 84 count/angle/45deg ball`；`output/cable-scene-web-review/test-kinematics.mjs:82-94 input-wrap conservation`；`docs/cable-trigger-input.md;docs/cable-trigger-integration.md;docs/cable-assembly-inventory.md`；`docs/current-status.md;docs/final-assembly.md;docs/physical-validation.md`

**当前假设：** 现有纯测试锚定旧导出071458并断言84、-1/3、端球45°，即使改源也可能读取旧证据。

**最小一致修改：** 测试改显式输入fresh report/manifest，验证source匹配；新增cap同步及非线性law/路径。旧测试冻结保留；新测试不把旧fixture覆盖为已通过。文档当前结论更新为源/几何/切片/页面的实际新证据索引，保留历史失败，不沿用实体回位/夹持/耐久未测为已过。

**验收范围：** 旧law兼容独立fixture；新law数字/真实浏览器两层分开。数字验证通过不宣称一次过实物保证。

## 有意义的执行顺序与命令

以下仅建议，必须在对应修改完成和源冻结后执行；本轮未执行。变量尖括号需替换为新产物路径，不能指向旧证据。

### syntax-after-edits

```sh
node --check web/cable-scene-kinematics.mjs
node --check web/feeder-motion.mjs
node --check web/feeder-motion-kinematics.mjs
python3 -m py_compile scripts/export_cable_scene.py scripts/publish_cable_scene.py scripts/review_cable_slice.py analysis/cable_trigger_system.py analysis/cable_actuation_budget.py
```

语法通过只证明可解析。

### source-contract-after-edits

```sh
/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD --hardwarnings -o <new-output>/scene-contract.echo -D 'cse_part="contract"' cad/cable-scene-export.scad
```

new-output先创建；回读ci完整键、law、stop/delta、数量，不用旧JSON替代。

### motion-test-after-new-test-created

```sh
node <new-law-test.mjs> <fresh-export-report.json>
```

建议新入口；当前test-kinematics.mjs没有参数接口且固定旧报告，不能直接当v2测试。

### integrated-geometry-after-freeze

```sh
python3 analysis/cable_trigger_system.py --render
python3 analysis/cable_housing_route.py
python3 analysis/cable_service_review.py
python3 analysis/cable_retention_service.py
python3 analysis/cable_actuation_budget.py
```

分别覆盖全机离散姿态、曲率/局部路由、已声明服务包络、支架与包络、理想线长力比。先补cap/new-law/new-service probe后执行才有意义。本轮未运行。

### source-export-after-freeze

```sh
python3 scripts/export_cable_scene.py --workers 2
```

应85行/56打印，source_stable；历史正式导出不能复用为新身份。

### offline-slice-after-PLAN-adoption

```sh
/Applications/FreeCAD.app/Contents/Resources/bin/python scripts/review_cable_slice.py --export-report <fresh-report.json> --parts cable-input-body cable-input-lever cable-input-cover cable-input-terminal-cap --workers 2
```

当前terminal-cap仍diagnostic门禁；先正式采用PLAN。新切片必须逐件artifact/path review，非发打印命令。

### publication-last

```sh
python3 scripts/publish_cable_scene.py <fresh-report.json>
```

需要已修publisher fresh-render路径及新web验证；随后HTTP身份/真实Chrome统一场景验证。不要运行build_feeder_motion.py。

## 最小图形与控制器同步方案

一个输入求解函数是控制器、扳机/上盖/随动五金刚体角度、端球位置、导向切点和钢芯路径的共同来源。每帧以原送料 u 输入，只解一次 a；所有视角共享同一场景实例。CAD→Three 的现有基底和 feederMount 保留，不为旧假手位置平移新机构。未知 law、缺参数或源/产物身份不符必须失败，不退回旧悬空概念图。

新路径应按相同 u 连接端球 B、切点 T、固定导向弧及护套口。外护套和固定路由芯取同一个 delta；若界面没有实现联动重建，保持 delta0 设置且无交互调节承诺。总览、局部视角、按需加载、显隐、剖切与润滑标记保留。球运动依旧明确为示意。

## 仍不能由本次集成证明

实际摩擦、预紧与回差、夹线强度、PETG长期变形、真实端套坐深、带载回位、一次只出一球和最终风机/三通/人体包络均需相应外部或实体证据。保留这些边界不影响当前继续完成数字集成。所有旧失败与独立候选报告保留；严禁把旧候选切片改名当正式当前源通过。

完整结构化映射、读到的源身份和命令见同目录 `integration-plan.json`。
