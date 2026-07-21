#!/bin/bash
# 使用. (source) 来加载环境变量
# 系统默认 python3 可能是 3.14，ESP-IDF 5.5 环境装在 py3.9；优先用 3.9 以匹配已安装的 venv
if [ -x /opt/homebrew/bin/python3.9 ]; then
    export PATH="/opt/homebrew/bin:$PATH"
    # 让 export.sh 的 "python3" 检测落到 3.9
    _idf_py_bin="$(mktemp -d)"
    ln -sf /opt/homebrew/bin/python3.9 "$_idf_py_bin/python3"
    export PATH="$_idf_py_bin:$PATH"
fi

. /Volumes/NormanData/sdk/esp-idf-v5.5.1/export.sh
echo "已加载ESP-IDF环境变量,可以使用idf.py进行build, flash, monitor等操作。"
echo "示例: idf.py -p /dev/cu.usbmodemXXXX build flash monitor"
cd "$(cd "$(dirname "$0")" && pwd)"
exec "$SHELL"
