# Plan：贝塞尔 → OpenSCAD 外壳

**目标**：打印外壳与 Live/Shape（Three.js 贝塞尔）一致，光滑无阶梯；孔腔仍用 `parameters.scad`。

**主战场**：OpenSCAD（阶段 1：查表 + 64 层放样；后续可接 BOSL2 sweep）。

---

## 阶段 0 — 准备

- [x] 决策文档 `enclosure-openscad.md`
- [x] 本 Plan

## 阶段 1 — 贝塞尔外形（2026-06-01 修正，与 Three.js 一致）

**已废弃**：沿 Y 切圆片 + HX 查表。

**当前**：底板 polygon 挤出 + 手柄截面放样 → `generated/bezier_geometry.scad`

- [x] `bezier_to_openscad.py` 重写
- [x] `paddle_shell.scad` → `bezier_paddle_outer()`
- [x] STL + 分析 PNG 重新导出

## 阶段 2 — 验证与文档

- [x] 更新 `print-prep.md` / `visual-checklist.md`
- [x] 导出贝塞尔 STL + `run-analyze.sh` → `enclosure/analysis/**/*.png`
- [x] `enclosure/analysis/README.md` 索引
- [ ] 对比 Live 与 SCAD 关键尺寸（柄颈/柄尾宽度与 parameters 24/34 有偏差，以贝塞尔 JSON 为准）
- [ ] 试打一片再开腔（可选）

## 阶段 3 — 后续（未做）

- [ ] BOSL2 `path_sweep` 替代多层放样
- [ ] 从浏览器 localStorage 导出 JSON 的 CLI
- [ ] 压电/螺丝位随 join 线自动偏移

---

## 使用

```bash
# 改 JSON 或浏览器导出后：
python3 scripts/bezier_to_openscad.py

# 或一键 STL：
./scripts/export-stl.sh
```

`paddle_shell.scad` 顶部的 `USE_BEZIER_PROFILES = false` 可回退旧椭圆外形。

## 验收（阶段 1）

1. `enclosure/generated/profiles.scad` 存在且新于 JSON  
2. OpenSCAD echo：`Profile: bezier (generated/profiles.scad)`，`Loft slices: 64`  
3. 前壳 CGAL 渲染成功（已测 2026-06-01）

---

*状态：阶段 1 完成 · 阶段 2 待做*
