# SmartPaddle M5 可换电池拍柄 — OpenSCAD 实施计划

> **2026-07-31 废弃声明：电池匣 / 滑扣 / 外购充电总成方案已取消。**  
> 现行实现：满截面自研尾板（`pcb-tail`）+ 环槽卡位 + Step6 干涉开孔。见 [`m5/README.md`](m5/README.md)。  
> 下文电池匣段落仅作历史记录，**禁止再按匣体落地**。

> 状态：**历史设计规范（部分已废弃）**
>
> 适用组合：`M5.C5`。当前 C4 的制造对象仍配套 `M4`；本文不得用来修改或重新生成 C4 PCB。
>
> 电气与整机真理源：[`../pcb/C5_PLAN.md`](../pcb/C5_PLAN.md)。

---

## 1. 最终效果

M5 保留现有拍头、甜区刚性主板和拍柄基本人体工学外形，只重做拍柄尾段：

- 拍尾固定一块与尾面大致平行的窄 C5 尾板；Type-C、唯一用户电气按键、充电/电源指示灯和小型 RGB 均留在固定端。
- 一只封闭的单节 14500 电池匣从拍尾沿 `Y− → Y+` 推入，换电时不移动尾板、USB、线束或主板。
- 电池匣和固定尾板在 `X` 方向并排，禁止在 `Z` 方向叠放，也不再采用“主 PCB 中间开窗穿电池”的废弃结构。
- 用户拨动 `X+` 侧凹陷的横向机械滑块解锁；弱顶出弹簧只将电池匣向 `Y−` 推出 3–5mm，电池不会弹射。
- 电池匣内有独立 1S 保护板；固定端使用凹陷式弹簧触点，触点不承担导向、止挡或锁止载荷。
- M4 必须始终可从当前源文件复现。M5 采用独立入口、独立参数、独立输出名，任何 M5 试验都不能覆盖 M4 STL。

---

## 2. 开工前必须读取的文件

没有历史上下文的接手人或 AI 必须按顺序阅读：

1. [`../pcb/C5_PLAN.md`](../pcb/C5_PLAN.md)：C5/M5 已冻结架构、电子器件、线束和整机门禁。
2. [`parameters.scad`](parameters.scad)：M4 壁厚、拍柄坐标、孔位和现有尾端结构。
3. [`paddle_shell.scad`](paddle_shell.scad)：M4 外壳、内腔、分壳、PCB槽、USB/按钮/LED模块和导出入口。
4. [`bezier_profile.scad`](bezier_profile.scad) 与 [`../scripts/bezier_to_openscad.py`](../scripts/bezier_to_openscad.py)：Web 贝塞尔轮廓到 SCAD 的生成关系。
5. [`README.md`](README.md) 与 [`../scripts/export-stl.sh`](../scripts/export-stl.sh)：当前 M4 导出方式。
6. [`../TODOS.md`](../TODOS.md)：M5 开工门禁和当前 C4 状态。

若这些文件与本文冲突：电气/产品架构以 `C5_PLAN.md` 为准；M4 已实现行为以当前可执行源为准；未实测的尺寸不得擅自标记为已确认。

---

## 3. 版本隔离和建议目录

### 3.1 不允许直接改成 M5 的现有文件

下列文件是 M4/C4 的可复现基线。在建立回归基线之前不得为了 M5 直接改名、搬迁或覆盖：

- `enclosure/parameters.scad`
- `enclosure/paddle_shell.scad`
- `enclosure/bezier_profile.scad`
- `scripts/export-stl.sh` 的现有 M4 默认行为
- `web/src/data/userBezierProfiles.json` 的当前拍型数据

### 3.2 M5 实施时新建

