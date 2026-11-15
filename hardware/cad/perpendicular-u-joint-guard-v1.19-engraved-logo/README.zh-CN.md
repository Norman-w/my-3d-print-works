# 围挡止转卡 v1.19 阴刻标识

基于 v1.18 横桥加固结构。X 为上管长度，Y 为下脚长度，Z 向上，单位毫米。
顶部 Norman@PingCloud 保持原位置与字号，改为从 Z=31 向内阴刻 0.6 mm。
其他结构、装配内腔、通孔及最底部1.5mm内扣保持原设计。

构建：`uv run --with numpy --with manifold3d python hardware/cad/perpendicular-u-joint-guard-v1.19-engraved-logo/build.py`
打印工程：`python hardware/cad/perpendicular-u-joint-guard-v1.19-engraved-logo/package.py`

成品 STL 位于 `../exports/perpendicular-u-joint-v1.19-engraved-logo/guard-v1.19.stl`。
单件3MF位于 `../print-packages/barrier-clip-v1.19-engraved-logo/`，X1C黑色PETG、6墙30%gyroid，自动树支撑。
3MF顶盖朝下（绕X旋转180度），为可编辑未切片工程；打印前在Bambu Studio切片检查支撑与首层。
最终STL封闭、单实体，尺寸55.8×77×54.5mm，无退化面/边界边/非流形边。
旧v1.18应力数据不等同于阴刻版重新求解结果；本次没有重新运行FEA。
