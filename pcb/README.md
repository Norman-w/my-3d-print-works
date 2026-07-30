## PCB 生成管线

管线的机械基准来自 `enclosure/paddle_shell.scad` 的 `rigid_pcb_slot_points`（V3 起尾端平收，无金手指窄尖）。
每一步都是独立的 Python 脚本，按顺序执行：

| Step | 脚本 | 功能 | 操作层 |
| --- | --- | --- | --- |
| 1 | `scripts/step1_clear_and_reference.py` | 清空全部元素，绘制 SCAD 参考轮廓、坐标十字、PZT 腔体圆、X±/Y± 方向标记 | `Dwgs.User` |
| 2 | `scripts/step2_substrate_outline.py` | 清空 `Edge.Cuts`，绘制 PCB 基材外形（内缩 0.30mm、PZT 码头缩回、拍柄截断） | `Edge.Cuts` |
| 3 | `scripts/step3_module_cutouts.py` | 刷新 ESP32-S3 和 IMU 模块矩形开孔，并生成嵌入焊接 rule area | `Edge.Cuts` + rule area |
| 3.1 | `ato build`（由根目录入口调用） | 用 `ato.yaml` 锁定的 0.12.5 生成最新 C4 网表 | 构建输出 |
| 3.2 | `scripts/step3_import_netlist.py` + `scripts/step3_finalize_generated_board.py` | 拒绝旧/C3/拓扑不符网表，通过 63 地址全量门禁后同步受审 C4 网络；无摆放地恢复可读元数据和背面尾插几何 | 网络 + 元数据 |
| C3→C4 | `scripts/migrate_c3_to_c4_unrouted.py` | 换 S3、加入比较器/DAC/去耦/ADC DNP，并按受审表赋网；显式清除 C3 铜线 | 封装 + 网络 + 铜线 |
| 4 | `scripts/step4_ato_placement.py` | 从 snapshot 恢复大陆/宽栈道/PZT/尾插并放置 C4 新器件；存在全板 C4 快照时最后优先恢复其 63 个变换 | 封装 |

> ~~step4.4 金手指加强小板~~ 已废弃：尾插改为 MX1.25 正反 5P，不再生成 `TAIL_STIFF_*` / `TAIL_FINGER_*`。

Step1 是破坏性的（清空后重新开始），Step2~4 仅修改各自负责的层。

### 运行方式

```sh
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3
PCB=pcb/layouts/default/default.kicad_pcb

# 完整重建（从零开始，丢弃原有封装）:
$KPY pcb/scripts/step1_clear_and_reference.py
$KPY pcb/scripts/step2_substrate_outline.py
$KPY pcb/scripts/step3_module_cutouts.py
# atopile build 生成封装（须使用 ato.yaml 锁定的 0.12.5）...
$KPY pcb/scripts/step4_ato_placement.py --force
# 若 ato 未带上 Molex 尾插封装，再补：
# $KPY pcb/scripts/apply_tail_mx125.py
```

### 位置快照（step1 前备份 / step4 自动吃）

| 区域 | 备份 | 快照文件 |
| --- | --- | --- |
| PZT 岛 | `step4.1_backup_docks.py` | `dock_snapshot.json` |
| 大陆阻容 | `step4.1b_backup_mainland.py` | `mainland_snapshot.json` |
| 宽栈道三键 | `step4.1c_backup_corridor.py` | `corridor_snapshot.json` |
| 尾插 F/B | `step4.1d_backup_tail.py` | `tail_snapshot.json` |
| C4 全部 63 器件（最终真理源） | 菜单 Step 4.1e / `step4.1e_backup_c4_placement.py` | `c4_placement_snapshot.json` |

### 部分更新（保留封装）

```sh
# 仅重绘机械层，不影响已有封装:
$KPY pcb/scripts/step1_clear_and_reference.py   # 清机械层+重绘参考线
$KPY pcb/scripts/step2_substrate_outline.py      # 重绘基材外形
$KPY pcb/scripts/step3_module_cutouts.py         # 重绘模块开孔和 IMU rule area
$KPY pcb/scripts/step4_ato_placement.py          # 仅移动仍位于 ato 网格位置的封装
```

### 当前 C4 无布线交接板

当前 `layouts/default/default.kicad_pcb` 已进入 Norman 手工摆放/布线阶段。原交接板的独立 `TP_GND` 已按 Norman 确认取消；2026-07-30 的 atopile 0.12.5 新网表与当前板均为 63 个封装。正式快照尚未生成前不要选择 Step 4，也不得再运行 Step 3.2 写入或带 `--yes-clear-copper` 的迁移命令。

```sh
# 只读校验板上 C4 pad→net、器件、尾插、DNP、S3 保留脚和无铜线状态：
$KPY pcb/scripts/validate_c4_unrouted_board.py
```

迁移脚本不替代 atopile 编译器。仓库 `ato.yaml` 自 2026-06-13 起锁定 `0.12.5`；提交 `c9df0aa` 写明“适配 atopile 0.12.5”，`f10342b` 写明“ato build 刷新”。这些是强版本意图证据，但没有 C3 出板时的运行日志/工具指纹能证明当时实际可执行文件版本。C4 于 2026-07-30 从标准路径 `~/.local/share/uv/tools/atopile/bin/ato` 实测版本 0.12.5，并由项目 Step 3.1 明确 `Build successful`；旧 `~/.atopile-env` 的 0.2.69 未参与生成。新 `.net` 为 63 个 C4 地址，旧 48 地址 C3 `.net` 仍只作历史产物。