```text
enclosure/
├── parameters.scad                  # M4，保持现状
├── paddle_shell.scad                # M4，保持现状
├── M5_SCAD_PLAN.md                  # 本文
└── m5/
    ├── README.md                    # M5 状态、实测尺寸和导出说明
    ├── parameters_m5.scad           # 只放 M5 专有参数；每项带 VERIFIED/TBD 来源
    ├── paddle_shell_m5.scad         # M5 完整装配入口
    ├── tail_housing_m5.scad         # 尾段固定壳、尾板槽、电池仓、排液
    ├── battery_cartridge_m5.scad    # 电池匣、尾盖、导轨配合面、保护板/触点包络
    ├── latch_m5.scad                # 横向滑块、锁舌、复位/顶出弹簧包络
    ├── interface_envelopes_m5.scad  # 尾板、USB公头、按键、LED、手指和线束禁布包络
    ├── assembly_m5.scad             # 插入/锁定/顶出/爆炸状态
    └── generated/                   # M5 尺寸报告和预览；生成物不作手工真理源

scripts/
├── export-stl.sh                    # 继续默认导出 M4
├── export-m5-stl.sh                 # 新入口，文件名必须带 m5
└── validate-m5-geometry.py          # 读取机器可读尺寸并执行机械门禁
```

实现者可以先复制 M4 的必要模块到 `m5/` 再逐步重构；不得一开始就大规模抽取公共代码。若以后抽取 `enclosure/common/`，必须先证明抽取前后的 M4 STL 拓扑、边界框和体积在规定容差内一致。

### 3.3 版本输出命名

所有 M5 输出必须包含 `m5`，例如：

```text
enclosure/stl/m5_paddle_handle_front.stl
enclosure/stl/m5_paddle_handle_back.stl
enclosure/stl/m5_battery_cartridge_body.stl
enclosure/stl/m5_battery_cartridge_cap.stl
enclosure/stl/m5_latch_slider.stl
enclosure/stl/m5_tail_fit_coupon.stl
/tmp/smartpaddle-m5/<timestamp>/m5_geometry_report.json
```

禁止生成同名 `paddle_handle_front.stl` 覆盖 M4。

---

## 4. 坐标和装配基准

沿用现有 SCAD 坐标：

| 方向 | 定义 | M5用途 |
|---|---|---|
| `+Y` | 拍尾指向拍头 | 电池插入方向、内端触点方向 |
| `−Y` | 拍头指向拍尾 | 电池拔出/顶出方向、尾面外侧 |
| `+X` | 从正视图看向拍柄右侧 | 冻结为电池匣和释放滑块候选侧 |
| `−X` | 从正视图看向拍柄左侧 | 冻结为固定窄尾板候选侧 |
| `+Z` | 前壳方向 | 与现有 `front` 半壳一致 |
| `−Z` | 后壳方向 | 与现有 `back` 半壳一致 |

首轮固定方向为：**尾板位于 `X−`，电池匣位于 `X+`，释放滑块位于 `X+` 外侧。** 若握持样块表明必须镜像，只允许修改一个 `m5_mirror_x` 参数，并同步更新尾板 PCB 朝向、装配图和线束针序图，不能在不同文件中分别手工镜像。

三个机械基准面必须在 SCAD 注释和尺寸报告中明确输出：

- `M5_DATUM_A`：拍柄尾端齐平面，法向 `−Y`。
- `M5_DATUM_B`：整拍对称面 `X=0`。
- `M5_DATUM_C`：前后壳分型面 `Z=0`。

现有 `handle_butt_y = -178.5mm` 是参数基准；贝塞尔生成后的实际平底由生成几何决定。M5 所有尾部坐标必须从“实际平底”派生，不能混用 `min(handle_butt_y, BEZIER_Y0)` 之类的旧补偿写法。

---

## 5. 当前 M4 基线和已知空间矛盾

当前 M4 参数给出：

- 尾端外宽目标约 34mm，外厚约 26mm。
- `wall_t = 2.0mm`，`handle_cavity_inset = 1.5mm`。
- 粗估常规内腔约 `27 × 19mm`，但真实值必须逐个 Y 截面从贝塞尔包络计算。
- C4 刚性主板尾巴在 SCAD 中止于 `_tail_neck_y = -100mm`，半宽 9mm。

这组基线不能直接证明 C5 结构放得下：

