# 统一拉索候选实例与导出契约

`cable-assembly-inventory.json` 是当前统一场景的按实例清单；`cad/cable-scene-export.scad` 是只调用既有 CAD 的导出适配入口。未修改原机构几何，未使用旧 STL 代替新 CAD。

## 数量来源

从 `analysis.launcher_final_assembly.inventory()` 实际读得 38 个送料打印实例。保持这些实例 ID，仅替换：

- `feeder/beam-grip` → `co_beam()`，同时包含原背梁及输出固定桥，不能再叠原背梁或另外再加一次桥。
- `feeder/frame` → `co_frame(t)`，替换原凸轮架，不能同时保留旧 frame。

新增 7 个打印实例：输入 body/lever/cover、输出 cap、输出弯导向 base/cap/lower。因此送料打印件为 45 个。`analysis.spin_head_geometry.PARTS` 实际列出 10 个旋转头打印实例，合计 55 个。旋转头的保持叉是第 10 件，归入 `hold` 旁置/选装组，正常工作装配只含另外 9 件。

完整清单共 84 个场景实例：55 个打印件、23 个购置候选显示组、6 个参考显示组。五金的一行可以包含同一运动关系下多颗螺钉、螺母、垫片，**84 不是实物零件总数量，23 也不是采购数量**。购置候选均不表示已经购买或完成供应商公差闭合。

当前 JSON 的可选 `instance_kind` 是早期显示分组标签，购置组中沿用了 `rigid-reference-subassembly` 字样，其中弹簧并非刚体。此字段不参与发布或动画，不能用于判断物理刚性或运动；运动只依据 `motion`。为保持导出快照身份，本轮不据这一未使用标签重导模型。

## 文件与选择器

每行有唯一 `id`、`name`、`role`、`group`、`family`、`source`、`definitions`、`backend` 和 `motion`。旧件尽量沿用 `feeder/原id`、`spin/原id`。新拉索附件使用 `feeder/cable-...`，允许前端单独显隐。

`source` 均为 `cad/cable-scene-export.scad`；把 `definitions` 的键值原样传给 OpenSCAD 的 `-D` 即可。典型选择器：

| `cse_part` | 实际调用 |
|---|---|
| `legacy` | `la_item(cse_legacy,cse_side,cse_rear,t)` |
| `beam` / `frame` | `co_beam()` / `co_frame(t)` |
| `input-body/lever/cover` | `ci_body()` / `ci_lever(20*t)` / `ci_cover()` |
| `output-cap` | `co_lug_cap(t)` |
| `route-base/cap/lower` | `crr_base()` / `crr_cap()` / `crr_lower()` |
| `original-fixed-hardware` | `ct_original_fixed_hardware()` |
| `follower-hardware` | 当前一侧、一个前/后挡指的肩销、已就座螺母和顶紧五金 |
| `input-fixed/moving-hardware` | `ci_fixed_hardware()` / `ci_moving_hardware(20*t)` |
| `output-fixed/moving-hardware` | 调节器及端套 / `co_terminal_hardware(t)` |
| `route-hardware/housing` | `crr_hardware()` / `cr_housing()` |
| `input/output-wire` | `ci_cable(20*t)` / `co_wire(t)` |
| `spin-printed` | `cse_legacy` 指定的真实旋转头打印模块 |
| `spin-hardware` | `sch_hardware(cse_legacy,cse_float,cse_preload,false)` |

原送料已知需要 CGAL 的实例沿用旧导出器列表；新 `co_frame` 也使用 CGAL，避免已知 Manifold 退化面。其余由主导出器完成当前源的网格检查，清单本身不是网格验证结论。

导出顶点保持 **t=0 的原 CAD 装配坐标**，不居中、不单独旋转、不放上打印床。送料与旋转头分别保留各自原 CAD 坐标系；网页对两组的摆放是展示变换，不代表新增一个已验证的三通/风机安装接口。

## 五金和线芯不能重复

