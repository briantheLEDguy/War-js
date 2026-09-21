"""Layout contracts; actual native collision and GM checks run separately."""
from pathlib import Path
import sys
import unittest
import runpy
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/unreal"))
from capital_kit_layout import build_layout
from capital_geography import source_map, height, road_surface, mountain_surface


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
        towers = {(round(row["centerBottom"][1] / 3600), round((row["centerBottom"][0] - 17300) / 3000))
                  for row in rows if row["district"] == "castle_tower"}
        self.assertEqual(towers, {(-1, -1), (-1, 1), (1, -1), (1, 1)})
        self.assertTrue(all(row["centerBottom"][2] >= 4200 for row in rows if row["district"] == "keep"))

    def test_original_house_identities_districts_and_winding_ascent_survive(self):
        layout = build_layout()
        source = source_map()
        houses = [p for p in source["props"] if p["kind"].startswith(("aegis_house_", "aegis_rowhouse_"))]
        actual = [p for p in layout["placements"] if p["kind"].startswith("house")]
        self.assertEqual({p["id"] for p in houses}, {p["id"] for p in actual})
        self.assertEqual({p["district"] for p in actual}, {p["id"] for p in source["cityDistricts"]})
        self.assertEqual(layout["arrival"][:2], [-11800,0])
        route = layout["routes"]
        self.assertGreater(max(p[2] for p in route)-min(p[2] for p in route),4000)
        self.assertLess(min(p[1] for p in route),-5000)
        self.assertGreater(max(p[1] for p in route),1000)
        self.assertEqual({p["id"] for p in source["paths"]},set(layout["sourcePathIds"]))

    def test_original_terrain_and_authored_mountain_geometry(self):
        self.assertEqual(height(0,-118),0)
        self.assertEqual(height(0,180),42)
        mountain, _, images = mountain_surface()
        self.assertEqual(len(mountain["indices"])//3,22042)
        self.assertEqual(mountain["removedDegenerateTriangles"],2)
        self.assertGreater(max(p[2] for p in mountain["positions"]),39000)
        self.assertEqual(len(images),3)
        roads = road_surface()
        self.assertEqual(len(roads["positions"]),len(roads["uvs"]))
        self.assertTrue(all(0 <= i < len(roads["positions"]) for i in roads["indices"]))
        # A center-height-only ribbon creates raised lips where switchbacks overlap.
        for x,y,z in roads["positions"]:
            self.assertAlmostEqual(z,height(y/100,x/100)*100+3, places=6)

    def test_perimeter_decks_fill_each_original_scaled_wall_span(self):
        layout = build_layout()
        for wall in (p for p in source_map()["props"] if p["kind"] == "aegis_wall"):
            decks = [p for p in layout["placements"] if p["kind"] == "floor" and p.get("sourceId") == wall["id"]]
            expected = wall["colliders"][0]["width"] * wall.get("scaleX",1) * wall.get("scale",1)
            self.assertAlmostEqual(sum(p["scale"][0]*3 for p in decks),expected)
            self.assertTrue(decks)

    def test_layout_fits_builder_bounds_and_has_complete_house_types(self):
        rows = build_layout()["placements"]
        self.assertEqual({r["kind"] for r in rows if r["kind"].startswith("house")},
                         {"house" + str(i) for i in range(1, 4)})
        for row in rows:
            if row["kind"].startswith("house"):
                self.assertEqual(row["scale"][2],1)
            self.assertTrue(all(abs(v) < 100000 for v in row["centerBottom"]))
            self.assertTrue(all(0.05 <= v <= 20 for v in row["scale"]))

    def test_each_canopy_has_its_authored_frame_at_the_same_pivot(self):
        rows = build_layout()["placements"]
        def pivots(kind):
            return {(tuple(row["centerBottom"]), row["yaw"], tuple(row["scale"]))
                    for row in rows if row["kind"] == kind}
        self.assertEqual(len(pivots("stall")), 8)
        self.assertEqual(pivots("stall"), pivots("stallframe"))

    def test_staging_project_cannot_receive_the_game_world(self):
        script = Path(__file__).resolve().parents[1] / "scripts/unreal/build-kit-capital.py"
        fake = SimpleNamespace(Paths=SimpleNamespace(project_dir=lambda: str(script.parent / "CityKitStaging")))
        with patch.dict(sys.modules, {"unreal": fake}), patch.object(Path,"exists",lambda path: False):
            with self.assertRaisesRegex(RuntimeError,"Build the playable city in AegisWar"):
                runpy.run_path(str(script))

    def test_owner_draft_blocks_generation_before_any_unreal_mutation(self):
        script = Path(__file__).resolve().parents[1] / "scripts/unreal/build-kit-capital.py"
        with patch.dict(sys.modules, {"unreal": object()}), patch.object(Path, "exists",
                lambda path: str(path).replace("\\", "/").endswith("Saved/WorldEdit/crownward-draft.json")):
            with self.assertRaisesRegex(RuntimeError, "Preserve the owner's Crownward draft"):
                runpy.run_path(str(script))


if __name__ == "__main__":
    unittest.main()
