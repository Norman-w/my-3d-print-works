# 拉索厂家资料的限定复查

本轮只查03096-35-03180507夹头、03096-25-0350端套和03096-14拉索。结论是**裁短许可有官方依据；夹丝扭矩、最短余尾、保持力及实际承力坐深仍未获得数值依据**。没有改CAD、联系厂家、购买或打印。

[03096-14官方页面](https://www.norelemusa.com/en-us/Product-Overview/Flexible-standard-component-system/03000/Accessory-for-indexing-plungers-cam-action-indexing-plungers-and-ball-lock-pins/Bowden-cables-for-indexing-plungers-with-remote-actuation/p/agid.32096)明确允许安装时缩短拉索，并要求布线后再调节芯套长度；还要求带护套路径始终满足R65、安装时也不能暂时过弯，护套仅承受压缩。这只确认可裁短原则，不等于取得裁切、内管端口和端套压接工艺，也不能给出最终裁切长度。

| 尚缺字段 | 已有证据不能替代它的原因 |
|---|---|
| Ø1.5钢芯对应夹丝扭矩 | M4只是螺纹规格，不能代用通用M4紧固扭矩 |
| 最短外露余尾 | 端头L7、横孔位置L1=3.5均不是钢芯余尾要求 |
| 夹头抗滑/拉脱或允许载荷 | 钢芯材质和孔径不证明夹持能力；还需配套扭矩、尾长及载荷条件 |
| 端套在调节器中的实际承力坐深 | 鼻端、配合锥面与公差不完整，显示位置不是坐实尺寸 |
| 护套插入端套后的止面和压接工艺 | Ø5直孔深9及压接区位置4.5不是最终压入量/压接深度 |

[夹头官方说明](https://www.norelem.de/en/Product-overview/Flexible-standard-component-system/03000/Accessories-for-indexing-plungers-cam-action-indexing-plungers-and-ball-lock-pins/Screw-nipples-locked-with-grub-screw/p/agid.30769)和已有原图未给前三项；[端套型号页](https://www.norelem.mx/es/Vista-general-de-productos/Sistema-flexible-de-piezas-est%C3%A1ndar/03000/Accesorios-para-pernos-de-bloqueo-pasadores-de-bloqueo-y-pernos-de-bloqueo-de-bola/Fundas-terminales/Casquillo-terminal-lat%C3%B3n-pasivado-en-azul/p/03096-25-0350)确认标称尺寸及压接区，但没有补出后两项。本轮重新目视检查了保存的三张厂家原图，没有按图片比例猜尺寸。

当前CAD只为余尾提供从端头中心向外8 mm、名义露出本体5.5 mm的空间预算，**不是厂家规定的最短余尾**。若真正需要的余尾大于5.5 mm，不能为了装进去就再剪短，需另行处理接口空间。

访问范围也已记录：官方旧夹头PDF链接返回404；普通文件下载有406和超时，当前页面没有取得可读的新PDF，CAD下载需要登录。因此准确说法是“本轮可访问正文与已保存原图未提供这些数值”，不是断言厂家任何文件都没有。检索仅围绕这三个型号族，没有借用其他产品的扭矩或载荷。

可执行的后续路径有两条：保留现型号，以同一型号的正式装配参数或实际成品五金/钢芯验证补齐；或选择已定义端部尺寸、长度基准和额定保持能力的厂家预制总成，再核对接口。这里没有选新产品，也不要求打印耗材试片。具体应取得的字段已列在[报告](/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/current-cable-supplier-closure/report.json)，尚未向任何人发送。

证据索引：[官方访问记录](/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/current-cable-supplier-closure/reviewed-official-evidence.json)、[原始下载结果](/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/current-cable-supplier-closure/retrieval.json)。脚本仅按已记录证据重建报告并核对本地SHA，不会重新联网或改变设计：

```sh
/Applications/FreeCAD.app/Contents/Resources/bin/python -B output/current-cable-supplier-closure/build_report.py
```
