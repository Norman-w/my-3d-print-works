# 摇臂转轴：可拆后叉耳装配候选

**状态：已完成名义 CAD 装配路径与 X1C/PETG 离线切片筛查；未选入当前 49 件打印清单，未试印或放行。** 原一体叉耳在固定后挡住带输出销摇臂沿 +Y 轴向进入；摇臂与叉耳先预装再整体平移，也没有找到畅通的直线路径。[原路径报告](../output/electric-output-crosshead-screen/assembly-review.json)记录了这项否决依据。本候选把原叉耳分成固定基座与可拆后叉耳，先装摇臂，再从 +Y 装后叉耳。[CAD](../cad/electric-rocker-service-fork-screen.scad) · [复核报告](../output/electric-rocker-service-fork-screen/review.json)。

## 接口与承力

固定基座沿用主壳 `Y=40、Z=16/−10 mm` 的两颗 M3 合壳螺钉及其原孔位；前叉耳与低梁仍是一件。后叉耳与基座在 `Y=68 mm` 接合，接合脚的标称外廓为 `X=7…23、Z=−21…8 mm`。两颗 M3 螺钉中心为 `(X,Z)=(15,−14)/(15,2) mm`，从 +Y 侧穿过后叉耳，拧入先从接合面放入基座六角窝的螺母。后叉耳盖住螺母入口，装好后不需要从被主壳挡住的 −Y 侧拿套筒。螺钉、螺母和头部只按候选包络建模，实际长度、垫片、防松和拧紧扭矩尚未选定。

基座上的 `X=10…20、Z=−8…−4 mm` 凸键沿 +Y 伸入后叉耳 4 mm 深的盲袋，名义单侧间隙 0.3 mm。它让接合面在 X/Z 方向有实体定位；摇臂轴的径向反力经后叉耳座、根部、凸键/接合面和两颗 M3 紧固件回到低梁，再经原合壳孔传入主壳。这个**力流描述不是 PETG 承载或耐久证明**。两颗 M3 的预紧、打印层间方向、凸键边缘应力、主壳合缝预紧及气密都尚未实测。

[静态承力筛查](../output/electric-rocker-service-fork-screen/load-screen.json)核对了基座沿用的 3×11 mm 低梁。仅按卖家未核实的 4–5 kgf 推力、理想 75/50 mm 摇臂及竖直反向输入/输出力计算，枢轴反力为 19.6–24.5 N，孤立直梁名义弯曲应力为 8.1–10.1 MPa；若有同量级 X 向侧载，薄 3 mm 方向的应力灵敏度为 29.7–37.1 MPa。这些数值均**不是可许用值或安全系数**。基座切片的 X+90° 朝向使低梁 Y 向长轴垂直于打印层面，梁根弯曲可能拉开层间粘接。定位键每侧留 0.3 mm，M3 代理轴在两件 Ø3.4 孔内各有 0.2 mm 径向余隙；螺栓实际贴孔位置及预紧未定，不能保证键面先承受剪力。后叉耳接合面、键根、螺钉和壳体凸台均无实际载荷或耐久验证，**该叉耳还不能作为一次过的承力结构放行**。

为减轻 3 mm 薄向侧载风险，另做了[低梁加宽到 7 mm 的独立筛查](electric-rocker-service-fork-reinforcement-screen.md)；局部名义空间通过，但螺钉孔根部和 PETG 层间承载仍未验收，尚未替换本页叉座。

## 按当前 CAD 的装入顺序

1. 拆下右导向盖，在未装电机时把基座对准原两颗 M3 合壳孔，按最终壳体紧固方案固定。基座的原锚点区域与上一版一体叉耳在模型中保持相同。
2. 把衬套装进有贯通轴孔的摇臂；让摇臂输出销从 +Y 方向进入一体送料横头的封闭槽，直至摇臂轴孔与前叉耳同轴。
3. 从 `Y=68 mm` 接合面把两颗 M3 六角螺母放入基座窝，然后把后叉耳沿 −Y 方向推到基座，凸键进入盲袋；从 +Y 侧上两颗连接螺钉。
4. 从 +Y 方向穿入摇臂轴并完成两端防脱，最后装电机端连接、线束和右导向盖。轴径/衬套的实际配合、输出销防脱、电机活动端连接以及装后维护拆卸仍需要实物闭合。

