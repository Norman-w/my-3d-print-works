# SmartPartsDrawer：FreeCAD 可选验证支线

> 当前 `8765` 预览的主线是 **OpenSCAD/SCAD → STL → Three.js 网页**。方案1的输入轮、输出轮、狗牙离合、银色轴承和拨叉都由
> `cad/openscad/enclosure/cabinet_chain.scad` 导出，并由 `web/cabinet-preview` 播放；FreeCAD 不参与这条页面链路。

## FreeCAD 支线说明

FreeCAD 支线按「**单一本地真值源（FreeCAD）+ STL 展示**」实现：
1) 几何、联动、干涉、机构尺寸都在 **FreeCAD macOS** 里建模和验证；  
2) 只把最终结构导出为 STL + `manifest.json` 到 `web/assets/stl`；  
3) 浏览器里的 `freecad-viewer.html` 只做视觉观看，不再承载物理真实性判断。

如果你只要“看效果”，这条链路最省成本、最直观，也最容易持续迭代，不会把真实逻辑和可视化混在一起导致自相矛盾。

## 第一优先：先确认 FreeCAD 环境可用

执行：

```bash
cd /Users/norman/CodexProjects/SmartPartsDrawer
./scripts/check_freecad_ready.sh
```

通过后再执行完整重建/预览命令。若检测失败，请先安装 FreeCAD（macOS）：

```bash
brew install --cask freecad
```

> `check_freecad_ready.sh` 只做可执行性检查，不会改动模型。 

你现在的目标是把“机构真实验证”放在本地单一 CAD（FreeCAD）里做，网页只做展示。当前仓库新增了这套链路：

- `scripts/freecad_drawer_pipeline.py`：参数化建模 + FCStd + STL + 分件 STEP（**默认 selector-mode=snake**）
- `scripts/freecad_snake_animate.py`：FreeCAD GUI 动画（方案 1：选格 → 停稳 → 单离合啮合 → 单抽屉驱动 → 释放 → 回 HOME）
- `web/freecad-viewer.html`：读取 `manifest.json`，加载 STL 的轻量展示页
- `web/assets/stl/*`：导出的 STL 与清单文件
- `build/step/*`：分件 STEP（ISO 螺钉包络一并导出）
- `web/assets/stl/manifest.json`：含 `mechanismMap`（抽屉/联轴器/驱动链路映射）

## 一次性运行（推荐）

> 先确认下方“环境检查通过”再开始；目前未装 `freecadcmd` 就会卡在 CLI 建模这一步。

你在 macOS 上执行：

```bash
cd /Users/norman/CodexProjects/SmartPartsDrawer
/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd \
  -P scripts scripts/freecad_drawer_pipeline.py \
  --pass "--columns 4 --layers 3 --out web/assets/stl"
```

默认就是卡片 A「蛇形同步带选择」（HTD3M-9 + 20T，`n=60v/(20×3mm)`）。其他方案仍可用 `--selector-mode cam|fourier|centrifugal`。

### 常见安装后第一步（命令）

```bash
# 安装完成后先确认是否识别 CLI
./scripts/check_freecad_ready.sh

# 如果你把 freecadcmd 放在 PATH（常见），可快速跑一套（含 dry-run）
./scripts/run_freecad_pipeline.sh -- --dry-run --columns 4 --layers 3
./scripts/dev_local_loop.sh --columns 4 --layers 3 --selector-mode snake

# 局域网访问（同网段机器可访问）：
./scripts/dev_local_loop.sh --host 0.0.0.0 --lan-host 192.168.6.187 --columns 4 --layers 3 --selector-mode snake
# 或自动探测 LAN IP（启动时会打印出可访问 IP）：
./scripts/dev_local_loop.sh --host 0.0.0.0 --lan-host auto --columns 4 --layers 3 --selector-mode snake
```

### 日志说明

流水线执行日志写入：

