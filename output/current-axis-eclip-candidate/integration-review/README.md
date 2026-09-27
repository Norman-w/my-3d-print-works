# E 卡簧轴候选的正式集成清单（只读审计）

结论：可以沿用当前统一场景接口，但必须把输入轴系和偏移路线迁入正式 CAD 后统一导出。不能只换网页几张 STL，也不能让正式 CAD 继续依赖 `output/` 中串联的旧候选。打印实例数应仍为 **56（送料46＋旋转/保持10）**；这不是制造放行。E 环目前只有明确尺寸域的空间预算，尚无实际安装态环形几何或压入工具认证。

## 1. 单一几何来源

1. `cad/cable-trigger-input.scad` 的唯一 `ci_origin` 改成 `[75,-85,5]`。保留 `ci_mount_cad()`、`ci_mount_hardware_cad()` 和四孔的原全球坐标、M4×60 长度及原螺母。局部体通过 `ci_from_cad()` 与原固定背板相接，故**不能把旧整个 body 简单向 −Y 平移3 mm**。
2. 将候选真实几何合入 `ci_local_body()` / `ci_local_cover()` / `ci_local_lever_zero()`：主体与盖 D8.3 贯通轴孔；盖 D9.2、local Z11.3…14.3 根部让位；杠杆 AF12.4 六角贯通套窝。保留局部运动、止挡、线球口、盖螺钉和固定导向。形状以冻结候选为准，正式迁移后做几何等价核对。主体继续 CGAL 导出，不能继承 Manifold 退化网格。
3. 拆出正式的轴件、尾垫、内部推力垫、六角 POM、其他固定五金模块；固定组只含静态件，移动组只含六角 POM/端球/端球盖螺钉螺母。候选的 `ar_rotor()` 是完整组合，**不可直接放进移动五金组**，否则杠杆和端球盖打印件重复，圆形内部推力垫也错误随动。迁移时用显式模块替代候选中“旧五金减去中心大圆柱”的临时分区。
4. `ci_spec()` 保留 `fixed-guide-direct-pull-v2`、20 mm、导向和端球运动参数，更新 origin 并暴露同源轴系参数：HCDG8-30/NETW7、槽位置定义、尾垫规格、六角 POM、内部 ID10 推力垫、已声明工程包络和未证明项。删除或明确废弃旧 `metal_sleeve_*` / 圆 OD12 轴套字段，不能让旧字段继续被当作有效轴合同。旧转子轴向浮量与新整根销捕获浮量是不同量，分别命名，不能用同一 `total_axial_float` 偷换意义。
5. `cad/cable-housing-route.scad` 唯一 `cr_side_run=198`，有限名义域断言同步198和新 origin；保留正式等长算法。不要引用隔离目录的 `input-offset.scad`，它是输入源副本。路线 δ=0 的前两个顶点沿 −Y3，后3顶点及第三弧不动；总外露端口路线由746.507234220变749.507234220 mm。其他 δ 应重新解本路线等长根，不能搬旧 s 值；这3 mm不是裁切许可。

## 2. 实例与五金的准确增减

| 层级 | 删除/替换 | 新采用 | 数量影响 |
|---|---|---|---|
| 打印件 | input-body、input-cover、input-lever 几何变更 | 沿用原3个实例 ID | +0/−0 |
| 端球捕获盖打印件 | 局部形状不变，装配全球位置−Y3 | 沿用原 ID；复用切片必须证刚体等价 | +0/−0 |
| 主轴固定物料 | 定距钢管1、M4×35轴栓1、该轴M4普通垫2、该轴M4螺母1 | HCDG8-30销1、尾部M8垫2、随销NETW7环1 | 5旧→4新 |
| 主轴替换物料 | 圆POM轴套1、ID8.4推力垫2 | AF12 POM-C加工套1、SWSPS16-10-.25推力垫2 | 3→3 |
| 保留 | 四根主机M4×60及其4垫、主机原4颗M4螺母、其余止挡/拉索五金 | 各只出现一次 | 不变 |

上述主轴实体物料为8旧→7新；NETW7是随销成员，采购根不能再把销套件与环相加一次。POM不是新增PETG打印件。MISUMI销的名义参考形状也不是厂家精确CAD。

推荐最小场景方案：保留原两条输入固定/移动五金组 ID；另增 `feeder/cable-input-eclip-space`，`role=reference`、`motion.kind=fixed`，名称写“E卡簧安装空间要求（非环实体）”。因此由85行变 **86行=56打印＋23采购组＋7参考**。这只是推荐展示结构，不是物料计件数；若另外拆分POM/轴/垫片场景行，必须实际重新枚举，不能硬套86。环预算不可作为有体积实体参与实际重量统计。

## 3. 场景、网页及合同同步入口

