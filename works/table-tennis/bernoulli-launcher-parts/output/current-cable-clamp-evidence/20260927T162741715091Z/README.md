# 输出夹头：公开额定参数缺口复核

本轮没有取得能改变下一步动作的额定拉力、紧固扭矩或最低尾长。原候选仍是 **norelem 03096-35-03180507**；未采购、未询价，也未修改 CAD/BOM。状态为重复确认既有外部参数缺口，不是新的设计或制造通过。

## 先前资料和本轮边界

已先查旧 `docs/cable-hardware-evidence.md`、厂家原图和当前装配指南。尺寸、镀镍黄铜材料、一字紧定螺钉、配套线芯此前已查；旧文档已经明确扭矩、夹丝保持力与最小尾长未闭合。因此没有重新搜索图纸或替代型号。

本轮有限补查同系列夹头、03096-14 套件、03096-15 钢丝及 03096-10 原配系统的官方描述。[夹头官方页](https://www.norelem.de/en/Product-overview/Flexible-standard-component-system/03000/Accessories-for-indexing-plungers-cam-action-indexing-plungers-and-ball-lock-pins/Screw-nipples-locked-with-grub-screw/p/agid.30769)仍列几何/材料和配套关系，未给以下三项数值；[03096-14 官方页](https://www.norelem.de/en/Product-overview/Flexible-standard-component-system/03000/Accessories-for-indexing-plungers-cam-action-indexing-plungers-and-ball-lock-pins/Bowden-cables-for-indexing-plungers-with-remote-actuation/p/agid.32096)确认其与亮面 1.4401 钢丝配套，但没有夹持额定值。

| 项目 | 当前证据 |
|---|---|
| 最大/额定夹丝拉力 | 未在已读官方说明或既有图纸中找到；不由黄铜/M4尺寸反推 |
| 紧定螺钉扭矩 | 未给；普通 M4 螺栓扭矩不能替代压丝要求 |
| 夹头外最低余尾 | 未给；不能把模型的5.5 mm上限当最低要求 |
| 线材兼容 | 厂家03096-15/03096-14配套、名义Ø1.5与1.4401可证；任意Ø1.5钢丝、股数/绞法、破断力及循环寿命不能据此通用化 |

## 下载入口的真实结果

当前官方 HTML 已保存，找到两条新版产品 PDF 地址，见 `official-pdf-links.json`。直接下载均 HTTP406，Web PDF读取也不可访问；旧 MX 页公开 PDF 地址返回404。**PDF正文未读，不能声称已穷尽全部厂家资料，也不能声称这些未读PDF必然没有参数。** 没有继续绕路登录或无限重复下载。本轮新增的是可追溯的当前产品描述、PDF入口及失败记录。

## 当前构型能证明的内容

只引用既有名义几何，不新增干涉/强度验证：横孔Ø1.8对线芯Ø1.5有0.15 mm单边名义几何余量。输出余尾空间为夹头中心下8 mm，扣除本体半径2.5 mm后，本体外最多5.5 mm。金属垫圈和打印盖保持夹头本体；这与紧定螺钉能否夹住钢丝是两条不同的受力关系。贯通螺钉出口解决盖合空间，不证明紧固扭矩或抗滑力。

下一动作不变：在裁线和端接放行前，需同型号、同线材的厂家安装/额定资料，明确夹紧扭矩、最小尾长和可承拉力，并与实际所需拉力及现有5.5 mm空间比较。若最低尾长超过空间，应先修订端接/空间，不能剪短迁就。当前请求禁止询价，本轮未联系任何供应商。

`report.json` 给出参数空值、范围和原始来源；`local-baseline/` 固定本轮读到的旧证据/当前构型版本。运行 `python3 verify_evidence.py` 可核验这份报告绑定的文件哈希。数字几何不构成夹丝防滑、疲劳寿命或实物验收。
