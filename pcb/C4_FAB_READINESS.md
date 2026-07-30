# C4 最终制造与回板就绪审计

> 审计日期：2026-07-30（Asia/Shanghai）  
> 适用对象：`pcb/layouts/default/default.kicad_pcb`，标题栏 **SmartPaddle Rigid PCB / C4**  
> 审计板 SHA256：`86389d959e48d7393d59ea44571635a1011f239213585d538611171193bb0b70`

## 1. 一句话结论

**C4 裸板已经达到“小批量工程样板可投板”的门槛；C4 整机尚未达到“无需实测即可确认稳定工作”的门槛。**

- 可以下单：当前板的 Atopile 拓扑、63 件放置、当前物理焊盘网络、走线、铺铜、DRC、Gerber、钻孔与压缩包门禁均已通过机器检查。
- 建议只下工程样板：先做 5 片或厂家最低样板数量，不直接量产。
- 首次 bring-up 必须先用限流台式 5 V 电源，不要先接照片中的充放电小板。
- 要把照片中的六焊脚 Type-C 充放电小板用于供电可以，但其 Type-C **没有 D+/D−**；C4 的 USB D+/D− 必须由另一只完整 USB 2.0 Type-C 母座/尾板或测试线接入。
- 是否会在 Wi-Fi + IM948 + LED 峰值负载下稳定，仍取决于外置 5 V 模块的瞬态能力和 AP2112 温升。这两项只有回板带载测试能定论。

因此放行状态分成两层：

| 对象 | 状态 | 含义 |
|---|---|---|
| C4 裸 PCB 工程样板 | **GO** | 可用当前门禁重新导出后投 0.8 mm、2 层、ENIG 样板 |
| C4 首件装配 | **CONDITIONAL GO** | 按本文装配与限流上电顺序进行 |
| 使用现成充放电模块的完整整机 | **HOLD FOR TEST** | 先验证 5 V 瞬态/压降、AP2112 温升、USB 独立尾线与机械装配 |
| 批量生产 | **NO-GO** | 回板、射频、热、功耗、振动、汗液和内部开槽工艺都尚未验证 |

## 2. 审计基线与工具

| 项 | 锁定结果 |
|---|---|
| KiCad | 9.0.6 |
| Atopile | `ato.yaml` 锁定且实跑 0.12.5 |
| ESP-IDF | 5.5.1，目标 `esp32s3` |
| OpenSCAD | 2021.01 |
| PCB 标题 / 修订 | `SmartPaddle Rigid PCB` / `C4` |
| PCB SHA256 | `86389d959e48d7393d59ea44571635a1011f239213585d538611171193bb0b70` |
| 封装数 | 63：顶面 62，背面 1 |
| 板尺寸包围盒 | 80.856 mm × 146.293 mm |
| 板厚 | KiCad 设定 0.8 mm |

最终采购或装配前必须再次核对 PCB SHA。任何铜线、焊盘网络、板框、器件位置或封装修改都会使本审计失效，应重新执行第 12 节全部命令。

## 3. 已通过的机器门禁

### 3.1 Atopile 与物理焊盘网络

- `ato_build_safe.sh`：Atopile 0.12.5 `Build successful`，构建前后权威 PCB 字节保持不变。
- S3 pinmap 门禁：Atopile、S3 封装、导入器和 ESP-IDF 配置一致。
- Step 3.2 `--check-only`：63 个地址、225 个引脚-网络关系、182 个已连接焊盘号通过。
- 导出门禁不仅比较网表，还逐一比较当前板上所有物理焊盘的 pad number、pad set 与实际 net；当前为 0 项不匹配。
- 导出门禁拒绝重复 Reference、重复 `atopile_address`、遗留 C6、错误 DNP、无铜线、无铺铜、无网络铜和错误标题栏。

这解决了“源网表正确但手工布线板上的某个实体焊盘被误赋网”不会被普通新鲜度检查发现的问题。

### 3.2 最终放置快照