1. 原固定五金调用 `ct_original_fixed_hardware()`，它移除旧 `sh_bolts`，保留原 `sh_nuts`。新的四颗 M4×60 只由输入固定五金出现一次。
2. 原移动五金不能整体随 frame 向 Z 平移。四套挡指五金分别跟随各自的径向运动；弹簧运动端五金单独沿 Z 移动。
3. 输入五金分为固定件及绕轴旋转件。输出五金分为固定调节器/端套及随架平移的端头/保持垫片/盖螺钉；不存在把整个 `co_hardware()` 平移的做法。
4. `cr_wire()` 原本含输入调节器内的一段直线，它与 `ci_cable()` 重叠。中段线芯显示采用 `cr_wire() − (ci_cable(0) ∪ co_wire(0))`；输入和输出芯线仍各自完整显示。扣除的是已有重复参考固体，三个显示组的联合几何与原参考联合一致。该交叠位于固定切线段，不随扣动改变。
5. 保持叉常驻螺母保留在 `spin/hardware-latch`；旁置可拆螺钉/垫片采用 `sch_latch_hardware(true) − sch_latch_hardware(false)`。没有把常驻螺母复制到两组。

## 运动元数据

`motion.kind` 使用 `fixed`、`translate`、`radial`、`trigger-rotate`、`spring`、`input-wire`、`output-wire`。归一化 `t∈[0,1]` 对应滑架位移 `u=20*t` mm。所有刚体变换都是相对于已处于 t=0 装配位置的 STL 顶点的增量。

- frame、输出 cap、输出端头五金、弹簧运动间隔套及运动端五金：`+Z·20t`。
- 前挡：`r=21+5·clamp((t−0.6)/0.4,0,1)`；后挡：`r=26−5·clamp(t/0.4,0,1)`。左右实例沿 X 分别乘 `side=±1`，相对于各自初始半径位移；没有给整套四指统一移动。
- 输入扳机及随动五金：绕 CAD `[75,-82,5]`、轴 `[0,1,0]` 旋转 `−t/3` rad；钢芯半径60 mm，手指半径36 mm。全行程手指向近端的分量约11.779 mm，不能把20 mm钢芯行程显示成20 mm手指位移。
- 输入芯线：保留固定切线段，重建从 `45°−u/60` 到90°的包绕弧，角度换算按弧度/度数处理。不能刚体平移整条输入芯线。
- 输出芯线：上端仍在护套入口 Z111；下端为端头中心 `15+u` 减8 mm尾长。不能把上端随滑架一起抬起。
- 回位弹簧：固定端环不动，移动端环沿Z移动，中部线圈包络从 `coil_start_z=−9.45` 到 `coil_end_z=8.63+u`。不对整个弹簧连同端环做统一缩放。

旋转头的浮动量 `spin_float_mm`、预压量 `spin_preload_mm` 与扳机行程独立，当前快照均为0。旋转头弹簧及浮动件不得跟随扣扳机动画改变。预压五金包含螺钉和两个固定锁紧螺母，此快照作为固定设置显示；不能把该组当刚体随预压量平移。若将来新增预压操作动画，需另拆该组，不能复用一个错误变换。

`scene_contract.ci/co/cr` 来自适配器实际 CLI `contract` 输出，随后转换为对象；`ci.wire_arc_rest_angle_deg=45` 明确引用 `ci_local_cable` 的源表达式。`scene_contract.spring` 与源弹簧端点方程一致，并记录 `rs_L(0)=30.82`、`rs_L(1)=50.82`、两端挡指半径与轴向位置的 CAD 回读值。源摘要在 JSON 的 `source_sha256` 中。

## 验收边界

本子任务核对数量、唯一 ID、源调用、动静分组和实际 CLI 契约解析，不重复执行全套机构检查。完整导出、打印件严格拓扑检查和网页快照验证由主任务另做。该清单不更改旧打印报告，不证明实物承载、摩擦、单球释放、旋转性能或打印装配已经通过。
