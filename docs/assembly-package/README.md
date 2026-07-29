# SmartPaddle 一句话焊接装配包

板子到手后，在项目根目录执行：

```bash
./steps/assembly-package.sh "板子到手了，生成可打印焊接装配包"
```

输出位于 `output/pdf/assembly-package/`，不会修改现有 `output/assembly/` 旧版焊接图，也不会修改 PCB、原理图、固件、网表或走线。

## 产物

- `smartpaddle_printable_assembly_package.pdf`：A4 横向可打印包，含顶/底面定位、分区放大、参考标号、元件值/封装、Pad 1、安装顺序和焊前/焊后清单。
- `smartpaddle_assembly_components.csv`：所有封装实例的可审计数据，包括位置、面别、旋转、状态和证据。
- `assembly_package_manifest.json`：PCB SHA256、Git 状态、警告和生成统计。
- `assembly_package_qa.json`：PDF 页数、A4 页面、关键文本和渲染检查。
- `smartpaddle_assembly_package_contact_sheet.png`：渲染后的快速目检总览。

## 证据与状态

- `[OK] 已验证`：该结论可由本次 PCB 快照或受控证据直接支持。
- `[CHECK] 待确认`：PCB 只能给出位置/Pad 1，不能证明收到的实物顶标、极性标记、替代料或连接器机械朝向。开焊前必须查确切料号资料。
- 红色 `1`：PCB Pad 1 位置，不等于自动确认实物上的 Pin 1 标记。
- 红叉：DNP，默认不安装。

坐标、面别、旋转、值与封装每次都从 `pcb/layouts/default/default.kicad_pcb` 的精确字节快照提取；生成器在清单和 PDF 中记录 SHA256，并在生成结束时再次检查源文件是否变化。

旧 V3 图只作为配色、分区放大和引线标注的视觉参考。它的硬编码位置与极性说明不会被当作当前 C4 快照的事实来源。

## 依赖

脚本优先使用包含 `reportlab` 的 `python3`。若未安装但系统有 `uv`，入口会临时解析 `reportlab`、`pypdf` 与 `pillow`。Poppler 的 `pdftoppm` 可用于渲染 QA；缺少时 PDF 仍会生成，但 QA 会标为待检查。

可指定另一份只读板文件或独立输出目录：

```bash
./steps/assembly-package.sh --pcb path/to/board.kicad_pcb --out output/pdf/assembly-package-alt
```