- `c4_placement_snapshot.json` 锁定全部 63 个 `atopile_address` 的 X/Y、绝对角度和正反面。
- KiCad Python 只读比较通过：63 个变换与当前板完全一致。
- 制造导出会拒绝快照缺失或当前板位置偏离快照。

### 3.3 走线、铺铜与 DRC

| 项 | 结果 |
|---|---:|
| 铜线项目 | 996 |
| 普通线段 | 898 |
| 过孔 | 98，统一 0.6/0.3 mm |
| 0.2 mm 线段 | 468 |
| 0.4 mm 线段 | 429 |
| 0.6 mm 线段 | 1 |
| 区域总数 | 16 |
| 实际铜区 | 1，B.Cu GND |
| 无网络铜 | 0 |
| DRC error | **0** |
| DRC unconnected | **0** |
| DRC warning | 72，均已分类复核 |

72 条 warning 的处置：

| 类型 | 数量 | 处置 |
|---|---:|---|
| `lib_footprint_mismatch` | 35 | 当前板与现有库逐 pad 比较；pad number、层、形状、属性、尺寸、钻孔、角度、圆角均无实质差异。最大位置差 0.000015 mm，属于库/版本小数序列化噪声，接受。 |
| `silk_edge_clearance` | 17 | 只影响丝印可能被板厂裁切，不影响铜连接；样板接受。 |
| `silk_over_copper` | 13 | 只影响丝印可读性，不影响阻焊/电气；样板接受。 |
| `silk_overlap` | 7 | 只影响丝印可读性；装配以当前焊接装配包、Reference/Value 和显微镜定位为准。 |

### 3.4 关键网络几何

以下长度为 KiCad 铜线段几何长度，不含焊盘内部长度和过孔 Z 向长度：

| 网络 | 线段 | 过孔 | 长度 | 线宽 |
|---|---:|---:|---:|---|
| `usb_dp` | 17 | 1 | 84.055 mm | 0.4 mm |
| `usb_dn` | 23 | 3 | 87.642 mm | 0.4 mm |
| `sys_5v_in` | 32 | 0 | 114.072 mm | 0.4 mm |
| `sys_5v_sw` | 70 | 3 | 150.565 mm | 主干 0.4 mm，局部分支 0.2 mm |
| `vcc`（3.3 V） | 117 | 19 | 294.187 mm | 主干 0.4 mm，局部分支 0.2 mm |
| `i2c_sda` / `i2c_scl` | 16 / 13 | 1 / 1 | 18.919 / 18.607 mm | 0.2 mm |
| IMU UART TX / RX | 2 / 3 | 0 / 0 | 4.751 / 5.054 mm | 0.2 mm |

USB D+/D− 的板内长度差约 3.59 mm，对 USB Full-Speed 的传播时间不是首要问题；真正的剩余风险是未按阻抗工具确认 90 Ω 差分、D− 多两个过孔、没有串联电阻预留和没有 USB ESD。C4 可作为短线工程样板验证，不能把这等同于 USB 量产合规。

### 3.5 Gerber、钻孔与压缩包

最终导出实测结果：

- 制造门禁：`OK`；manifest 为 `production_ready: true`。
- 上传 ZIP：11 个文件；9 个 Gerber、1 个 `.gbrjob`、1 个 Excellon 混合镀孔钻孔文件。
- 钻孔：0.300 mm × 98、0.600 mm × 56、0.900 mm × 12、1.000 mm × 2、1.200 mm × 8，共 176 孔。
- ZIP 解压完整性测试无错误。
- A4 Fab 图和钻孔图已渲染人工检查；外形、内部 MCU/IMU 开槽、PZT 码头、尾部孔位与制造注释可见。
- 导出物是临时审计产物，不作为永久真理源提交；下单时必须由当前 Git 工作树重新运行导出脚本。

## 4. 电源电路审计

### 4.1 C4 实际电源路径

```text
外置充放电总成 5 V OUT
        │
        └─ SYS_5V_IN → AO3401A P-MOS → SYS_5V_SW
                                      ├─ IM948 VBUS
                                      ├─ 尾部 LED 5 V
                                      └─ AP2112K-3.3 → VCC/3V3 → ESP32-S3、DAC、比较器

单节锂电 B+ ── 外置充放电总成 B+
        └────── C4 BAT_CELL_P → 1 MΩ / 1 MΩ 分压 → BAT_SENSE
```

