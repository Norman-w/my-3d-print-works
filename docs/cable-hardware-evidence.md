# 拉索五金的厂家证据

核对日期：2026-09-27。对象均为厂家候选，未确认已购，未采购、未联系卖家。本文区分厂家标注、由尺寸链和剖面顺序得到的界、尚无尺寸的区域；不按图片像素补造尺寸。

原图由普通浏览器加载 norelem 官方产品页后保存已加载的原始图片。对应 `output/cable-hardware-evidence/*-assets.json` 保存原资源 URL。以下 PNG 是厂家原图，不是重画图。

## 调节器 03096-30-0306X24

[官方系列页](https://www.norelem.de/en/Product-overview/Flexible-standard-component-system/03000/Accessories-for-indexing-plungers-cam-action-indexing-plungers-and-ball-lock-pins/Setscrews/p/agid.36191)；原图：`output/cable-hardware-evidence/03096-30-drawing.png`。

| 图纸字段 | 所选型号值 mm | 经截面确认的含义 |
|---|---:|---|
| D | M6 | 外螺纹 |
| D1 | 7 | 护套端入口大孔直径 |
| D2 | 3 | 钢丝贯通孔直径 |
| L | 34 | 调节器总长 |
| L1 | 24 | 螺纹段长度 |
| L2 | 8.5 | 入口 Ø7 等径直孔深度，到锥形过渡起点 |
| SW | 8 | 头部六角对边 |

型号材料为黄铜，表面镀镍。由 L−L1 得头部长 10 mm。截面明确显示 Ø7 后接锥形收口再到 Ø3，锥段位于螺纹段起点之前；因此锥段位于入口深度 8.5 至 10 mm 之间。这个界来自尺寸链及截面中的前后顺序，不是已标注的锥长。锥角、锥段终点、入口倒角和公差没有标出。

输出端 CAD 的外入口为 `co_housing_entry()=[-58,35.5,111]`；Ø7 直孔延伸到 Z102.5，未标锥段处于 Z101..102.5 范围。**Z102.5 不是已经确认的护套承力止面。** CAD 省略未标锥面，以直孔加小通孔的最大材料阶梯包络作参考；这不是采购件的完整制造模型，不能拿内部台阶证明端套已坐实。

## 端套 03096-25-0350

[官方型号页](https://www.norelem.mx/es/Vista-general-de-productos/Sistema-flexible-de-piezas-est%C3%A1ndar/03000/Accesorios-para-pernos-de-bloqueo-pasadores-de-bloqueo-y-pernos-de-bloqueo-de-bola/Fundas-terminales/Casquillo-terminal-lat%C3%B3n-pasivado-en-azul/p/03096-25-0350)；原图：`output/cable-hardware-evidence/03096-25-drawing.png`。

| 图纸字段 | 值 mm | 经截面确认的含义 |
|---|---:|---|
| D | 5.5 | 外径 |
| D1 | 5 | 护套插入内孔直径 |
| D2 | 2.5 | 钢丝出孔直径 |
| L | 11 | 总长 |
| L1 | 9 | 从开口端到内锥开始的 Ø5 等径孔深 |
| L2 | 4.5 | 从开口端到压接区的轴向位置，图注 1 为压接区 |

型号材料为黄铜，蓝色钝化。L−L1=2 mm 的鼻端区包含内锥与小孔，不能解释成均匀 2 mm 厚平底。内锥角度/长度、外鼻端倒角尺寸、压接后的形变与公差未标。

名义 Ø5.5 端套能进入 Ø7 入口，单边名义间隙 0.75 mm；Ø5 护套与 Ø5 套孔是厂家配套名义尺寸，不代表已知装配间隙。Ø1.5 线芯能够通过 Ø2.5 端套孔和 Ø3 调节器孔。端套的鼻端接触调节器未标锥面；由于两件倒角/锥面尚无完整尺寸，不能给出精确轴向承力坐深。CAD 将鼻端放在入口直孔末端作为浅边界参考位置，不能据此宣布真实部件已经坐实或端套已完成压接。

## 压丝端头 03096-35-03180507

[官方系列页](https://www.norelem.de/en/Product-overview/Flexible-standard-component-system/03000/Accessories-for-indexing-plungers-cam-action-indexing-plungers-and-ball-lock-pins/Screw-nipples-locked-with-grub-screw/p/agid.30769)；原图：`output/cable-hardware-evidence/03096-35-drawing.png`。

| 图纸字段 | 值 mm | 经图纸确认的含义 |
|---|---:|---|
| D | 5 | 黄铜圆柱体外径 |
| L | 7 | 圆柱体长度，不包括未标注的螺钉突出量 |
| D1 | M4 | 轴向紧定螺钉 |
| D2 | 1.8 | 穿线横孔，垂直于端头/螺钉轴线 |
| L1 | 3.5 | 螺钉入口处的本体端面至穿线孔中心 |

材料是**镀镍黄铜**，不是钢。端视图显示紧定螺钉为**一字槽**。截面显示螺钉能够突出圆柱本体端面；螺钉长度、实际突出量、槽宽/深、拧紧扭矩和夹丝保持力均未标。

此证据曾暴露旧 Ø3.5 维护孔可能顶住突出的 M4 螺钉。后续 [金属垫圈保持修订](cable-washer-retention-review.md) 已用金属 M4 垫圈捕获端头、Ø6 盖出口贯通，使盖合不再需要猜测突出长度；没有采用仅靠0.2 mm PETG挡边的Ø4.6孔方案。仍在拆盖状态夹丝，未知一字槽尺寸、扭矩和实际采购公差不能由通孔自动证明。

## 完整拉索 03096-14 与球形端头

[官方系列页](https://www.norelem.de/en/Product-overview/Flexible-standard-component-system/03000/Accessories-for-indexing-plungers-cam-action-indexing-plungers-and-ball-lock-pins/Bowden-cables-for-indexing-plungers-with-remote-actuation/p/agid.32096)；原图：`output/cable-hardware-evidence/03096-14-drawing.png`。

厂家装配图确认：D1=1.5 为钢丝直径；D2=5 为出厂固定端球直径，剖面和外形均为球形；D3=5 为护套外径。另一端可调压丝端头 B=7。钢丝材料为不锈钢 1.4401；护套为带塑料涂层钢护套。完整套件列出 03096-15 钢丝及固定端件、03096-20 护套及内管、03096-25 端套、03096-30 调节器、03096-35 压丝端头及 07212-106 六角螺母。

03096-14-1000 表中护套 L=1000、钢丝 L1=1200；另有 3000/3200 与 5000/5200 型号。此处仅记录规格，不等于已选择或已购买长度。

**厂家最小弯曲半径 R65 mm 适用于带护套的 Bowden 拉索布线路径**，包括安装过程中不得暂时弯得更小。厂家还说明护套只能承受压力，拉伸会损坏它。此 R65 不能外推成输入扳机中裸钢丝的卷绕半径要求；裸芯局部绕弯、反复弯曲寿命与对应负载仍缺厂家证据。

## 剩余边界和可采取动作

- 厂家资料已能支持候选五金、方向、已标孔径、已标长度和入口/线芯关系，不再继续无期限搜图。
- 未标锥面与鼻端倒角保留为不确定区域；需要同型号的完整 STEP/制造图或已采购实物尺寸，才能给精确止面。
- 压丝端头螺钉突出已通过金属垫圈捕获和独立贯通出口解除与盖合的长度依赖；仍需实际一字槽工具/扭矩、采购公差与保持强度证据，不能把通过几何捕获当作防松和载荷验证。
- 弹簧/凸轮实际阻力、线缆摩擦、夹持扭矩、使用寿命、PETG 受载与打印偏差未被这些图纸验证。数字干涉检查只覆盖明确画出的包络。
- 本轮未把候选五金写成已购；未修改用户已有 CAD 原件，独立候选改动由父任务统一复核。
