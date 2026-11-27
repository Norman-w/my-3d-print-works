#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "$0")/.." && pwd)"

cd "$project_root"
bash -n scripts/build.sh scripts/render_previews.sh scripts/render_views.sh scripts/validate.sh
node --check web/app.js
node --check web/motion.js
python3 -m py_compile serve.py
.venv/bin/python scripts/test_part_physics.py
./scripts/build.sh

# The repository-local mechanical checker also writes per-STL topology reports.
.venv/bin/python scripts/check_mechanics.py
node --test scripts/test_motion.cjs

echo "All source, export, and STL topology checks passed."
