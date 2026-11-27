# 已归档：FreeCAD 实验残留

> 纠正说明：SmartPartsDrawer 当前以及实际采用的研发流程一直是 **OpenSCAD → STL → Three.js**。FreeCAD 从未成为本项目的实际建模、干涉检查、装配预览或验收工具。

仓库里仍然能看到 `fc_*`、`freecad_*`、`web/freecad-viewer.html` 等文件，是早期一次实验性提交留下的残留（历史提交 `ca3dcb0`），不是当前工程的实现依据。它们保留在仓库中只为了 Git 追溯，不能生成当前生产装配、采购尺寸或 ESP32 控制参数。

## 当前唯一有效入口

- OpenSCAD 真值：[`cad/openscad/`](cad/openscad/)
- SCAD → STL/契约导出：[`scripts/export_cabinet_clutch.sh`](scripts/export_cabinet_clutch.sh)、[`scripts/export_cabinet_chain.sh`](scripts/export_cabinet_chain.sh)
- 链条参数求解与同步检查：[`scripts/solve_cabinet_chain.py`](scripts/solve_cabinet_chain.py)、[`scripts/validate_cabinet_chain_sync.py`](scripts/validate_cabinet_chain_sync.py)
- Three.js 装配预览：[`web/cabinet-preview/`](web/cabinet-preview/)
- 控制层边界：[`docs/control/README.md`](docs/control/README.md)
- 装配坐标分工：[`docs/parts/assembly-coordinate-ownership.md`](docs/parts/assembly-coordinate-ownership.md)

当前机械真值是 5 列 × 3 层、15 个抽屉站点；当前离合是永磁触发/释放方案。网页只消费 OpenSCAD 导出的 STL、运动契约和装配实例，不从 FreeCAD 文件读取任何尺寸或坐标。

## 明确禁止

不要运行以下历史入口来重建或预览当前工程：

- `scripts/check_freecad_ready.sh`
- `scripts/run_freecad_pipeline.sh`
- `scripts/run_freecad_snake_anim.sh`
- `scripts/dev_local_loop.sh`
- `scripts/freecad_drawer_pipeline.py`
- `scripts/freecad_snake_animate.py`
- `web/freecad-viewer.html`

这些入口使用旧的 FreeCAD/4 列或旧离合假设，运行结果不属于当前 5×3/15 站 OpenSCAD 装配。需要局域网预览时，使用项目现有的 `scripts/preview_http.sh` 和 `output/3d-preview` 导出目录。
