"""Regression checks for support motion in X1C G-code manufacturing screens."""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from screen_electric_rocker_root_gusset_orientation import (  # noqa: E402
    support_in_shell_void_cores,
)
from screen_service_fork_base_orientation import supports_in_void_core  # noqa: E402
from slice_electric_rocker_service_fork import support_crossings  # noqa: E402


IDENTITY = [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0]
CENTER = [0, 0, 0]


class SupportPathClassificationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.gcode = Path(self.temp.name) / "probe.gcode"

    def write(self, start: str, actual_path: str = "") -> None:
        self.gcode.write_text(
            "; FEATURE: Support\n" + start + "\nG1 E.8 F1800\n" + actual_path)

    def test_prime_inside_joint_hole_does_not_count_as_support(self) -> None:
        self.write("G1 X15 Y65 Z2")
        box = {"joint_hole": [[14.5, 15.5], [64.5, 65.5], [1, 3]]}
        self.assertEqual(support_crossings(self.gcode, box)["joint_hole"], 0)
        self.assertEqual(supports_in_void_core(
            self.gcode, IDENTITY, IDENTITY, CENTER)["bolt_upper"], 0)

    def test_xy_extrusion_inside_joint_hole_is_counted(self) -> None:
        self.write("G1 X15 Y65 Z2", "G1 X15.5 Y65 E.04\n")
        box = {"joint_hole": [[14.5, 15.5], [64.5, 65.5], [1, 3]]}
        self.assertGreater(support_crossings(self.gcode, box)["joint_hole"], 0)
        self.assertGreater(supports_in_void_core(
            self.gcode, IDENTITY, IDENTITY, CENTER)["bolt_upper"], 0)

    def test_prime_inside_shell_hole_does_not_count_as_support(self) -> None:
        self.write("G1 X8 Y40 Z-10")
        self.assertEqual(support_in_shell_void_cores(
            self.gcode, IDENTITY, IDENTITY, CENTER)["lower_through_core"], 0)

    def test_xy_extrusion_inside_shell_hole_is_counted(self) -> None:
        self.write("G1 X8 Y40 Z-10", "G1 X8 Y41 E.04\n")
        self.assertGreater(support_in_shell_void_cores(
            self.gcode, IDENTITY, IDENTITY, CENTER)["lower_through_core"], 0)


if __name__ == "__main__":
    unittest.main()
