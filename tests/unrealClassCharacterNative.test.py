import copy
import importlib.util
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('native_class_body', Path(__file__).resolve().parents[1] / 'scripts/unreal/class_character_native.py')
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


class NativeClassBodyTests(unittest.TestCase):
    def setUp(self):
        self.checkpoint = dict(built=48, sourcePosePassed=48, dentitionPassed=8, characters=[])
        self.requests, self.playable = {}, []
        for index, career in enumerate(native.STYLES):
            race = ['empire', 'dwarf', 'high_elf', 'chaos', 'greenskin', 'dark_elf'][index // 4]
            for body in ('m', 'f'):
                identity = career + '_' + body
                self.requests[identity] = dict(classKey=career, className=career, race=race, bodyVariant=body)
                self.playable.append(dict(race=race, className=career, bodyVariant=body, profileKey='own_' + identity))
                candidate = 'dentition-v1' if race == 'greenskin' else 'optimized-v2'
                self.checkpoint['characters'].append(dict(identity=identity, model=identity + '/' + candidate + '/body.glb',
                    technicalPassed=True, suppliedPosePassed=True, modelSha256='a'*64, heightM=1.8, triangles=39000))

    def test_every_body_keeps_its_exact_class_race_and_variant(self):
        selected = native.selected_bodies(self.checkpoint, self.requests, self.playable)
        self.assertEqual(len(selected), 48)
        self.assertEqual(sum(row['source'].endswith('/dentition-v1/body.glb') for row in selected.values()), 8)
        for profile, row in selected.items():
            self.assertEqual(profile, 'own_' + row['classId'] + '_' + row['bodyVariant'])

    def test_incomplete_or_failed_candidates_do_not_reach_native_conversion(self):
        for field, value in [('built', 47), ('sourcePosePassed', 47), ('dentitionPassed', 7)]:
            checkpoint = copy.deepcopy(self.checkpoint); checkpoint[field] = value
            with self.assertRaises(ValueError): native.selected_bodies(checkpoint, self.requests, self.playable)
        checkpoint = copy.deepcopy(self.checkpoint); checkpoint['characters'][0]['suppliedPosePassed'] = False
        with self.assertRaises(ValueError): native.selected_bodies(checkpoint, self.requests, self.playable)

    def test_changed_identity_source_and_hash_are_rejected(self):
        for field, value in [('identity', 'other_f'), ('model', '../body.glb'), ('modelSha256', 'not-a-hash')]:
            checkpoint = copy.deepcopy(self.checkpoint); checkpoint['characters'][0][field] = value
            with self.assertRaises((ValueError, KeyError)): native.selected_bodies(checkpoint, self.requests, self.playable)
        checkpoint = copy.deepcopy(self.checkpoint); checkpoint['characters'][-1] = checkpoint['characters'][0]
        with self.assertRaises(ValueError): native.selected_bodies(checkpoint, self.requests, self.playable)

    def test_main_roster_replacement_preserves_world_and_legacy_settings(self):
        before = ('[/Script/AegisWar.WarRuntimeSettings]\nWorldSetting=retained\n'
                  '+PlayableRoster=old_a\n+PlayableRoster=old_b\n\n'
                  '[/Script/UnrealEd.ProjectPackagingSettings]\n+DirectoriesToAlwaysCook=(Path="/Game/World")\n')
        revisions = ['classbody_' + row['identity'] + '_aaaaaaaaaaaa' for row in self.checkpoint['characters']]
        after = native.roster_config(before, revisions)
        self.assertEqual(after.count('+PlayableRoster='), 48)
        self.assertIn('WorldSetting=retained\n', after)
        self.assertIn('+DirectoriesToAlwaysCook=(Path="/Game/World")\n', after)
        self.assertNotIn('old_a', after)
        self.assertEqual(native.roster_config(after, revisions), after)
        with self.assertRaises(ValueError): native.roster_config(before, revisions[:-1])
        with self.assertRaises(ValueError): native.roster_config(before, ['unowned']*48)

    def test_source_bind_hierarchy_converts_gltf_axes_and_metres(self):
        doc = dict(nodes=[dict(name='root', translation=[2, 3, 4],
                              rotation=[0, 0, 2**-.5, 2**-.5], children=[1]),
                          dict(name='hand_R', translation=[1, 0, 0])], skins=[dict(joints=[0, 1])])
        chunk = json.dumps(doc).encode()
        binary = struct.pack('<4sIIII', b'glTF', 2, len(chunk)+20, len(chunk), 0x4e4f534a)+chunk
        with patch.object(Path, 'read_bytes', return_value=binary):
            positions = native.gltf_joint_positions('fixture.glb')
        self.assertEqual(positions['root'], [200, 400, 300])
        for actual, expected in zip(positions['hand_R'], [200, 400, 400]):
            self.assertAlmostEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
