# ===== 分区：导入/依赖 =====
"""Purchased and printed part catalog for the cleaning-kit assembly."""


# ===== 分区：公开 API =====
from parts.standard_parts import PartsCatalog, PartKind

__all__ = ["PartsCatalog", "PartKind"]
