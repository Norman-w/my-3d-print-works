"""KiCad 机械几何共享模块。

本文件中的坐标为 KiCad 板编辑器坐标（毫米），除非变量名显式标注 SCAD。
KiCad 的 Y 轴正方向为板编辑器中的"下"方向（拍柄方向），
SCAD 的 Y 轴正方向为"上"方向（拍头方向），两者通过 slot_scad_to_kicad() 互转。

所有 SCAD 衍生值（螺丝孔、PZT 腔体、大陆区矩形、槽点轮廓）在导入时
从 enclosure/*.scad 文件解析，修改 SCAD 参数后 Python 管线自动同步。
"""

from __future__ import annotations

import math
import re
from pathlib import Path

# ===== 分区：SCAD 参数解析 =====

_ROOT = Path(__file__).resolve().parents[2]


def _eval_scad_term(text: str, ctx: dict[str, object]) -> object:
    """求值单个 SCAD 表达式：纯数字、向量 [x, y]、或嵌套向量列表 [[x,y],...]"""
    text = text.strip()

    # 嵌套列表：[[...], [...], ...]
    if text.startswith("["):
        # 找到匹配的闭合括号
        depth = 0
        end = 0
        for i, ch in enumerate(text):
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break

        inner = text[1 : end - 1].strip()
        if inner.startswith("["):
            # 向量列表（如 screw_positions）
            items = _split_top_level_commas(inner)
            return tuple(_eval_scad_term(it, ctx) for it in items)
        elif "," in inner:
            # 单个向量 [x, y] 或 [x, y, z]
            parts = [p.strip() for p in inner.split(",")]
            return tuple(_safe_eval(p, ctx) for p in parts if p)

    # 标量表达式（数字，可能含四则运算）
    return _safe_eval(text, ctx)


def _safe_eval(expr: str, ctx: dict[str, object]) -> float:
    """在给定上下文中求值数值表达式，失败返回 0.0"""
    try:
        return eval(expr, {}, ctx)
    except Exception:
        return 0.0


def _split_top_level_commas(text: str) -> list[str]:
    """按顶层逗号拆分文本，尊重括号嵌套深度"""
    items: list[str] = []
    depth = 0
    current: list[str] = []
    for ch in text:
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
        if ch == "," and depth == 0:
            items.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        items.append("".join(current).strip())
    return items


def _parse_scad_file(path: Path) -> dict[str, object]:
    """从 SCAD 文件中提取顶层变量赋值。

    支持数字、向量 ([x, y])、向量嵌套列表 ([[x0,y0], ...])。
    行注释 (//) 在解析前被剥离。
    多行数组被折叠为单行形式后匹配。
    """
    text = path.read_text(encoding="utf-8")
    # 删除行注释
    clean = re.sub(r"//.*$", "", text, flags=re.MULTILINE)
    # 折叠空白使多行数组变为单行
    collapsed = re.sub(r"\s+", " ", clean).strip()

    result: dict[str, object] = {}
    # 匹配: 变量名 = 值; （非贪婪，在第一个 ; 处停止）
    for m in re.finditer(r"(\w+)\s*=\s*(.+?);", collapsed):
        name = m.group(1)
        expr = m.group(2).strip()
        try:
            value = _eval_scad_term(expr, result)
            if value is not None:
                result[name] = value
        except Exception:
            pass

    return result


# 先解析 paddle_shell.scad（获取 PCB 槽点轮廓），
# 再解析 parameters.scad（获取尺寸和几何参数），
# 合并顺序保证 parameters.scad 在同名变量上优先生效。
_PARAMS = _parse_scad_file(_ROOT / "enclosure" / "parameters.scad")
_SHELL_PARAMS = _parse_scad_file(_ROOT / "enclosure" / "paddle_shell.scad")
_PARAMS = {**_SHELL_PARAMS, **_PARAMS}

# ===== 分区：常量/配置 =====

# --- 坐标系转换 ---

