# 定距管选型接入限定复核

结论：**PASS_LIMITED_SELECTION_INTEGRATION**。独立比较旧装配包 `113921981888Z` 与新包 `122149439656Z`；未重跑 CAD/切片，也未修改生产文件。

- 44 行 BOM 的规格标识完全相同；仅 `cable/steel-distance-tube` 的 `description`、`design_selection`、`nominal_contracts` 发生变化。原提取合同保留为后一个条目；全部数量与安装位置不变。
- 301 个安装实例结构完全一致。56 件取件清单结构一致，`print-picklist.csv` 字节完全一致。五金 CSV 仅定距管一行的说明及合同两列变化。
- 原输出盖 `output-cap-drive` 选择逐字段相同；套件层级、替换/保留记录、工作/保持档及遗留开放项均未改。
- 当前 108 个绑定文件均存在且 SHA-256 匹配。相比旧包新增两份供应证据绑定；共有来源只改变 selections 与生成器脚本。核对结束时再次确认全部匹配。
- README 的 4 个本地链接均有效；唯一外部链接为原输出盖官方商品页，URL 未变，本次未重复测在线可达性。

选型中的 SUS304、SPMSS-D8-V4.3-L15 目录编码和外径7.9～8.0、内径4.3～4.4、长度14.98～15.02 mm 与冻结供应证据一致。Accu HPS-8-15-ST 的最大外径8.5及宽长度范围被明确排除。`live_configurator_accepted`、`availability_verified`、`purchased` 均为 false；README 和选择限制明确轴套/推力垫片及整轴仍未放行，没有把目录配置当成当前已确认 SKU。

供应复核报告内保留的是采用前 selections 哈希，这是历史证据。新包分别绑定当前 selections 和冻结报告本体，且 `open_items_note` 明确说明此边界，没有改写旧报告为当前状态。

本检查通过仅指数据接入正确，不是轴系制造或实物验收通过。详细差异、108 个实测绑定及审查输入 SHA 见 [JSON](integration-review.json)。
