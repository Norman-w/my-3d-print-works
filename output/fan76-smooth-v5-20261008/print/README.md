# Ø76 v5 单外壳打印准备

本次只打印 `fan76-smooth-v5-body-clean.stl` 一件；不打印四个共用 Ø41 气嘴。
**尚未发送打印，也未完成原生界面放行。**

## 已准备

- `fan76-smooth-v5-body-only-prepared.3mf`：仅包含一个干净实体，无嵌入支撑，毫米单位、100%比例、风机套口向下、中心在(128,128)。原始 STL SHA256 为 `e0be6b465aebef9dff9f6886d6a49f9420e24ea8416c321caef14fc1e02a42fc`。
- 沿用历史已验证的 X1C/0.4 mm 喷嘴、PETG、纹理 PEI、0.2 mm 层高、4圈墙、25%填充、6 mm裙边、树形自动支撑且仅接触打印板。模型高248 mm，冻结预设高度250 mm，余量2 mm。
- `prepared-project.json`、`config/native-baseline.json` 记录网格、摆位及原生启动/结束代码哈希；账号、语言、连接和机器高度限制均未修改。

## 本次 CLI 预检，不是已放行任务

在独立临时配置目录中调用已安装的 Bambu Studio 02.08.02.61；没有访问打印机。约 **5小时20分、159.91 g、1240层**，只代表切片估计。

`native-audit.json` / `slice-provenance.json` 的检查结果：

- 原始STL与切片内网格在0.0001 mm界限内逐顶点、逐三角形对应；最大坐标误差约0.00000384 mm。密集顶点按唯一最近邻和双射匹配，不放宽误差阈值，仍拒绝合并、等距歧义和反面。
- 两个卡槽顶都有支撑接触，沉积表面间隙约0.2 mm。Support 与 Support interface 均检查；支撑Z范围0.2..21.4 mm，无卡槽区以外支撑，母螺纹无支撑。
- 181个母牙采样层保留牙根/牙顶刀路变化，最小径向对比约0.858 mm。
- 原生启动和结束代码未变；归零、调平、热床/喷嘴等待及AMS指令存在。这不证明机器已经执行这些动作。
- **CLI包中的 `slice_info.printer_model_id` 为空，机型核验未通过。没有手动补写这个标识，也没有发送该包。** CLI候选、日志、诊断采样、重复预设和原始缓存均被Git忽略。

拓竹界面最初能读取到上一套Ø41任务完成（100%、732/732）；打开本次准备工程后，桌面控制连续超时。进程仍在运行，没有强制退出、重新登录、重配打印机或重复发送。打印板清空和灰色PETG确认已向用户询问，尚待回复。上一套完成不代表当前打印板已清理。

## 恢复后继续

1. 在拓竹打开本目录的单件prepared工程，确认X1C、纹理PEI和灰色PETG，检查模型与卡槽树形支撑。
2. 在原生界面切片，另存新的工程及实际G-code包，不能发送旧版本或CLI候选冒充正式包。
3. 执行下面的`audit`，要求所有检查通过；再确认打印板已清空、AMS映射、调平和流量校准选项。
4. 发送后分别记录传输、准备、首层、完成和实物配合。LiDAR警告若出现须单独记录，不能宣称自动首层检查通过。

```sh
python3 scripts/fan76_smooth_v5_print.py prepare
python3 scripts/fan76_smooth_v5_print.py slice  # 仅预检，不发送
python3 scripts/fan76_smooth_v5_print.py audit --project <原生工程.3mf> --package <实际G-code包.3mf>
python3 scripts/test_fan_nozzle_print_package.py
```

只有原始STL及准备工程可用于继续准备；切片放行、机器执行、强度、气密性及实配均未完成。
