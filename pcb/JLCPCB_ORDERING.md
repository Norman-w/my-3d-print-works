# 嘉立创打板操作小本（全版本通用）

> 适用：本仓库每一次向嘉立创（JLCPCB）下 PCB / 部分 SMT 订单。  
> **不绑定某一电路版本。** C4、C5 或以后任何修订，都按本页流程走；版本专属备注、门禁结论去对应 `*_FAB_NOTES.md` / `*_FAB_READINESS.md`。

## 1. 先分清三种订单

| 模式 | 嘉立创做什么 | 你回板还要做什么 | 何时用 |
|---|---|---|---|
| **A. 只做裸板** | 按 Gerber 做 PCB | 全部元件自己焊 / 本地贴 | 新拓扑首版、工艺不确定、SMT 料不全 |
| **B. 裸板 + 部分 SMT** | PCB + 贴本仓库导出的 BOM/CPL 里的 SMD | 模块、连接器、THT、线焊盘手焊 | 样板想少焊阻容/IC |
| **C. 全交钥匙 SMT** | 几乎全贴 | 尽量少 | 本项目通常**不走**：有嵌入开槽模块、手焊尾插、PZT 线焊盘 |

默认推荐样板路径：**B**（或先 **A** 验证再开 SMT）。

## 2. 下单前本地 checklist（每次必做）

在仓库根目录、**当前要投的那块板**上：

1. **确认投的是哪一版**  
   KiCad 标题栏 Title / Revision、板文件路径、对应 FAB 备注文件。禁止把旧版 Gerber ZIP 混进新版订单。
2. **读该版专属备注**（若有）  
   - 例：C4 → [`C4_FAB_NOTES.md`](C4_FAB_NOTES.md)、[`C4_FAB_READINESS.md`](C4_FAB_READINESS.md)  
   - 以后 C5 → 预期会有 `C5_FAB_NOTES.md` / readiness；没有就先别盲投。
3. **门禁绿了再导出**  
   DRC 0 error、0 unconnected；放置快照/网表门禁按该版脚本要求通过。
4. **用当前工作树重新导出**  
   禁止复用几天前的临时 ZIP；审计 ZIP 不是真理源。