- `~/.cache/smartpartsdrawer/pipeline_YYYYMMDD_HHMMSS.log`

如导出失败，请先回看该日志里的报错，再对 `scripts/freecad_drawer_pipeline.py` 调整。

如果你是标准路径安装，可以直接用 `freecadcmd`：

```bash
freecadcmd -P scripts scripts/freecad_drawer_pipeline.py --pass "--columns 5 --layers 4 --selector-mode fourier"
freecadcmd -P scripts scripts/freecad_drawer_pipeline.py --pass "--columns 6 --layers 3 --selector-mode centrifugal"
freecadcmd -P scripts scripts/freecad_drawer_pipeline.py --pass "--columns 4 --layers 3 --selector-mode snake"
```

执行后会生成：

- `build/SmartPartsDrawer.FCStd`（用于 GUI 打开看真模型）
- `build/snake_animation.json`（蛇形弧长动画清单）
- `build/step/*.step`（分件 STEP，含 ISO 4762 螺钉包络）
- `web/assets/stl/cabinet.stl`
- `web/assets/stl/drawers.stl`
- `web/assets/stl/drive.stl`
- `web/assets/stl/selector.stl`
- `web/assets/stl/all.stl`
- `web/assets/stl/manifest.json`

### FreeCAD GUI 动画（主仿真）

建模完成后必须用 **FreeCAD.app GUI** 播蛇形选择循环（QTimer，循环、不退出）。不要用网页 canvas / Three.js 替代，也**不要用 `freecadcmd` 播这场动画**。

`freecadcmd` + `showMainWindow()` 会在脚本结束时拆 3D 视图，macOS 上常见 `View3DInventor` 析构 `SIGSEGV`。阻塞的 `sleep` 循环会卡住 Qt 事件循环，窗口里看起来完全不动。

```bash
./scripts/run_freecad_snake_anim.sh
```

或：

```bash
open -n -a FreeCAD --args \
  -P "$(pwd)/scripts" \
  "$(pwd)/build/SmartPartsDrawer.FCStd" \
  "$(pwd)/scripts/freecad_snake_animate.py"
```

不要直接执行 `Contents/MacOS/FreeCAD` 或 `Contents/Resources/bin/freecad`：在 Cursor/终端里那样启动经常出现进程在跑、窗口数为 0，屏幕上什么也没有。

窗口打开后约一秒开始循环：INDEX → ENGAGE → DRIVE（仅目标抽屉的动力支路转）→ RELEASE → RETURN → HOME。选择带移动时动力轴断开；目标停稳后才接合一个离合；释放完成后才回程。绿色件是拨叉，状态栏会显示目标格、离合状态和动力开关。

### 方案 1 的状态约束

蛇形选择机构的动画清单会为每个格位生成一对固定狗牙盘和滑动狗牙盘。滑动盘的默认位置与固定盘留有 `2.6 mm` 间隙，只有拨叉到达目标格并完全停稳后，才沿轴向推进 `3.0 mm` 接合。动力总线的状态按下面顺序执行：

```text
INDEX   选择带移动，全部离合脱开，动力轴断电
ENGAGE  选择带停止，目标滑动盘推进，动力轴仍断电
DRIVE   目标离合已接合，只转目标抽屉取力支路
RELEASE 动力轴先断电，目标滑动盘退出
RETURN  选择带回 HOME，所有离合保持脱开
HOME    等待下一次选格
```

`selectedIndex` 表示当前被拨叉接触的格位，`drivenIndex` 表示最后一次实际受力的格位，`powerOn` 表示动力电机是否通电。动力轴角度在断电后保持最后位置，避免释放/回程画面出现不真实的回零跳变。

若模型已在 GUI 里打开，Python 控制台执行：

```python
import sys
sys.path.insert(0, "scripts")
import fc_snake_player as p
p.schedule_when_gui_ready()
```

## GUI 与 CLI 循环更新