# KiCad/SCAD Y 轴握手锚点：SCAD 拍头椭圆圆心映射到 KiCad 板原点 (0,0)
# 来自 parameters.scad: blade_ellipse_cy = -10
# 公式: y_kicad = -y_scad + SCAD_TO_KICAD_Y_OFFSET
SCAD_TO_KICAD_Y_OFFSET = float(_PARAMS.get("blade_ellipse_cy", -10.0))  # type: ignore[arg-type]

# --- 手柄接合线（来自 SCAD，用于推导 PCB 尾端截断） ---

# handle_join_y: 拍头-拍柄接合处 SCAD Y 坐标（parameters.scad，默认 -78.5）
_handle_join_y_scad = float(_PARAMS.get("handle_join_y", -78.5))  # type: ignore[arg-type]
# 转换为 KiCad Y: y_kicad = -y_scad + offset
_HANDLE_JOIN_KICAD_Y = -_handle_join_y_scad + SCAD_TO_KICAD_Y_OFFSET

# --- PCB 基材外形参数 ---

# PCB 边缘相对于 SCAD 槽点参考线的平行内缩量（mm）
# 值越小 PCB 越贴近外壳壁，越大则越保守
SUBSTRATE_EDGE_CLEARANCE = 0.30

# PCB 尾端向手柄空腔内的延伸量（mm）。
# 从拍头-拍柄接合线再向手柄方向延伸此距离后截断。
# 9.5mm：留出一个螺丝让位孔的深度，同时给电池导线预留出口空间。
_TAIL_EXTEND_INTO_HANDLE = 9.5

# PCB 尾端截断线 KiCad Y 坐标 — 从 SCAD handle_join_y 推导
SUBSTRATE_TAIL_MAX_Y = _HANDLE_JOIN_KICAD_Y + _TAIL_EXTEND_INTO_HANDLE

# PCB 轮廓边的采样步长（mm），用于在边上插入中间点以平滑 PZT 避让过渡
SUBSTRATE_EDGE_SAMPLE = 1.0

# --- PZT 码头避让参数 ---

# PZT 压电片腔体与 PCB 码头之间的最小径向间隙（mm）
PZT_CAVITY_CLEARANCE = 0.32

# 码头触碰 PZT 禁区时的回退触发带宽度（mm）
# 码头点到腔体中心的距离 < radius + CLEARANCE + BAND 时触发回退
PZT_DOCK_RETREAT_BAND = 4.0

# 码头点回退的初始步进量（mm），沿码头→大陆区方向一次性后撤
PZT_DOCK_RETREAT_STEP = 3.0

# --- SCAD 衍生几何（全部从 SCAD 文件解析，附带合理回退值） ---

# PZT 压电片腔体 — 圆心坐标和半径均来自 SCAD
# piezo_disc_d: 压电片直径（mm），/2 得半径
_pzt_radius = float(_PARAMS.get("piezo_disc_d", 20.5)) / 2  # type: ignore[arg-type]
# piezo_positions: 四角压电片中心 SCAD 坐标
PZT_CAVITIES_SCAD = [
    (float(p[0]), float(p[1]), _pzt_radius)  # type: ignore[index]
    for p in _PARAMS.get("piezo_positions", [])  # type: ignore[union-attr]
]

# 螺丝孔 — screw_d_boss 决定让位半径，screw_positions 给出中心坐标
# screw_d_boss: 螺丝柱外径（mm），/2 得柱半径
_screw_boss_d = float(_PARAMS.get("screw_d_boss", 5.5))  # type: ignore[arg-type]
# 螺丝柱外半径 + 额外间隙 — 防止 PCB 孔边缘与螺丝柱壁干涉
_SCREW_EXTRA_CLEARANCE = 0.75
SCREW_CLEARANCE_RADIUS = _screw_boss_d / 2.0 + _SCREW_EXTRA_CLEARANCE
SCREW_HOLES_SCAD = [
    (float(p[0]), float(p[1]))  # type: ignore[index]
    for p in _PARAMS.get("screw_positions", [])  # type: ignore[union-attr]
]

