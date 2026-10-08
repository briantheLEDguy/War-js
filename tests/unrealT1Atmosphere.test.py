import copy
import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_atmosphere import atmosphere_recipe, native, validate_live_atmosphere


class AtmosphereTests(unittest.TestCase):
    def source(self, zone):
        return dict(id=zone, spawnPoint=dict(x=12, z=-7, y=3), orvrLayout=dict(
            keeps=[dict(deliveryPoint=dict(x=i, z=2)) for i in range(2)],
            battlefieldObjectives=[dict(x=i, z=4) for i in range(3)]))

    def test_source_coordinates_and_gameplay_remain_exact(self):
        source = self.source('sunmeadow_march'); before = copy.deepcopy(source)
        result = atmosphere_recipe(source, [])
        self.assertEqual(result['villageCentre'], [-700, 1200, 300])
        self.assertEqual(len(result['militaryCentres']), 5)
        self.assertEqual(result['steamSites'], [])
        self.assertEqual(source, before)
        self.assertFalse(result['collision']); self.assertFalse(result['activeCampaignChanged'])

    def test_steam_uses_only_authored_regional_sites(self):
        scenes = [dict(id='cinderfen_outskirts_'+name, placements=[dict(x=i, z=5) for i in range(10)])
                  for name in ('basalt_shelf', 'peat_dyke', 'mineral_rise')]
        result = atmosphere_recipe(self.source('cinderfen_outskirts'), scenes)
        self.assertEqual(len(result['steamSites']), 8)
        self.assertTrue(all(p[0] == 500 for p in result['steamSites']))
        with self.assertRaises(ValueError): atmosphere_recipe(self.source('cinderfen_outskirts'), [])

    def test_unsafe_or_later_batch_inputs_rejected(self):
        with self.assertRaises(ValueError): atmosphere_recipe(self.source('brightfen_approach'), [])
        source = self.source('sunmeadow_march'); source['orvrLayout']['keeps'] = []
        with self.assertRaises(ValueError): atmosphere_recipe(source, [])
        with self.assertRaises(ValueError): native(dict(x=float('nan'), z=0))
        with self.assertRaises(ValueError): native(dict(x=4000, z=0))

    def test_live_clock_collision_and_shelter_evidence(self):
        config = dict(zone='sunmeadow_march', routes=[dict(points=[dict(capture=False), dict(capture=True, indoor=True)])])
        state = dict(waypoint=1, zone='sunmeadow_march', active=True, replicated=False, collisionEnabled=False,
                     particles=0, queuedAudioBytes=12000, observerInside=True)
        report = dict(environmentUnixSeconds=1000, routes=[dict(atmosphereFrames=[state])])
        validate_live_atmosphere(report, config)
        for key, value in [('active', False), ('replicated', True), ('collisionEnabled', True),
                           ('particles', 1), ('observerInside', False), ('queuedAudioBytes', 24001)]:
            invalid = copy.deepcopy(report); invalid['routes'][0]['atmosphereFrames'][0][key] = value
            with self.assertRaises(ValueError): validate_live_atmosphere(invalid, config)
        invalid = copy.deepcopy(report); invalid['environmentUnixSeconds'] = float('nan')
        with self.assertRaises(ValueError): validate_live_atmosphere(invalid, config)


if __name__ == '__main__': unittest.main()
