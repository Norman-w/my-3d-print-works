# 乒乓球机械点射与可调旋转改装

> 当前方向改为信号扳机 + BY141-3 往复电机 + 槽型光电归位。旧拉索件已退出当前选件；电机座与双向传动尚未完成，当前结构不能作为完整电动版打印包。详见[当前状态](docs/current-status.md)。

当前已定义的无拉索结构为**39件送料 + 10件旋转头**：送料左Y导向盖与运动弹簧间隔套由光电版各替换一件，固定背梁由一体式电子扳机支座替换，另增独立勾扣杠杆；旋转头保持叉是非工作档附件。滑架保留原凸轮和导轨并去掉手扣指环；拉索输入/输出/护套导向及专用五金不再采用。49件只是现阶段的结构实例，尚未计入待设计的电机座和双向传动件。[电动版清单](docs/electric-assembly-inventory.json)明确列出当前与排除项。

- [局域网模型与爆炸图](http://192.168.7.187:8877/)
- [双风机当前装配预览](http://192.168.7.187:8877/fan-nozzle/#fan76-direct)：Ø76 直插 / 80 mm、Ø41 直插 / 40 mm，均为 P4，气嘴 Ø15/20/25/30；[交付包及验证说明](docs/fan-nozzle-current.md)。
- [同场景查看已选电子扳机与整机](http://192.168.7.187:8877/models.html?trigger=1)（扳机结构已选；电路、实物开关及电机未验收）
- [电动版当前装配边界](docs/current-assembly.md)、[电动版制作状态](docs/current-manufacturing.md)
- [电子扳机 CAD、装配审查与开放项](docs/electronic-trigger.md)（已选入 49 件结构，未放行打印）
- [往复电机必要负载与缺失的实物接口](docs/electric-drive-feasibility.md)
- [电动版实例与旧件排除清单](docs/electric-assembly-inventory.json)
- [往复电机与槽型光电原候选证据](docs/optical-home-candidate.md)
- [工程状态与实际边界](docs/current-status.md)
- [历史拉索总装与动作场景](http://192.168.7.187:8877/feeder-motion.html?view=system)（该网页尚未改为电动版，不作为当前总装）
- [历史拉索选件](docs/cable-assembly-inventory.md)、[历史拉索装配说明](docs/history/current-assembly-cable-2026-09-30.md)
- [旋转头五金与装入路径](docs/spin-complete-hardware.md)
- [柔性摩擦垫材料](docs/spin-material-selection.md)、[密封工序](docs/final-sealing-process.md)、[当前润滑工序](docs/current-lubrication.md)

当前无拉索装配入口为 [electric-feeder-assembly.scad](cad/electric-feeder-assembly.scad)，其[65项几何报告](output/electric-feeder/review.json)只审查送料和光电替换件，电机未实装建模。原 `cad/cable-scene-export.scad`、HCDG8-30扳机轴系及[56件/86场景项导出报告](output/cable-scene-export/20260927T153058669616Z/report.json)均属于拉索历史版本。整个 `output/` 还包含失败件和诊断体，不能整体当作打印清单。

现阶段已定义结构中，47件刚性实例按PETG候选、旋转头摩擦垫1件按Bambu TPU 95A HF候选；待设计的电机座和传动件不在这48件内。目标工艺为X1C/0.4 mm/PEI。旧拉索版42盘切片不能直接用于本版；材料、夹持、总公差及实际发球尚未经首机验证，用户不接受把耗材试片当作继续数字设计的前置条件。

## 已确认接口

40+球；透明PC硬管内48/外50，可任意裁长；钢丝软管内50/外55，套在硬管外；硬管插原斜三通。送料模块接在软管与三通之间，旋转头接原出球管末端。新版出口有外夹座和长内衬，裁管按统一装配说明，不再沿用旧25 mm短接口的总长公式。

只有最早风机明确不能调速。后来三款已购套餐已核实，额定供电与调速能力未确认；用户回忆21 V设备在电源设42 V时能发球，不作为本版供电方案。完整记录见[现有硬件](docs/current-hardware.md)。

## 本机复跑

Git保存源码、文档和文本工程审查记录；生成物默认不入库，但已交付风机件的干净 STL、正式原生工程/切片及精选审查图按 `.gitignore` 白名单保留。采购原始数据、本机服务、缓存及临时拼盘仍忽略。文本记录保留原路径和哈希，部分历史链接指向仅在本机保存的生成物。新克隆不是整机完整离线打印包，也没有验证在全新环境下完整复跑；详见[版本快照范围](docs/version-control-snapshot.md)。

以下命令用于已配置OpenSCAD、Python依赖及本机检查工具的原工作目录：

```sh
python3 scripts/build_electric_inventory.py
python3 scripts/review_electric_feeder.py
python3 scripts/review_electronic_trigger_candidate.py
python3 analysis/electronic_trigger_release_margin.py
python3 scripts/slice_electronic_trigger_candidate.py
python3 scripts/publish_electric_preview.py
python3 scripts/preview_lan.py status
python3 scripts/verify_launcher_lan.py
```

旋转头、切片及边界分析分别由对应报告记录实际调用和文件哈希。局域网服务绑定0.0.0.0:8877，当前登录会话由launchd维持；注销或重启后执行 `python3 scripts/preview_lan.py start`。首页和零件预览已切到无拉索的 49 件现阶段结构；原动作网页保留为历史拉索场景。电机尚未安装建模，网页也不能显示已安装的往复电机。

旧README保存在 `docs/history/README-before-final-integration.md`，历史子报告保留原始失败和旧身份，不把它们改写为当前通过记录。