### CLI 重建

修改参数后再运行上面的命令会直接重建并覆盖 `FCStd` 与 STL。

### GUI 查看

在 FreeCAD 里打开 `build/SmartPartsDrawer.FCStd`，参数或拓扑变化可以直接在 GUI 里看。

### 网页展示

启动任一静态服务后访问 `web/freecad-viewer.html`，它会自动读取 `manifest.json` 与 STL：

- 可切换显示子系统（cabinet / drawers / drive / selector / all）
- 可点击复选框逐项开关
- 有自动转动和镜头重置

## 常用命令

```bash
# 仅检查参数，不重建
python3 scripts/freecad_drawer_pipeline.py --dry-run
./scripts/dev_local_loop.sh -- --dry-run --columns 2 --layers 2 --selector-mode snake

# 如果安装了 freecadcmd 也可这样运行，效果同上
freecadcmd -P scripts scripts/freecad_drawer_pipeline.py --pass "--dry-run"

# 不导出 STL，只生成 FCStd
freecadcmd -P scripts scripts/freecad_drawer_pipeline.py --pass "--no-export"
```

```bash
# 启动网页预览服务（默认 4173）
./scripts/serve_freecad_viewer.sh 4173
```

然后访问：

```text
http://127.0.0.1:4173/freecad-viewer.html
```

## 说明

- 当前默认模型是**蛇形同步带选择**（闭合同步带 + 释放指滑架），凸轮/傅里叶/离心仍可通过 `--selector-mode` 切换，几何骨架未改。

### 核心定位：真实验证在 FreeCAD，本地 GUI 看，网页只展示

- **真实机构几何 + 干涉 + 受力路径**：在 FreeCAD 打开 `build/SmartPartsDrawer.FCStd` 检查。
- **展示与汇报**：在浏览器打开 `web/freecad-viewer.html`，只用于渲染 STL。

## 支持的选择机构

- `snake`（**默认 / 主仿真**，对应网页卡片 A）
- `cam`
- `fourier`
- `centrifugal`

### 一键本地闭环（推荐）

你现在不需要在多个软件里来回切：

```bash
cd /Users/norman/CodexProjects/SmartPartsDrawer
./scripts/dev_local_loop.sh --columns 4 --layers 3 --selector-mode snake
```

这条命令会自动：

- 调用 `run_freecad_pipeline.sh` 重建 FCStd/导出 STL（如环境有 `freecadcmd`）
- 启动 `http://127.0.0.1:4173`
- 用 `open` 打开 `build/SmartPartsDrawer.FCStd`（FreeCAD GUI）
- 自动打开 `web/freecad-viewer.html`（STL 预览）

可加 `--port` 指定端口：

```bash
./scripts/dev_local_loop.sh --port 8080 --columns 4 --layers 3 --selector-mode fourier
```

可加 `--skip-gui` / `--skip-view` 做调试：

```bash
./scripts/dev_local_loop.sh --skip-gui --columns 2 --layers 2 --selector-mode cam
./scripts/dev_local_loop.sh --skip-view --columns 2 --layers 2 --selector-mode cam
```

如果只需要打开现有产物做展示（不重建）：

```bash
./scripts/dev_local_loop.sh --only-view
./scripts/dev_local_loop.sh --only-view --port 8080
```

若你只想看“参数检查输出”而不接触文件：

```bash
./scripts/dev_local_loop.sh -- --dry-run --columns 2 --layers 2 --selector-mode snake
```

运行时会在终端输出产物校验，并将执行日志写到：

`~/.cache/smartpartsdrawer/pipeline_YYYYMMDD_HHMMSS.log`

脚本会在前台等待，按 `Ctrl-C` 停止本地服务。

如果只想更新 FCStd 而不导出 STL（用于先在 GUI 里核对草模）：

```bash
./scripts/dev_local_loop.sh -- --no-export --columns 2 --layers 2
```
