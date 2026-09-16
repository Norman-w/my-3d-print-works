#!/usr/bin/env bash
# Resolve optional skill utilities without depending on one developer's home
# directory.  Callers may set the *_SKILL_DIR or individual *_PY variables.

# ===== 分区：导入/依赖 =====
# This file is sourced by the export/preview scripts; it must not enable
# `set -euo pipefail` or overwrite the caller's shell options.

# ===== 分区：常量/配置 =====
OPENSCAD_SKILL_ROOTS=()
STL_PREVIEW_SKILL_ROOTS=()

if [[ -n "${OPENSCAD_STL_PRINT_SKILL_DIR:-}" ]]; then
    OPENSCAD_SKILL_ROOTS+=("${OPENSCAD_STL_PRINT_SKILL_DIR}")
fi
if [[ -n "${STL_HTTP_PREVIEW_SKILL_DIR:-}" ]]; then
    STL_PREVIEW_SKILL_ROOTS+=("${STL_HTTP_PREVIEW_SKILL_DIR}")
fi
if [[ -n "${HOME:-}" ]]; then
    OPENSCAD_SKILL_ROOTS+=(
        "${HOME}/.codex/skills/openscad-stl-print"
        "${HOME}/.cursor/skills/openscad-stl-print"
        "${HOME}/.claude/skills/openscad-stl-print"
    )
    STL_PREVIEW_SKILL_ROOTS+=(
        "${HOME}/.codex/skills/stl-http-preview"
        "${HOME}/.cursor/skills/stl-http-preview"
        "${HOME}/.claude/skills/stl-http-preview"
    )
fi

# ===== 分区：私有成员 =====
first_existing_preview_file() {
    local relative_path="$1"
    shift
    local root candidate
    for root in "$@"; do
        [[ -n "${root}" ]] || continue
        candidate="${root}/${relative_path}"
        if [[ -f "${candidate}" ]]; then
            printf '%s\n' "${candidate}"
            return 0
        fi
    done
    return 1
}

# ===== 分区：公开 API =====
if [[ -z "${INSPECT_PY:-}" ]]; then
    INSPECT_PY="$(first_existing_preview_file \
        scripts/inspect_stl.py "${OPENSCAD_SKILL_ROOTS[@]}")" || INSPECT_PY=""
fi
if [[ -z "${MANIFEST_PY:-}" ]]; then
    MANIFEST_PY="$(first_existing_preview_file \
        scripts/write_preview_manifest.py "${STL_PREVIEW_SKILL_ROOTS[@]}")" || MANIFEST_PY=""
fi
if [[ -z "${PREVIEW_SH:-}" ]]; then
    PREVIEW_SH="$(first_existing_preview_file \
        scripts/preview_http.sh "${STL_PREVIEW_SKILL_ROOTS[@]}")" || PREVIEW_SH=""
fi