Step 3.2 先核对 S3 的 ato/封装/固件/导入器脚位，再递归定位实际嵌套的 `default.net`，拒绝早于 `ato.yaml` / `main.ato` / `parts.ato` / S3 pinmap 的网表，解析仓库真实的多行 `atopile_address` / node 格式，并验证 63 个地址、182 个已连接焊盘号以及完整拆网/并网关系。只有无 track/via、无铜区交接板才允许写入；重复同号焊盘的 188 个物理实例会全部赋网。随后元数据收尾器恢复 63 个可读 Reference/Value、四个 DNP、IMU 3D 缩放及 Atopile 0.12.5 会翻错的背面尾插内部几何，并断言 0 个元件坐标/角度/板层变化。若 Norman 已开始布线，只运行 pinmap 校验与 `--check-only`，不得让 Step 3.2 改写板文件。

### 截图验证

```sh
kicad-cli pcb render --side top --width 1600 --height 1200 --background opaque --quality high \
  -o pcb/output/stepN_top.png pcb/layouts/default/default.kicad_pcb
```

### 器件布局分区

| 区域 | 内容 | 列数 |
| --- | --- | --- |
| MCU X+ | 电源锁存电路 + LED 接口（Q×2、D×1、R×3、LDO×1、C×2） | 2 |
| MCU X- | 调试焊盘 *仅此*（GND、VCC、VBAT、UART_TX、UART_RX） | 1 |
| IMU X- | LDO 滤波电容（c_in、c_out） | 1 |
| IMU X+ | 剩余调试焊盘（EN、BOOT、PWR_LATCH、IMU_KEY、IMU_GPIO、VBUS、LED_DATA） | 2 |

### 电气逻辑

电气连接定义在 `main.ato`，`ato.yaml` 指向 `main.ato:SmartPaddleRigid`。

项目自 2026-06-15 起的一键入口是根目录 `scripts/scad_to_kicad.sh`，不是已删除的旧 `generate_kicad.py`。只做电气生成时，从仓库根目录运行它并选择 **Step 3.1**；随后选择 **Step 3.2** 导入新网表。脚本会打印实际可执行文件和版本，在不是 `0.12.5` 时拒绝生成，并要求构建日志出现 `Build successful`，避免 Atopile 报错却返回零时误报完成。Step 3.2 不做元件摆放。C4 不要选择全链路 `a`、Step 4 或任何 Step 5 路由操作。

```sh
./scripts/scad_to_kicad.sh
# 选择 3.1；成功后继续选择 3.2
```

标准脚本默认使用 `~/.local/share/uv/tools/atopile/bin/ato`，可由调用者已有的 `ATO=/绝对路径/ato` 配置覆盖；仓库脚本不会安装、升级或重建 Python/atopile 环境。

封装以 `atopile_address` 属性作为电气真源实例。

管线脚本不处理布线，KiCad 仍负责:

- 元件放置决策
- 所有走线、过孔、敷铜和 DRC 清理
- 最终原理图图形维护

### 嵌入式 IMU 半孔接口

`layouts/lib/footprints.pretty/IM948_CUTOUT.kicad_mod` 将 IM948 建模为内嵌模块接口:

- IMU 模块本体进入 `step3_module_cutouts.py` 生成的内部开孔，不与主 PCB 厚度方向叠放。
- 16 个 IMU 引脚使用 PTH 圆孔焊盘；开孔边线切过这些焊盘，形成主 PCB 侧的半孔/邮票孔焊接界面。
- KiCad 电气上仍把 `IMU_IM948` 当作普通元件，所以可以直接从这些焊盘往主板引线。
- `layouts/default/default.kicad_dru` 用 `IMU_EMBEDDED_CASTELLATED_EDGE` rule area 仅在 IMU 嵌入接口附近放宽 `edge_clearance`；普通板边仍按 0.5mm 检查。
- `layouts/default/default.kicad_pro` 的工程级 `min_copper_edge_clearance` 保持为 0mm，这是为了允许 custom rule 对 IMU 区域设置负的 edge clearance。不要删除 `.kicad_dru`，否则普通板边的 0.5mm 规则不会被恢复。

## Status

当前分支已包含 C4 无铜线交接 PCB。后续工作:

- Norman 手工摆放 63 个器件；完成后由 Codex 用 Step 4.1e 回存 `c4_placement_snapshot.json`、复测恢复并重新生成装配资料
- Norman 按 `C4_ROUTING_HANDOFF.md` 手工布线、铺铜并清零最终 DRC
- C4 嵌入模块制造说明与板上 Fab 注释已完成；正式生产包仍由布线/铺铜/连通/DRC/新网表门禁共同锁定

当前 C4 快照的可打印装配包已生成到 `output/pdf/assembly-package/`，16 页渲染 QA 通过；尾插 HTML/端面图位于 `output/assembly/`。现有装配包是摆放前快照；应在摆放回存后和最终布线后分别重新生成。
