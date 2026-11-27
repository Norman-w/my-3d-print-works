#!/bin/sh
# Run from anywhere. Isolated output: never overwrite the v1.16 baseline.
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
CAD=$(CDPATH= cd -- "$HERE/../.." && pwd)
TASK_CASE="$HERE/v1.17"
export CASE_DIR="$TASK_CASE"
export MESH_COORD_DECIMALS="${MESH_COORD_DECIMALS:-2}" MESH_RATIO="${MESH_RATIO:-1.2}"
export SOURCE_STL="$CAD/exports/perpendicular-u-joint-v1.17-load-path/guard-v1.17-body.stl"
UV="${UV:-/Users/norman/.local/bin/uv}"
"$UV" run --with numpy --with manifold3d --with tetgen python "$HERE/tetrahedralize.py"
"$UV" run --with numpy python "$HERE/quality.py"
export MESH_DIR="$TASK_CASE" ASSEMBLY_DIR="$TASK_CASE/assembly"
export ASSEMBLY_STATIC="${ASSEMBLY_STATIC:-.1,1.,.000001,.25}"
"$UV" run --with numpy python "$HERE/build_assembly_contact.py"
cd "$ASSEMBLY_DIR"
OMP_NUM_THREADS=4 /Applications/FreeCAD.app/Contents/Resources/bin/ccx -i contact > solver.stdout.log 2>&1
export CASE_DIR="$ASSEMBLY_DIR" RESULT_DIR="$CAD/preview/guard-v117-results" MODEL_VERSION=1.17
"$UV" run --with numpy python "$HERE/export_results.py"
"$UV" run --with numpy python "$HERE/validate_assembly.py"
