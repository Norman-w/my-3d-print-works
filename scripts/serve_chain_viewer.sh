#!/usr/bin/env bash
# ===== 分区：导入/依赖 =====
set -euo pipefail

# ===== 分区：常量/配置 =====
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PORT="${1:-4174}"

# ===== 分区：模型/类型 =====
# 静态预览服务，无数据模型。

# ===== 分区：私有成员 =====
# 无。

# ===== 分区：公开 API =====
cd "${PROJECT_ROOT}"
echo "CH1 03C 预览: http://127.0.0.1:${PORT}/chain-viewer.html"
python3 -m http.server "${PORT}" --directory web

# ===== 分区：业务逻辑 =====
# 只托管 web/，STL 由 export_ch1_03c_chain.sh 预先导出。

# ===== 分区：方法/工具 =====
# 端口可用第一个参数覆盖。
