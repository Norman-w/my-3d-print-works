# M5 预览（诊断用）

> **无电池匣**。可打印最终件在 `enclosure/stl/`，由 `./scripts/export-stl.sh` 统一导出。  
> 尾板开孔由 **Step6** 对已导出拍柄做布尔干涉，**不要**再跑独立 m5 裁切/清螺丝脚本。

## 唯一导出入口

```bash
./scripts/export-stl.sh
```

若存在 `pcb-tail/layouts/default/default.kicad_pcb`，导出结束后自动：

1. 从 KiCad 导出 Edge.Cuts + USB/按钮/LED 开孔事实  
2. 干涉 `paddle_handle_{front,back}.stl`  
3. 重拼 `paddle_shell_*` / `paddle_split_assembly.stl` / tip  
4. 镜像 tip + 诊断到本目录 `build/` 供预览

```bash
./scripts/preview-m5.sh
```

## 本目录

| 文件 | 职责 |
|------|------|
| `tail_board_cuts_m5.scad` | 自动生成：KiCad 开孔（OpenSCAD 可选引用） |
| `preview.html` | tip / 板槽 / UI 切换预览 |
| `build/*.stl` | Step6 镜像（非独立管线产物） |

废弃：`build-m5-from-real-handle.py`、独立 `export-m5-*` 挖孔逻辑。