[插入摇臂](../output/electric-rocker-service-fork-screen/rocker-entry.png) → [摇臂就位、后叉耳待装](../output/electric-rocker-service-fork-screen/rocker-seated.png) → [后叉耳就位](../output/electric-rocker-service-fork-screen/rear-seated.png)。图中的电机是卖家图片过包络、螺钉是尺寸代理；没有实际电机座和杆端接头。

基座的[前视](../output/electric-rocker-service-fork-screen/base-front.png)、[螺母窝接合面](../output/electric-rocker-service-fork-screen/base-nut-face.png)、[顶视](../output/electric-rocker-service-fork-screen/base-top.png)、[等轴](../output/electric-rocker-service-fork-screen/base-iso.png)以及后叉耳的[前视](../output/electric-rocker-service-fork-screen/rear-front.png)、[顶视](../output/electric-rocker-service-fork-screen/rear-top.png)、[等轴](../output/electric-rocker-service-fork-screen/rear-iso.png)可单独检查孔、凸键和开口螺母窝。

[名义几何报告](../output/electric-rocker-service-fork-screen/review.json)导出的基座、后叉耳各为单连通、封闭 STL；`0/5/10/15/20 mm` 送料位置的静态避让、摇臂先入横槽、螺母从接合面放入、后叉耳安装、摇臂轴穿入及工具通道合计的离散探针未见正体积相交。这个结果只说明采样路径在模型中可走；不包含打印尺寸、真实螺母保持、晃动间隙、动态负载和可重复拆装。实购 BY141-3 电机的外壳/固定端/活动端数据及 30→20 mm 的双向传动和端点顺应仍未闭合，不能据此发整机打印单。

[离线切片报告](../output/electric-rocker-service-fork-screen/slice-review.json)使用 X1C、0.4 mm 喷嘴、纹理 PEI、Generic PETG、0.2 mm 层高、4 壁、25% 填充、5 mm brim 和仅从热床生成的树状支撑。基座 X+90° [3MF](../output/electric-rocker-service-fork-screen/slices/base-x-plus-90-tree/slice-review.3mf)约 10.76 g、185 层；后叉耳 X−90° [3MF](../output/electric-rocker-service-fork-screen/slices/rear-x-minus-90-tree/slice-review.3mf)约 6.07 g、45 层。两份原生切片均无警告；按实际 3MF 变换核对，螺母窝和定位键袋都朝上。再查 G-code，两件的 M3 贯通孔、基座两个螺母窝与轴孔、后叉耳定位键袋与轴孔的投影内均无支撑挤出。可看[基座盘面](../output/electric-rocker-service-fork-screen/slices/base-x-plus-90-tree/plate-preview.png)和[后叉耳盘面](../output/electric-rocker-service-fork-screen/slices/rear-x-minus-90-tree/plate-preview.png)。这些结果没有证明其他支撑易拆、螺母/衬套/转轴的实际配合或 PETG 键根在往复载荷下可靠；**未发送打印机**。

针对基座 90° 朝向的层间承力疑问，另做了[12 档离线朝向对照](../output/electric-rocker-service-fork-screen/orientation-screen.json)。0°/30° 让低梁更接近热床平面，但在下螺母窝名义孔腔核心分别查到 18/27 条实际 XY 支撑挤出段；90° 的关键孔投影内没有支撑，但梁轴垂直于层面。40° [盘面图](../output/electric-rocker-service-fork-screen/orientation-screen/base-x-plus-40-tree/plate-preview.png)约 9.21 g、303 层，梁轴在打印高度方向的几何分量为 0.643；按 0.15 mm 间隔采样支撑挤出线，在两个 M3 孔、螺母窝和摇臂轴孔的**内缩名义孔腔核心**均为 0 条。修正 G-code 扫描器、排除 `G1 E...` 原地补料后，40° 的关键孔外围包围盒也未见实际 XY 支撑线；线宽、打印误差及清理可达性仍未因此得到验证。40° 只是可能减轻层间拉开的**切片候选**，尚无能证明其比 90° 更强的实测数据，未替换正式切片、未选定朝向、未发打印机。
