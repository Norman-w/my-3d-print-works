#!/usr/bin/env python3
"""FreeCAD GUI 入口：打开模型后用 QTimer 播蛇形选择，保持窗口不退出。"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import fc_snake_player as player

# ===== 分区：常量/配置 =====
# 真正的播放器在 fc_snake_player.SnakePlayer，用 QTimer，禁止 sleep 循环。

# ===== 分区：模型/类型 =====
# 无额外类型。

# ===== 分区：私有成员 =====
def _exe_name() -> str:
    return Path(sys.argv[0]).name.lower() if sys.argv else ""

def _is_freecadcmd() -> bool:
    name = _exe_name()
    return "freecadcmd" in name or name.endswith("cmd")

def _should_run() -> bool:
    if _is_freecadcmd():
        return False
    if __name__ in ("__main__", "freecad_snake_animate"):
        return True
    return "freecad" in _exe_name()

# ===== 分区：公开 API =====
def start() -> None:
    player.start()

# ===== 分区：业务逻辑 =====
if _should_run():
    player.schedule_when_gui_ready()
elif _is_freecadcmd():
    print("不要用 freecadcmd 播 GUI 动画（脚本结束拆窗口会 SIGSEGV）。请运行 ./scripts/run_freecad_snake_anim.sh")

# ===== 分区：方法/工具 =====
# 控制台手动开播：import fc_snake_player as p; p.start()
