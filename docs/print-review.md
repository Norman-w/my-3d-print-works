# 保持叉离线切片与共享配置修复

状态：**共享 X1C 配置的五个官方 G-code 模板已展开，保持叉已按原模型、原朝向重切且无警告。没有发送打印任务。** 本报告只覆盖保持叉及此次共享配置修复，不代表其他零件、整机装配或实物验收通过。

## 原错误与完整修复

原共享 `output/print-review/config/machine.json` 虽然记录了 X1C 的五项 `include` 名称，却未把对应模板字段展开。它保留了继承来的通用启动 G-code，旧保持叉实际文件只有 `M109 S205`，之后直到关机没有改到 PETG 的255°C目标。

此次从本机 BambuStudio 附带的 **Bambu Lab X1 Carbon 0.4 nozzle** 子预设读取五项 `include`，逐个载入对应官方模板的同名字段，覆盖继承字段，再移除已展开的 `include`。没有仅把205改成255，也没有合并模板的 `name/instantiation` 等元数据。

| 字段 | 原配置情况 | 当前检查 |
|---|---|---|
| `machine_start_gcode` | 不匹配官方 X1C 模板 | 完全一致 |
| `machine_end_gcode` | 不匹配 | 完全一致 |
| `time_lapse_gcode` | 不匹配 | 完全一致 |
| `change_filament_gcode` | 不匹配 | 完全一致 |
| `layer_change_gcode` | 原已一致 | 再次确认一致 |

修复后共享 `machine.json` SHA256：`134804b2209e6413b0e54614367e15792e0648446258dffab8406604093de857`。五模板的应用内绝对路径及 SHA256 已加入 `config/source-identity.json`。共享工艺和耗材配置未修改，其余机器字段也保持不变。

旧证据各自只归档一次，复跑时会先检查归档哈希，禁止覆盖：

- `output/print-review/config/before-template-expansion/`：旧 machine、process、filament、source-identity 及清单。
- `output/print-review/hold-fork/before-template-expansion/`：旧3MF、实际205°C G-code、原生结果及清单。

旧切片不自动随配置修复而更新；以上旧产物只用于追溯，不作打印输入。其他零件若曾使用旧共享配置，必须分别重新切片并核对实际指令。

## 保持叉身份、朝向与实际结果

输入是 `output/spin-head/spin-hold-fork.stl`，SHA256 `1d2b9004c3419a398c714f8f50b56647ffced6fe1b20a3ffe3c28e5188b6976d`，1190个三角面。脚本把旧3MF的源偏置加回网格，对三角面逐点按1e−5 mm规范化比较，确认旧切片与当前STL是同一几何；同时检查原始STL哈希及相关 CAD 在切片期间不变。

原模型包络是 X[59,71]、Y[−7,7]、Z[52,77]。继续采用绕 Y 轴 −90°，即 `(x,y,z)→(−z,y,x)`；原 +X 成为打印 +Z。3MF源偏置仍为 `(65,0,64.5)`，摆放平移仍为 `(127.99999,128,6)`。摆放后包络 **25×14×12 mm**，底部 Z=0，没有自动换朝向或替换零件。

| 核验项 | 当前结果 |
|---|---|
| 工具 | 本机 BambuStudio 02.08.02.61，项目内隔离配置目录 |
| 分层 | 0.20 mm，60层，4壁，25%填充，关闭支撑 |
| CLI / 原生结果 | 返回0 / Success |
| 原生警告 | 空 |
| 首层前末条喷嘴温度指令 | **`M109 S255`** |
| Generic PETG 首层目标 | **255°C** |
| 五个机器 G-code 字段 | 均与官方模板完全一致 |
| 预计总时间 | **21分07秒** |
| 预计总耗料 | **3.550 g** |

模板中清洁、冲刷等阶段有其他温度，这是官方序列的一部分；检查对象是完整模板一致性和首层实际目标，不是删除所有非255的温度指令。没有连接打印机验证这些指令的物理执行。

X1C、0.4喷嘴、PETG 已按用户输入采用；Generic PETG 的具体品牌曲线未实测。用户确认的是 PEI，**Textured PEI 仍是离线分析假设**，不是已经确认的板型。

![保持叉切片预览](../output/print-review/hold-fork/plate-preview.png)

## 产物与复跑

- `output/print-review/hold-fork/review-report.json`：全部检查、原/新3MF变换、温度指令、输入和产物哈希、完整命令。
- `output/print-review/hold-fork/hold-fork-slice-review.3mf`：本轮审查3MF。
- `output/print-review/hold-fork/plate_1.gcode`：本轮离线 G-code，未发送。
- `output/print-review/hold-fork/result.json` 与 `bambu-cli.log`：原生结果和日志。

复跑命令：

```text
python3 scripts/review_hold_fork_slice.py
```

脚本会先保护旧证据并核对旧3MF的真实源几何，再展开五项官方字段、离线切片、核对温度与警告、比较朝向和摆放。它不修改 CAD，不访问 LAN 或打印机，不操作集成报告。

本轮证明的是配置展开正确、该保持叉能按指定参数生成无警告切片、首层文件指令与 PETG 目标相符。实际板面附着、打印尺寸、孔槽配合、材料强度、层间结合与使用磨损仍未验收；不把切片成功称为整机“一次过”。
