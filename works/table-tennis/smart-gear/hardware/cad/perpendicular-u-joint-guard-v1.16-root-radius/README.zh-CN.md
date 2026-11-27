# v1.16 旋转载荷加强试验版

X 上梁、Y 下脚、Z 向上，毫米，X1C / PETG，一体件沿 -Z 套入。下脚侧推经卡臂、绿色斜坡及紫色筋传向上墙。沿用原通孔、顶盖、字样和最低 1.5 mm 内扣，7 mm 卡臂不变。

每端沿 Y 抱持长度 23→28 mm，外端 ±33.5→±38.5；延长部分复制原端部截面，包含内扣。紫色筋保持顶部尺寸，下端 Y 向棱跟随延伸。绿色斜坡落向卡臂的内凹转折加入 R4 圆柱切削定义的相切补料过渡。原上墙旁的转折已被斜坡填实，故圆角放在实际斜坡脚部；不是在已实心处重复补料。

`strength_guard.scad` 是参数入口；`build_export.py` 沿用 v1.15 的分阶段统一阳边倒角导出方法；`validate_geometry.py` 检查接缝、安装通道、通孔、底棱及上盖不变量。需先准备 v1.13 文字导出，参见 v1.15 README。

复现：`uv run --no-project --with manifold3d==3.5.4 --with numpy==2.5.4 python hardware/cad/perpendicular-u-joint-guard-v1.16-root-radius/build_export.py`，随后同环境运行本目录 `validate_geometry.py`。

整件输出 `../exports/perpendicular-u-joint-v1.16-root-radius/guard-v1.16.stl`，1:1 毫米。审图位于 `../review/perpendicular-u-joint-v1.16-root-radius/`。外包 55.8×77×55.1 mm。建议继续使用房盖向上、内扣朝下的姿态并重新切片检查支撑；本次未切片或发送打印。

这是几何加强候选，尚未进行接触有限元或抗踢试验。抱持加长和补料会降低卡臂弹性，须重新验证扣入、拆卸、双向旋转和地面间隙；不能据此给出强度提升百分比。
