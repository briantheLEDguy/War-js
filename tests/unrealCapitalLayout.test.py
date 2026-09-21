"""Layout contracts; actual native collision and GM checks run separately."""
from pathlib import Path
import sys
import unittest
import runpy
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/unreal"))
from capital_kit_layout import build_layout


class CapitalLayoutTests(unittest.TestCase):
    def test_repeatable_unique_builder_identities(self):
        first = build_layout()
        self.assertEqual(first, build_layout())
        rows = first["placements"]
        self.assertEqual(len(rows), len({row["id"] for row in rows}))
        self.assertLess(len(rows), 10000)

    def test_castle_has_keep_curtain_gatehouse_and_four_towers(self):
        rows = build_layout()["placements"]
        for district in ["keep", "castle", "gatehouse", "castle_tower", "rampart"]:
            self.assertTrue(any(row["district"] == district for row in rows))
        towers = {(round(row["centerBottom"][0] / 3600), round((row["centerBottom"][1] - 9300) / 3000))
                  for row in rows if row["district"] == "castle_tower"}
        self.assertEqual(towers, {(-1, -1), (-1, 1), (1, -1), (1, 1)})

    def test_processional_route_has_no_low_wall_across_its_center(self):
        for row in build_layout()["placements"]:
            if (row["kind"] in ["wall", "merlon"] and row["yaw"] == 0
                    and row["centerBottom"][2] < 300 and -12500 <= row["centerBottom"][1] <= 9600):
                self.assertGreater(abs(row["centerBottom"][0]), 150, row["id"])

    def test_layout_fits_builder_bounds_and_has_complete_house_types(self):
        rows = build_layout()["placements"]
        self.assertEqual({r["kind"] for r in rows if r["kind"].startswith("house")},
                         {"house" + str(i) for i in range(1, 4)})
        for row in rows:
            self.assertTrue(all(abs(v) < 100000 for v in row["centerBottom"]))
            self.assertTrue(all(0.05 <= v <= 20 for v in row["scale"]))

    def test_each_canopy_has_its_authored_frame_at_the_same_pivot(self):
        rows = build_layout()["placements"]
        def pivots(kind):
            return {(tuple(row["centerBottom"]), row["yaw"], tuple(row["scale"]))
                    for row in rows if row["kind"] == kind}
        self.assertEqual(len(pivots("stall")), 8)
        self.assertEqual(pivots("stall"), pivots("stallframe"))

    def test_owner_draft_blocks_generation_before_any_unreal_mutation(self):
        script = Path(__file__).resolve().parents[1] / "scripts/unreal/build-kit-capital.py"
        with patch.dict(sys.modules, {"unreal": object()}), patch.object(Path, "exists",
                lambda path: str(path).replace("\\", "/").endswith("Saved/WorldEdit/crownward-draft.json")):
            with self.assertRaisesRegex(RuntimeError, "Preserve the owner's Crownward draft"):
                runpy.run_path(str(script))


if __name__ == "__main__":
    unittest.main()
