#!/usr/bin/env python3
"""已废弃：勿再裁尾/清螺丝柱。

错误根因：旧管线用 Z 向圆柱清 M4 螺丝柱，会把拍柄挖出错误空洞。

正确流程：
  ./scripts/export-stl.sh
  → OpenSCAD 导出完整拍子
  → Step6 用 pcb-tail Edge.Cuts + USB/按钮/LED 干涉已导出拍柄
  → 最终件写入 enclosure/stl/
"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import sys


# ===== 分区：公开 API =====
def main() -> int:
    print(
        "build-m5-from-real-handle.py 已废弃（不再清螺丝柱/裁独立 m5 尾段）。\n"
        "请运行：./scripts/export-stl.sh\n"
        "（若存在 pcb-tail，会自动跑 Step6 干涉并覆盖最终 STL）",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
