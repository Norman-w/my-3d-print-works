#!/usr/bin/env python3
# ===== 分区：导入/依赖 =====
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path


# ===== 分区：常量/配置 =====
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from parts.standard_parts import PartKind, PartsCatalog
from simulation.part_models import simulate_catalog


# ===== 分区：业务逻辑 =====
class PartPhysicsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = PartsCatalog.from_json_path()
        cls.report = simulate_catalog(cls.catalog)

    def test_catalog_is_common_parts_only(self) -> None:
        kinds = {part.kind for part in self.catalog.parts}
        self.assertEqual(kinds, {PartKind.DcMotor, PartKind.SpurGear, PartKind.MetricScrew})
        self.assertFalse(any("shell" in part.id for part in self.catalog.parts))

    def test_gear_module_and_center_distance(self) -> None:
        gears = [item for item in self.report["parts"] if item["kind"] == "SpurGear"]
        self.assertEqual(len(gears), 2)
        for gear in gears:
            self.assertTrue(gear["ok"], gear["notes"])
            self.assertAlmostEqual(gear["metrics"]["module_mm"], 0.5)
            self.assertAlmostEqual(gear["metrics"]["required_center_distance_mm"], 12.0)

    def test_drive_chain_without_shell_load(self) -> None:
        drive = self.report["drive"]
        self.assertAlmostEqual(drive["gear_ratio"], 5.0)
        self.assertAlmostEqual(drive["output_shaft_nm"], 0.05 * 5.0 * 0.85)
        self.assertAlmostEqual(drive["output_no_load_rpm"], 20.0)
        self.assertTrue(drive["screws_hold_stall"])
        self.assertNotIn("latch_tooth_nm", drive)

    def test_screws_are_steel_fasteners(self) -> None:
        screw = next(item for item in self.report["parts"] if item["kind"] == "MetricScrew")
        self.assertGreater(screw["metrics"]["shear_allow_n"], 20)
        self.assertGreater(screw["metrics"]["tensile_allow_n"], screw["metrics"]["design_clamp_n"])
        self.assertTrue(math.isfinite(screw["metrics"]["install_torque_nmm"]))
        self.assertTrue(self.report["ok"])


# ===== 分区：公开 API =====
if __name__ == "__main__":
    unittest.main()
