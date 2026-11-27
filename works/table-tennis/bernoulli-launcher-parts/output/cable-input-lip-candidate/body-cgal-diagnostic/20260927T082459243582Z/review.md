# 原样 body 的 CGAL / Manifold 对照

同一份冻结候选的 `cil_body()` 用 CGAL 导出后，通过本轮严格 STL 检查，可进入下一验证层。无需为这次 Manifold 导出残片修改机械尺寸、加入 epsilon 或手工删除三角形。这里没有做全机检查、切片或物理放行。

源文件 `output/cable-input-lip-candidate/candidate.scad` 的导出前、导出后、检查时 SHA-256 均为 `491ded77149a2147f010092f7f715f59ef50a2dd714abb56677d596fb6544c9d`；被 include 的 `cad/parameters.scad` 和旧 Manifold STL 也未变化。包装入口从旧任务原样复制，只调用 `cil_body()`，未改变 include、参数或网格分段。

| 检查 | 旧 Manifold | 原样 CGAL |
| --- | ---: | ---: |
| 三角形数 | 6448 | 5930 |
| 精确零面积面 | 0 | 0 |
| 边界边 | 0 | 0 |
| 非流形边 | 2 | 0 |
| 方向不一致的二面边 | 0 | 0 |
| 非环形顶点链 | 3 | 0 |
| 顶点连接分量 | 1 | 1 |
| 严格网格结果 | FAIL，保留原文件 | PASS |

边计数同时使用原始浮点坐标的精确同值键与 1e-6 mm 焊接键；前者也检出旧文件相同两条四面边。面积用导出 ASCII 数字的 `Fraction` 精确叉积检查，顶点链使用 1e-6 mm 坐标量化，分量使用既有 1e-7 mm 工具。原 Manifold 的 native `NoError` 不能代替这些检查。

两条异常边位于局部 `x=-45,z=-4`，Y 区间分别为 `58.0987992502..61.9012007498` 与 `61.9012007498..70`。它们共享面 1224、2801：三个顶点完全相同，绕序相反；局部几乎共线，每面双精度面积约 `2.13e-14 mm²`。导出十进制数使其精确面积仍非零，故单做零面积检查会漏掉。报告保存所有相邻面的 CAD / 局部坐标和法向。

CGAL 没有上述边与顶点链问题。两后端体积差为 `-0.0116228324 mm³`，相对 `-4.35449e-8`；包围盒端点最大偏差 `3.79573e-6 mm`。这些结果支持后端共面三角化残片的诊断，没有证据要求改动此处机械连接；未把不同三角化的整套面逐一对应。

证据均在本目录：`invocation.json`、`body.scad`、`body-cgal.log`、`body-cgal.stl`、`report.json`、可复跑的 `inspect_comparison.py`。新 CGAL STL SHA-256 为 `5716489739fbd429304b73669b7becd7ee2627ff7dcd22cf5cfb493fc6ab811f`。旧 Manifold 文件仍为 `runs/20260927T081924133477Z-491ded7714/body.stl`，SHA-256 为 `cbb5e34df230744c11de77599e96c3a28f446c0b67bc9918b0fd4f2de506d8e2`。

PASS 只覆盖这个静态网格。配合公差、局部打印路径、PETG 强度、钢丝摩擦与耐久仍由各自后续证据判断。
