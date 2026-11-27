# SmartPaddle 电源架构重整：跨层设计与放行说明

状态（2026-08-23）：当前硬件登记为 **M7.C5**。电气、封装、网络映射、元件位姿和固件接口已同步；尾板 J2/J3 已换为 Molex 53261-0471 卧插 SMT。当前主板 67 个封装、尾板 33 个封装均已完成布线和铺地；主板 DRC 为 0 error / 0 warning / 0 未连接，尾板为 0 error / 0 未连接（保留 3 条已审计 warning）。`scripts/validate_power_rework.py --release-gate --target all` 已通过，当前达到**工程样板下单**标准，不等于量产放行。独立上传包位于 `fab/jlcpcb-orders/20260823-m7c5/`。

版本判断以现行源为准：M7 相对 M6 新增受保护 14500 的局部内腔、两束实购 4 芯线通道、8 个 PZT 焊点让位，以及主板 B3U 调试键/ESP32 天线边界的跨层门禁；电气拓扑仍是增加 TPS62162、按键隔离、修正尾板 USB-C、双 TPS2553、ACH 电池座等内容的 C5。外壳打印件使用当前模型号 `paddle_m7_*`；PCB、同步脚本和交接文件保持跨版本通用名。OpenSCAD 连续承力生成链内部仍保留 `m6_*` 模块/参数名。现行通用入口为 [`../../pcb/ROUTING_HANDOFF.md`](../../pcb/ROUTING_HANDOFF.md)、[`../../pcb-tail/ADAPTER_HARNESS.md`](../../pcb-tail/ADAPTER_HARNESS.md) 与 [`../mechanical-handoff/README.md`](../mechanical-handoff/README.md)。

## 为什么不能只看 DRC

本轮按以下证据链放行：

1. 原厂/供应商数据表与额定值；
2. Atopile 原理连接和元件值；
3. 每个实物触点、焊盘编号、封装几何和 NC 定义；
4. 当前 PCB 的 pad-to-net 映射与机械位姿；
5. 主尾板线束逐芯对应；
6. 固件引脚极性、ADC 量测语义和网页显示语义；
7. KiCad 整板 3D、机械空腔、按键可达性与最终 DRC/连通性。

DRC 只理解板文件内已经声明的网络，不知道供应商连接器触点的真实语义。旧 J1 就是在 DRC 为 0 的情况下发生 VBUS–GND 硬短，因此制造门禁必须运行 `scripts/validate_power_rework.py --release-gate`，不能单独以 KiCad 绿色状态放行。

## 归档主证据

| 器件/用途 | 项目内文件 | SHA-256 |
| --- | --- | --- |
| IP5305T 充放电/升压 | `sources/IP5305T-V1.4.pdf` | `210568ac364ef2588792d879ffa6266ad7f70b84940bece5123ec86553d785b0` |
| TPS2553 可调限流 | `sources/TPS2553-RevF.pdf` | `56c62cd42a9b37ef3b680ab08b4921c3ec8cc997760ee403287dc4c1971852db` |
| TPS62162 固定 3.3V 降压 | `sources/TPS62162-RevE.pdf` | `6c26eb5b607f7af543c24ed99b8ed942e4819326352ae9fb87e8396686d06659` |
| Coilcraft XFL3012 2.2uH | `sources/Coilcraft-XFL3012-Doc747.pdf` | `a939120103cf22d59438ec9eaee8a385e6a7f36fc0b05492206a6e0840a94689` |
| XFL3012 原厂网页机械/推荐 land 图 | `sources/Coilcraft-XFL3012-official-land-pattern.gif` | `54a7f89087deb535be2ba85aa181000b61f45786cde12c7020013033b30c7a09` |
| Coilcraft XFL4020 2.2uH | `sources/Coilcraft-XFL4020-Doc745.pdf` | `6dca915ac1daa47210f7708a7540221ffef4f34a88a8621c94bd50cdf48647e6` |

J1、ACH 电池座和 B3U 开关的主证据分别归档在相邻专题目录，哈希由尾板审计脚本锁定。J2/J3 的 Molex 原厂链接、stock footprint 快照与哈希见 [`../molex-picoblade-53261-4p-horizontal/README.md`](../molex-picoblade-53261-4p-horizontal/README.md)。

## 最终电源路径与额定边界

