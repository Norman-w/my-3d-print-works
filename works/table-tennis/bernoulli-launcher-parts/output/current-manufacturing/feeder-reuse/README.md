# 当前旧送料件切片复用审计

审计范围为当前清单中的 36 个旧送料打印实例，排除 `cable-*` 与已替换的 `beam-grip` / `frame`。当前权威是 `docs/cable-assembly-inventory.json` 与 `output/cable-scene-export/20260927T091627124663Z/report.json`。未修改 CAD、原切片、旧报告或打印预设，也未启动切片或发送打印。

**23 件可沿用已有 14 盘的离线切片证据，13 件需要重切。** 这不是制造或实物功能放行。

- 19 件当前 STL 与旧切片输入字节完全相同，并再次核对了实际 3MF 三角面。
- 4 个 `finger` 文件字节不同，但全部 1964 个实际 3MF 有向三角面与当前模型一一对应；没有合并、缺面或新增面。使用明确单位刚体变换与 3MF 原始偏移恢复 CAD 坐标，最大角点差约 0.000001004 mm。这里记录的是有界数值转换对应，不称字节身份相同。
- 8 件几何改变：左右支座、左右 Y 盖、4 个 Y keeper。旧盘完整保留，但不能用于当前件。
- 5 件无旧切片：左右 `frame-y-gib`、`inlet-rear`、`inlet-front`、`inlet-backplate`。旧脚本已有计划不能当成已切片产物。

复用盘核对包含：当前 STL 哈希、实际选中 3MF 的每实例 normal mesh、完整有向面对应、3MF 内外 G-code 相同、原生执行结果、旧有层面/支撑审查文件、未改变的工艺文件、X1C / 0.4 / PETG、实际装盘刚体矩阵与贴床法向、盘内实例数量。旋转矩阵及每件 CAD→G-code 坐标变换保存在 JSON。复用的 14 盘均是整盘所需数量，无需从 G-code 删除旧实例。

旧 CAD 的源哈希发生变化本身不会导致拒绝；接受条件是当前零件与实际切片模型对应且旧工艺证据完整。相反，名字、包围盒或切片退出码相同均不构成复用证明。

原工艺仍采用 Generic PETG 与 Textured PEI；用户只确认 PETG / PEI，没有确认具体品牌和板面纹理。旧支撑清理、尺寸、材料强度、磨损和机构实际动作的物理限制仍然保留。

## 文件与复跑

- `report.json`：完整实例、盘、模型对应、摆向、证据哈希与限制。
- `mapping.json` / `mapping.csv`：统一制造清单需要的实例映射。
- `runs/`：每次审计的独立快照；`latest.json` 指向本次快照。
- `review.py`：只读原模型/旧切片，可复跑；仅写本目录。

```sh
/Applications/FreeCAD.app/Contents/Resources/bin/python output/current-manufacturing/feeder-reuse/review.py
```

CSV 的 `slice_folder` 可能是**被拒绝的历史盘**，必须同时读取 `needs_reslice`。只有 `needs_reslice=false` 且 `process_status=BOUNDED_OFFLINE_EVIDENCE_REUSABLE` 才可进入复用清单。
