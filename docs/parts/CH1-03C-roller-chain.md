# CH1 · 03C 单排滚子链条（本 listing 最小规格）

同一店铺商品里完整链条按节距从小到大：

| 型号 | 节距 | SKU 文案 | 角色 |
|---|---|---|---|
| **03C (15)** | **4.7625 mm** | **单排03C-1X210L长1米** | **当前目标** |
| 04B | 6 mm | 单排04B-1X254L长1.5米 | 同店更大 |
| 04C (25H) | 6.35 mm | 25H(04C)2分单排链条长1.5米 | 先前误选，见 [CH1-25H-04C-roller-chain.md](CH1-25H-04C-roller-chain.md) |
| 05B | 8 mm | 单排05B-1X190L长1.5米 | 同店最大 |

接头（CL/OL）和链轮定制不是链条本体。`03C单排全接CL` 只是开口扣。

## 身份

来源：MCP `read_product_evidence` + `quote_sku`，扩展可见页已选中 03C（2026-09-12）。

| 字段 | 值 | 证据级别 |
|---|---|---|
| 位号 | CH1 | 本仓库 BOM |
| 已选 SKU | **单排03C-1X210L长1米** | MCP，校验 **exact** |
| itemId | `40603194129` | URL / 扩展 |
| skuId | `3456802337510` | URL / 扩展 |
| 报价 | **¥40.56 / 份** | MCP `pricePerPackCny` |
| 店铺 | 常州市东科链传动科技企业店（4.9） | 详情页 |
| 链接 | https://item.taobao.com/item.htm?id=40603194129&skuId=3456802337510 | |
| 证据指纹 | `evidence_c1f48225` | MCP |
| 运费 / 库存 / 交期 | 未捕获 | `missingEvidence: packQty, shipping` |

MCP：`classification=exact`，`exactMpn=true`，分数 55。运费仍缺，不能当完整报价。

## 几何

SKU：210 节 × 4.7625 mm = **1000.1 mm ≈ 1.00 m**，与「长1米」一致。

卖家在切到本 SKU 后给出的 03C 尺寸图（`O1CN019SmdFP1TC3tN3tyOX`）：

| 尺寸 | 符号 | 图面 |
|---|---|---|
| 节距 | P | 4.762 mm（系列表写 4.7625 mm） |
| 内链板高度 | h2 | 4.3 mm |
| 滚子直径 | d1 | 2.48 mm |
| 销轴直径 | d2 | 1.62 mm |
| 销轴长度 | — | 6.9 mm |
| 链板厚度 | T | 0.6 mm |
| 图面长度 | — | 1.524 m ← 与 SKU「1 米 / 210L」冲突，以 SKU 节数为准 |
| 图面质量 | — | 0.12 kg ← 可能对应 1.524 m，到货称重 |

当前 CAD 选择机构仍是 HTD3M-9（节距 3 mm）。03C 不能当同步带用；若改链传动需另做 03C 链轮、张紧和润滑。

## 采购 BOM

[`../procurement/03C-roller-chain.bom.csv`](../procurement/03C-roller-chain.bom.csv)

- `requirementId`: `req_9aa3a297aa1a6b03`
- 板数 1 → `targetQty` 2（special 备损）

原始捕获：[`CH1-03C-roller-chain.evidence.json`](CH1-03C-roller-chain.evidence.json)
