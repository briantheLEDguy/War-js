import copy
import importlib.util
import math
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / 'scripts/unreal/citadel_decor_polish.py'
spec = importlib.util.spec_from_file_location('decor_polish', MODULE)
polish = importlib.util.module_from_spec(spec)
spec.loader.exec_module(polish)


def mounts():
    return [dict(id=f'{room}_{kind}_{i}', group=room, mountKind=kind,
                 point=[100, 200, 6000], boundsCm=[[80, 180, 6000], [144, 220, 6110]],
                 yawDegrees=0)
            for room in polish.ROOMS for kind in ('ceiling_chandelier', 'wall_lantern')
            for i in range(2)]


class DecorPolishTests(unittest.TestCase):
    def test_distinct_room_settings_and_input_preservation(self):
        rows = mounts()
        before = copy.deepcopy(rows)
        plan = polish.mounted_light_plan(rows)
        self.assertEqual(rows, before)
        self.assertEqual(len(plan), 16)
        self.assertEqual({r['id'] for r in plan}, {r['id'] for r in rows})
        self.assertTrue(all(r['castShadows'] for r in plan))
        self.assertEqual(next(r for r in plan if r['group'] == 'west_archive')['intensityLumens'], 180000)
        lantern = next(r for r in plan if r['kind'] == 'wall_lantern')
        self.assertEqual(lantern['positionCm'], [170, 200, 6055])
        self.assertGreater(lantern['emitterToHousingBoundsGapCm'], lantern['sourceRadiusCm'])

    def test_missing_duplicate_and_wrong_room_fail(self):
        for mutate in (lambda r: r.pop(), lambda r: r[0].update(id=r[1]['id']),
                       lambda r: r[0].update(group='courtyard')):
            rows = mounts()
            mutate(rows)
            with self.assertRaises(ValueError):
                polish.mounted_light_plan(rows)

    def test_room_distribution_cannot_hide_missing_fixture(self):
        rows = mounts()
        rows[0]['group'] = 'throne_hall'
        with self.assertRaises(ValueError):
            polish.mounted_light_plan(rows)

    def test_invalid_coordinates_and_housing_intersections_fail(self):
        for mutate in (lambda r: r[0].update(yawDegrees=math.nan),
                       lambda r: r[0].update(boundsCm=[[0, 0, 7000], [1, 1, 6000]]),
                       lambda r: r[2]['boundsCm'][1].__setitem__(0, 169)):
            rows = mounts()
            mutate(rows)
            with self.assertRaises(ValueError):
                polish.mounted_light_plan(rows)

    def test_yaw_rotates_lantern_offset(self):
        rows = mounts()
        row = rows[2]
        row['yawDegrees'] = 90
        row['boundsCm'] = [[80, 180, 6000], [120, 244, 6110]]
        light = polish.mounted_light_plan(rows)[2]
        self.assertAlmostEqual(light['positionCm'][0], 100)
        self.assertAlmostEqual(light['positionCm'][1], 270)

    def test_paint_is_bounded_and_original_is_immutable(self):
        original = dict(tint=[.025, .19, .18], roughness=.24, metallic=.28, twoSided=True)
        before = copy.deepcopy(original)
        adapted = polish.checked_paint(polish.PAINT_ROLES[0], original)
        self.assertEqual(original, before)
        self.assertEqual(adapted['tint'], [.015, .032, .078])
        self.assertEqual(adapted['roughness'], .48)
        self.assertEqual(adapted['metallic'], .12)
        self.assertTrue(adapted['twoSided'])

    def test_textured_or_changed_source_paint_rejected(self):
        original = dict(tint=[.025, .19, .18], roughness=.24, metallic=.28, twoSided=True)
        for role, spec in [('banner', original),
                           (polish.PAINT_ROLES[0], {**original, 'baseColor': 'texture.png'}),
                           (polish.PAINT_ROLES[0], {**original, 'tint': [.2, .2, .2]})]:
            with self.assertRaises(ValueError):
                polish.checked_paint(role, spec)


if __name__ == '__main__':
    unittest.main()
