# v2 前端源实现与接口变化（未发布）

仅修改 web/cable-scene-kinematics.mjs、web/feeder-motion.mjs、web/feeder-motion.html。旧文件及原 SHA 已保存到 output/cable-direct-pull-v2/pre-adoption/web/。未改 CAD、inventory、发布脚本或局域网资源。

## 接口

新增 `inputKinematics(u, ci)`：读取 ci.motion_law=fixed-guide-direct-pull-v2，返回 a/phi（弧度）、B（端球本地坐标）、T（导向切点）、L（调节器出口至端球路径长）、u、takeup、restLength、effectiveArm、axialLeadIn、coreLengthFromMouth。内部对 L(a)-L(0)=u 做 56 步有界反解；缓存同一契约/位姿的解，最多保留4个姿态；契约参数改变使缓存失效。

ci 必需参数使用根约定：ball_orbit_radius、fairlead_center、fairlead_core_radius、wire_terminal_local、angle_solve_deg、fairlead_extent_deg、adjuster_delta、adjuster_exit_local、wire_tangent_local、ferrule_mouth_display_local、wire_z，以及原有stroke/radius_finger/origin/bases/wire_d。兼容 radius_cable 不参与直拉收线或力臂。

trigger-rotate 行保留 origin/axis/stroke_mm，与 ci 校验一致；新行不得再携带 radians_per_t。清单必须同时包含随动扳机、终端盖、随动五金与输入/输出钢芯；盖缺失、设为fixed或禁用随动将显式失败。input-wire 行不得再携带 arc_rest_angle_deg / arc_end_angle_deg。缺失或未知motion_law、错误坐标基、超行程、无效反解域和导向弧越界均报错；不回退旧圆弧公式。

`triggerPose`、`rigidPose` 与 `inputCorePoints` 共用同一解。钢芯连续连接 B→T→固定导向弧→护套口，导向弧用最多0.1°分段。扳机、终端盖与移动五金必须使用相同trigger-rotate记录。co与送料凸轮/弹簧20mm时序不改；spin非stroke运动不消费扳机位移。

## 界面

终端盖新增为透明/剖切壳体，并与扳机共色，沿用原清单加载和显隐逻辑。运动文案改为“通过固定导向拉动送料滑架”；未加载时不再显示虚构12mm满行程占位。当前清单必须先通过契约和运动校验，才启用新场景标识。仍为一套scene graph，相机预置、零件列表、全部加载、按需加载、剖切、润滑和球路功能保留。

## 验证

`node --check web/cable-scene-kinematics.mjs` 与 `node --check web/feeder-motion.mjs` 通过。

`node output/cable-direct-pull-v2/web-review/test-kinematics.mjs` 通过10组测试：对原生SCAD断言已验证的401个位姿×3个调节器设置共1203次比较，角度最大差4.44e−14°，收线误差3.91e−14mm；钢芯折线路径长度最大偏差6.14e−7mm。满20mm行程角度19.3342519252°，手指近端位移11.9188276632mm。覆盖新盖/杆/五金同轴、世界近端方向、线长守恒、非法契约/域、原送料与spin行为。

测试目录的清单是旧84行历史清单加新运动参数和cap元数据的85行fixture，**不是当前v2真实模型导出**。未在浏览器或LAN发布后验收；后续根仍需生成真实85项新清单/网格并完成页面验证。`interface.diff` 给出三个文件的精确改动；`report.json` 保存测试源SHA及验收边界。
