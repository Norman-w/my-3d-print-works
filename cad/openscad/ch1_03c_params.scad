// CH1 03C 单排滚子链 — 尺寸真值源：docs/parts/CH1-03C-roller-chain.md
// 单位：毫米。这是外购碳钢链条的 CAD 包络，不是 FDM 打印件。

//#region 导入/依赖
// 无外部库；几何由本文件常数驱动。
//#endregion

//#region 常量/配置
P = 4.7625;          // 节距：系列表 / SKU 210L（图面写 4.762）
h2 = 4.3;            // 内链板高度 h2（卖家图 + ISO h2 max）
d1 = 2.48;           // 03C 图面「滚子」= ISO 套筒外径 d1 max（本规格无独立滚子）
d2 = 1.62;           // 销轴直径 d2 max
Lc = 6.9;            // ISO / 图面销轴总长 Lc max；装配外形用贴板铆头，不把细杆伸出这么长
L = 6.10;            // 铆头内侧销长 L max（ISO，图面未标数）
T = 0.6;             // 链板厚度 T max
b1 = 2.38;           // 内节内宽 b1 min（ISO；图面有符号无数字）
waist = 2.6;         // 链板腰宽：按卖家 8 字外形，不是标准表列
rivet_d = 2.15;      // 铆头直径：按侧视铆头 > d2
rivet_h = 0.40;      // 贴在外板外侧的铆头高度；避免 (Lc-L)/2 拉出细 stem
fillet = 0.42;       // 腰部凹圆角
roller_end_gap = 0.02;  // 仅 CSG 间隙，不留可见轴向窜动
journal_od = 2.05;      // 穿内板轴颈；可见鼓面仍用 d1
links_sku = 210;

inner_width = b1;
bushing_od = journal_od;
plate_stack = inner_width + 4 * T;
outer_face = plate_stack / 2;
pin_length = plate_stack + 2 * rivet_h;
visible_bush_len = inner_width - 2 * roller_end_gap;
clearance = 0.04;
eps = 0.05;
//#endregion

//#region 模型/类型
// 无独立类型；零件由 inner/outer plate、roller、pin、bushing 组成。
//#endregion

//#region 私有成员
// 几何常数全部公开给根模型 include。
//#endregion

//#region 公开 API
// include 后直接使用 P / h2 / d1 / d2 / pin_length / T。
//#endregion

//#region 业务逻辑
// SKU 210L × 4.7625 mm = 1000.125 mm。
// b1 / L 图面未标数，取 ISO 03C min/max；链板腰宽按卖家 8 字外形。
// 可见套筒长度必须是 b1，不是 b1+2T；后者会从斜向看成过长的连接棍。
// 销轴细杆只穿过板叠；铆头贴外板。Lc=6.9 是规格上限，不是要把 stem 拉到 6.9。
//#endregion

//#region 方法/工具
// 无。
//#endregion