# 大陆区矩形 — KiCad 坐标 (x_center, y_center, width, height)
# pcb_cavity_center: SCAD 槽体中心 [X, Y]
# pcb_cavity_size:   SCAD 槽体尺寸 [宽, 高]
# Y 轴转换: y_kicad = -(scad_y) + SCAD_TO_KICAD_Y_OFFSET
_cav_center = _PARAMS.get("pcb_cavity_center", (0, -1))  # type: ignore
_cav_size = _PARAMS.get("pcb_cavity_size", (42, 50))  # type: ignore
_KICAD_MAINLAND_CENTER_Y = -float(_cav_center[1]) + SCAD_TO_KICAD_Y_OFFSET  # type: ignore[index]
MAINLAND_RECT = (
    float(_cav_center[0]),  # type: ignore[index]
    _KICAD_MAINLAND_CENTER_Y,
    float(_cav_size[0]),  # type: ignore[index]
    float(_cav_size[1]),  # type: ignore[index]
)


def slot_scad_to_kicad(point: tuple[float, float]) -> tuple[float, float]:
    """将 SCAD 槽坐标转换为 KiCad 机械参考坐标系。

    SCAD: +Y=↑(拍头方向)     KiCad: +Y=↓(拍柄方向)
    转换: y_kicad = -(y_scad) + SCAD_TO_KICAD_Y_OFFSET
    """
    x, y = point
    return (x, -y + SCAD_TO_KICAD_Y_OFFSET)


# 拍形外轮廓槽点 — 从 paddle_shell.scad 的 rigid_pcb_slot_points 解析。
# 该多边形定义了 PCB 在球拍壳体中的最大投影轮廓（38 个顶点）。
# SCAD 中用 polygon(points=rigid_pcb_slot_points) 驱动腔体切割，
# KiCad 中用同一组点（经 slot_scad_to_kicad 转换）绘制参考线和 Edge.Cuts。
# 两边共享同一个数据源，修改 paddle_shell.scad 即可同步。
_shell_pts = _PARAMS.get("rigid_pcb_slot_points")
if _shell_pts is not None and len(_shell_pts) > 0:  # type: ignore[arg-type]
    SCAD_SLOT_POINTS = [
        (float(p[0]), float(p[1]))  # type: ignore[index]
        for p in _shell_pts  # type: ignore[union-attr]
    ]
else:
    # 回退：与 paddle_shell.scad 中当前值一致（2026-06-15）
    SCAD_SLOT_POINTS = [
        (9.00, -108.00), (-9.00, -108.00), (-9.00, -26.00),
        (-16.75, -26.00), (-29.99, -40.11), (-28.24, -41.75),
        (-35.08, -49.05), (-41.65, -42.90), (-34.81, -35.60),
        (-33.06, -37.24), (-21.00, -24.39), (-21.00, 16.00),
        (-19.48, 16.00), (-29.66, 35.62), (-31.62, 34.32),
        (-37.17, 42.64), (-29.68, 47.63), (-24.13, 39.31),
        (-26.15, 37.97), (-14.75, 16.00), (14.75, 16.00),
        (26.15, 37.97), (24.13, 39.31), (29.68, 47.63),
        (37.17, 42.64), (31.62, 34.32), (29.66, 35.62),
        (19.48, 16.00), (21.00, 16.00), (21.00, -24.39),
        (33.06, -37.24), (34.81, -35.60), (41.65, -42.90),
        (35.08, -49.05), (28.24, -41.75), (29.99, -40.11),
        (16.75, -26.00), (9.00, -26.00),
    ]

# ===== 分区：几何工具函数 =====


def _embedded_substrate_scad_points() -> list[tuple[float, float]]:
    """从 SCAD 槽参考线派生 PCB 基材轮廓（SCAD 坐标系）。

    保持码头/栈道/大陆区顶点与 SCAD 槽一致，确保 PCB 不会飘出黑色参考框。
    仅缩短拍柄尾端 — 刚性 PCB 应止于手柄空腔内部。

    截断 Y = handle_join_y - _TAIL_EXTEND_INTO_HANDLE
    原尾端为 Y=-108（延伸到手柄底部），截断后尾端上移到手柄空腔内。
    """
    points = list(SCAD_SLOT_POINTS)
    # 拍柄尾端截断：首尾两个点（SCAD 索引 0,1）的 Y 坐标截断到接合线以上
    _tail_y_scad = _handle_join_y_scad - _TAIL_EXTEND_INTO_HANDLE
    points[0] = (points[0][0], _tail_y_scad)
    points[1] = (points[1][0], _tail_y_scad)
    return points


