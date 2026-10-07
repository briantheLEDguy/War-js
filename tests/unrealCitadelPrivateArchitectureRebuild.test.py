import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/unreal'))
from citadel_private_architecture_rebuild import rebuild_private_source


def source_fixture():
    return dict(id='stairs_and_balconies', collision=True,
                positions=[[0,0,0],[200,0,0],[200,200,0],[0,200,0],[999,999,999]],
                normals=[[0,0,1]]*5, uvs=[[0,0],[2,0],[2,2],[0,2],[9,9]],
                indices=[0,1,2,0,2,3], triangleMaterials=[0,1], materials=['stone','iron'])


def addition_fixture():
    return dict(id='rail_00', collision=False, navigation=False,
                coordinateSpace='final_unreal_world_cm',
                sourceTriangleWinding='counter_clockwise_cross_aligned_with_normals',
                positions=[[0,0,150],[200,0,150],[200,8,150]],
                normals=[[0,0,1]]*3, uvs=[[0,0],[2,0],[2,.08]],
                indices=[0,1,2], triangleMaterials=[0], materials=['limestone','stone'])


def run_fixture(source=None, selected=None, additions=None, expected=None, target='private_stair_render'):
    source = source_fixture() if source is None else source
    raw = (json.dumps(source, separators=(',', ':')) + '\n').encode()
    return rebuild_private_source(raw, hashlib.sha256(raw).hexdigest() if expected is None else expected,
                                  [0] if selected is None else selected,
                                  [addition_fixture()] if additions is None else additions, target)


class PrivateArchitectureRebuildTests(unittest.TestCase):
    def test_retains_unselected_oriented_occurrence_and_unused_source_vertex(self):
        source = source_fixture()
        addition = addition_fixture()
        protected = copy.deepcopy((source, addition))
        rebuilt, receipt = run_fixture(source, additions=[addition])
        self.assertEqual((source, addition), protected)
        self.assertEqual(rebuilt['positions'][:5], source['positions'])
        self.assertEqual(rebuilt['normals'][:5], source['normals'])
        self.assertEqual(rebuilt['uvs'][:5], source['uvs'])
        self.assertEqual(rebuilt['indices'][:3], [0,2,3])
        self.assertEqual(rebuilt['triangleMaterials'][0], 1)
        self.assertEqual(receipt['retainedSourceIndices'], [1])
        self.assertTrue(receipt['retainedSourceOccurrencesExact'])
        self.assertFalse(receipt['nativePackedBufferPreservationClaimed'])
        self.assertFalse(receipt['sharedAdoptionAllowed'])
        self.assertFalse(rebuilt['collision'])
        self.assertFalse(rebuilt['navigation'])

    def test_material_mapping_uses_roles_and_preserves_original_slots(self):
        rebuilt, receipt = run_fixture()
        self.assertEqual(rebuilt['materials'], ['stone','iron','limestone'])
        self.assertEqual(rebuilt['triangleMaterials'], [1,2])
        self.assertEqual(rebuilt['indices'][3:], [5,6,7])
        self.assertEqual(receipt['additions'][0]['targetFirstTriangle'], 1)

    def test_preserves_unused_declared_roles_in_the_actual_source_protocol(self):
        source = source_fixture()
        source['materials'].extend('furniture_' + str(i) for i in range(24))
        rebuilt, receipt = run_fixture(source)
        self.assertEqual(rebuilt['materials'][:26], source['materials'])
        self.assertEqual(rebuilt['triangleMaterials'], [1,26])
        self.assertEqual(receipt['sourceDeclaredMaterialRoles'], 26)
        self.assertEqual(receipt['outputUsedMaterialRoles'], 2)

    def test_source_byte_hash_blocks_changed_source_and_ordinal_reinterpretation(self):
        with self.assertRaisesRegex(ValueError, 'Source hash changed'):
            run_fixture(expected='a'*64)
        with self.assertRaisesRegex(ValueError, 'Source hash changed'):
            run_fixture(expected='A'*64)

    def test_rejects_duplicate_boolean_out_of_range_and_whole_source_selections(self):
        for selected in ([0,0], [True], [-1], [2], [0,1]):
            with self.subTest(selected=selected), self.assertRaises(ValueError):
                run_fixture(selected=selected)

    def test_rejects_unknown_source_and_nonprivate_target(self):
        source = source_fixture()
        source['id'] = 'campaign_floor'
        with self.assertRaisesRegex(ValueError, 'four owned'):
            run_fixture(source)
        with self.assertRaisesRegex(ValueError, 'private source target'):
            run_fixture(target='stairs_and_balconies')

    def test_requires_final_space_and_explicit_import_winding(self):
        for key, value in [('coordinateSpace','blender_meters'), ('sourceTriangleWinding','clockwise')]:
            addition = addition_fixture()
            addition[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                run_fixture(additions=[addition])
        addition = addition_fixture()
        addition['indices'] = [0,2,1]
        with self.assertRaisesRegex(ValueError, 'winding disagrees'):
            run_fixture(additions=[addition])

    def test_rejects_render_only_contract_violation(self):
        for key in ('collision','navigation'):
            addition = addition_fixture()
            addition[key] = True
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'render-only'):
                run_fixture(additions=[addition])

    def test_rejects_incomplete_invalid_and_degenerate_attributes(self):
        cases = [('normals', [[0,0,1]]*2), ('uvs', [[0,0]]*2),
                 ('positions', [[0,0,150]]*3), ('indices', [0,1,True]),
                 ('triangleMaterials', [2]), ('materials', ['stone','stone'])]
        for key, value in cases:
            addition = addition_fixture()
            addition[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                run_fixture(additions=[addition])

    def test_never_silently_discards_an_extra_source_channel(self):
        for key in ('uvChannels','lightmapUvs','colors','tangents','binormals'):
            source = source_fixture()
            source[key] = []
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'Additional source channels'):
                run_fixture(source)

    def test_append_only_is_explicit_and_deterministic(self):
        first = run_fixture(selected=[])
        self.assertEqual(first, run_fixture(selected=[]))
        self.assertEqual(first[0]['indices'][:6], source_fixture()['indices'])
        with self.assertRaisesRegex(ValueError, 'explicit change'):
            run_fixture(selected=[], additions=[])


if __name__ == '__main__':
    unittest.main()
