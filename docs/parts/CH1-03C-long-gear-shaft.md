# CH1 · 03C Y 向长齿轮轴

当前决定：**X1C 细版 solid 为主方案**；`sleeve` 只作为备用封存版本保留，不作为默认安装方案。原来的 `12T / 3 mm` 版本继续保留为现有机构的兼容回退。

## 设计契约

- 单位：毫米；齿轮轴线沿世界 **Y**，齿轮截面在 **XZ** 平面。
- X1C 细版齿形：**10 齿 / 2.4 mm 节距 / 0.60 mm 径向齿深**；这是按原装 `0.4 mm` 喷嘴选出的最小实用档，不是数学上的绝对最小值。
- 兼容回退齿形：当前离合原型的 **12 齿 / 3 mm 节距 / 0.82 mm 径向齿深**。
- 主齿段：`159.0 mm`，齿沿 Y 连续贯通；两端各有 `6.0 mm` 的安装余量方案。
- 工艺假设：FDM 低负载原型，材料优先 PETG 或尼龙；树脂版更适合做配合验证。
- 该件不是钢轴替代品；尤其是实心版两端的 Ø3 mm D 轴，应先做首件和同步轮配合验证。

## 两个版本

| 模型 | 输出文件 | 结构 | 用途 |
|---|---|---|---|
| `solid`（X1C 主方案） | [`ch1_03c_long_gear_shaft_solid_x1c_fine.stl`](../../output/3d-print/long-gear-shaft/ch1_03c_long_gear_shaft_solid_x1c_fine.stl) | 细版实心长齿轮 + 两端整体名义 Ø3 mm D 轴，各外露 6 mm | 不依赖外部 D 轴，直接作为一根打印齿轮轴 |
| `sleeve`（X1C 备用封存） | [`ch1_03c_long_gear_shaft_sleeve_x1c_fine.stl`](../../output/3d-print/long-gear-shaft/ch1_03c_long_gear_shaft_sleeve_x1c_fine.stl) | 细版长齿轮本体贯通 D 孔，孔按 Ø3 mm D 轴加 0.12 mm 径向余量 | 仅在需要套已有金属 D 轴时启用；安装时需要从轴端穿入 |
| `solid`（旧兼容回退） | [`ch1_03c_long_gear_shaft_solid.stl`](../../output/3d-print/long-gear-shaft/ch1_03c_long_gear_shaft_solid.stl) | 12T / 3 mm 的实心版本 | 与当前 3 mm 节距配套件保持兼容 |
| `sleeve`（旧备用封存） | [`ch1_03c_long_gear_shaft_sleeve.stl`](../../output/3d-print/long-gear-shaft/ch1_03c_long_gear_shaft_sleeve.stl) | 12T / 3 mm 的套筒版本 | 仅作旧方案备用 |

实心版总长为 `159 + 6 + 6 = 171 mm`。sleeve 版本体长度为 `159 mm`，其两端延伸由穿过它的外部金属 D 轴提供；这是为了避免在同一截面上同时要求“外径 Ø3 mm 实心 D 轴”和“可容纳 Ø3 mm D 轴的内孔”。

## 尺寸依据

- **Ø3 mm D 轴**：沿用仓库动力轴约定，当前电机输出轴和同步轮 D 孔均按这个名义尺寸建模。
- **两端各 6 mm**：来自本次需求，用作同步轮的轴向安装长度；solid 版的 D 轴外露长度就是 6 mm，不包含隐藏在齿段内的 0.20 mm 连接搭接。
- **159 mm 齿段**：当前 `cabinet_clutch.scad` 中 `BUS_BOTTOM_Y` 到 `BUS_TOP_Y` 的同步轮中心间距约为 158.93 mm，因此取整到 159 mm。加上两端 D 轴后，总包络为 171 mm。
- **X1C 细版的齿数选择**：X1C 原装喷嘴是 `0.4 mm`；在保持齿顶平台和齿根槽至少接近一条挤出线宽、同时避免长杆根部过薄的前提下，选 10T 而不是继续压到 8T 以下。齿数再少，理论外径会继续下降，但齿形啮合、齿根承载和长杆抗扭都会变差。
- **X1C 细版的计算**：

  ```text
  节圆直径 = 10 × 2.4 / π ≈ 7.64 mm
  齿根直径 = 7.64 − 2 × 0.60 ≈ 6.44 mm
  齿顶直径 = 7.64 + 2 × 0.60 ≈ 8.84 mm
  齿顶平台宽 ≈ 0.32 × 2.4 × (齿顶半径 / 节圆半径) ≈ 0.89 mm
  齿根槽宽 ≈ 0.25 × 2.4 × (齿根半径 / 节圆半径) ≈ 0.51 mm
  ```

  因此细版齿段名义外径约 `8.84 mm`，实心版总长仍为 `171 mm`；STL 包围盒会因圆周采用多边形点而略小于名义外径。
