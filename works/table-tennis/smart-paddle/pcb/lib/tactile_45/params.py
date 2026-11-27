# ===== 分区：常量/配置 =====
"""4.5×4.5 mm SPST 轻触（与尾部电源键同规格；V3 测试键改 THT）。

几何与既有 SmartPaddle:SW_SPST_4.5x4.5 SMD 焊盘中心一致；
壳体槽见 enclosure/parameters.scad：button_pocket_w = 4.5 + 0.5。
"""

from __future__ import annotations

BODY_MM = 4.5
# 四脚：左右同号短接（1–1 / 2–2），中心距与原 SMD 封装一致
PAD_XY_MM = (
    ("1", -2.75, -1.70),
    ("1", 2.75, -1.70),
    ("2", 2.75, 1.70),
    ("2", -2.75, 1.70),
)
PAD_SIZE_MM = 1.6
DRILL_MM = 0.9
SILK_HALF_MM = 2.35
FAB_HALF_MM = 2.25
CRTYD_HALF_XY_MM = (3.40, 2.70)
