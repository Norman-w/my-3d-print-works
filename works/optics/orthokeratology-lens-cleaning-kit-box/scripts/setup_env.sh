#!/usr/bin/env bash
# ===== 分区：常量/配置 =====
set -euo pipefail
project_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_root"

python3 --version
node --version
bash "$project_root/scripts/openscad.sh" --version
bash "$project_root/scripts/freecad.sh" --version

if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi
.venv/bin/pip install -r scripts/requirements-validation.txt

# ===== 分区：公开 API =====
.venv/bin/python -c "import numpy, trimesh, scipy, manifold3d; print('python validation deps ok')"
node --check web/app.js
node --check web/motion.js
.venv/bin/python scripts/test_part_physics.py
echo "CAD / FreeCAD / web toolchain is ready."
echo "Preview: python3 serve.py --host 0.0.0.0 --port 8766"
echo "Part simulation: .venv/bin/python scripts/simulate_by_parts.py"
