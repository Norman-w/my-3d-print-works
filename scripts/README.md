# SmartPaddle Scripts

本目录放与外壳生成、导出、分析相关的脚本。

## 常用脚本

- `bezier_to_openscad.py`  
  将 `web/src/data/userBezierProfiles.json` 转成 `enclosure/generated/*.scad`。

- `export-stl.sh`  
  用 OpenSCAD 导出 4 个打印件与 2 个组装件 STL。

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

# 3) 分析截图与尺寸
./scripts/run-analyze.sh
```

## 说明

- `scripts/.venv-analyze/` 是分析脚本虚拟环境。
- `scripts/__pycache__/` 是 Python 缓存，可忽略。