def _polygon_points(poly) -> list[tuple[float, float]]:
    """将多边形顶点四舍五入到 3 位小数"""
    return [(round(x, 3), round(y, 3)) for x, y in poly]


def _signed_area(points: list[tuple[float, float]]) -> float:
    """计算多边形有向面积 — 正值=CCW(逆时针)，负值=CW(顺时针)"""
    area = 0.0
    for (ax, ay), (bx, by) in zip(points, points[1:] + points[:1]):
        area += ax * by - bx * ay
    return area / 2.0


def _line_intersection(
    a1: tuple[float, float],
    a2: tuple[float, float],
    b1: tuple[float, float],
    b2: tuple[float, float],
) -> tuple[float, float] | None:
    """计算两条线段的交点，平行时返回 None。

    _FLOAT_EPSILON = 1e-9：小于此值视为平行/共线，防止浮点除零产生无穷大值。
    此值不依赖于任何几何参数，是 IEEE 754 双精度浮点的合理容差。
    """
    _FLOAT_EPSILON = 1e-9  # 浮点比较容差（纯算法保护，非几何参数）
    ax, ay = a1
    bx, by = a2
    cx, cy = b1
    dx, dy = b2
    adx, ady = bx - ax, by - ay
    bdx, bdy = dx - cx, dy - cy
    denom = adx * bdy - ady * bdx
    if abs(denom) < _FLOAT_EPSILON:
        return None
    t = ((cx - ax) * bdy - (cy - ay) * bdx) / denom
    return (ax + adx * t, ay + ady * t)


def _edge_inset_polygon(
    points: list[tuple[float, float]],
    distance: float,
) -> list[tuple[float, float]]:
    """将多边形的每条边沿其内法线方向平移 distance，取相邻平移边的交点形成内缩多边形。

    相比把所有顶点朝中心收缩，沿边法线平移能更好保持栈道/码头的长度。
    最少需要 3 个顶点（闭合多边形）。
    """
    if len(points) < 3:
        return points

    area = _signed_area(points)
    # 内法线方向 = 正向(CCW 面积>0) 取 +1，反向(CW) 取 -1
    inward_sign = 1.0 if area > 0 else -1.0
    offset_edges = []
    for a, b in zip(points, points[1:] + points[:1]):
        ax, ay = a
        bx, by = b
        dx, dy = bx - ax, by - ay
        # 边长度，零长边（退化为点）用 1.0 防除零
        length = math.hypot(dx, dy) or 1.0
        # 边单位法线 × 内法线符号 × 距离
        nx, ny = (-dy / length * inward_sign, dx / length * inward_sign)
        offset_edges.append(
            (
                (ax + nx * distance, ay + ny * distance),
                (bx + nx * distance, by + ny * distance),
            )
        )

    inset: list[tuple[float, float]] = []
    count = len(offset_edges)
    for i in range(count):
        prev_edge = offset_edges[i - 1]
        edge = offset_edges[i]
        intersection = _line_intersection(
            prev_edge[0], prev_edge[1], edge[0], edge[1]
        )
        if intersection is None:
            # 平行边：取相邻端点中点作为近似交点
            px = (prev_edge[1][0] + edge[0][0]) / 2
            py = (prev_edge[1][1] + edge[0][1]) / 2
            intersection = (px, py)
        inset.append(intersection)
    return inset


