# 工厂卡簧槽带头 Ø8 销：有限来源复核

找到两个真实工厂系列；本轮没有找到同时具备“26 mm 外跨适用、完整槽位置公差、明确可直接下单标准 SKU”三项证据的现货销。没有采购、联系厂家、改 CAD，亦不建议自行给已购销开槽。

| 来源 | 实际目录/型号 | 已公布的关键尺寸 mm | 对本机的意义 |
|---|---|---|---|
| Technifast | `ISO 2341 – Circlip`，配 DIN471；目录 Ø8、L1=35 行 | 轴 8 h11；头 Ø14×3；槽宽 C1=0.9；槽底 ØC2=7.6；头下到槽近壁 G1=30.5；L1=35±0.5 | 可供隔离方案引用的标准目录规格；未给独立 SKU，不能把目录系列库存描述当这一具体件实时现货 |
| mbo Osswald | `10 79 4305 0008/000`，SKU `0012972`，MPN `DIN-471-BEG-8-X-205-X-165-V2A-BLANK` | 8 h11；槽底 7.6 h10；槽宽 0.9 H13；头 12 h14×2 js15；L1=20.5 +0.3，L2=16.5 +0.3 | 工厂标准件身份和公差明确，但连总长度都不足26，不能直接用 |

Technifast 的 [官方总目录第20页](https://www.technifast.co.uk/_files/ugd/6c88df_b1d817e44b044412b92b6be37d8828fa.pdf?index=true)已下载并[目视图页](evidence/technifast-clevis-p20.png)：L1 从头下到尾端，G1 从头下到槽近壁。Ø8 的 L1=32 行对应 G1=27.5，35 行对应30.5。槽径7.6使名义径向深度为(8−7.6)/2=0.2；它不是槽深公差。12～50长度段的±0.5明确列在长度表，但没有单独赋给G1，因此 **G1允差、槽宽/槽径允差、头根包络、头部允差保持未知**。不能借用mbo或Rotor Clip的数值给Technifast销作厂家保证。

Technifast另有[单页官方资料](https://www.technifast.co.uk/_files/ugd/6c88df_26c772a74b0b45a9bde35f7bb4f76a65.pdf?index=true)说明库存包括DIN471槽系列，但没有明确8×35的库存或SKU。系列材料包括镀锌低碳钢、不锈钢303/316；本轮未锁定一件具体供货材料版本，不能把选材当已购规格。头和槽的位置/形状仍须供应图或接受标准约束。

[mbo确切不锈钢型号页](https://www.mbo-osswald.de/en/shop/bolt-with-groove-for-retaining-rings-din-471-suitable-for-clevises-beg-8-x-20-5-x-16-5-stainless-steel-bright)给材料1.4305、bright。其官网产品表仅返回三种Ø8标准版本，全部BEG8×20.5×16.5。保留[原始产品表](evidence/mbo-product-grid.json)和[Ø8摘取](evidence/mbo-d8-published.json)，没有推定其他未列型号不存在。官方[图底图](evidence/mbo-groove-drawing.webp)与页面SVG字段映射显示L2到槽近壁；它不是孔中心或槽中心。图示z1/z2约1和尾部30°/头边45°不是头根圆角完整公差。

mbo的[工厂槽销配置器](https://www.mbo-osswald.de/en/configurators/bolts-configurator-with-groove)明确区分标准库存系列与按用户夹持长/长度制造的配置件。本轮仅阅读说明，没有提交配置、生成订单或虚构“8×35”SKU。若后续允许工厂按配置供货，可在该正规系列中要求适合26外跨与尾垫的夹持长并取得最终图；它仍须被标为定制配置供货。

卡簧本体、卡簧钳通道、尾垫、受力和整机避障由根线程独立处理。本报告只锁定轴销目录事实；不迁移卡簧厂推荐槽公差作为销轴厂家承诺，不声称任何方案制造或物理通过。

数据与证据SHA：[report.json](report.json)。本次证据为2026-09-27只读查询。
