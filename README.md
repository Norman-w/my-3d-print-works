# therapy-cable-inline-box-for-physio

理疗仪线缆串联保护盒（OpenSCAD 参数化外壳 + Web STL 预览）。

## 版本说明

### v1 — 水泥电阻方案（已弃用）

最初方案：在理疗仪线缆中间串联 **5W 水泥电阻**，用上下对开壳体固定电阻体、引脚焊接区与线缆出线孔，起到限流/保护作用。

这一版的历史方案已经被当前 `scad/` 中的 v3 参数化模型取代。

**弃用原因：** 实测水泥电阻发热过高，壳体与使用环境无法可靠散热，存在烫手与安全风险，因此不再推进水泥电阻方案。

### v2 — PWM 调速信号板（已弃用）

因发热问题，第二版曾改用 Synairy ESC-Adaptor V02。该板只能输出
PWM 控制信号，不能直接向负载输出所需能量，因此不再作为当前硬件方案。

旧版资料保留供追溯：

- [docs/synairy-esc-adaptor-v02/](docs/synairy-esc-adaptor-v02/)

### v3 — 直流电机调速功率板（当前方向）

当前改用带功率器件、散热片和四位电源/电机端子的直流调速板。
商品图标称 PCB **50 × 32 mm**；壳体改为十字布局：盒体长轴沿 PCB
50 mm 方向，线缆从接线端附近的两侧进入，与盒体长轴垂直。模型包含
侧向旋钮半孔、四孔固定、双线缆应力释放和散热片上方的参数化通风槽。
当前内腔为 **80 × 44 mm**，接线端单侧比上一版增加 **12 mm**；PCB/端子
到最近线缆限位柱约有 **10.6 mm** 净空。侧壁为 **2.4 mm**，给四角合盖
Boss 的加固斜坡留出约 **1.65 mm** 外侧实体余量。
PCB 使用 4× **M2×5 mm 沉头螺丝**固定，直接锁入下壳 ⌀1.7 mm 打印底孔；
`flat.stl` 附带 4 个打印承压垫圈，避免沉头直接压伤 PCB 平孔。

- 硬件资料与实物照片：[docs/dc-motor-speed-controller-v03/](docs/dc-motor-speed-controller-v03/)
- 待测尺寸与装配决策：[docs/dc-motor-speed-controller-v03/dimensions.md](docs/dc-motor-speed-controller-v03/dimensions.md)

### 旧 v2 壳体要点（不适用于 v3）

- 内腔 **70 × 30 × 15 mm**（加宽接线；上半净高 7.5）
- **底面** 4×M2 合盖（顶面只露旋钮/数码，无合盖螺孔）；盒内 2×罗马柱锁 PCB
- 开窗：轴 10~15（⌀**8.0**）、数码管 18.5~27（8.5×12）；板宽居中；开关不开孔
- 模组安装孔：短边内缩 **1.5**、长边 **2.0**（孔心距 ΔX **28.5**，对齐复测）

## 仓库结构

```
docs/synairy-esc-adaptor-v02/   已弃用的 v2 PWM 信号板资料
docs/dc-motor-speed-controller-v03/ 当前 v3 功率调速板资料与实物照片
scad/                           OpenSCAD 参数化模型（v3 功率调速板盒）
stl/                            导出的 STL（gitignore 可忽略）
web/                            Three.js STL 预览与下载页
index.html                      跳转到 web/index.html
```

## 本地预览（v3 模型）

不要直接双击 `web/index.html`：`file://` 页面会绕过 STL 同步检查，并只显示
本地服务启动提示。请在项目根目录运行：

```bash
python3 web/server.py
```

浏览器打开 [http://localhost:8080](http://localhost:8080) 即可查看/下载 STL。
服务启动时会比较 `scad/*.scad` 与三份 `stl/*.stl` 的修改时间；任一 STL
缺失或过期时，会自动调用 OpenSCAD 重新导出全部模型。若 OpenSCAD 不可用
或导出失败，服务会停止启动，避免继续展示旧模型。
