# 外壳：OpenSCAD 主战场

设计真源是网页 **贝塞尔 JSON**（`web/src/data/userBezierProfiles.json` + 浏览器 localStorage）。  
**OpenSCAD** 负责可打印实体（分型、腔体、螺柱、压电槽、USB）。  
**Three.js（Live / Shape）** 只做预览，与打印几何通过导出脚本对齐。

## 原则

1. **轮廓**：贝塞尔采样 → 2D 路径，**一次 sweep/loft**，不用沿 Y 叠上百层 `linear_extrude`（避免阶梯网格与俯视锯齿）。
2. **功能**：继续用 `difference` / 参数表（`parameters.scad`），毫米级容差、孔位不动硬编码在 JS 里。
3. **库**：优先 **BOSL2**（`bezpath`、`path_sweep`、圆角路径）；不引入 CadQuery，除非以后有多零件装配需求。
4. **验证**：打印前以 **OpenSCAD F6 + 切片** 为准；STL 二维分析仅作尺寸/热床核对，外形以 F5/F6 与 Live 对照为准。

## 目标流水线

```
BezierDrawEditor (Shape)
    → userBezierProfiles.json
    → scripts/bezier-to-openscad.py   # 待实现
    → enclosure/generated/profiles.scad
    → paddle_shell.scad (+ BOSL2)     # 外形用 generated，特征用 parameters
    → scripts/export-stl.sh
    → Bambu Studio
```

## 分阶段

### 阶段 1 — 打通轮廓（已完成 2026-06-01）

- [x] `scripts/bezier_to_openscad.py` → `generated/profiles.scad`（`BEZIER_HX` / `BEZIER_HZ` 查表）
- [x] `bezier_profile.scad` + `paddle_shell.scad` 中 `USE_BEZIER_PROFILES=true`，`LOFT_SLICES=64`
- [x] `export-stl.sh` 自动跑 Python
- [ ] Live 与 OpenSCAD 并排对比（阶段 2）
- [ ] BOSL2 sweep（阶段 3）

### 阶段 2 — 保留现有功能件

- [ ] 螺柱、压电槽、走线槽、USB、对齐销仍读 `parameters.scad`
- [ ] 空腔 `handle_cavity()` 随新外形自动 inset，必要时按 Y 采样内轮廓
- [ ] 前/后壳 `HALF=front|back` 行为不变

### 阶段 3 — 工程化

- [ ] `export-stl.sh` 依赖检查：OpenSCAD + BOSL2 路径
- [ ] CI 或本地：`bezier-to-openscad` → `openscad` 渲染 smoke test
- [ ] 弃用纯椭圆 `blade_ellipse_*` 作主外形（可留作 fallback 开关）

## 文件职责（规划后）

| 文件 | 职责 |
|------|------|
| `parameters.scad` | 壁厚、孔位、压电、USB、螺丝、打印容差 |
| `generated/profiles.scad` | **自动生成**，勿手改 |
| `paddle_shell.scad` | 装配：外形 sweep + 腔体 + 特征 |
| `paddle_shell.scad`（旧 `paddle_outer`） | 阶段 1 完成后删除或 `#ifdef LEGACY` |

## BOSL2 使用范围（建议）

- **用**：路径 sweep、柄截面放样、路径圆角、截面缩放（FL 柄）
- **不用**：把螺柱/螺纹全搬进 BOSL2（现有 SCAD 已够用）

安装参考：将 BOSL2 克隆到 `enclosure/lib/BOSL2` 或在 OpenSCAD 首选项里配置库路径。

```openscad
include <BOSL2/std.scad>
```

## 与现有脚本的关系

| 脚本 | 用途 |
|------|------|
| `scripts/export-stl.sh` | 渲染 `paddle_shell` → STL |
| `scripts/analyze_stl_views.py` | 打印件尺寸/热床（**不**代表 Live 外形） |
| `scripts/analyze_bezier_views.py` | 2D 曲线核对 JSON |
| `scripts/bezier-to-openscad.py` | **待加**，JSON → `generated/profiles.scad` |

## 决策记录

- **主战场**：OpenSCAD（+BOSL2 做 sweep）
- **不选**：CadQuery 为主、纯 Three.js 外壳布尔
- **用户目标**：灵活改曲线、打印实物无毛刺/无阶梯纹
