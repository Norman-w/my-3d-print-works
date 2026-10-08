#!/usr/bin/env python3
"""Small regression checks for geometry-only packaging and G-code parsing."""
from pathlib import Path
import math
import struct
import tempfile
import unittest
from zipfile import ZipFile

from prepare_fan_tee_v5_print import LAYOUT, TEMPLATE, binary_mesh, build
from verify_fan_tee_v5_print import geometry, is_upright, mesh_equivalence, nozzle_xy_offset, signature, support_paths


class PrintPackageTests(unittest.TestCase):
    def test_dense_vertices_require_nearest_bijection_not_looser_tolerance(self):
        source = [(0., 0., 0.), (.00004, 0., 0.), (0., 1., 0.), (0., 0., 1.)]
        native = [(.000001, 0., 0.), (.000039, 0., 0.), (0., 1., 0.), (0., 0., 1.)]
        faces = [(0, 2, 1), (0, 1, 3), (0, 3, 2), (1, 2, 3)]
        self.assertTrue(mesh_equivalence(native, faces, source, faces)[0])
        native[1] = native[0]
        self.assertFalse(mesh_equivalence(native, faces, source, faces)[0])
        native[0] = (.00002, 0., 0.)
        self.assertFalse(mesh_equivalence(native, faces, source, faces)[0])

    def test_single_body_height_and_count_are_explicit(self):
        def tetra(height):
            points = [(0., 0., 0.), (4., 0., 0.), (0., 4., 0.), (0., 0., height)]
            faces = [(0, 2, 1), (0, 1, 3), (0, 3, 2), (1, 2, 3)]
            return bytes(80)+struct.pack('<I', 4)+b''.join(
                struct.pack('<12fH', 0, 0, 0, *(x for i in f for x in points[i]), 0) for f in faces)
        with tempfile.TemporaryDirectory(prefix='single-shell-test-') as d:
            work = Path(d)
            stl = work / 'connector.stl'
            stl.write_bytes(tetra(248))
            kwargs = dict(layout=[('connector', (128., 128.))], expected_parts=1, height_margin_mm=2)
            report = build({'connector': stl}, work/'output', TEMPLATE, **kwargs)
            self.assertEqual(report['part_count'], 1)
            self.assertEqual(len(geometry(Path(report['package']), report, expected_parts=1)), 1)
            with self.assertRaises(AssertionError):
                geometry(Path(report['package']), report)
            stl.write_bytes(tetra(248.1))
            with self.assertRaises(AssertionError):
                build({'connector': stl}, work/'too-tall', TEMPLATE, **kwargs)

    def test_native_float32_recentering_crosses_rounding_boundary(self):
        original = [(0., 0., 10.0375001), (1., 0., 0.), (0., 1., 0.)]
        native = [(0., 0., 10.037499), (1., 0., 0.), (0., 1., 0.)]
        self.assertNotEqual(signature(native, [(0, 1, 2)]), signature(original, [(0, 1, 2)]))
        equivalent, error = mesh_equivalence(native, [(1, 2, 0)], original, [(0, 1, 2)])
        self.assertTrue(equivalent)
        self.assertLess(error, .000002)
        self.assertFalse(mesh_equivalence(native, [(0, 2, 1)], original, [(0, 1, 2)])[0])
        native[0] = (0., 0., 10.036)
        self.assertFalse(mesh_equivalence(native, [(0, 1, 2)], original, [(0, 1, 2)])[0])

    def test_native_extruder_offset_is_preserved_for_gcode_to_mesh_mapping(self):
        self.assertEqual(nozzle_xy_offset({"extruder_offset": ["0x2"]}), (0., 2.))
        with self.assertRaises(AssertionError):
            nozzle_xy_offset({"extruder_offset": ["0x0", "0x2"]})

    def test_triangle_signature_preserves_winding(self):
        points = [(0., 0., 0.), (1., 0., 0.), (0., 1., 0.)]
        self.assertEqual(signature(points, [(0, 1, 2)]), signature(points, [(1, 2, 0)]))
        self.assertNotEqual(signature(points, [(0, 1, 2)]), signature(points, [(0, 2, 1)]))

    def test_upright_rotation_is_not_scale_or_mirror(self):
        a = math.radians(37)
        pose = [math.cos(a), math.sin(a), 0, -math.sin(a), math.cos(a), 0, 0, 0, 1, 80, 120, 10]
        self.assertTrue(is_upright(pose))
        self.assertFalse(is_upright([1, 0, 0, 0, -1, 0, 0, 0, 1, 0, 0, 0]))
        self.assertFalse(is_upright([2, 0, 0, 0, 2, 0, 0, 0, 2, 0, 0, 0]))
        pose[8] = -1
        self.assertFalse(is_upright(pose))

    def test_support_relative_and_absolute_extrusion(self):
        segments, counts = support_paths("""M83
; Z_HEIGHT: 0.2
G0 X10 Y20 Z0.2
; FEATURE: Support
G1 X11 Y20 E0.1
G1 E-0.4
; FEATURE: Support interface
M82
G92 E0
G1 X12 Y20 E0.1
G1 X13 Y20 E0.05
; FEATURE: Outer wall
G1 X14 Y20 E0.2
""")
        self.assertEqual(dict(counts), {"Support": 1, "Support interface": 1})
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0]["start"], [10., 20., .2])
        self.assertEqual(segments[1]["end"], [12., 20., .2])

    def test_packaged_triangles_preserve_original_coordinates(self):
        # Deliberately off-origin solids exercise native source-offset handling.
        points = [(2., 3., -7.), (6., 3., -7.), (2., 7., -7.), (2., 3., -1.)]
        faces = [(0, 2, 1), (0, 1, 3), (0, 3, 2), (1, 2, 3)]
        raw = bytes(80)+struct.pack("<I", len(faces))+b"".join(
            struct.pack("<12fH", 0, 0, 0, *(x for i in f for x in points[i]), 0) for f in faces)
        with tempfile.TemporaryDirectory(prefix="fan-print-package-test-") as d:
            work = Path(d)
            stls = {}
            for role, _ in LAYOUT:
                stls[role] = work/(role+".stl")
                stls[role].write_bytes(raw)
            report = build(stls, work/"output", TEMPLATE)
            records = geometry(Path(report["package"]), report)
            self.assertEqual(len(records), 5)
            self.assertTrue(all(r["all_triangles_match_at_0_001_mm"] for r in records))
            with ZipFile(report["package"]) as archive:
                self.assertFalse(any(n.endswith((".gcode", ".png")) for n in archive.namelist()))
                self.assertIn(b'<Relationships xmlns=', archive.read("_rels/.rels"))
                self.assertNotIn(b'ns0:', archive.read("3D/_rels/3dmodel.model.rels"))
            with self.assertRaises(AssertionError):
                build(stls, work/"invalid", TEMPLATE, plate_name="illegal:plate")
            broken = work/"open.stl"
            broken.write_bytes(raw[:80]+struct.pack("<I", 3)+raw[84:84+150])
            with self.assertRaises(AssertionError):
                binary_mesh(broken)


if __name__ == "__main__":
    unittest.main()
