# ===== 分区：导入/依赖 =====
from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

_BOOT_ENV = os.environ.get("PROJECT_ROOT")
_BOOT_HERE = Path(__file__).resolve() if "__file__" in globals() else Path.cwd()
_BOOT_CANDIDATES = []
if _BOOT_ENV:
    _BOOT_CANDIDATES.append(Path(_BOOT_ENV))
_BOOT_CANDIDATES.extend([_BOOT_HERE.parent, *list(_BOOT_HERE.parents)[:3]])
ROOT = next(path for path in _BOOT_CANDIDATES if (path / "parts" / "catalog.json").exists())
os.environ["PROJECT_ROOT"] = str(ROOT)
if str(ROOT / "cad") not in sys.path:
    sys.path.insert(0, str(ROOT / "cad"))

import FreeCAD as App
import FreeCADGui as Gui
from build_parts_freecad import build_parts

try:
    from PySide6 import QtCore
except ImportError:
    from PySide import QtCore


# ===== 分区：常量/配置 =====
PINION_ID = "pinion_m05_z8"
WHEEL_ID = "spur_m05_z40"
MOTOR_ID = "motor_n20"
PINION_TEETH = 8
WHEEL_TEETH = 40
PINION_ORIGIN = App.Vector(0, 0, -12)
WHEEL_ORIGIN = App.Vector(0, 0, 0)
AXIS = App.Vector(1, 0, 0)
STEP_DEG = 5.0
TIMER_MS = 40
FRAME_LIMIT = 8
FRAME_EVERY = 4
COLORS = {
    MOTOR_ID: (0.20, 0.62, 0.86),
    PINION_ID: (0.22, 0.78, 0.35),
    WHEEL_ID: (0.96, 0.67, 0.16),
    "screw_m2x8_a": (0.72, 0.78, 0.86),
    "screw_m2x8_b": (0.72, 0.78, 0.86),
}


# ===== 分区：模型/类型 =====
class GearTrainAnimator:
    def __init__(self, pinion, wheel) -> None:
        self.pinion = pinion
        self.wheel = wheel
        self.angle_deg = 0.0
        self.frame_index = 0
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.step)

    def start(self) -> None:
        self.timer.start(TIMER_MS)

    def step(self) -> None:
        self.angle_deg = (self.angle_deg + STEP_DEG) % 360.0
        self.pinion.Placement = App.Placement(PINION_ORIGIN, App.Rotation(AXIS, self.angle_deg))
        self.wheel.Placement = App.Placement(
            WHEEL_ORIGIN,
            App.Rotation(AXIS, wheel_angle_deg(self.angle_deg)),
        )
        if Gui.ActiveDocument is not None:
            Gui.updateGui()
        _maybe_save_frame(self.frame_index)
        self.frame_index += 1


# ===== 分区：私有成员 =====
_ANIMATOR = None
_START_TIMER = None
LOG_PATH = ROOT / "output" / "simulation" / "freecad-animation.log"
FRAME_DIR = ROOT / "output" / "simulation" / "freecad-frames"


def _log(message: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(message.rstrip() + "\n")
    App.Console.PrintMessage(message.rstrip() + "\n")


def _color_parts(doc) -> None:
    for name, color in COLORS.items():
        obj = doc.getObject(name)
        if obj is not None and getattr(obj, "ViewObject", None) is not None:
            obj.ViewObject.ShapeColor = color
            obj.ViewObject.LineColor = (0.05, 0.08, 0.12)


def _active_view():
    gui_doc = Gui.ActiveDocument
    if gui_doc is None:
        return None
    return gui_doc.activeView()


def _setup_view() -> None:
    Gui.activateWorkbench("PartWorkbench")
    view = _active_view()
    if view is None:
        raise RuntimeError("FreeCAD 三维视图还没准备好。")
    view.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    if hasattr(view, "setAnimationEnabled"):
        view.setAnimationEnabled(True)


def _maybe_save_frame(frame_index: int) -> None:
    if frame_index >= FRAME_LIMIT * FRAME_EVERY:
        return
    if frame_index % FRAME_EVERY != 0:
        return
    view = _active_view()
    if view is None or not hasattr(view, "saveImage"):
        return
    FRAME_DIR.mkdir(parents=True, exist_ok=True)
    path = FRAME_DIR / f"frame_{frame_index:03d}.png"
    view.saveImage(str(path), 1280, 720, "Current")
    _log(f"saved-frame {path.name}")


def _safe_start(attempt: int = 0) -> None:
    try:
        start_animation()
    except RuntimeError as exc:
        if "三维视图还没准备好" in str(exc) and attempt < 25:
            _log(f"retry-view {attempt}")
            QtCore.QTimer.singleShot(200, lambda: _safe_start(attempt + 1))
            return
        text = traceback.format_exc()
        _log(text)
        App.Console.PrintError(text + "\n")
    except Exception:
        text = traceback.format_exc()
        _log(text)
        App.Console.PrintError(text + "\n")


# ===== 分区：公开 API =====
def start_animation() -> None:
    global _ANIMATOR
    _log("starting")
    existing = App.listDocuments()
    if "CotsDrive" in existing:
        App.closeDocument("CotsDrive")
    result = build_parts()
    doc = App.getDocument("CotsDrive")
    Gui.getDocument(doc.Name)
    Gui.setActiveDocument(doc.Name)
    _color_parts(doc)
    _setup_view()
    pinion = doc.getObject(PINION_ID)
    wheel = doc.getObject(WHEEL_ID)
    if pinion is None or wheel is None:
        raise RuntimeError("装配里找不到齿轮，无法播放传动动画。")
    _ANIMATOR = GearTrainAnimator(pinion, wheel)
    _ANIMATOR.start()
    _log(
        "FreeCAD 传动动画已开始：绿色小齿轮快转，黄色大齿轮按 5:1 反向慢转。电机和螺钉固定。"
    )
    _log(f"STEP 装配：{result['assembly']}")
    try:
        Gui.getMainWindow().statusBar().showMessage(
            "COTS drive animation running: green pinion 5:1 yellow wheel",
            0,
        )
    except Exception as exc:
        _log(f"status-bar skipped: {type(exc).__name__}: {exc}")


# ===== 分区：业务逻辑 =====
def wheel_angle_deg(pinion_angle_deg: float) -> float:
    return -pinion_angle_deg * PINION_TEETH / WHEEL_TEETH


# ===== 分区：方法/工具 =====
def schedule_animation() -> None:
    global _START_TIMER
    _START_TIMER = QtCore.QTimer()
    _START_TIMER.setSingleShot(True)
    _START_TIMER.timeout.connect(_safe_start)
    _START_TIMER.start(800)
    _log("scheduled")


schedule_animation()