5. **SMT 前更新料号表**  
   [`jlcpcb/smt_parts_map.yaml`](jlcpcb/smt_parts_map.yaml) 里的 LCSC C 号会过期，下单当天在 [jlcpcb.com/parts](https://jlcpcb.com/parts) 再核库存 / Basic·Extended。

## 3. 导出命令（通用）

```sh
# 输出目录每次用新路径，避免覆盖旧包
OUT="$(mktemp -d /tmp/smartpaddle-jlc.XXXXXX)"

# 只预检：报告 + Fab 图，不写 Gerber/ZIP
python3 pcb/scripts/export_jlcpcb.py --preflight-only --output "$OUT"

# 正式裸板包（门禁全绿才出 ZIP）
python3 pcb/scripts/export_jlcpcb.py --output "$OUT"

# 正式裸板 + 部分 SMT（BOM/CPL）
python3 pcb/scripts/export_jlcpcb.py --smt --output "$OUT"

# 也可单独出 SMT（需 KiCad 自带 Python）
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
$KPY pcb/scripts/export_jlc_smt.py --output "$OUT"
```

成功时大致得到：

```text
$OUT/
  gerbers/ …          # 进 ZIP 的源
  drill/ …
  ORDER_NOTES.txt     # 英文工艺要点；中文订单备注见该版 FAB_NOTES
  C4_fabrication_drawing.pdf   # 文件名随板；人工看外形/开槽
  reports/…           # DRC、门禁、manifest（勿上传）
  smt/                # 仅 --smt 时
    bom.csv
    cpl.csv
    hand_solder.csv
    README.txt
$OUT 同级或父级:
  ${OUT名}_smartpaddle_*_jlcpcb.zip   # 上传嘉立创的 Gerber 包
```

核对：

```sh
unzip -t "${OUT}"*_jlcpcb.zip   # 或看脚本打印的 Upload archive 路径
```

## 4. 嘉立创网站：裸板怎么点

1. 打开 [JLCPCB](https://jlcpcb.com/) → **Order now** / 立即下单。  
2. **Upload Gerber** → 选本次导出的 `*_jlcpcb.zip`（只要 Gerber+钻孔扁平包，不要把 `reports/` 塞进去）。  
3. 等识别外形后，按该版 FAB 备注填参数，SmartPaddle 刚性样板常见默认：

   | 项 | 常见选择 | 说明 |
   |---|---|---|
   | Layers | 2 | 除非该版写明多层 |
   | PCB Thickness | **0.8 mm** | C4 及当前拍内板默认；改厚必须改文档 |
   | Surface Finish | **ENIG / 沉金** | 嵌入半孔/手焊友好 |
   | PCB Qty | 5（或厂最低） | 工程样板，勿一口气量产 |
   | Board Outline | 跟随 Gerber | 不要让系统“拉直”内凹尖角 |
   | Remove Order Number | 按喜好 | 丝印区若挤可去掉 |

4. **Remark / 生产备注**  
   粘贴该版 `*_FAB_NOTES.md` 里的**中文建议备注**（内部开槽、角孔、禁止擅自改工艺等）。没有专属备注就自己写清非常规工艺，并要求改价/改外形先联系。  
5. 预览 Gerber（顶/底铜、阻焊、丝印、钻孔、Edge.Cuts）。重点看：板框、内部模块开窗、尾部连接器区、有无多余层。  
6. 若本次**不做 SMT**，直接下单支付。

## 5. 嘉立创网站：部分 SMT 怎么点

前提：已用 `--smt`（或 `export_jlc_smt.py`）生成 `smt/bom.csv` + `smt/cpl.csv`。

1. 在 PCB 参数页打开 **SMT Assembly** / PCBA。  
2. 选 **Economic**（经济型）除非该版明确要 Standard。  
3. **Assembly Side**：本仓库当前导出默认 **Top only**（顶面）。背面若有连接器，应在 `hand_solder.csv` 里，不进 CPL。  
4. **Upload BOM** → `smt/bom.csv`。  
5. **Upload CPL / Centroid** → `smt/cpl.csv`。  
6. **Process BOM & CPL**，逐项看：  
   - LCSC 是否匹配、库存、Basic / Extended；  
   - Extended 会加 setup 费；冷门料（如部分比较器）可能缺货 → 改 `smt_parts_map.yaml` 再导出，或该料改手焊；  
   - 旋转方向在 3D/贴片预览里对一下极性件（二极管、LED、电解若有、IC 缺口）。不对就改板或改 CPL，**不要赌**。  
7. 确认 **不贴**清单与 `hand_solder.csv` 一致：模块、尾插、THT 键、测试点、DNP、线焊盘等。网站上这些位应显示为不装配。  
8. Tooling / stencil：Economic 通常含钢网策略按页面默认；样板可接受厂家默认。  
9. 与 PCB 一起下单。

### 料号表维护

- 映射文件：[`jlcpcb/smt_parts_map.yaml`](jlcpcb/smt_parts_map.yaml)  
- 键是 PCB 上的 **Value** 字符串；`smt: false` 的永不进 BOM。  
- 新版本加了新器件：先补 C 号再 `--smt`；没有 C 号时 BOM 仍可能带空 LCSC，上传后要人工选料（或 `--smt-require-lcsc` 直接排除）。  
- 通用阻容优先 **Basic** 料，降低 SMT 加价。

## 6. 回板后通用顺序（与版本无关的骨架）

具体电压/限流/功能点以该版 readiness 为准。骨架如下：

1. **对板**  
   标题/修订、板厚、沉金、开窗外形、孔数观感；对照 Fab PDF。  
2. **空板电气**  
   电源对地不短路（该版电源网名以网表为准）。  
3. **确认 SMT 结果**  
   对照 `bom.csv`：该贴的已贴、极性正确；`hand_solder.csv` 位为空。  
4. **手焊**  
   按 `hand_solder.csv` + 该版装配包/焊接图：模块嵌入半孔 → 连接器 → THT → 线焊盘。  
5. **限流上电**  
   台式电源，从低压/低限流开始；不要一上来接未验证的充放电小板。  
6. **bring-up**  
   烧录、总线扫描、传感器、射频等按该版清单。  
7. **记笔记**  
   订单号、Gerber ZIP 时间戳、板 SHA、缺料/极性错误，写回该版 issues 或 readiness，方便下一版改小本与映射表。

## 7. 版本专属信息放哪

| 内容 | 放哪里 |
|---|---|
| 嘉立创怎么点、导出命令、SMT 上传 | **本文（固定）** |
| 板厚、沉金、订单中文备注、开槽工艺 | `pcb/<REV>_FAB_NOTES.md` |
| 能不能投、风险、回板逐步实测 | `pcb/<REV>_FAB_READINESS.md` |
| LCSC C 号 | `pcb/jlcpcb/smt_parts_map.yaml`（可按版本分段注释） |
| 焊接地图 / 装配 PDF | 焊接装配包输出（技能/脚本生成） |

新开一版电路时：复制/改写 NOTES + READINESS，**不必**复制本文；只改映射表和专属备注。

## 8. 常见翻车

| 现象 | 处理 |
|---|---|
| 上传了几天前的 ZIP | 删掉，从当前 Git 板重新 `export_jlcpcb.py` |
| 厂家拉直内凹角 / 移动开窗 | 备注写清；不同意加价就驳回重制 |
| SMT 预览 IC 旋转错 90°/180° | 停单；核封装 courtyard 与 CPL；必要时本地先手贴一颗对照 |
| Extended 料无货 | 换 `smt_parts_map.yaml` 替代料或该颗改手焊 |
| 把模块/尾插也勾进 SMT | 看 `hand_solder.csv`；Economic 顶贴不应含嵌入开槽模块 |
| C3 备注贴到 C4 订单 | 每版只用自己的 FAB_NOTES |

## 9. 一页速查

```text
门禁绿 → export_jlcpcb.py [--smt] → 核 ZIP + smt/*.csv
→ 嘉立创上传 ZIP → 0.8mm / 2层 / 沉金 / 填中文备注
→（可选）开 SMT → bom.csv + cpl.csv → 核旋转与不贴清单
→ 下单 → 回板对板 → 手焊 hand_solder → 限流上电 → bring-up
```
