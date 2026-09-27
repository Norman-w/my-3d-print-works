# 乒乓球机械点射与可调旋转改装

当前数字总装为**33件送料机构 + 10件旋转头**。送料已经集成V定位挡指、回位弹簧端头、X/Y调隙件、背梁握把和出口连接，不能再混用旧27件总装的同名零件。

- [局域网模型与爆炸图](http://192.168.7.187:8877/)
- [统一装配、裁管和五金说明](docs/final-assembly.md)
- [工程状态与实际边界](docs/current-status.md)
- [送料离线切片](docs/final-feeder-print.md)
- [旋转头五金与装入路径](docs/spin-complete-hardware.md)
- [柔性摩擦垫材料](docs/spin-material-selection.md)、[密封工序](docs/final-sealing-process.md)

两处CAD入口分别是 `cad/launcher-final-assembly.scad`、`cad/spin-head.scad`。当前送料STL在 `output/launcher-final/`，旋转头STL在 `output/spin-head/`。整个 `output/` 还包含历史失败件、碰撞探针及研究快照，不能将目录内所有STL当作打印清单。

42个刚性件使用PETG，摩擦垫1件使用Bambu TPU 95A HF。离线工艺为X1C/0.4 mm，板型默认纹理PEI；用户只确认PEI。材料、夹持、总公差和实际发球尚未经首机验证，因此本版是数字制作候选，不能承诺一次制作必过。用户不接受先耗材打印试片，这不是继续数字设计的前置条件。

## 已确认接口

40+球；透明PC硬管内48/外50，可任意裁长；钢丝软管内50/外55，套在硬管外；硬管插原斜三通。送料模块接在软管与三通之间，旋转头接原出球管末端。新版出口有外夹座和长内衬，裁管按统一装配说明，不再沿用旧25 mm短接口的总长公式。

只有最早风机明确不能调速。后来三款已购套餐已核实，额定供电与调速能力未确认；用户回忆21 V设备在电源设42 V时能发球，不作为本版供电方案。完整记录见[现有硬件](docs/current-hardware.md)。

## 本机复跑

```sh
python3 analysis/launcher_final_assembly.py
python3 scripts/preview_lan.py status
```

旋转头、切片及边界分析分别由对应报告记录实际调用和文件哈希。局域网服务绑定0.0.0.0:8877，当前登录会话由launchd维持；注销或重启后执行 `python3 scripts/preview_lan.py start`。只服务专用预览目录，不包含采购订单或本机配对信息。

旧README保存在 `docs/history/README-before-final-integration.md`，历史子报告保留原始失败和旧身份，不把它们改写为当前通过记录。
