#!/usr/bin/env bash
# Safe atopile build: never leave a mutated PCB behind.
# Usage: pcb/scripts/ato_build_safe.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PCB="$ROOT/pcb/layouts/default/default.kicad_pcb"
ATO="${ATO:-$HOME/.local/share/uv/tools/atopile/bin/ato}"
TEMP_DIR="$(mktemp -d -t smartpaddle-ato-safe.XXXXXX)"
BAK="$TEMP_DIR/default.kicad_pcb"
BUILD_LOG="$TEMP_DIR/ato-build.log"
cp -a "$PCB" "$BAK"
cleanup() {
    cp -a "$BAK" "$PCB"
    rm -f "$BAK" "$BUILD_LOG"
    rmdir "$TEMP_DIR"
}
trap cleanup EXIT
if ! test -x "$ATO"; then
    echo "atopile executable missing: $ATO" >&2
    exit 1
fi
ATO_VERSION="$("$ATO" --version)"
echo "atopile executable: $ATO"
echo "atopile actual version: $ATO_VERSION"
if [[ "$ATO_VERSION" != *"0.12.5"* ]]; then
    echo "version mismatch: pcb/ato.yaml requires 0.12.5" >&2
    exit 1
fi
cd "$ROOT/pcb"
if ! "$ATO" build "$@" 2>&1 | tee "$BUILD_LOG"; then
    echo "ato build command failed" >&2
    exit 1
fi
# atopile 0.12.5 can report a build-stopping decode error while returning 0.
if ! grep -q "Build successful" "$BUILD_LOG"; then
    echo "ato build did not print its success marker" >&2
    exit 1
fi
echo "ato build OK; PCB restored from pre-build backup (layout/net ECO preserved)."
