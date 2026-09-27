# 正式组件测力记录判据

这份工具消费[整链测力步骤](../supplier-bounds/README.md)产生的真实配对记录，不用猜测拉索η、摩擦系数或实际弹簧初拉力。当前[结果](current-result.json)为 **NO_MEASUREMENTS，真实记录0条**，装配配置身份也尚未填写；未进行回位验收。

读数/录像由正式组件测量取得。配置、源身份、路线和证据路径由助手从实际装配记录整理，用户不必手填29列。工具不要求打印试片，也不要求现在操作尚未完成的总成。

每条记录按同一实际配置、布线、姿态、行程位置区间、球载与风状态配对，计算：

`S下界 = 实测弹簧最小力 − 弹簧测量误差`

`Q上界 = max(0, 实测整链最大回程需求 + 整链测量误差) + 尚未计入的有利工装影响上界`

`余量 = S下界 − Q上界`

余量必须严格大于0。力值用十进制精确算术比较，零余量不会因二进制舍入变成“通过”。力误差须包含位置配对误差；未知误差不能填0。整链数据已包括的摩擦和重力不得再次扣除[模型自重预算](../moving-mass/README.md)。

脚本检查字段、有限数值、非负误差、配置一致、UTC时间、重力方向、实际重复次数、芯线张紧、原挂线方向与本地原始证据文件。错误、空表、缺证据和非正余量都会返回非零退出码2；这表示没有达到样本判据，不是程序运行失败。

**有证据文件不等于已读懂曲线。** 脚本记录文件SHA，但明确输出`trace_content_reviewed=false`。仅凭正样本也永不设置`overall_return_verified=true`；全行程、起动峰值、各预定姿态、实际自由释放、带球带风及耐久性不能由少量行数据自动推定。

复跑当前空表：

```sh
python3 output/current-return-budget/measurement-assessment/assess.py \
  --csv output/current-return-budget/supplier-bounds/paired-return.csv \
  --configuration output/current-return-budget/measurement-assessment/configuration-template.json \
  --output output/current-return-budget/measurement-assessment/current-result.json
```

未来真实测量使用另存的实际配置JSON及独立输出报告，不把占位配置伪装成已装总成。[合成控制](controls-report.json)只检查正余量算术、零边界、NaN、负误差、松芯、配置不符、缺证据和未绑定身份的处理，不是机构试验。
