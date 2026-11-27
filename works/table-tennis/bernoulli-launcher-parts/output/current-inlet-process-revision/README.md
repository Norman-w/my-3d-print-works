# 入口后夹工艺比较与限定数字绑定

本轮使用同一当前入口后夹 STL（SHA256 `146bcf746c8f1a52825c68675ad1844d8ed4de079c75c3885504240121e3069a`），没有改变机械 CAD 或总装模型。候选 3 已作为限定范围的数字制造证据绑定到[正式选盘](../current-manufacturing/inlet-process/manifest.json)，其余候选未采用；全部切片仅离线生成，未发送打印。选盘不等于制造或实物验收。

## 已完成的比较

| 候选 | 变化 | 当前结论 |
|---|---|---|
| [1：原方向、四处局部屏蔽](key-growth-review.md) | 原 +CAD Z 生长，0.1 mm 层高；只屏蔽安装板孔和绑带槽 | 四孔槽内支撑清空，但后键上片仍有约 5.19 mm 首道缺少此前模型/有效支撑承接。拒绝采用。 |
| [2：再加两处强制支撑](runs/20260927T110029857048Z/key-growth-review.md) | 保留候选 1 的全部参数，后键孔上方增加两个支撑增强区域 | 部分首道得到承托，仍有约 4.39 mm 首道无此前模型/有效支撑承接。拒绝采用。 |
| [3：后键端朝下](runs/20260927T110450585847Z/inlet-rear-rear-key-ends-down-supported/key-bed-start-review.md) | 原 STL 绕 X +90°，+CAD Y 生长；恢复原 0.2 mm 配置和 0.35 mm 支撑 XY 间隙 | 四段后键均从床面开始；其自身首道承托、完整五金空域和起始接触来源已核对，现作为限定数字选盘绑定。原严格接触失败及物理限制保留。 |
| [4：后键端朝下，XY 间隙 0.6](runs/20260927T111514812952Z/inlet-rear-rear-key-ends-down-xy060-supported/current-review.json) | 相对候选 3 只把 `support_object_xy_distance` 从 0.35 改到 0.6 mm；机械实体不变 | 原生切片及身份/床面范围检查通过，整树退取检查仍未通过。不能凭增大间隙认定可取出。 |

这里的“整树退取未通过”指最初的严格零交叠检查，不等于实物绝对拆不出。最初扫掠把同层全部挤出合并成统一高度范围，属于保守检查；同层桥线与普通壁线高度不同，会造成额外命中。逐路径定位已区分这种算法保守项、起始包络接触和移动方向上的后续障碍，原始失败保留。

[候选 3 逐路径定位](runs/20260927T110450585847Z/inlet-rear-rear-key-ends-down-supported/hit-localization.json)修正同层高度后，严格模型珠体命中剩 5 层、STL 命中 1 层，合并 6 层；[候选 4](runs/20260927T111514812952Z/inlet-rear-rear-key-ends-down-xy060-supported/hit-localization.json)分别为 7、4、合并 9 层。**两者均未找到位于支撑起始层底以下的阻挡**；现有命中位于起始接触范围，因此不能称整棵树被下方倒扣锁住。候选 3 沿 −print Z 移动严格大于约 0.08543 mm、候选 4 严格大于约 0.200001 mm 后，报告中相应名义包络均可脱离；这些是数值分离界，不是允许加工误差、施力指令或拆除力证明。未因此制造放行。

**候选 3 已完成本范围的数字绑定，候选 4 不采用。** 第四候选在 print Z13.6 / 19.8 的同层支撑与模型珠体有约 0.2 mm 高度的起始包络重叠，不能当成浮点噪声；增大全局 XY 间隙没有改善这项结果。

候选 3 的[起始接触来源复核](runs/20260927T110450585847Z/inlet-rear-rear-key-ends-down-supported/initial-compatibility-origin.md)进一步定位了原报告中的全部剩余命中：唯一源 STL 三角面接触对应连续 CAD 外表面与实际 FDM 台阶之间的差异；实际同层模型与支撑包络最小间距约 0.018900 mm，首次覆盖发生在下一层。五个模型命中层中，四层的约 1e−6 mm 高度重叠来自 `LAYER_HEIGHT` 文字与机器 Z 层面增量的差异，另一层原本即为边界接触；按机器层面均为边界，不是正间隙。原严格结果没有删除或改成全空交，0.018900 mm 也不是实物制造间隙保证。