- `cad/cable-scene-export.scad` 现有 `input-body/lever/terminal-cap/cover` 和 fixed/moving-hardware 选择器可保留；新增独立 `input-eclip-space` 选择器。参考包络与真实五金分开。保留 `cse_route_wire()` 对输入/输出重叠钢芯的差集分区，钢芯仍是一根。
- `scripts/sync_cable_inventory.py` 已从 `contract-precise` 刷新 ci/co/cr，且将杠杆、端球盖、移动五金 motion.origin 从 ci.origin 写入；继续用此入口，不手改网页坐标。它现在硬断言85/23/6，需要为明确新增的参考行更新断言与幂等新增逻辑。body 的 CGAL 设置保留。
- `web/cable-scene-kinematics.mjs` 已用同源非线性反解和 ci.origin，无需改为新运动律；其 origin 一致性拒绝逻辑应保留。当前默认加载全部实例且 `applyRecord()` 会重置 opacity：若新增空间参考行，必须在 publisher 白名单传递明确的 `display_kind/default_visible/opacity` 等字段，并由网页处理；仅在 inventory 填透明度目前无效。建议参考包络橙色透明、默认隐藏但可打开，名称和图例持续说明“空间要求”。不能显示成银色实物 E 环。
- `scripts/publish_cable_scene.py` 目前只传 id/name/role/group/family/motion，后续任何显示字段必须显式透传。需要新导出报告＋新源渲染且目视复核，再发布新的 snapshot；不可改旧 manifest 指向新文件而保留旧哈希。
- `cad/cable-trigger-system.scad` / `cable-complete-review.scad` 已通过 ci 公共模块合成；更新 ci 后自然更新轴。若完整场景也要展示环预算，应单独明确开关，不能把预算体塞进 ci_hardware。`ct_original_fixed_hardware()` 的原4栓替换与原螺母恢复逻辑原样保留。

## 4. 制造、五金包与服务脚本必须调整

1. `scripts/export_cable_scene.py` 本身按实例/后端通用，不需另写出口；对新正式源运行会生成全新时间戳。正式源与候选几何核对、合同一致性、拓扑/主机/路线/服务检查应绑定新源，而不是把旧隔离报告改哈希。
2. `scripts/review_cable_slice.py` 默认仍指向早期071458报告，调用必须显式 `--export-report <新报告>`。body/cover/lever 新几何需要新切片及孔口/承面审查。其 cover 摆向说明仍写旧4.3/4.5座面，须更新到新贯孔/根部让位。`analysis/cable_input_slice_review.py:151`、`cable_direct_pull_slice_review.py:47`、`cable_flat_slice_review.py:74/81` 硬编码−82和/或195；改成读取本次精确合同与 invocation 变换。旧圆套座 floor 的专用分析也不可原样作为新孔的通过证据。
3. `scripts/build_current_manufacturing_manifest.py:17` 硬编码旧091627导出，并核验旧报告所有源仍现存同哈希。采用后它会正确拒绝，不能去掉校验伪装兼容。应参数化当前导出/绑定来源并产生新绑定；旧记录留档。其他52件（56减3改形减1平移盖）的复用按实际新STL字节或明确刚体等价证明；不可仅全局SCAD哈希变动就一律重切，也不可只凭名字继承。
4. `output/current-assembly-package/cable-hardware/extract.py:115…164/226…228` 仍按旧轴源码字面串抽取并期望旧数量。它属于历史冻结输出，**另建正式/新版本提取入口**消费新轴合同，不覆盖旧报告。新BOM须显式去掉上表旧轴物料；保留其他相同SKU安装位置数量，不能全局删所有M4螺母/垫片。
5. `docs/current-assembly-selections.json` 的 `input-axis-distance-tube` 已不适用；`scripts/build_current_assembly_package.py:143…147` 也只认识旧定距管选择字段。替换为销套件、尾垫、POM加工要求和内部推力垫的明确选择/缺口，并更新脚本维度映射与旧 spacer 说明。旧采购/来源报告不改，按新提取结果重建包。
6. `cad/cable-service-contract.scad:23/28/97` 仍写拆“轴螺钉”。更新新顺序：卸载并支承→断开输出芯/护套→拆主机4长栓得到台面模块→处理E环/尾垫/销→再拆盖。台面组装相反：主机4栓未装，盖/转子/POM/内部线芯在场，销从+localZ穿入、两尾垫从−Z套入，随后装环。已存在的台面连续路径证据仅证明销/垫及空侧通道；不证明E环压入变形、钳子或拆环路径。现有 cover sweep 应采用新 cover 真几何；旧肩轴扳手通过不能继承。

## 5. 最短采用顺序与验收边界

**正式ci/轴合同＋cr → 新精确合同与inventory → 源等价/局部及主机检查 → 新统一导出 → 新渲染并发布 → 3件新切片与其余按身份转移 → 新五金/制造/装配包。** 56打印断言可保留；85场景行断言仅在采用上面独立参考时变86。

只读依据包括最新 `runs/20260927T145851957995Z/report.json`、偏移路线 `runs/20260927T133337580476Z/report.json`、台面路径 `bench-access/runs/20260927T150259301641Z/report.json`。本审计没有执行修改、原生全导出、切片、采购或打印；不把“可统一采用”称为整机构造/真实环/公差/回位负载均已验证。具体源身份见同目录 report.json。
