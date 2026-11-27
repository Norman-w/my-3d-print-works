#!/usr/bin/env bash
set -euo pipefail

slug="${1:-}"
if [[ -z "$slug" || ! "$slug" =~ ^[a-z0-9][a-z0-9-]*$ ]]; then
  echo "usage: $0 <lowercase-slug>" >&2
  exit 2
fi

destination="works/$slug"
if [[ -e "$destination" ]]; then
  echo "already exists: $destination" >&2
  exit 1
fi

mkdir -p "$destination/src" "$destination/docs" "$destination/output/3d-print" "$destination/output/previews" "$destination/output/validation" "$destination/web" "$destination/scripts"
cp templates/work/README.md "$destination/README.md"
cp templates/work/src/README.md "$destination/src/README.md"
cp templates/work/docs/README.md "$destination/docs/README.md"

echo "created $destination"
