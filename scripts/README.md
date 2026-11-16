# SmartPaddle Scripts

本目录放与外壳生成、导出、分析相关的脚本。

## 常用脚本

- `bezier_to_openscad.py`  
  将 `web/src/data/userBezierProfiles.json` 转成 `enclosure/generated/*.scad`。

- `export-stl.sh`  
  用 OpenSCAD 导出 4 个打印件与 2 个组装件 STL。  
  优先使用 `/Applications/OpenSCAD.app` (Manifold 后端, ~400x 快于 CGAL)，  
  回退到 `openscad` (brew 安装的 CGAL 版本)。
- `export-lightboard-stl.sh`
  导出 `M7-LB1` 光板版的四层 STL、按真实手柄截面偏置生成的 TPU95A 独立拍柄把套、刚体拼板、arranged-model 3MF 和网页预览 manifest。
- `build_3mf_package.py`
  将拼板 manifest 中的独立 STL 与刚体位姿写入真实 3MF，不做隐式缩放；也支持 `--single-source` 生成单件 arranged-model 3MF。

- `run-analyze.sh`  
  运行分析流程，生成截图与尺寸检查结果。

- `analyze_bezier_views.py`  
  基于贝塞尔设计数据生成 2D 轮廓核对图（非 STL 网格采样）。

- `analyze_stl_views.py`  
  对 STL 做正交视图与尺寸规则检查。

## 推荐执行顺序

```bash
# 1) 更新生成几何
python3 scripts/bezier_to_openscad.py

# 2) 导出 STL
./scripts/export-stl.sh

# M7-LB1 光板版：拍面实心、拍柄内腔
./scripts/export-lightboard-stl.sh

# 3) 分析截图与尺寸
./scripts/run-analyze.sh
```

## 说明

- `scripts/.venv-analyze/` 是分析脚本虚拟环境。
- `scripts/__pycache__/` 是 Python 缓存，可忽略。
