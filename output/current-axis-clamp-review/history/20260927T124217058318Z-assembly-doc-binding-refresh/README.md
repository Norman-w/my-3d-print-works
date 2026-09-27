# 夹紧说明纠正后的文档绑定刷新

限定复核通过，39项检查全部成立。此次只消费根线程已纠正的 `docs/cable-trigger-input.md`；没有修改CAD、规格、数量、制造选择或当前文档。

旧包：[20260927T122149439656Z](../../../current-assembly-package/runs/20260927T122149439656Z/manifest.json)。新包：[20260927T124252819653Z](../../../current-assembly-package/runs/20260927T124252819653Z/manifest.json)。新 manifest SHA：`61556dc3690f9313f85c70cf5bf9f1e5b4baa9bcc172a6c58c20e680b73e2cc4`。

- 44条BOM（含名义规格、设计选择、数量）完全相同。
- 301条安装记录及56条打印取件记录完全相同。
- 新旧五金CSV、取件CSV和包README逐字节相同。
- 原输出盖及定距管设计选择均未变化；套件非加计层次、保留螺母与替换记录均未变化。
- 当前包108条来源绑定均与实际文件匹配；拉索增量20条来源均匹配。
- `hardware.json` 只改变生成时间和输入说明文档SHA；合并包相应更新该文档及 `hardware.json` 的来源SHA、生成时间。

先按 [backup-manifest.json](backup-manifest.json)保存原 hardware.json、README.md、extract.log、verification.json、latest.json，另加提取脚本副本，全部字节哈希已核。随后运行原提取脚本和原合并脚本，未改变它们。当前 cable-hardware/verification.json 已记录本次实际计数、层次和来源检查。

完整差异及检查结果：[comparison.json](comparison.json)；增量刷新单独比较：[hardware-comparison.json](hardware-comparison.json)。复核脚本：[verify_refresh.py](verify_refresh.py)。复跑仅重新验证上述固定两次包并更新时间戳和本次verification，不做CAD、切片、采购或打印。

这次文档绑定更新没有解除夹紧尺寸链本身的未闭合项；制造/实物放行仍为false。