- 约 16mm 的电池匣 + 9.5–11mm 尾板 + 分隔壁 + 装配间隙，已经接近或超过 27mm 内宽。
- 20–22mm 高的尾板大于粗估的 19mm 常规内厚。
- 电池匣长度 55–58mm 意味着内端约到尾面向 `+Y` 55–58mm 的位置，必须核对它与 C4/C5 主板尾端、线束弯曲半径和手柄螺丝柱是否冲突。

因此 M5 很可能需要对最后约 65–70mm 拍柄做**局部加宽/加厚或减小无必要内缩**，而不是把 M4 内腔原样挖两个孔。外形变化必须由握持样块确认；不得为满足表格尺寸直接削薄到低于结构门禁。

---

## 6. 输入实物和测量表

Gate 1 建模冻结前至少需要以下实物或可靠机械图：

| 对象 | 必测项目 | 记录精度 | 当前状态 |
|---|---|---:|---|
| 14500 K10 候选电芯，至少3节 | 最大直径、总长、正极帽高度、热缩膜偏心 | 0.05mm | TBD |
| 电池匣保护板试样 | PCB长宽厚、MOS/焊点最高点、触点区 | 0.05mm | TBD |
| C5 尾板首轮器件包络 | PCB、Type-C、按键、电感、LED最高/最深点 | 0.05mm | 尚未画板 |
| 固定弹簧触点 | 本体、尾针、工作行程、推荐预压、额定电流 | 数据手册+实测 | TBD |
| 复位弹簧/顶出弹簧 | 自由长、外径、压并长、弹簧率 | 0.05mm/测力 | TBD |
| USB-C 公头 | 插头壳体、护套、完全插入深度、线缆弯曲包络 | 0.05mm | TBD |
| FDM/SLS打印样条 | XY孔/轴、Z孔/轴、燕尾/滑块配合偏差 | 0.05mm | TBD |

所有实测值写入 `enclosure/m5/README.md` 的带日期表格，再写入 `parameters_m5.scad`。禁止直接把商家“典型值”改名为 `VERIFIED`。

---

## 7. 参数表和派生公式

### 7.1 首轮参数名

以下值只是建模起点，变量注释必须保留状态：

```scad
// MODEL_TARGET / DATASHEET / MEASURED_SAMPLE / VERIFIED_PRINT
m5_tail_active_length_y       = 70.0;   // 尾段重构长度
m5_battery_cell_d             = 14.10;  // TBD：同批电芯最大值
m5_battery_cell_l             = 50.10;  // TBD
m5_cartridge_outer_x          = 16.00;  // TARGET
m5_cartridge_outer_z          = 16.00;  // TARGET
m5_cartridge_total_y          = 57.00;  // TARGET，期望55–58
m5_tail_board_x               = 10.00;  // TARGET，期望9.5–11
m5_tail_board_z               = 21.00;  // TARGET，期望20–22
m5_tail_board_t               = 1.00;   // TARGET，需与PCB厂/USB脚确认
m5_cartridge_clearance_xy     = 0.25;   // 每侧，打印样条后修正
m5_rail_clearance             = 0.25;   // 每侧
m5_divider_min_t              = 1.20;   // 不含局部加强筋
m5_shell_min_t                = 1.80;   // 普通壳最薄门禁
m5_rail_root_min_t            = 1.50;   // 导轨根部剩余壁厚
m5_latch_travel_x             = 1.80;   // 目标1.5–2.0
m5_latch_engagement_x         = 1.00;   // 目标0.8–1.2
m5_eject_travel_y             = 4.00;   // 目标3–5
m5_contact_working_travel_y   = 1.00;   // TBD：由触点规格确定
m5_contact_overtravel_y       = 0.30;   // TBD
m5_wire_min_bend_r            = 3.00;   // 按实际线规复核
m5_tpu_pad_preload            = 0.20;   // 起点
m5_drain_min_d                = 1.20;   // 起点，打印验证
m5_mirror_x                   = false;  // false = 尾板X−、电池X+
```

### 7.2 必须自动计算的可行性量

实现中不得只观察渲染图；至少输出下列公式结果：

