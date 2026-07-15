#!/usr/bin/env bash
# Safe atopile build: never leave a mutated PCB behind.
# Usage: pcb/scripts/ato_build_safe.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PCB="$ROOT/pcb/layouts/default/default.kicad_pcb"
BAK="$(mktemp -t smartpaddle_pcb_XXXXXX).kicad_pcb"
cp -a "$PCB" "$BAK"
cleanup() { cp -a "$BAK" "$PCB"; rm -f "$BAK"; }
trap cleanup EXIT
cd "$ROOT/pcb"
ato build --keep-designators --keep-net-names "$@"
echo "ato build OK; PCB restored from pre-build backup (layout/net ECO preserved)."
