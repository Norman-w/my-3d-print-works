# 打印前准备

外壳长期方案见 **[enclosure-openscad.md](./enclosure-openscad.md)**；执行清单见 **[plan-enclosure-bezier.md](./plan-enclosure-bezier.md)**。

**当前默认**：`USE_BEZIER_PROFILES=true`，导出 STL 前会自动运行 `scripts/bezier_to_openscad.py`（与 `web/src/data/userBezierProfiles.json` 同步）。在 Shape 页改曲线后，把 JSON 更新到该文件再导出。

## 必打件（球拍本体）

| STL | 来源 | 数量 | 材料 |
|-----|------|------|------|
| `enclosure/stl/paddle_shell_front.stl` | `paddle_shell.scad` `HALF="front"` | 1 | PETG |
| `enclosure/stl/paddle_shell_back.stl` | `paddle_shell.scad` `HALF="back"` | 1 | PETG |

拍面与手柄在同一件里，前后壳合拢即完整拍。

---

目录说明见 [`enclosure/README.md`](../enclosure/README.md)。

---

## 1. 导出 STL

```bash
cd /path/to/SmartPaddle
./scripts/export-stl.sh
```

依赖：已安装 [OpenSCAD](https://openscad.org/)（`openscad` 在 PATH 中）。  
前壳、后壳各渲染一次，耗时约 1–5 分钟/件，视机器而定。

---

## 2. OpenSCAD 检查

1. 打开 `enclosure/paddle_shell.scad`
2. `HALF = "both"` → 预览前后能否对齐
3. 控制台核对 echo：总高、拍宽、柄长、螺丝数量
4. 关键尺寸见 `enclosure/parameters.scad`（如拍宽 150mm、柄长 100mm）

---

## 3. Bambu Studio 建议

| 项 | 建议值 |
|----|--------|
| 材料 | PETG |
| 层高 | 0.16 mm |
| 壁厚 | 2 mm（与 `wall_t` 一致） |
| 热床 | 256×256 mm，四周留 ≥5 mm |
| 支撑 | 拍面大面贴床；后壳 **USB 开口朝上** 时柄部可能需要局部支撑（见 BOM） |
| 预估 | ~180 g/件 ×2 |

**摆放**：让拍面（较大平面）尽量贴热床，手柄沿 Z 或斜放——以切片里「第一层接触面积最大、悬垂最少」为准；导出 STL 默认 Z 轴为厚度方向，导入后若过高可绕 X/Y 旋转。

---

## 4. 试装顺序（省料）

1. 只打 **一套** 前+后壳  
2. 游标卡尺量分型面外廓、柄颈内宽（≥18 mm 放板）  
3. 试拧 M2 自攻（方案 A，见 BOM）  
4. 确认无误再打第二套或可选件  

---

## 5. 二维投影自动分析（推荐）

```bash
./scripts/run-analyze.sh
```

生成两套图，**不要混用**：

| 目录 | 来源 | 对应页面 |
|------|------|----------|
| `enclosure/analysis/paddle_shell_*/` | **OpenSCAD STL**（`paddle_shell.scad`） | 实际打印件 |
| `enclosure/analysis/bezier_design/` | **贝塞尔 JSON**（与 Three.js 相同曲线） | Shape 页 `BezierDrawEditor` / 3D 正视侧视 |

Web 上 `?tab=shape&target=handle-bottom&section=bezier` 的柄底视是 **SVG 画贝塞尔**，3D 预览是 **Three.js 放样**（`paddleFromBezier.ts`），**不是** SCAD 图。

STL 分析图用于核对 **打印壳**；若要与网页外形对比，请看 `bezier_design/` 或 Shape 页正/侧视。

- 每个 STL：`top.png` / `front.png` / `side.png` / `width_profile.png`
- `SUMMARY.md` — 与 `parameters.scad` 对比的尺寸表

## 6. 视觉确认

按 [visual-checklist.md](./visual-checklist.md) 截图 6 张，在切片/OpenSCAD 里核对 A–E 条。

---

## 改外形后

1. 改 `enclosure/parameters.scad`（或后续接入 Web 贝塞尔导出）  
2. 重新 `./scripts/export-stl.sh`  
3. 重新切片看重量与热床占用  
