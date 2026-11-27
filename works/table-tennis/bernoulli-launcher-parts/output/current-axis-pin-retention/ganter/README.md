# Ganter 标准销轴：尺寸语义与配套止退件筛选

2026-09-27 只读核对。官方图已下载并目视，未采购、未替换候选轴或正式CAD。

候选 **GN 2342-NI-8-28-B-2** 为AISI304销、平头垫片、带横孔型。厂家将头部沉头螺钉锁固为不可拆件；用户装配不需要通过该螺钉给PETG施加中央预紧。[官方图](https://live-katalog.ganternorm.com/pdf/ganter/EN/2342.pdf?dispositiontype=attachment)及[本地原件](evidence/gn-2342.pdf)。

## 图纸上的长度不能混读

Identification 2 图的 **l1=28 指头下到横孔靠头侧孔边**，并非孔中心或销尾。d2=2.5为孔径；l2=5.5从该孔边量到尾端。因此名义孔中心距头下29.25，头下总杆长33.5。B头垫片外径12、厚s1=3；销径8h9。两人独立目视核对了尺寸线。

依据同厂[ISO公差摘录](https://live-katalog.ganternorm.com/pdf/ganter/en/286_2.pdf?dispositiontype=attachment)，8h9为7.964～8.000 mm。其余未标注尺寸的实际允差、头下过渡和成套交货检查条件未取得，不能全部设为零。

对于圆直腿止退件，令孔中心距头下E、孔径D、直腿实际外径d、尾垫厚t。忽略变形并要求尾垫与直腿真实接触时，有效捕获跨度的几何区间为：

`E − D/2 − t ≤ L_capture ≤ E + D/2 − d − t`。

它来自直腿中心可在孔内沿销轴方向移动±(D−d)/2，不是用孔中心直接减塑料厚度。实际壳跨26 mm还要与尺寸公差、轴倾斜和直腿保持姿态共同比较。该式本身没有证明垫片不会倾斜、止退件强度或实物装配。

## 原厂配套R形销不作为当前默认选型

厂家为Ø8指定 **GN 1024-NI-2-D**。其直线方向总长56=25+31，侧高14，双圈轴向厚s=5.5，允许配销径8～14。[官方图](https://live-katalog.ganternorm.com/pdf/ganter/EN/1024.pdf?dispositiontype=attachment)及[本地原件](evidence/gn-1024.pdf)。

它绕主销转动的侧向范围远大于旧杯/锁母约6 mm半径，不能继承旧尾部几何或套筒工具检查。当前没有做实际R形曲线的交集，所以结论是**不优先选用，须独立检查**，而非已经证实碰撞。表中约10 N安装力、9 N拆出力对应Ø12销，不是本Ø8装配的脱出额定，更不是主销轴向保持载荷。

原厂[承载表](https://live-katalog.ganternorm.com/pdf/ganter/en/kugelsperrbolzen_belastbarkeit.pdf?dispositiontype=attachment)列的是双剪破坏量级，不能代替头部连接、止退件、塑料座和实际弯曲载荷验证。当前优先继续比较紧凑的标准开口销；无自行改钻厂家销轴、无供货沟通或采购。

`selected=false`、`geometric_collision_proved=false`、`manufacturing_release=false`、`physical_acceptance=false`。