C4 **没有**锂电充电 IC、电池保护 IC、5 V 升压 IC或 USB VBUS OR-ing；这些功能都由外置充放电总成承担。不要把裸电池直接接 `SYS_5V_IN`，也不要把升压 5 V 接到 `BAT_CELL_P`。

### 4.2 软开关

- `PW_Q_LOAD = AO3401A`：P 沟道，SOT-23，当前脚位 1=G、2=S、3=D。
- `PW_Q_LATCH = AO3400A`：N 沟道，SOT-23，当前脚位 1=G、2=S、3=D。
- 用户按键通过 1N4148W 拉低 P-MOS gate 启动；MCU GPIO47 拉高 `PWR_LATCH`，AO3400A 随后保持 P-MOS gate 为低。
- 固件 `app_main()` 首项即调用 `power_control_init()`，先保持 GPIO47，再初始化 NVS、IMU、网络等耗时部分。
- `PWR_LATCH` 有 100 kΩ 下拉；P-MOS gate 有 100 kΩ 上拉，断电状态确定。

本轮已把原先“泛型 P/N MOS”收敛成确切料号，并同步 Atopile、放置脚本和当前 PCB Value。任何替代 MOS 都必须重新核对方向、VGS、RDS(on) 和 1/2/3 引脚，不能只看同为 SOT-23。

### 4.3 AP2112 的主要残余风险

AP2112 官方给出 600 mA 输出能力；SOT-25 的结到环境热阻典型为 184 °C/W。C4 从 5 V 线性降到 3.3 V：

| 3.3 V 负载 | 理想损耗 `(5−3.3)×I` | 仅按 184 °C/W 估算温升 |
|---:|---:|---:|
| 250 mA | 0.425 W | 约 78 °C |
| 300 mA | 0.510 W | 约 94 °C |
| 500 mA | 0.850 W | 约 156 °C |

这不是实际壳温预测，但足以说明“额定 600 mA”不等于 C4 上可以长期在 5→3.3 V、600 mA 运行。ESP32-S3 Wi-Fi 峰值和环境温度可能触发压降、热保护或 brownout。C4 回板必须测 AP2112 的 3.3 V 谷值、输入/输出电流与热像/热电偶温升。C5 已规划改用 TPS62162 降压，不能把该改进倒灌到已冻结 C4。

## 5. 外置充放电模块边界

用户提供的商品图文字只宣称约 450 mA 常规 5 V 输出，并注明 1 A 时可能落到约 4.9–4.5 V；这属于商品宣传参数，**不是本项目实测**。而 ESPressif 的 ESP32-S3 硬件指南建议电源至少具备 500 mA 能力，整机还包括 IM948、LED 和转换损耗。

所以现成小板可以作为 C4 供电候选，但不能在下列测试前被认定为合格总成：

1. 电子负载 0→0.6 A 阶跃，示波器看 5 V 谷值、振铃和恢复时间。
2. 接 C4 后同时开启 Wi-Fi 发包、IM948 100 Hz 和 LED 峰值亮度，记录 5 V/3.3 V 最低值与 ESP brownout 日志。
3. USB 5 V 插入、拔出和边充边工作，确认不会把系统 5 V 反灌至 USB 或电池节点。
4. 电池满电、标称电压与保护临界电压分别测试开机、关机、自动切换和静态电流。
5. 用热像仪观察升压电感/芯片、AP2112、AO3401A 和电池温升。

首次 C4 bring-up 应旁路这个未知模块，直接由限流台式 5 V 接 `SYS_5V_IN/GND`。确认主板本身稳定后再加入充放电板，这样才能区分主板问题与电源模块问题。

## 6. USB 结论

### 已证实

