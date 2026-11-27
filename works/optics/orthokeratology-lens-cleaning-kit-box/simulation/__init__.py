# ===== 分区：导入/依赖 =====
"""Part-wise physical logic for the cleaning-kit assembly."""


# ===== 分区：公开 API =====
from simulation.part_models import simulate_catalog

__all__ = ["simulate_catalog"]