```text
available_inner_x(y) = 2*envelope_hx(y) - left_wall(y) - right_wall(y)
available_inner_z(y) = 2*half_z_at(y) - front_wall(y) - back_wall(y)

required_x = board_slot_x + divider_t + cartridge_outer_x
required_z_battery = cartridge_outer_z + upper_clearance + lower_clearance
required_z_board = board_z + board_slot_clearance

x_margin(y) = available_inner_x(y) - required_x
z_margin_battery(y) = available_inner_z(y) - required_z_battery
z_margin_board(y) = available_inner_z(y) - required_z_board
```

门禁：完整插入路径的所有截面 `x_margin >= 0`；普通装配余量目标 `>= 0.4mm`，否则必须明确是受控压配合。任何负值都应使验证脚本失败。

### 7.3 电池匣长度链

```text
cartridge_total_y = tail_cap_t
                  + cell_end_clearance
                  + measured_cell_l
                  + protection_pcb_envelope_y
                  + contact_pad_structure_y

housing_depth_y >= cartridge_total_y
                 + eject_travel_y
                 + hard_stop_margin_y
```

保护板、焊点、镍带弯折和导线应分别建包络，不能都藏进一个无依据的“2mm余量”。

---

## 8. 几何模块的明确职责

### 8.1 `tail_housing_m5.scad`

必须包含：

1. 从 M4 手柄外形平滑过渡到 M5 尾段的局部外包络。
2. 电池匣入口、全行程仓体、双导轨、内端硬止挡。
3. 固定尾板槽、尾板定位基准、螺钉/压条位置和器件背部避让。
4. 尾板区与电池仓之间的连续隔壁；排液不得穿向电子仓。
5. `X+` 侧滑块通道、限位肩和防误触凹槽。
6. 内端触点座、顶出弹簧座、线束通道和应力释放点。
7. TPU 防响垫槽、尾盖密封唇配合槽、USB软塞预留。
8. 前后半壳的装配销/螺钉；任何原有螺丝柱与电池运动包络冲突时要参数化迁移，不能简单删除。

### 8.2 `battery_cartridge_m5.scad`

电池匣至少拆成可制造的匣体与尾盖，并建出：

- 电芯最大实体包络和热缩膜保护间隙。
- 保护板、MOS、电阻、焊点和镍带包络。
- 凹陷的 `P+`/`P−` 触点窗；一个常见金属平面不应轻易同时接触两极。
- 非对称导轨或定位键，阻止旋转180°或左右反插。
- 锁舌凹槽前的斜导角、锁止平面和独立拔出受力面。
- 齐平尾盖、浅抓取纹、序列号/电池批次标识区。
- TPU/硅胶密封唇和两点防响预压面。
- 装配后不可让硬边直接压迫电芯热缩膜。

### 8.3 `latch_m5.scad`

单独可打印和爆炸显示：

- 横向滑块和外露拨片。
- 与滑块一体或机械联动的锁舌。
- 1.5–2.0mm 有效行程、两端硬限位和防脱肩。
- 复位弹簧实体包络及预压状态。
- 0.8–1.2mm 锁舌啮合。
- 解锁后锁舌与电池匣全行程的净间隙。
- 内端顶出弹簧自由、锁定、顶出三种长度。

外露滑块必须凹入拍柄侧面，形状与唯一电气圆按键明显不同。滑块是纯机械件，不增加第二个电气按键。

### 8.4 `interface_envelopes_m5.scad`

用半透明/高对比色占位，不作为可打印实体：

- C5 固定尾板及每个高器件的三维禁布包络。
- USB-C 公头完全插入及线缆弯折包络。
- 用户按键帽行程、手指按压圆柱。
- 两颗灯的发光面、导光柱和串光隔墙。
- 8P线束、电池两根功率线和最小弯曲半径。
- 固定触点工作/最大压缩包络。
- 用户抓取电池尾盖所需的双指包络。
- 横拍/直拍典型握持禁区，防止滑块被掌根自然触发。

### 8.5 `assembly_m5.scad`

至少支持这些 `ASSEMBLY_STATE`：

```text
shell_only
board_only
cartridge_removed
cartridge_inserting
cartridge_locked
cartridge_ejected_3mm
latch_pressed
usb_plug_inserted
exploded
section_x
section_z
clearance_debug
```