```text
USB-C VBUS
  -> TPS2553 (59k, IOS(max) <= 500mA)
  -> IP5305T VIN / 1S charger

1S battery
  -> JST ACH J4.1 BAT_P
  -> IP5305T BAT + 2.2uH boost
  -> vout_5v_raw
  -> TPS2553 (43.2k, 544..673mA)
  -> J2.1 / main SYS_5V_IN
  -> AO3401A latch switch / SYS_5V_SW
  -> TPS62162 fixed 3.3V buck
  -> ESP32-S3 and 3V3 loads
```

- `J4.1=BAT_P/red`、`J4.2=GND/black`；J4 与 `J2.3 BAT_P` / `J2.2 GND` 并联。电池绝不能接 `SYS_5V_IN`。
- USB 输入限流是固定硬件上限，不是 USB-C 电流协商，也不会根据 USB 2.0 枚举动态改变。IP5305T 的 1.2A 标称充电能力高于入口允许值，样机必须验证限流时的降额、重启/打嗝行为和温升。
- 系统 5V 最坏限流约 673mA，意图是在低电芯电压时把 ACH 电池电流控制在项目 1.5A 连续门槛附近，并给 J2 单触点留余量。首板仍须实测最低电量、Wi-Fi 峰值和 LED 峰值组合。
- 尾板 `XFL4020-222MEC` 的官方值为 2.2uH、DCR 最大 23.5mΩ、10% 降感 Isat 3.1A、20°C 温升 Irms 6.0A；PCB land 也已逐尺寸匹配 0.98×3.40mm、中心距 2.37mm。它能通过当前 673mA 输出上限的解析筛查，但在最低电芯电压、最低开关频率/电感公差下峰值余量并不宽，仍必须用首板示波/温升验证，不能用 DCR/Isat 表格代替实测。
- 主板 `XFL3012-222MEC` 是 TPS62162 数据表候选表明确列出的 2.2uH 电感。原厂值为 DCR 最大 97mΩ、Isat 1.0/1.3/1.6A（10/20/30% 降感）及 Irms 1.4/1.9A（20/40°C 温升）；官方推荐 land 为 1.00×2.90mm、内间距 2.03mm，即中心距 3.03mm，当前封装已逐尺寸匹配。它适合该 1A 降压器，但满载峰值并没有很宽的 10% 降感余量，首板仍须测开关波形和温升。
- TPS62162 的 VIN/EN/PGND/AGND/FB/VOS/SW/PG/EP 已按 Rev.E 逐脚绑定；PG 明确 NC。输入 10uF、输出 22uF、XFL3012 电感按开关电流顺序紧邻放置。
- 尾板 J2/J3 使用 53261-0471 卧插后，C2 从旧 J3 包络移到 F.Cu `(2.000,1.000)`。C1/C2 同为 `V5_SW_RETURN–GND` 的 100nF，现分别靠近 D1 与 U1；C3 仍在 B.Cu `(8.001,-1.397)`，U3/L1 也保持原位。这样没有拉长 IP5305T `BAT_P–C3–GND` 与 `BAT/SW–L1` 的高脉冲电流回路，也无需旋转 5305 电源簇。

## 关机与按键

旧方案让 3.3V GPIO 上拉经按键二极管钳住 P 沟道 MOSFET 门极，能形成约 3.3V 的阈值半开反馈。新方案把原始按键网用独立 AO3400A 反相隔离：原始键由 `SYS_5V_IN` 100k 上拉，经 1k 驱动 NMOS；漏极由外部 100k 拉到 3.3V，GPIO48 按下读高。GPIO47 仍只控制独立锁存 NMOS。尾板 KEY/WLED 另加单向隔离，防止 IP5305T 照明低边输出在松键后持续拉住主板门极。

固件的关机语义是释放 GPIO47，不是只关闭 IMU。IP5305T V1.4 的长按大于 2 秒切换照明 LED，双短按才关闭升压；因此主板关机与尾板 boost 状态是两个不同概念。

## 电池遥测边界

