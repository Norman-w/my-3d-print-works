#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "→ 安装 Web 锁定依赖"
npm ci --prefix web

echo "→ 下载 Go 服务依赖"
(cd server && go mod download)

echo "→ 创建 STL/布尔几何环境"
python3 -m venv scripts/.venv-stl
scripts/.venv-stl/bin/python -m pip install --upgrade pip
scripts/.venv-stl/bin/python -m pip install --upgrade \
  manifold3d \
  mapbox-earcut \
  networkx \
  numpy \
  shapely \
  trimesh

echo "→ 创建 STL 分析环境"
python3 -m venv scripts/.venv-analyze
scripts/.venv-analyze/bin/python -m pip install --upgrade pip
scripts/.venv-analyze/bin/python -m pip install --upgrade \
  -r scripts/requirements-analyze.txt

echo "→ 生成当前贝塞尔 OpenSCAD 几何"
python3 scripts/bezier_to_openscad.py

echo "✓ SmartPaddle Cloud 环境依赖就绪"
