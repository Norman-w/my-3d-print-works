#!/usr/bin/env python3
"""在 FreeCAD GUI 事件循环里用 QTimer 播放蛇形选择，不阻塞、不退出进程。"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import json
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
_ROOT = _SCRIPTS.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from fc_snake_path import loop_pose
from fc_snake_parts import apply_mechanism

# ===== 分区：常量/配置 =====
DEFAULT_FCSTD = _ROOT / "build" / "SmartPartsDrawer.FCStd"
DEFAULT_ANIM = _ROOT / "build" / "snake_animation.json"
TICK_MS = 120
HIDE_PREFIXES = ("CabinetShell", "FrontWall", "BackWall", "SelectorGuide", "SelectorCarriage", "Fastener_Carriage")
GHOST_PREFIXES = ("DrawerBody", "DrawerGuide", "CabinetBase", "DrawerCoupler", "RowRail")
SHOT_PATH = _ROOT / "build" / "snake_view.png"
PAINT_ONCE = {
    "SelectorBelt_HTD3M9": (1.0, 0.45, 0.08),
    "SelectorDrivePulley_20T": (1.0, 0.55, 0.15),
    "SelectorIdler_20T_A": (0.12, 0.72, 0.95),
    "SelectorIdler_20T_B": (0.12, 0.72, 0.95),
    "SelectorFinger": (0.12, 0.92, 0.28),
    "MotorMA_Case": (0.28, 0.32, 0.36),
}

# ===== 分区：模型/类型 =====
class SnakePlayer:
    """闭带循环：拨叉夹在带子上，带轮按 θ=s/R 转。"""

    def __init__(self, doc, animation: dict):
        self.doc = doc
        self.animation = animation
        self.elapsed = 0.0
        self.last_label = ""
        self._timer = None

    def start(self) -> None:
        App, Gui, QtCore = _apps()
        _disable_qt_accessibility()
        _activate_model_view(Gui, self.doc)
        pose = loop_pose(self.animation, 0.0, float(self.animation.get("speedMmS") or 120.0))
        apply_mechanism(self.doc, App, self.animation, pose)
        self._prepare_view(Gui)
        self._timer = QtCore.QTimer()
        self._timer.timeout.connect(self._tick)
        self._timer.start(TICK_MS)
        try:
            Gui.getMainWindow()._snake_player = self
        except Exception:
            pass
        _heartbeat("START", 0.0, 0.0)
        _console("闭带循环：皮带节线贴 20T 节圆，绿色拨叉是固定夹具，正转周而复始。")

    def stop(self) -> None:
        if self._timer is not None:
            self._timer.stop()

    def _tick(self) -> None:
        try:
            self._tick_impl()
        except Exception as exc:
            _console(f"动画帧失败: {exc}")
            _heartbeat(f"ERR {type(exc).__name__}", self.elapsed, 0.0)

    def _tick_impl(self) -> None:
        App, _, _ = _apps()
        speed = float(self.animation.get("speedMmS") or 120.0)
        pose = loop_pose(self.animation, self.elapsed, speed)
        apply_mechanism(self.doc, App, self.animation, pose)
        _heartbeat(pose["phaseLabel"], self.elapsed, pose["distance"])
        rpm = pose["timeline"]["rpm"]
        length = float(pose.get("loopLength") or self.animation.get("loopLength") or 0.0)
        if int(self.elapsed * 2) != int((self.elapsed - TICK_MS / 1000.0) * 2):
            _status(None, f"LOOP  s={pose['distance']:.0f}/{length:.0f}mm  n={rpm:.0f}rpm")
        self.elapsed += TICK_MS / 1000.0

    def _prepare_view(self, Gui) -> None:
        for obj in self.doc.Objects:
            vo = getattr(obj, "ViewObject", None)
            if vo is None:
                continue
            name = obj.Name or ""
            if name.startswith(HIDE_PREFIXES):
                vo.Visibility = False
                continue
            if name.startswith(GHOST_PREFIXES):
                vo.Visibility = True
                vo.Transparency = 70
                continue
            if name.startswith("DrawerFront"):
                vo.Visibility = True
                vo.Transparency = 20
                continue
            if name.startswith(("MotorA_", "BusShaft", "RowShaft", "RowGear", "Takeoff", "DriveBelt")):
                vo.Transparency = 55
                continue
            if name.startswith("SelectorFinger"):
                vo.ShapeColor = (0.12, 0.92, 0.28)
                vo.Visibility = True
                continue
            color = PAINT_ONCE.get(name)
            if color is not None:
                vo.Visibility = True
                vo.Transparency = 0
                try:
                    vo.ShapeColor = color
                    vo.LineWidth = 2.0
                except Exception:
                    pass
        try:
            view = Gui.getDocument(self.doc.Name).ActiveView
            if hasattr(view, "viewIsometric"):
                view.viewIsometric()
            if hasattr(view, "fitAll"):
                view.fitAll()
            if hasattr(view, "saveImage"):
                view.saveImage(str(SHOT_PATH), 1600, 900, "Current", "White")
        except Exception as exc:
            _console(f"视图适配跳过: {exc}")

# ===== 分区：私有成员 =====
_PLAYER = None
_STARTER = None

def _apps():
    import FreeCAD as App  # type: ignore
    import FreeCADGui as Gui  # type: ignore
    try:
        from PySide6 import QtCore  # type: ignore
    except ImportError:
        from PySide2 import QtCore  # type: ignore
    return App, Gui, QtCore

def _disable_qt_accessibility() -> None:
    try:
        from PySide6.QtGui import QAccessible  # type: ignore
    except ImportError:
        try:
            from PySide2.QtGui import QAccessible  # type: ignore
        except ImportError:
            return
    try:
        QAccessible.setActive(False)
    except Exception:
        pass

def _console(message: str) -> None:
    try:
        import FreeCAD as App  # type: ignore

        App.Console.PrintMessage(message + "\n")
    except Exception:
        print(message, flush=True)

def _activate_model_view(Gui, doc) -> None:
    try:
        Gui.ActiveDocument = Gui.getDocument(doc.Name)
    except Exception:
        return
    try:
        from PySide6.QtWidgets import QMdiArea  # type: ignore
    except ImportError:
        try:
            from PySide2.QtWidgets import QMdiArea  # type: ignore
        except ImportError:
            return
    try:
        mdi = Gui.getMainWindow().findChild(QMdiArea)
        if mdi is None:
            return
        for sub in mdi.subWindowList():
            title = sub.windowTitle() or ""
            if "SmartPartsDrawer" in title and not title.endswith(".py"):
                mdi.setActiveSubWindow(sub)
                break
    except Exception:
        pass

def _status(Gui, message: str) -> None:
    try:
        import FreeCADGui as RealGui  # type: ignore

        RealGui.getMainWindow().statusBar().showMessage(message, 8000)
    except Exception:
        _console(message)

def _heartbeat(phase: str, elapsed: float, distance: float) -> None:
    try:
        path = _ROOT / "build" / "snake_anim_heartbeat.txt"
        path.write_text(f"{elapsed:.2f}\t{distance:.1f}\t{phase}\n", encoding="utf-8")
    except Exception:
        pass

def _load_animation(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fp:
        return json.load(fp)

def _find_model_doc(App, fcstd: Path):
    for doc in list(App.listDocuments().values()):
        blob = f"{doc.FileName or ''} {doc.Name}"
        if "SmartPartsDrawer" in blob:
            return doc
    if fcstd.exists():
        return App.openDocument(str(fcstd))
    return None

def _gui_view_ready(Gui, doc) -> bool:
    if doc is None:
        return False
    try:
        gdoc = Gui.getDocument(doc.Name)
        return gdoc is not None and gdoc.ActiveView is not None
    except Exception:
        return False

# ===== 分区：公开 API =====
def start(fcstd: Path = DEFAULT_FCSTD, anim_path: Path = DEFAULT_ANIM) -> None:
    global _PLAYER
    App, Gui, _ = _apps()
    if not anim_path.exists():
        raise FileNotFoundError(f"缺少动画清单: {anim_path}")
    doc = _find_model_doc(App, fcstd)
    if doc is None:
        raise RuntimeError(f"打不开模型: {fcstd}")
    App.setActiveDocument(doc.Name)
    try:
        Gui.ActiveDocument = Gui.getDocument(doc.Name)
    except Exception:
        pass
    if not _gui_view_ready(Gui, doc):
        raise RuntimeError("FreeCAD 3D 视图尚未就绪")
    animation = _load_animation(anim_path)
    if _PLAYER is not None:
        _PLAYER.stop()
    _PLAYER = SnakePlayer(doc, animation)
    _PLAYER.start()

def schedule_when_gui_ready(fcstd: Path = DEFAULT_FCSTD, anim_path: Path = DEFAULT_ANIM, attempt: int = 0) -> None:
    global _STARTER
    App, Gui, QtCore = _apps()
    doc = _find_model_doc(App, fcstd)
    if doc is not None:
        App.setActiveDocument(doc.Name)
        try:
            Gui.ActiveDocument = Gui.getDocument(doc.Name)
        except Exception:
            pass
        try:
            if "Start" in App.listDocuments():
                App.closeDocument("Start")
        except Exception:
            pass
    if _gui_view_ready(Gui, doc):
        start(fcstd, anim_path)
        return
    if attempt > 120:
        _console("等待 3D 视图超时。请点选 SmartPartsDrawer 三维窗口，再执行: import fc_snake_player as p; p.start()")
        return
    _STARTER = QtCore.QTimer()
    _STARTER.setSingleShot(True)
    _STARTER.timeout.connect(lambda: schedule_when_gui_ready(fcstd, anim_path, attempt + 1))
    _STARTER.start(250)

# ===== 分区：业务逻辑 =====
# 本模块被 import 时不自动播放。

# ===== 分区：方法/工具 =====
if __name__ == "__main__" or (Path(sys.argv[0]).name.lower().startswith("fc_snake_player") if sys.argv else False):
    schedule_when_gui_ready()