def _retreat_from_pzt(
    point: tuple[float, float],
    pzt: tuple[float, float, float],
    hub: tuple[float, float],
) -> tuple[float, float]:
    """将靠近 PZT 腔体的码头点沿"码头→大陆区"方向回退，直至脱离禁区。

    不向外扩张码头，而是向内缩短 — 确保 PCB 轮廓不闯入 PZT 安装空间。

    搜索参数：
    - _PZT_RETREAT_SEARCH_STEP = 0.10 mm/步
    - _PZT_RETREAT_MAX_STEPS = 100 步（= 最多回退 10mm）
    """
    px, py = point
    cx, cy, radius = pzt
    keepout = radius + PZT_CAVITY_CLEARANCE  # PZT 禁区半径 = 腔体半径 + 间隙
    distance = math.hypot(px - cx, py - cy)
    if distance >= keepout + PZT_DOCK_RETREAT_BAND:
        return point  # 远离禁区，无需回退

    hx, hy = hub
    dx, dy = hx - px, hy - py  # 指向大陆区中心的方向向量
    step_len = math.hypot(dx, dy) or 1.0  # 零长向量用 1.0 防除零（纯算法保护，非几何参数）
    ux, uy = dx / step_len, dy / step_len  # 单位方向向量

    # 初始大步回退（PZT_DOCK_RETREAT_STEP mm）
    initial_retreat = PZT_DOCK_RETREAT_STEP if distance >= keepout else 0.0
    px += ux * initial_retreat
    py += uy * initial_retreat

    # 细粒度逐步回退搜索
    _PZT_RETREAT_SEARCH_STEP = 0.10   # 每步前进 0.10mm（搜索精度/速度权衡，非几何参数）
    _PZT_RETREAT_MAX_STEPS = 100      # 最多 100 步 = 10mm（算法边界保护，非几何参数）
    for i in range(1, _PZT_RETREAT_MAX_STEPS):
        candidate = (px + ux * i * _PZT_RETREAT_SEARCH_STEP,
                     py + uy * i * _PZT_RETREAT_SEARCH_STEP)
        if math.hypot(candidate[0] - cx, candidate[1] - cy) >= keepout:
            return candidate
    return point  # 兜底：达到最大步数仍未脱离禁区，返回原始点


def _embedded_substrate_points() -> list[tuple[float, float]]:
    """生成最终的 PCB 基材轮廓顶点列表（KiCad 坐标）。

    流程：
    1. 从 SCAD 槽参考点出发 → 转换为 KiCad 坐标系
    2. 每条边沿内法线平行内缩 SUBSTRATE_EDGE_CLEARANCE
    3. 沿边采样（步长 SUBSTRATE_EDGE_SAMPLE）生成中间点
    4. 拍柄侧截断到 SUBSTRATE_TAIL_MAX_Y
    5. 靠近 PZT 腔体的码头点自动回退避让
    6. 合并距离 < 0.05mm 的重复点
    """
    hub = (MAINLAND_RECT[0], MAINLAND_RECT[1])
    pzt_keepouts = [
        (*slot_scad_to_kicad((cx, cy)), radius)
        for cx, cy, radius in PZT_CAVITIES_SCAD
    ]

    base_points = _edge_inset_polygon(
        [slot_scad_to_kicad(raw) for raw in _embedded_substrate_scad_points()],
        SUBSTRATE_EDGE_CLEARANCE,
    )

    points: list[tuple[float, float]] = []
    _POINT_MERGE_THRESHOLD = 0.05  # 去重距离阈值（mm，纯算法参数，非几何参数）
    for point_a, point_b in zip(base_points, base_points[1:] + base_points[:1]):
        ax, ay = point_a
        bx, by = point_b
        steps = max(
            1, math.ceil(math.hypot(bx - ax, by - ay) / SUBSTRATE_EDGE_SAMPLE)
        )
        for step in range(steps):
            t = step / steps
            point = (ax + (bx - ax) * t, ay + (by - ay) * t)
            # 拍柄端截断
            point = (point[0], min(point[1], SUBSTRATE_TAIL_MAX_Y))
            # PZT 码头回退
            for pzt in pzt_keepouts:
                point = _retreat_from_pzt(point, pzt, hub)
            # 距上一点 > _POINT_MERGE_THRESHOLD mm 才加入（去重）
            if (
                not points
                or math.hypot(
                    point[0] - points[-1][0], point[1] - points[-1][1]
                )
                > _POINT_MERGE_THRESHOLD
            ):
                points.append(point)

    return _polygon_points(points)


PCB_SLOT_POINTS = _embedded_substrate_points()

# ===== 分区：模块开孔与螺丝让位 =====