## 后键朝下的结果与代价

候选 3 的实际 3MF 恢复出 `print Z = CAD Y + 53.7999987232`。四段后键都有首层实际模型挤出，Z0.2 至 5.8 共 29 层保持相邻模型重叠；Z6.0 才开始的是宽锚板扩展，不能与旧的后键上片悬空问题混为一谈。

两个 Ø2.9 孔及两个 3×22 mm 绑带槽的模型中心线未跨越名义空域封顶。两孔只有 Z0.2 首层存在支撑铺底，绑带槽未见支撑。模型珠体与孔槽边缘仍有薄带交叠；这不是成品孔径或实物配合的验收。

新摆向把背梁贴合面放到支撑上。[候选 3 自身的逐先后承托检查](runs/20260927T110450585847Z/inlet-rear-rear-key-ends-down-supported/underlay-review.md)已核对 Z6.0 新增底面与两 M4 螺母肩台：锚板第 63643 行的 10.81 mm 路径有约 5.295 mm 中心线位于此前支撑投影上，不能说整条无支撑；局部最长直线缺托段为第 64599 行 `Bridge` 的 **4.60631 mm**，两端有此前投影承托。两 M4 肩台第 257700 / 257215 行的首道中心线缺少垂直下承，但珠体端部与前层孔缘有少量搭接；最长缺托环弧为 2.65715 / 3.47300 mm，不能叫作相同长度的自由直桥。后打的直线 `Bridge` 最大缺托约 0.84909 / 0.84918 mm，也未倒算成先前环弧的支撑。这些局部悬挑和部分线宽承托均保留，不能据此认证 PETG 桥接、支撑间隔、承面质量或强度。

[候选 3 完整名义五金包络](runs/20260927T110450585847Z/inlet-rear-rear-key-ends-down-supported/hardware-volume-review.md)检查了两根 Ø2.5 螺杆、两根 Ø4 螺杆及两个 AF7 螺母从原开口到承面的完整入位体积；六项均未命中模型挤出，但都有支撑占用。支撑必须在装五金前清理，不能靠螺钉硬拉入。此证据不等于实孔尺寸或供货公差验收。

## 与当前正式交付的关系

- [正式制造索引](../current-manufacturing/manifest.json)现为 **56 实例绑定 42 盘**，没有剩余待审候选盘；新增选盘仅为候选 3 的入口后夹。原 41 张选盘、其他 55 件及全部 56 件 STL / 材料 / 数量不变。
- [当前正式装配包](../current-assembly-package/runs/20260927T113921981888Z/README.md)只更新后夹取件工艺；44 行五金 CSV 与旧包逐字节一致，工作档仍装 55 件、保持档装 56 件。旧包 `20260927T104027787103Z` 保留原样。
- [独立集成核对](../current-manufacturing/inlet-process/integration-review.md)的 29 项检查通过：后夹 64 项证据及新装配包 106 项来源身份均匹配。该结论是工件和证据绑定，不是打印质量或实物验收。
- 原生参数继续使用 Generic PETG、Textured PEI 假设；用户已确认的是 PETG 和 PEI，具体品牌与表面仍待确认。
- [拉索供应资料限定复查](../current-cable-supplier-closure/README.md)确认可安装裁短原则，但夹丝扭矩、最短余尾、保持力和端套承力坐深仍缺数值依据。

索引同步前的 [README 原件](../current-manufacturing/history/before-inlet-process-binding-20260927T113531345167Z/output/current-inlet-process-revision/README.md)、[比较清单原件](../current-manufacturing/history/before-inlet-process-binding-20260927T113531345167Z/output/current-inlet-process-revision/process-comparison.json)及[身份记录原件](../current-manufacturing/history/before-inlet-process-binding-20260927T113531345167Z/output/current-inlet-process-revision/current-identity-verification.json)均逐字节保存；四个候选的原生报告未修改。当前引用及 SHA 见[比较索引](process-comparison.json)与[身份核对](current-identity-verification.json)。

机械固定、运动方向、止挡余量和回位结论见[当前机械复核](../../docs/current-mechanical-review.md)。本轮不将打印路径证据扩大为负载、摩擦、强度或一次成功保证。

`manufacturing_release=false`、`physical_acceptance=false`、`sent_to_printer=false`。
