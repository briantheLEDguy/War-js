"""Portable identity tests only; no native lighting or visual approval is inferred."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/unreal'))
from aegis_citadel_lighting import (FIXTURES, bind_fixture_edits, expected_copied_fixture,
    fixture_catalog, reference_fixture_requests, shadowed_practical_requests)
from aegis_citadel_blueprint import LIGHTING_FIXTURES_V1 as LIGHTING_FIXTURES


def baseline():
    result = dict(actors={}, packageHashes={})
    for _, actor, klass, label, _, layer, tag in FIXTURES:
        package = '/Game/WorldRebuild/DutchBastion_fixture/Layers/' + layer
        result['packageHashes'][package] = 'a' * 64
        result['actors'].setdefault(package, []).append(dict(actor=actor,
            state=dict(**{'class': klass}, label=label, tags=[tag], components=[])))
    return result


class LightingIdentity(unittest.TestCase):
    def test_same_actor_name_remains_distinct(self):
        rows = fixture_catalog(baseline())
        lights = [r for r in rows if r['actor'] == 'DirectionalLight_0']
        self.assertEqual([r['id'] for r in lights], ['sun', 'dutch_street_fill'])
        self.assertNotEqual(lights[0]['package'], lights[1]['package'])
        self.assertNotEqual(lights[0]['requiredTag'], lights[1]['requiredTag'])
        self.assertNotEqual(lights[0]['sourceStateHash'], lights[1]['sourceStateHash'])

    def test_actor_name_alone_cannot_match_another_copied_layer(self):
        source = baseline()
        sun, fill = [r for r in fixture_catalog(source) if r['actor'] == 'DirectionalLight_0']
        row = source['actors'][sun['package']][0]
        self.assertTrue(expected_copied_fixture(sun, sun['package'], row['actor'], row['state']))
        self.assertFalse(expected_copied_fixture(sun, fill['package'], row['actor'], row['state']))
        self.assertFalse(expected_copied_fixture(fill, sun['package'], row['actor'], row['state']))

    def test_unknown_native_class_or_lost_tag_fails(self):
        for member, replacement in [('class', 'GameplayLightingBlueprint_C'), ('tags', [])]:
            source = baseline()
            first = next(iter(source['actors'].values()))[0]
            first['state'][member] = replacement
            with self.assertRaises(ValueError):
                fixture_catalog(source)

    def test_duplicate_source_and_unhashed_package_fail(self):
        source = baseline()
        package = next(iter(source['actors']))
        source['actors'][package].append(copy.deepcopy(source['actors'][package][0]))
        with self.assertRaises(ValueError):
            fixture_catalog(source)
        source = baseline()
        source['packageHashes'][next(iter(source['packageHashes']))] = ''
        with self.assertRaises(ValueError):
            fixture_catalog(source)

    def test_unmeasured_atmosphere_values_never_fill_defaults(self):
        requested = [dict(id=row[0], properties={'intensity': 1}) for row in FIXTURES]
        requested[5]['properties'] = {}
        with self.assertRaises(ValueError):
            bind_fixture_edits(baseline(), requested)

    def test_identity_override_and_unenumerated_property_fail(self):
        requested = [dict(id=row[0], properties={'intensity': 1}) for row in FIXTURES]
        requested[0]['package'] = '/Game/Foreign/Level'
        with self.assertRaises(ValueError):
            bind_fixture_edits(baseline(), requested)
        requested[0].pop('package')
        requested[0]['properties'] = {'affects_world': False}
        with self.assertRaises(ValueError):
            bind_fixture_edits(baseline(), requested)

    def test_measured_repair_changes_only_two_atmosphere_fields(self):
        original = copy.deepcopy(LIGHTING_FIXTURES)
        rows = bind_fixture_edits(baseline(), reference_fixture_requests(original))
        self.assertEqual(original, LIGHTING_FIXTURES)
        by_id = {r['id']: r for r in rows}
        self.assertEqual(by_id['atmosphere']['properties'], {
            'rayleigh_scattering_scale': .0331, 'rayleigh_exponential_distribution': 8})
        self.assertEqual(by_id['dutch_street_fill']['properties']['light_color']['value'], [173,192,218,255])
        self.assertEqual(by_id['dutch_street_fill']['properties']['intensity'], 0)
        self.assertEqual(by_id['soft_sky_fill']['properties']['intensity'], 800)
        self.assertEqual(by_id['sun']['rotationDegrees'], [-20,30,0])
        self.assertEqual(by_id['ambient_sky']['properties']['intensity'], .35)
        self.assertEqual(by_id['distance_haze']['properties']['fog_density'], .006)
        for fixture_id in ('soft_sky_fill', 'dutch_street_fill'):
            self.assertTrue(by_id[fixture_id]['properties']['cast_shadows'])
            self.assertTrue(by_id[fixture_id]['properties']['cast_dynamic_shadows'])
        self.assertEqual(by_id['exposure']['properties']['dynamic_global_illumination_method'],
                         dict(kind='enum', type='DynamicGlobalIlluminationMethod', value='SCREEN_SPACE'))
        self.assertEqual(by_id['exposure']['properties']['reflection_method'],
                         dict(kind='enum', type='ReflectionMethod', value='SCREEN_SPACE'))

    def test_practical_shadow_repair_preserves_native_placement_and_power(self):
        original = [dict(id='sconce', pointCm=[1,2,3], intensityCd=24000, mobility='movable', castShadows=False)]
        changed = shadowed_practical_requests(original)
        self.assertFalse(original[0]['castShadows'])
        self.assertTrue(changed[0]['castShadows'])
        self.assertEqual({k:v for k,v in original[0].items() if k!='castShadows'},
                         {k:v for k,v in changed[0].items() if k!='castShadows'})


if __name__ == '__main__':
    unittest.main()