# 模块开孔相对于模块外形尺寸的单边装配间隙（mm）
# ESP32-C6-WROOM-1: 本体 25.5×18.0mm → 开孔 25.9×18.4mm
# ICM-948:          本体 18.5×13.0mm → 开孔 18.9×13.4mm
MODULE_CUTOUT_CLEARANCE = 0.20

# IMU 模块相对大陆区中心的 Y 轴偏移量（mm，负=拍头方向）。
# IMU 放在大陆区上半部靠近拍头侧。
_IMU_Y_OFFSET_FROM_MAINLAND_CENTER = -15.5

# MCU 模块相对大陆区中心的 Y 轴偏移量（mm，正=拍柄方向）。
# MCU 放在大陆区下半部靠近拍柄侧。
_MCU_Y_OFFSET_FROM_MAINLAND_CENTER = 11.5

# ESP32-C6-WROOM-1 MCU 模块开孔（KiCad 坐标: x_center, y_center, width, height）
# X 居中于大陆区中线（= PCB X 轴原点），Y 相对大陆区中心偏移
ESP32_CUTOUT = (
    0.0,                                                            # X 居中
    _KICAD_MAINLAND_CENTER_Y + _MCU_Y_OFFSET_FROM_MAINLAND_CENTER,  # Y = 大陆中心 + MCU 偏移
    25.5 + MODULE_CUTOUT_CLEARANCE * 2,                             # 宽 = 模块宽 + 双边间隙
    18.0 + MODULE_CUTOUT_CLEARANCE * 2,                             # 高 = 模块高 + 双边间隙
)

# ICM-948 IMU 模块开孔（KiCad 坐标: x_center, y_center, width, height）
# X 居中于大陆区中线，Y 相对大陆区中心偏移（负=拍头方向）
IMU_CUTOUT = (
    0.0,                                                             # X 居中
    _KICAD_MAINLAND_CENTER_Y + _IMU_Y_OFFSET_FROM_MAINLAND_CENTER,   # Y = 大陆中心 + IMU 偏移
    18.5 + MODULE_CUTOUT_CLEARANCE * 2,                              # 宽 = 模块宽 + 双边间隙
    13.0 + MODULE_CUTOUT_CLEARANCE * 2,                              # 高 = 模块高 + 双边间隙
)

# 参考线用全部 M2 螺丝孔（含板外的拍面螺丝，用于 Dwgs.User 可视对照）
# 每个元素: (kicad_x, kicad_y, clearance_radius)
M2_CLEARANCE_HOLES = [
    (*slot_scad_to_kicad((x, y)), SCREW_CLEARANCE_RADIUS)
    for x, y in SCREW_HOLES_SCAD
]

# 实际 PCB Edge.Cuts 上的螺丝让位孔 — 从 SCAD 螺丝列表中筛选穿过板体的螺丝。
# 筛选规则：SCAD X=0 且 Y 在大陆区下方（拍柄侧）的螺丝。
# 当前匹配到 SCAD 坐标 (0, -33) 的拍柄侧螺丝。
def _pcb_clearance_holes() -> list[tuple[float, float, float]]:
    """从 SCAD 螺丝列表中筛选穿过 PCB 板体的螺丝让位孔。"""
    holes: list[tuple[float, float, float]] = []
    for sx, sy in SCREW_HOLES_SCAD:
        if sx != 0.0:  # 只取中轴线 (X=0) 上的螺丝
            continue
        ki_x, ki_y = slot_scad_to_kicad((sx, sy))
        # 螺丝必须在大陆区下方（拍柄侧，KiCad Y > 大陆中心Y + 大陆半高 + 柱半径）
        if ki_y <= _KICAD_MAINLAND_CENTER_Y + MAINLAND_RECT[3] / 2 + SCREW_CLEARANCE_RADIUS:
            continue
        # 螺丝不得超过手柄接合线以下太远（避免进入手柄深处）
        if ki_y > SUBSTRATE_TAIL_MAX_Y:
            continue
        holes.append((ki_x, ki_y, SCREW_CLEARANCE_RADIUS))
    return holes

PCB_CLEARANCE_HOLES = _pcb_clearance_holes()