- ESP32-S3 原生 USB D+ / D− 已经通过 C4 正反 MX1.25 尾插引出。
- C4 板内两条网络已连通，DRC 无未连接。
- 现有充放电板照片中的 Type-C 只有六个信号焊脚，不具备 USB 2.0 D+/D− 引脚；不能从它上面飞出数据线。

### C4 可用接法

必须另做完整数据尾线/尾板：

- Type-C A6 与 B6 合并为 D+，接 C4 `usb_dp`。
- Type-C A7 与 B7 合并为 D−，接 C4 `usb_dn`。
- CC1、CC2 各接 5.1 kΩ Rd 到 GND，声明设备端/UFP。
- VBUS 进入充电/5 V 总成；GND 与 C4 共地。
- D+/D− 不经过照片中的充电小板，不与充电小板六脚 Type-C 的未知焊脚试接。

### 残余风险

- C4 没有 USB D+/D− 22/33 Ω 串阻预留，也没有 TVS/ESD。
- 未用场求解器或板厂叠层确认 90 Ω 差分阻抗。
- 尾部线束必须双绞/并行、短、等环境，并避免与升压电感和 LED 电源并行。

因此 USB 适合工程烧录/验证，能否稳定通过不同电脑、不同线材和 ESD 环境仍需回板矩阵测试；C5 的完整 16P Type-C 尾板必须补齐串阻、ESD、CC 与阻抗约束。

## 7. PZT、DAC、比较器与 IMU 审计

### 已由源和脚位证实

- MCP4728-E/UN：MSOP-10，四路 DAC，I²C 地址默认候选 `0x60`；LDAC 拉低。
- TLV1814PWR：TSSOP-14 四比较器，推挽输出，不需要四个外部输出上拉。
- 四个 PZT 码头：1 MΩ 泄放、4.7 kΩ 串联、BAT54S 到 0/3.3 V 钳位，再进入比较器正端。
- 四路 DAC 阈值进入比较器负端；TL/TR 通道有意对调以避免物理交叉。
- 四路 `JP_ADC_*` 是调试窥探 0 Ω，全部 DNP；未焊时正式定位功能不依赖 ADC。
- MCP4728/TLV1814 供电和 I²C 去耦、4.7 kΩ I²C 上拉均存在。
- IM948 UART 走线很短且无过孔；GPIO41 TX→IMU RXD，GPIO40 RX←IMU TXD。

### 必须回板验证

- 比较器没有模拟迟滞网络；机械振铃可能造成多次翻转。固件能锁存首次边沿，但误触发率和四角先后次序必须用真实 PZT 标定。
- 商品/模块数据不足以证明 IM948 `ADIN` 输入阻抗；`BAT_SENSE` 同时接 ESP32 ADC 和 IM948 ADIN，必须测量是否加载 1 MΩ/1 MΩ 分压并校准。
- 0.1–2 V 的真实 PZT 波形、钳位电流、门槛范围、静置噪声和击球 TDOA 必须实测，不能由 DRC 推导。

## 8. MCU、固件与射频

- MCU 锁定 ESP32-S3-WROOM-1-N16R8：16 MB Flash、8 MB Octal PSRAM；GPIO35–37 未分配。
- ESP-IDF 5.5.1 干净构建成功，`smartpaddle.bin` 为 0xD5410（853 KiB），最小 2 MiB app 分区约 58% 空余。
- 固件构建 SHA256：`8308cda41fab4f6064d2e940abdad4fb00fae092aecb550e7320a8c005a481d9`。该哈希是审计时的临时干净构建产物，不代替源码提交。
- ESP32 模块在 C4 主板内部开窗中嵌入；EP41 无主板 land，必须通过周边 GND pad 1/40 与就近地过孔完成接地。
- 主板在天线下方开空，但整机壳体、电池、线束、人体握持和附近铜仍会影响射频。必须做 BLE/Wi-Fi RSSI、吞吐、断线重连和方向性测试。

## 9. 制造与机械风险

### 内部 PTH 锣槽

ESP32-S3 与 IM948 的内部 `Edge.Cuts` 有意穿过主板 PTH 中心，形成嵌入模块的手焊界面。这不是普通板外边半孔。Gerber 和 Fab 注释已经明确：厂家若不能做内部半孔，可按普通锣槽切过已电镀孔，样板接受毛刺、露铜或孔壁不完整，但不得擅自移动开槽或加价改工艺。

