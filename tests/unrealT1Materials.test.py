from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_materials import terrain_recipe, world_uv, protected_saved, verify_protected, same_state


class T1MaterialsTest(unittest.TestCase):
    def test_reviewed_channels_and_seamless_physical_scale(self):
        root = Path(__file__).resolve().parents[1]
        for zone in ('sunmeadow_march', 'cinderfen_outskirts'):
            recipe = terrain_recipe(root, zone)
            self.assertEqual(set(recipe['layers']), {'terrain', 'roads'})
            self.assertFalse(recipe['visualApproved'])
            self.assertFalse(recipe['collisionChanged'])
            self.assertTrue(recipe['layers']['roads']['softVerge'])
            self.assertNotEqual(recipe['layers']['terrain']['color']['sha256'], recipe['layers']['roads']['color']['sha256'])
        # Neither rectangular dimensions nor duplicated seam UVs affect world-space detail.
        self.assertEqual(world_uv([300, 500, 70], 2), [2.5, -1.5])
        self.assertEqual(world_uv([500, 700, 900], 2), [3.5, -2.5])
        for scale in (0, float('nan'), float('inf')):
            with self.assertRaises(ValueError): world_uv([0, 0, 0], scale)
        with self.assertRaises(ValueError): terrain_recipe(root, 'brightfen_approach')

    def test_saved_content_and_owner_inventory_protection(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original = root/'unreal/AegisWar/Content/WorldRebuild/Capital.uasset'
            owner = root/'unreal/AegisWar/Saved/WorldEdit/home.json'
            for file in (original, owner): file.parent.mkdir(parents=True, exist_ok=True); file.write_text('original')
            hashes = protected_saved(root)
            new = original.parent/'NewStudy.uasset'; new.write_text('new')
            verify_protected(root, hashes)
            original.write_text('changed')
            with self.assertRaises(RuntimeError): verify_protected(root, hashes)
            original.write_text('original')
            (owner.parent/'other.json').write_text('{}')
            with self.assertRaises(RuntimeError): verify_protected(root, hashes)

    def test_clone_rounding_does_not_hide_geometry_or_binding_changes(self):
        state = dict(mesh='source', location=[0, 100.5, 3], collision='BlockAll', enabled=True)
        self.assertTrue(same_state(state, {**state, 'location': [0, 100.5+1e-10, 3]}))
        self.assertFalse(same_state(state, {**state, 'location': [0, 100.5001, 3]}))
        self.assertFalse(same_state(state, {**state, 'collision': 'NoCollision'}))
        self.assertFalse(same_state(state, {**state, 'enabled': 1}))


if __name__ == '__main__': unittest.main()
