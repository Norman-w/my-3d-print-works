# 乒乓球机械点射与可调旋转改装

> 当前拉索版已统一实例清单、完整三维场景及56实例/42板制作索引；数字审查的范围与缺口各有记录，实物功能尚未验收。当前文件用于设计审查，不能据此承诺一次制作必过。详见[当前状态](docs/current-status.md)。

当前拉索候选为**46件送料及拉线机构 + 10件旋转头**，共56个打印实例。它从38件送料基线替换背梁和滑架，再增加输入扳机四件（含端球捕获盖）、输出盖一件、护套导向三件；原有V挡指、导向、回位弹簧及管口连接保留。完整场景另含五金组和参考件，共86项；86不是采购数量。

- [局域网模型与爆炸图](http://192.168.7.187:8877/)
- [完整三维动作场景](http://192.168.7.187:8877/feeder-motion.html?view=system)
- [当前实例、替换关系与运动分组](docs/cable-assembly-inventory.md)
- [拉索固定与动作核验](docs/cable-trigger-integration.md)
- [当前完整装配与裁管、穿线、调零顺序](docs/current-assembly.md)
- [当前制作索引](docs/current-manufacturing.md)、[机械行程与回位复核](docs/current-mechanical-review.md)
- [工程状态与实际边界](docs/current-status.md)
- [送料基线历史装配说明](docs/final-assembly.md)
- [旋转头五金与装入路径](docs/spin-complete-hardware.md)
- [柔性摩擦垫材料](docs/spin-material-selection.md)、[密封工序](docs/final-sealing-process.md)、[当前润滑工序](docs/current-lubrication.md)

当前按实例导出入口为 `cad/cable-scene-export.scad`，局部拉索总装为 `cad/cable-complete-review.scad`；它们调用原生机械源码，没有用STL替代CAD。当前快照见[56打印件与86场景项导出报告](output/cable-scene-export/20260927T153058669616Z/report.json)。输入转轴已采用HCDG8-30及配套NETW7卡簧，轴套采用POM-C六角套。旧 `output/launcher-final/` 报告仍是33件历史快照；整个 `output/` 还包含失败件和诊断体，不能整体当作打印清单。

55个刚性打印实例设计使用PETG，摩擦垫1件使用Bambu TPU 95A HF；轴套和金属件另列，不混入打印数。目标工艺为X1C/0.4 mm，用户确认PEI但未确认表面种类。[当前制作索引](output/current-eclip-manufacturing/README.md)为56实例绑定42盘，三个新版输入件已重切，数字索引无待重切实例；制作与实物性能仍未放行。材料、夹持、总公差和实际发球尚未经首机验证；用户不接受先耗材打印试片，这不是继续数字设计的前置条件。

## 已确认接口

40+球；透明PC硬管内48/外50，可任意裁长；钢丝软管内50/外55，套在硬管外；硬管插原斜三通。送料模块接在软管与三通之间，旋转头接原出球管末端。新版出口有外夹座和长内衬，裁管按统一装配说明，不再沿用旧25 mm短接口的总长公式。

只有最早风机明确不能调速。后来三款已购套餐已核实，额定供电与调速能力未确认；用户回忆21 V设备在电源设42 V时能发球，不作为本版供电方案。完整记录见[现有硬件](docs/current-hardware.md)。

## 本机复跑

Git保存源码、文档和文本工程审查记录；STL、3MF、G-code、媒体、采购原始数据及本机服务状态不入库。文本记录保留原路径和哈希，部分链接指向仅在本机保存的生成物。新克隆不是完整离线打印包，也没有验证在全新环境下完整复跑；详见[版本快照范围](docs/version-control-snapshot.md)。

以下命令用于已配置OpenSCAD、Python依赖及本机检查工具的原工作目录：

```sh
python3 scripts/export_cable_scene.py
python3 scripts/preview_lan.py status
```

旋转头、切片及边界分析分别由对应报告记录实际调用和文件哈希。局域网服务绑定0.0.0.0:8877，当前登录会话由launchd维持；注销或重启后执行 `python3 scripts/preview_lan.py start`。只服务专用预览目录，不包含采购订单或本机配对信息。

旧README保存在 `docs/history/README-before-final-integration.md`，历史子报告保留原始失败和旧身份，不把它们改写为当前通过记录。