投板前必须把 [`C4_FAB_NOTES.md`](C4_FAB_NOTES.md) 的中文备注填入订单，并让厂家对内部槽反馈。首批要显微镜检查孔环残留、槽边毛刺、模块实际落位和可焊性。

### 外形与壳体

- SCAD M4 四件快速 STL 导出通过，OpenSCAD 无 manifold error。
- MX1.25 壳体间隙检查通过：最小 X 间隙 +2.800 mm，最小 Z 间隙 +2.839 mm。
- C4 尾部机械孔位和正反 MX1.25 方向已进入装配包。
- 以上只证明 CAD 几何，不证明板厂公差、连接器来料高度、焊锡堆积、线束弯曲半径和打印件收缩。

## 10. 当前 BOM 收敛状态

当前 PCB 的 63 个封装按 Value 分组如下；这不是可直接上传 JLC SMT 的 CPN 表：

| 数量 | 值 / 型号 | 说明 |
|---:|---|---|
| 1 | ESP32-S3-WROOM-1-N16R8 | 嵌入模块，必须锁 N16R8 |
| 1 | IM948 | 用户现有模块/来料仍需核尺寸和针脚 |
| 1 | MCP4728-E/UN | MSOP-10 |
| 1 | TLV1814PWR | TSSOP-14 |
| 1 | AP2112K-3.3 | SOT-23-5 |
| 1 | AO3401A | P-MOS；1=G、2=S、3=D |
| 1 | AO3400A | N-MOS；1=G、2=S、3=D |
| 4 | BAT54S | SOT-23 双肖特基 |
| 1 | 1N4148W | SOD-323 |
| 2 | MX1.25-5P | Molex 53261-0571 或机械/脚位完全复核的等效件 |
| 3 | 4.5×4.5 开关 | BOOT、EN、用户电源键；高度需按外壳实物确认 |
| 1 | 0603 电源 LED | 颜色/极性/亮度按 1 kΩ 串阻实物确认 |
| 2 / 1 / 10 / 6 / 2 / 1 | 100 kΩ / 10 kΩ / 1 MΩ / 4.7 kΩ / 1 kΩ / 330 Ω | 0603，建议 1% |
| 5 / 3 / 1 | 100 nF / 10 µF / 1 µF | 0603；10 µF 建议 X5R/X7R、≥6.3 V，须核实料盘有效容值 |
| 4 | 0 Ω DNP | `JP_ADC_TL/TR/BL/BR`，默认不焊 |
| 2 | 测试点 | 3V3、SYS_5V_SW，不装元件 |
| 8 | PZT 线焊盘 | 四组 signal/GND，不装元件 |

自动生成的 Atopile BOM 当前为空，旧采购 CSV 也与当前 C4 不一致。采购必须以当前 PCB Value、装配包 CSV 和本表为起点，再补齐厂牌料号、容差、额定值、生命周期与批准替代；不能直接照旧表下单。

## 11. 回板装配与 bring-up 顺序

### 11.1 空板

1. 对照板标题、C4 修订和订单 Gerber；检查板厚、表面处理、外形、内部槽和 176 个孔。
2. 显微镜检查槽边 PTH、阻焊桥、尾插焊盘、过孔偏移、短路和断线。
3. 万用表确认 `SYS_5V_IN-GND`、`SYS_5V_SW-GND`、`VCC-GND` 不短路。

### 11.2 分级焊接

1. 先焊 0603 阻容；四个 `JP_ADC_*` 保持空。
2. 焊 BAT54S、1N4148W、AO3401A、AO3400A、AP2112、MCP4728、TLV1814。
3. 再嵌入焊 ESP32-S3 和 IM948；逐脚检查半孔/孔环吃锡。
4. 焊三颗开关和正反 MX1.25；PZT 线、尾部线束最后接。
5. 对照本地生成的 `output/pdf/smartpaddle-ai-assembly/smartpaddle-c4-solder-assembly.pdf`；任何 `[CHECK]` 项先核数据手册和来料丝印。