不能把基准样板和改进版叠在同一层，也不能把多个装配状态默认重叠在同一渲染中。

---

## 9. 外壳和 PCB 的机械接口合同

M5 Gate 1 机械样块通过后，输出一份 `m5_tail_interface.json` 和同内容 Markdown 表，供 C5 尾板使用。至少包含：

- 尾板最大外形、厚度、角圆角和禁入区域。
- `M5_DATUM_A/B/C` 到尾板原点的变换。
- Type-C 壳体中心、开口宽高、插入方向和公头止挡面。
- 用户按键中心、按压方向、总行程和壳体帽尺寸。
- 状态灯/RGB中心、发光方向、导光柱直径和最大器件高度。
- 尾板固定孔/槽中心和公差。
- 8P线束焊盘出口、线束压条和弯曲禁区。
- 电池功率线出口、触点极性和线规。
- PCB正反面允许器件高度图。

C5 尾板外形必须读取这份冻结接口，不能从 M4 旧 USB/LED/按钮坐标派生。机械 JSON 更新后，C5 PCB 必须显式重新通过接口版本检查。

---

## 10. 分阶段实现顺序

### M5.0 — 冻结 M4 基线

1. 记录当前提交号、OpenSCAD版本、Web贝塞尔 JSON 哈希。
2. 用当前脚本导出四个 M4 零件到临时目录。
3. 记录每个 STL 的 SHA-256、三轴边界框、体积、三角面数和是否水密。
4. 保存 M4 尾部 XZ 截面和关键 Y 截面的尺寸报告。
5. 后续任何公共代码重构都必须重跑这一回归；默认 M4 文件名和几何不能静默变化。

通过条件：同环境重复导出一致；基线报告已提交，STL本体仍可保持忽略。

### M5.1 — 纯包络可行性

1. 新建独立 M5 入口，先复现 M4 外包络。
2. 仅加入尾板盒、电池匣盒、主板尾端和线束弯曲半径盒。
3. 以 2mm 为步长输出尾部70mm的内宽/内厚。
4. 求出需要局部加宽/加厚的最小区间。
5. 对 `X−板/X+电池` 与镜像方案生成独立图，不重叠。

通过条件：所有包络有非负余量，局部外形变化连续，且没有碰 C5 主板尾端与必要螺丝柱。

### M5.2 — 尾段和电池匣样块

1. 建仓体、入口、硬止挡、直导轨和空电池匣。
2. 输出尾部70mm样块，不先渲染整拍。
3. 用真实电芯尺寸假体和三档间隙样条：每侧 0.20/0.25/0.30mm。
4. 测试正插、反插阻止、晃动、拔出力、层纹方向和尾盖齐平。

通过条件：至少三套打印样块中选出稳定公差；无刮膜、卡死或明显晃动。

### M5.3 — 锁止和顶出

1. 加滑块、锁舌、复位弹簧和防脱结构。
2. 加弱顶出弹簧和3/4/5mm三档垫片。
3. 测量锁止啮合、解锁力、顶出量和100次循环磨损。
4. 做横拍/直拍握持，验证掌根不会自然解锁。

通过条件：自动“咔哒”锁止；冲击/甩动不脱；解锁后仅露出3–5mm；松手滑块自动复位。

### M5.4 — 触点、尾板和用户界面样块

1. 使用真实触点、USB公头、尾板厚度片、按键和导光柱。
2. 确认塑料硬止挡先到位，触点仍处于推荐工作行程。
3. USB插拔力由壳体限位吸收，不能经母座焊脚传到 PCB。
4. 检查按键手感、两灯串光、USB插头与换电/滑块动作互不干涉。
5. 冻结 `m5_tail_interface.json` v1。

通过条件：尾板外形和UI坐标可交给 C5 PCB；所有 TBD 尺寸有实测记录。

### M5.5 — 完整 M5 壳体

1. 将通过的尾段合并到完整拍柄前/后壳。
2. 迁移冲突螺丝柱、线槽和应力释放，不改变拍头甜区几何。
3. 加密封唇、排液和USB软塞空间。
4. 导出完整打印件和最终装配状态。
5. 重跑 M4 回归与 M5 几何门禁。

