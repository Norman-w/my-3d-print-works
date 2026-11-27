# CH1 · 25H / 04C 单排滚子链条（已不作为目标）

**CH1 已改到同店最小规格 03C。** 现行文档：[CH1-03C-roller-chain.md](CH1-03C-roller-chain.md)。本页只保留 04C / 25H 的历史捕获。

来源：淘宝采购 MCP `read_product_evidence` + `quote_sku`（扩展可见页，2026-09-12）。  
当前 CAD 选择机构仍是 **HTD3M-9 同步带**；本页只记录这条已打开商品的采购证据，不把它写成已上机零件。

## 身份

| 字段 | 值 | 证据级别 |
|---|---|---|
| 位号 | CH1 | 本仓库 BOM |
| 已选 SKU | **25H(04C)2分单排链条长1.5米** | MCP 可见规格 |
| itemId | `40603194129` | URL / 扩展 |
| skuId | `3456802337508` | URL / 扩展 |
| 商品标题 | 25H04C小规格工业链条05B04B03C传动链条滚子链条 2.5分2分链条 | 详情页 |
| 店铺 | 常州市东科链传动科技企业店（评分 4.9） | 详情页 |
| 链接 | https://item.taobao.com/item.htm?id=40603194129&skuId=3456802337508 | |
| 证据指纹 | `evidence_5ea48192` | MCP |
| 报价 | **¥13.31 / 份** | MCP `pricePerPackCny` |
| 运费 | 未捕获 | MCP `missingEvidence: shipping` |
| 库存 / 交期 | 未捕获 | MCP |
| 每份数量 | 未结构化；SKU 文案为 1.5 m | MCP `packQty=null` |

MCP 校验：`insufficient_evidence`（分数 29）。没有硬冲突。缺的是页面结构化 MPN/封装字段，不是 SKU 选错。人工核对前不得当 exact。

## 几何（卖家尺寸图）

主图尺寸标注来自商品图 `O1CN01Wr9wWi1TC3rNaYqxR`，针对 **04C 单排**。SKU 写「1.5 米」，图面写「1.524 米」——以下按图面记，长度以到货实测为准。

| 尺寸 | 符号 | 值 |
|---|---|---|
| 节距 | P | 6.35 mm |
| 内链板高度 | h2 | 6 mm |
| 滚子直径 | d1 | 3.3 mm |
| 销轴直径 | d2 | 2.31 mm |
| 销轴长度 | — | 8.4 mm |
| 链板厚度 | T | 0.8 mm |
| 标称长度 | — | 1.524 m（SKU：1.5 m） |
| 单根质量 | — | 0.23 kg |

同一 listing 的系列（**不是**当前已选 SKU）：

| 型号 | 节距 |
|---|---|
| 03C (15) | 4.7625 mm |
| 04B | 6 mm |
| **04C (25H)** | **6.35 mm** ← 当前 SKU |
| 05B | 8 mm |

25H / 04C 对应短节距滚子链 ANSI #25 一族；与本仓库 HTD3M（节距 3 mm）不是同一传动。

## 采购 BOM

文件：[`../procurement/25H-04C-roller-chain.bom.csv`](../procurement/25H-04C-roller-chain.bom.csv)

- `requirementId`: `req_f044b33734f8297c`
- 板数 1 → `baseRequiredQty` 1，备损后 `targetQty` 2（special 10% / 至少 1）

## 原始捕获

见 [`CH1-25H-04C-roller-chain.evidence.json`](CH1-25H-04C-roller-chain.evidence.json)。未写入 Cookie、地址或支付信息。

## 未闭合项

1. 运费、库存、交期需再读一次可见页或购物车证据。
2. 1.5 m vs 1.524 m：下单/收货时量长度。
3. 未在 FreeCAD 里当选择带使用；若改链传动，要另做链轮节圆、张紧和润滑，不能替换现有 `SelectorBelt_HTD3M9`。
