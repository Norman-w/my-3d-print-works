# OpenSCAD / STL / Three.js 装配坐标分工

本项目的机械几何真值在
`cad/openscad/enclosure/cabinet_clutch.scad` 及其参数/载体模块中。STL 只是导出的网格，
不携带父子装配关系或动画。

## 当前契约

导出脚本
`scripts/export_cabinet_clutch.sh` 会把 SCAD 生成的尺寸契约和装配坐标树写入
`output/3d-preview/manifest.json`：

```text
world
├── cabinet-fixed
│   ├── station:R1C1 ... station:R3C5
│   ├── center-input-carriage
│   ├── center-output-rotor
│   └── center-front-drive
├── power-bus-fixed
│   ├── tensioner-lower
│   └── tensioner-upper
├── drawer-drive-fixed
└── chain-source          （源链条坐标适配 frame）
```

站点模板和张紧支撑各自只导出一份 STL。manifest 的实例记录父 frame 和局部变换；网页
为每个实例创建轻量 Three.js 节点，共享同一个 `BufferGeometry`，不复制 STL 内容。

中心 R3C3 动态件的输入公轮、阶梯轴、圆套和磁铁挂到 `center-input-carriage`；输出母轮
和短轴挂到 `center-output-rotor`。两个 frame 的轴位来自 SCAD 契约，网页动画只修改它们
下面的局部枢轴位移/旋转。固定 LM3UU、输出轴承和机构板不会进入输入运动 frame。

## 分层边界

- OpenSCAD：几何、局部/世界基准、零件包络、机械尺寸和静态干涉检查。
- manifest：单位、根 frame、父子 frame、局部变换、实例引用和运动 frame 声明。
- Three.js：从 `world` 递归建立 frame，加载 STL，创建重复节点并执行运行时动画。
- `cabinet-chain-play.js`：只消费运动契约和 manifest frame，不重新定义离合行程、轴位或列距。

浏览器预览通过不等于打印、轴承压入、磁铁装配或负载验收通过；这些仍需单独做实物验证。

## 审计命令

导出完成后运行：

```sh
python3 scripts/validate_assembly_manifest.py \
  --manifest output/3d-preview/manifest.json
node --check web/cabinet-preview/app.js
node --check web/cabinet-preview/js/cabinet-chain-play.js
git diff --check
```