通过条件：四个壳体零件水密；切片无悬空薄壁；装配顺序可执行；尾段样块数据与完整件一致。

### M5.6 — C5 联调和设计冻结

1. 只装已台架通过的 C5 尾板和保护电池匣。
2. 检查线束、触点、开关、灯、USB和散热。
3. 进行换电、挥拍、跌落、汗液、USB插拔和锁止寿命测试。
4. 更新装配包、维修说明和接口JSON版本。

通过条件：满足 `C5_PLAN.md` Gate 4；在此之前 M5 只能标注工程样机，不能标注量产验证。

---

## 11. 打印和机械门禁

### 11.1 自动几何门禁

`validate-m5-geometry.py` 至少检查：

- 所有可打印 STL 存在、非空、水密、单一预期实体。
- 边界框与参数报告一致，禁止意外缩放或坐标漂移。
- 普通壳壁 `>= 1.8mm`；导轨根部和锁舌根部达到各自门禁。
- 电池全行程不与壳、尾板、触点基座、螺丝、线束包络相交。
- 锁止时啮合 0.8–1.2mm；解锁时净间隙为正。
- 弹簧不会超过压并长度；触点不会超过最大工作行程。
- 顶出状态位移 3–5mm。
- USB公头和电池拆装包络不相交。
- 排液通道连到外界且不穿过触点/尾板电子仓。
- M5 输出名不覆盖 M4。

### 11.2 首轮打印建议

- 先打印尾部70mm coupon、电池匣和滑块，不打印整拍。
- 壳体样件先用 PETG；滑块/锁舌最终优先 POM 或 PA12，FDM件只验证几何。
- 导轨方向应避免层间剥离承担主要锁止冲击；切片图必须人工检查。
- 对每种打印机/材料做孔轴、滑块和密封唇样条，不沿用别人的公差。
- 记录喷嘴、层高、线宽、壁数、材料批次、方向和环境温度。

### 11.3 机械验证矩阵

| 测试 | 首轮标准 | 冻结前标准 |
|---|---|---|
| 空匣插拔 | 20次无卡死 | 100次后仍可锁止 |
| 带电芯插拔 | 无刮膜、无触点顶死 | 500次工程寿命目标待产品定义 |
| 顶出量 | 3–5mm | 三套样件均在范围内 |
| 晃动 | 手摇无明显响声 | 挥拍采集无电源瞬断 |
| 误解锁 | 正常握持不触发 | 跌落/击球不脱匣 |
| USB插拔 | 不带动尾板 | 插拔循环后焊点/定位无松动 |
| 防汗/排液 | 液体不直达触点 | 工程泼溅流程通过；首版不宣称IP等级 |

---

## 12. 导出入口和建议命令

实现后的预期用法：

```bash
# M4 继续保持原命令和原输出
./scripts/export-stl.sh

# M5 快速预览，只写独立输出
QUALITY_MODE=quick ./scripts/export-m5-stl.sh tail-coupon

# M5 全部可打印件
./scripts/export-m5-stl.sh all

# 三种装配状态和剖面图
./scripts/export-m5-stl.sh validation-views

# 机器门禁；报告默认写临时目录
python3 scripts/validate-m5-geometry.py \
  --report /tmp/smartpaddle-m5/geometry-report.json
```

导出脚本必须打印：实际 OpenSCAD 可执行文件、版本、git提交、模型版本、参数文件哈希和输出目录。任何渲染失败、空 STL 或门禁失败都应返回非零。

---

## 13. 装配顺序必须被几何支持

1. 在不装电子件时安装滑块、锁舌、复位弹簧和弱顶出弹簧；这些零件合壳后仍需能维护或有明确不可维护声明。
2. 安装固定触点及两根电池功率线，确认硬止挡决定终点。
3. 安装并固定已台架验证的尾板；壳体而非 Type-C 焊脚承受插拔力。
4. 将 8P 线束和电池线放入独立通道/压条，避开所有运动和螺钉包络。
5. 用限流电源做整机上电，未通过前不插真实电池匣。
6. 插入已独立验证的电池匣，检查自动锁止、触点预压和3–5mm顶出。
7. 合壳后重复 USB正反插、按键、灯、充电、换电、摇晃和握持检查。