### 11.3 首次上电

1. 台式电源 5.0 V，限流从 50–100 mA 开始，接 `SYS_5V_IN/GND`。
2. 未按键时确认 P-MOS 关闭；按用户键后确认 `SYS_5V_SW` 建立。
3. 确认 `VCC=3.3 V`，再逐级提高限流；观察 AP2112 是否异常发热。
4. 烧录最小固件，确认 GPIO47 能保持开机、长按/软件关机能释放。
5. 依次验证 UART0、原生 USB、IM948 UART、I²C 扫描、MCP4728 0x60、四路比较器静态状态。
6. 最后接 PZT、LED、电池分压和外置充放电模块；每加一项都复测 5 V/3.3 V 谷值。

### 11.4 放行测试

- Wi-Fi + BLE + IM948 + LED 的峰值电流、AP2112 温升和 brownout。
- USB 在 macOS/Windows/Linux、不同 C-C/A-C 线和冷热插拔下枚举/烧录。
- 四角轻敲、强敲、静置、持拍振动的门槛、误触发和 first-order。
- M4 壳体装入后的 RSSI、温升、按键、线束受力和尾插可达性。
- 连续击球、跌落、汗液/潮气与电池低电压测试。

## 12. 可复现命令

从仓库根目录执行；不能在有未审查 PCB 修改时复用旧报告：

```sh
# Atopile 只读安全构建（会保护当前 PCB）
pcb/scripts/ato_build_safe.sh

# 源脚位与新鲜网表
python3 pcb/scripts/validate_esp32s3wroom1_pinmap.py
python3 pcb/scripts/step3_import_netlist.py --check-only

# 63 件位置快照；此脚本必须用 KiCad 自带 Python
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 \
  pcb/scripts/step4.1e_backup_c4_placement.py --check-only

# SCAD 尾插间隙
python3 pcb/scripts/check_tail_mx125_shell_fit.py

# 只预检
python3 pcb/scripts/export_jlcpcb.py --preflight-only

# 正式重新导出到明确的新目录；成功时才生成上传 ZIP
OUT="$(mktemp -d /tmp/smartpaddle-c4-jlc.XXXXXX)"
python3 pcb/scripts/export_jlcpcb.py --output "$OUT"
unzip -t "${OUT}_smartpaddle_c4_jlcpcb.zip"
```

固件干净构建应使用 ESP-IDF 5.5.1 和新的临时 build 目录；不能用已有 `firmware/build/` 的缓存结果替代。

## 13. 数据手册与规范证据

- [Espressif ESP32-S3-WROOM-1/1U 数据手册](https://documentation.espressif.com/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf)
- [Espressif ESP32-S3 硬件设计检查表（电源与 USB）](https://documentation.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/schematic-checklist.html)
- [Espressif ESP32-S3 PCB 布局指南（USB 90 Ω、串阻与回流）](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/pcb-layout-design.html)
- [Diodes AP2112 数据手册](https://www.diodes.com/datasheet/download/AP2112.pdf)
- [AOS AO3401A 数据手册](https://www.aosmd.com/sites/default/files/res/datasheets/AO3401A.pdf)
- [AOS AO3400A 数据手册](https://www.aosmd.com/res/data_sheets/AO3400A.pdf)
- [Microchip MCP4728 产品页与数据手册](https://www.microchip.com/en-us/product/MCP4728)
- [TI TLV1814 数据手册](https://www.ti.com/lit/gpn/TLV1814)

## 14. 后续版本边界

C4 现在冻结为“工程样板审计基线”。不得为了修 C5/M5 的电源、USB 或可换电池设计而继续无版本升级地改写 C4。C5 应从通过 bring-up 的 C4 证据派生，按 [`C5_PLAN.md`](C5_PLAN.md) 和 [`../enclosure/M5_SCAD_PLAN.md`](../enclosure/M5_SCAD_PLAN.md) 独立实现；M4/C4 的回归基线保留。
