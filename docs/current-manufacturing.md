# 当前制作绑定与采用前索引

**当前入口是[56件/42板manifest](../output/current-eclip-manufacturing/20260927T161537157301Z/manufacturing/manifest.json)**：53件复用既有39板，输入主体/杠杆/盖3件已重切并完成限定检查，`needs_reslice=0`、`pending_instances=0`。主体追加背板支撑，盖小轴孔一面朝床并加两方窝支撑；实际3MF有向面、G-code、摆向和源SHA均已绑定。见[选择依据及清理说明](../output/current-eclip-manufacturing/README.md)。数字制作索引完整不等于整机实物通过。

以下42盘说明保留采用前L15轴的历史来源。新版也有42板，但三个输入件的文件已替换，不能按数量相同而混用；制作及实物性能未放行。

以下历史绑定版本为`20260927T091627124663Z`，共56个打印实例：55 PETG、1 Bambu TPU95A HF。该历史时点逐件入口是[manifest.json](../output/current-manufacturing/manifest.json)和[实例CSV](../output/current-manufacturing/instances.csv)。56实例绑定42张已做限定审查的板；入口后夹已采用后键端朝打印板的第三候选。这里的选盘是制作证据绑定，尚未放行整机制作或实物性能。

`items`逐件列出当前STL、SHA、材料、采用的实际3MF/G-code及审查来源。`plates`按实际文件去重；同一盘已经包含多个实例时，只打印一次该盘，不能按每个实例重复整盘。`plate_quantity`是盘内零件数量，不是重复打印次数。

`needs_reslice=true`表示当前几何没有可用切片绑定，旧切片不会进入选择。`pending_review=true`表示该实例还有明确数字审查缺口，文件只进入`candidate_3mf`和`candidate_plates`，不进入选定板。没有这两个标记仍不代表实物验收：孔径、清理力、材料强度和装配摩擦没有由离线路径确认。

## 证据分组

| 分组 | 范围与处理 |
|---|---|
| [送料原件复用](../output/current-manufacturing/feeder-reuse/report.json) | 当前36个送料实例逐件比对旧实际切片。完整网格身份成立的实例复用；几何改变与历史无切片的实例单独处理。原报告保留其最初缺口，后续结果以统一索引为准。 |
| [送料13实例重切](../output/current-manufacturing/feeder-new/report.json) | 8张当前实际切片完成，正常模型有向面、G-code身份、工艺与床界均已核对。12实例完成报告所列孔槽/清理通道检查；入口后夹整树的切断及退出顺序仍开放。左右支座初始挑针越入盲孔底的失败保留，正确孔深范围另行复核。 |
| [入口后夹当前选盘](../output/current-manufacturing/inlet-process/README.md) | 后键端朝下的第三候选补齐自身起底、孔槽、完整五金包络、逐先后承托、全树路径与起始接触来源证据，替换上一行的入口后夹待审切片。原严格失败保留；桥接、支撑剥离和承面实物质量仍开放。 |
| [拉线输入四件](../output/current-manufacturing/input-process/README.md) | 固定座、扳机、球头盖采用已审核的0.1 mm局部手动支撑；主盖0.1 mm无支撑。正式STL与冻结候选、实际3MF辅助体、G-code和摆向明确绑定。 |
| [拉线其余六件](../output/current-manufacturing/cable-other-reuse/report.json) | 背梁、滑架、输出盖及护套导向三件与原切片输入字节相同。护套导向底座仍保留原生数值转换减少两片微小面的严格失败，另列有界顶点收缩解释，不改写为严格面数相同。 |
| [旋转头十件](../output/current-manufacturing/spin-reuse/README.md) | 当前与实际3MF保持有向网格对应，包含独立TPU摩擦垫配置；正确处理完整排版旋转，并补核限定支撑清理通道。 |

新增或重切的送料件使用`output/current-manufacturing/feeder-new/`内的新产物，后续覆盖关系在统一索引中逐件记录。历史报告、失败和原切片文件保留，不通过改名字或改旧SHA伪造新版产物。

## 使用边界

- X1C与0.4 mm喷嘴来自用户；PETG品牌及PEI具体表面尚未确认，Generic PETG/Textured PEI属于当前分析假设。TPU摩擦垫有独立材料、温度和填充配置，不与PETG混用。
- 支撑按每件绑定报告在装配前清理。输入拉臂/球头盖的外部首层小岛和内部浅窝支撑分开说明，原“支撑全在两孔内”的失败仍保留；可到达不等于已证明真实PETG分离力或全部无残屑。
- 有限孔槽和工具包络检查不扩大为完整整机公差、强度、长期蠕变、带载回位、单球或旋转验收；这些见[目标审计](goal-acceptance-audit.md)。

重建索引：`python3 scripts/build_current_manufacturing_manifest.py --export-report <当前源导出报告>`。脚本只校验和整理已有证据，不切片、不连接打印机。`manufacturing_release=false`、`physical_acceptance=false`。

当前三件更新的重建器为 `scripts/advance_eclip_manufacturing.py`，显式传入本次53/3基线与已完成的 `review-index.json`；脚本只绑定已有产物，不切片、不打印。前述旧索引重建说明仅属于历史流程。
