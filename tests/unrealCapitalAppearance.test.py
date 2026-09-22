import importlib.util
from pathlib import Path
import unittest
from types import SimpleNamespace
spec=importlib.util.spec_from_file_location('appearance',Path(__file__).resolve().parents[1]/'scripts/unreal/capital_appearance.py')
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
class AppearanceTests(unittest.TestCase):
    def test_stable_identity_palette(self):
        ids=['aegis_house_'+str(i) for i in range(145)]
        first={identity:m.palette_for(identity) for identity in ids}
        self.assertEqual(first,{identity:m.palette_for(identity) for identity in reversed(ids)})
        self.assertEqual(set(first.values()),set(m.PALETTES))
    def test_subtractive_tints_preserve_texture_contrast(self):
        for color in m.PALETTES.values():
            self.assertTrue(all(0 < channel < 1 for channel in color))
            self.assertLessEqual(max(color)-min(color),.12)
    def test_missing_required_scene_rejects_before_mutation(self):
        api=SimpleNamespace(MaterialEditingLibrary=None,EditorAssetLibrary=None,
            AssetToolsHelpers=SimpleNamespace(get_asset_tools=lambda:None))
        actors=SimpleNamespace(get_all_level_actors=lambda:[])
        with self.assertRaisesRegex(RuntimeError,'Required authored city'):
            m.apply_appearance(api,actors,'/Game/Test')
    def test_custom_terrain_rejects_before_actor_mutation(self):
        class Actor:
            def __init__(self,label):
                self.label=label
                self.static_mesh_component=SimpleNamespace(get_material=lambda index:object())
            def get_actor_label(self): return self.label
            def modify(self): raise AssertionError('Must preflight before modifying')
        api=SimpleNamespace(MaterialEditingLibrary=None,EditorAssetLibrary=None,
            AssetToolsHelpers=SimpleNamespace(get_asset_tools=lambda:None),StaticMeshActor=Actor,Material=str)
        actors=SimpleNamespace(get_all_level_actors=lambda:[Actor(label) for label in
            ['Aegis workbench sun','Aegis daylight exposure','Crownward original ground','Crownward authored mountain massif']])
        with self.assertRaisesRegex(RuntimeError,'Preserve customized terrain'):
            m.apply_appearance(api,actors,'/Game/Test')
if __name__=='__main__': unittest.main()
