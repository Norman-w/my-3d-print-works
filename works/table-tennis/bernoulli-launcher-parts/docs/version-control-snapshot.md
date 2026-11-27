# 当前拉索版的版本快照范围

> 以下记录为历史拉索版快照。2026-10-07 风机交付例外：Ø41 v5 与 Ø76 v1 的 10 个干净 STL、两份正式原生工程、两份真实 G-code 3MF、审查图及审查数据纳入 Git；前端源码与固定 Three.js 依赖也已纳入。缓存、部署副本、重建件和临时拼盘仍排除。当前入口见[双风机交付说明](fan-nozzle-current.md)。下文历史范围不作追溯改写。

本次提交保存电动方案讨论前的拉索版。未改动机械几何、现有场景服务、切片或打印状态。

## 保存内容

- `cad/`：原生参数化机械源码。
- `analysis/`、`scripts/`、`web/`：分析、导出、索引及场景程序。
- `docs/`、根README：设计说明、装配顺序、当前状态与历史边界。
- `output/`内的`.py`、`.scad`、`.md`、`.json`、`.csv`：手写审查脚本、冻结输入源码和文本证据，按原路径保存。有程序直接引用这些文件，不能把整个目录视为可删除缓存。

## 仅在本机保存的内容

STL、3MF、G-code、NPZ、图片、视频、PDF、压缩包及运行日志不入库。`output/procurement/`、`output/preview-service/`、`output/revision-review/`整体排除，分别包含采购原始数据、本机服务状态和部署后的预览资源。缓存及根目录切片临时文件`result.json`也排除。

历史记录中的文件路径、SHA和失败结果保持原样，未为使链接看似完整而改写。记录中的绝对工具路径来自当时执行环境；复跑前须配置对应依赖。完整网页需要生成的模型清单、STL及Three.js资源，完整切片审查还需要实际3MF/G-code；因此本提交不是即开即用的离线打印包，也不表示新克隆已完整复跑。

## 当前入口

- 场景：`output/cable-scene-export/20260927T153058669616Z/report.json`，56个打印实例、86项场景对象。
- 制作：`output/current-eclip-manufacturing/20260927T161537157301Z/manufacturing/manifest.json`，56实例、42板。
- 装配：`output/current-assembly-package/runs/20260927T164103218111Z/manifest.json`。
- 机械边界：`docs/current-mechanical-review.md`、`docs/goal-acceptance-audit.md`。

制作放行、实际装配和功能验收仍未完成；本次Git检查只确认快照内容及文件状态，不扩大现有工程结论。