若 SCAD 模型要求先封死外壳再安装不可穿入的触点/弹簧/尾板，则模型即判失败，不能留给装配人员“想办法”。

---

## 14. 必须保留的未确认项

开始 M5 时下列项目仍是 TBD：

- K10 实际采购批次最大尺寸及是否继续作为最终电芯。
- 保护板真实外形、焊接方式和器件高度。
- 固定弹簧触点、复位弹簧和顶出弹簧的确切料号。
- 最终 C5 尾板外形和器件高度；它必须在 M5 Gate 1 后冻结。
- 尾段是否需要局部加宽/加厚及人体工学接受度。
- 尾板/电池左右是否镜像；首轮按板 `X−`、电池 `X+`。
- PETG/PA12/POM 的实际配合间隙、磨损和汗液表现。
- 锁止寿命、跌落等级、产品防水等级和法规要求。

文档、SCAD 变量和预览图必须把这些项目标为 `TBD`、`TARGET` 或 `MEASURED_SAMPLE`，不能仅因模型能渲染就改成 `VERIFIED`。

---

## 15. 完成交接清单

M5 SCAD 实施任务只有在以下全部满足后才可称为完成：

- [ ] M4 基线报告存在，原命令仍能复现 M4。
- [ ] M5 源文件、参数、导出脚本和输出名与 M4 隔离。
- [ ] 尾板、电池匣、导轨、锁止、弹簧、触点、线束、USB和手指包络齐全。
- [ ] 锁定、解锁、3–5mm顶出、拔出和USB插入状态均可单独查看。
- [ ] 尾段 coupon、电池匣、滑块和完整壳体均能生成水密 STL。
- [ ] 自动尺寸/碰撞/最薄壁门禁通过。
- [ ] 至少三套真实打印样件记录了材料、方向、公差和测量值。
- [ ] 真实电芯、触点、弹簧、USB公头和尾板厚度片完成配合验证。
- [ ] `m5_tail_interface.json` 冻结并被 C5 尾板工程引用。
- [ ] 装配、维护和拆卸顺序实际可行。
- [ ] `README.md`、`TODOS.md`、`C5_PLAN.md` 和装配说明同步更新。
- [ ] 未验证项目仍明确标注，未作量产或IP等级承诺。

---

## 16. 给无上下文 AI 的直接开工指令

> 你正在 SmartPaddle 仓库实现 M5 可换电池拍柄。先完整阅读 `pcb/C5_PLAN.md`、`enclosure/M5_SCAD_PLAN.md`、`enclosure/parameters.scad`、`enclosure/paddle_shell.scad`、`enclosure/README.md` 和 `TODOS.md`。不得修改 C4 PCB，不得让 M5 覆盖 M4 SCAD/STL。先完成 M5.0 的 M4 回归基线，再在 `enclosure/m5/` 建独立入口；Gate 1 只做尾部70mm、电池匣、导轨、横向滑扣、触点座和真实包络样块。首轮方向为固定尾板在 X−、电池匣在 X+、电池从 Y−推向Y+、滑块位于X+侧。所有未实测尺寸标记 TBD/TARGET；先通过包络公式、碰撞和打印样块，再冻结 C5 尾板外形。禁止复活 `pcb/c5-integrated-tail/` 的长板/中间开窗方案。

---

## 17. 当前结论

M5 不是对 M4 尾端多挖一个 14500 圆孔，而是一套需要机械接口冻结的独立版本。正确执行顺序是：

> **冻结M4 → 包络计算 → 尾部coupon → 电池匣/导轨 → 横向滑扣/顶出 → 真实触点和尾板厚度片 → 冻结机械接口 → C5尾板 → 完整M5壳体 → 整机验证。**

在真实尺寸、样块和联调完成前，M5/C5 均只能标记为计划或工程样机，不能用于直接生产承诺。