- **兼容回退**：12T / 3 mm / 0.82 mm 版本的名义齿顶直径约为 `13.10 mm`；导出的 STL 实际包围盒约为 `13.03 mm`。它仍是当前 3 mm 节距机构的正确选择。

## 能否把齿轮做得更密、更细

可以，但需要同时改变齿距和配套啮合齿轮，不能只增加齿数。当前简化齿形的近似关系是：

```text
节圆半径 ≈ 齿数 × 节距 / (2π)
齿顶直径 ≈ 2 × (节圆半径 + 齿深)
```

在**保持 3 mm 节距**时，齿数越多，直径反而越大；要变细必须降低节距。几个候选值如下：

| 方案 | 齿数 / 节距 / 齿深 | 估算齿顶直径 | 结论 |
|---|---|---:|---|
| X1C 细版（当前主方案） | 10T / 2.4 / 0.60 | 8.84 mm | 原装 0.4 mm 喷嘴下的细杆实用折中 |
| 旧兼容版 | 12T / 3.0 / 0.82 | 13.10 mm | 与现有 3 mm 节距机构最兼容 |
| 更细实验版 | 16T / 2.0 / 0.55 | 11.29 mm | 不是更细；只有在改配套件时才有意义，齿形更密 |
| 极限实验版 | 20T / 1.5 / 0.42 | 10.39 mm | 普通 0.4 mm FDM 风险高，不作为当前主件 |

这里的“更密”与“更细”不是一回事：在同一节距下增加齿数会让直径变粗；要减小直径必须降节距。当前已选的 10T / 2.4 mm 是按 0.4 mm 喷嘴直接把外径压到约 8.84 mm 的方案。若还要更细，应先用可换 `0.2 mm` 喷嘴做 20–30 mm 短试片，再决定是否把整根 171 mm 长件降到 1.5–2.0 mm 节距。

注意：X1C 细版的 `2.4 mm` 节距不能直接啮合旧的 `3.0 mm` 节距齿轮/齿条；必须连同配套啮合件一起重做。

## 导出

```sh
./scripts/export_ch1_03c_long_gear_shaft.sh
```

输出目录：

- `output/3d-print/long-gear-shaft/`
- `output/previews/long-gear-shaft/`

也可以直接切换模型或恢复旧兼容参数：

```sh
/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD \
  -D 'LONG_GEAR_PRESET="x1c_fine"' -D 'LONG_GEAR_MODEL="solid"' \
  -o output/3d-print/long-gear-shaft/ch1_03c_long_gear_shaft_solid_x1c_fine.stl \
  cad/openscad/ch1_03c_long_gear_shaft.scad

/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD \
  -D 'LONG_GEAR_PRESET="standard"' -D 'LONG_GEAR_MODEL="solid"' \
  -o output/3d-print/long-gear-shaft/ch1_03c_long_gear_shaft_solid_legacy.stl \
  cad/openscad/ch1_03c_long_gear_shaft.scad
```

STL 不携带单位；切片软件应按 1:1、毫米导入。X1C 的成形空间为 `256 × 256 × 256 mm`，所以 `171 mm` 总长在尺寸上能放下；实际打印建议把模型轴线转到打印机 Z 方向并加 brim，或先在切片器中试水平摆放。打印前仍需确认：齿顶悬垂、长杆的翘曲/振动、同步轮在 6 mm D 端轴上的轴向定位，以及实心版端轴是否需要降低转速或改用金属 D 轴。