- 当前电量无需新增导线：`J2.3 BAT_P -> 主板 1M/1M + 100nF -> ESP32-S3 GPIO9/ADC1_CH8`。100nF 为高阻分压提供采样保持，固件只在 eFuse 曲线校准可用且电压处于合理 1S 范围时发布数据。
- 网页百分比是单节锂电电压曲线的**估算值**，受负载、温度、化学体系和分压误差影响；不是库仑计，也不得参与保护控制。
- 产品决定不为网页充电状态增加导线：现有 2×4P 尾板线束已满，额外芯线对尾部空间不利。固件只发送电压/估算百分比，不发送或推断 charging 字段。
- 充电状态由尾板实体 LED1 显示。当前 `LED1/VSET -> 200R -> 绿 LED -> GND`，且 LED2/LED3 短接后经 1k 到 BAT，逐网对应 IP5305T V1.4 图 6 的一灯典型应用。充电中约 0.5Hz 闪烁，充满常亮；正常放电常亮，低电约 1Hz 闪烁。用户可从闪烁频率识别“正在充电”和“低电”；常亮本身不能区分“充满且插电”和“正常放电”，这符合当前产品取舍。

## PCB 与机械状态

- 同步脚本使用独立 staging 板，按 `atopile_address + pad number/name` 映射，并在替换前后保护既有位姿；不能用一次 `ato build` 成功代替物理焊盘审计。
- 主板开关回路、MCU 去耦/EN 和 USB 22R 已移到对应器件附近；尾板新增两颗 TPS2553 及外围位于 F 面公共空腔，名义最小顶部余量 2.35mm。
- 拍尾端面本身不挡 J1 或 SW1；完整 KiCad 3D 装配与原 Step6 壳体曾在 12 个器件处出现约 9.73mm³ 的局部环槽/侧壁相交。当前按每个器件的 KiCad courtyard 和保守高度生成独立小避让，复核总交集约 `4.97e-08mm³`，属于布尔数值噪声。方法、逐件结果和预览见 [`../tail-handle-interference/README.md`](../tail-handle-interference/README.md)。
- B3U-1000P 的基准操作方式改为执行头中心 **Ø2.0mm 直通针孔**，可用针尖/笔尖操作，因此不再由推杆行程阻塞壳体放行。项目仍提供从壳内装入、Ø3.0mm 法兰防外脱的可选推杆；其 0.05mm 间隙和最坏 0.40mm 触发行程仍应先做尾段试片，未验证前不得把可选推杆当作唯一操作方式。
- 当前已按两板独立下单流程生成 Gerber、钻孔、Fab 图、上传 ZIP 和审阅 ZIP；主板/尾板包均绑定当前 PCB SHA，位于 `fab/jlcpcb-orders/20260823-m7c5/`。本轮不生成 BOM/CPL，也不处理用户已自制的转接线束。
- 当前主/尾板 3D 视觉检查图见 [`previews/README.md`](previews/README.md)；它们展示无铜交接态，不是制造预览。
- M7 电池、双线束、PZT 焊点和天线边界的参数、剖视图及验证结果见 [`../mechanical-handoff/README.md`](../mechanical-handoff/README.md)。主板三只 `B3U-1000P` 都是 DNP 调试件，正式外壳不开孔；尾板 SW1 仍为装配的日常按键。

## 安全同步与验证

Atopile 0.12.5 对旧 B 面实例存在几何重写风险，只允许用项目脚本同步：

```sh
cd pcb && ato build && ato build && cd ..
cd pcb-tail && ato build && ato build && cd ..

KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3
$KPY pcb/scripts/sync_power_architecture.py
$KPY pcb/scripts/place_power_architecture.py
$KPY pcb-tail/scripts/sync_power_architecture.py
$KPY pcb-tail/scripts/place_power_architecture.py
python3 scripts/validate_power_rework.py
```

当前应运行工程样板制造放行命令：

```sh
python3 scripts/validate_power_rework.py --release-gate
```

它要求逐触点/线束/数据表审计通过、两板存在铜、DRC 无 error 且无未连接，并确认 Ø2.0mm 针孔基准仍有效。可选 B3U 推杆的试片状态会被明确保留，但不再阻塞针孔基准方案；任何电气或基准机械条件失败都不会生成上传 ZIP。当前包已通过该门禁；回板后的电气、热、射频和可靠性测试仍未完成。

## 旧板结论

所有按错误 J1 映射制造、焊接或导出的旧尾板和旧制造包必须隔离退役：**不得上电、不得插 USB、不得再次下单，也不建议现场飞线返修。**
