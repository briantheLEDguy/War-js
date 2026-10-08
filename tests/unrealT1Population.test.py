import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_population import population_plan, inside_outline, nearest_route_points


class PopulationTest(unittest.TestCase):
    def setUp(self):
        self.npc = dict(id='scout', name='Mira', role='guard', characterProfileKey='exact_scout', x=1, z=2, rotY=0)
        self.node = dict(id='herb', kind='herb', professionId='cultivation', radius=5, respawnSeconds=90,
                         xp=8, visualPropId='herb_visual', loot=[dict(key='root', chance=.8, qty=1)], x=3, z=4)
        self.prop = dict(id='herb_visual', kind='herb_cluster', heightMode='terrain', x=3, z=4)
        self.canonical = dict(id='sunmeadow_march', npcs=[self.npc], resourceNodes=[self.node], props=[self.prop], craftingStations=[])
        self.candidate = copy.deepcopy(self.canonical)
        for key in ('npcs', 'resourceNodes', 'props'):
            for row in self.candidate[key]: row['x'] += 10; row['z'] -= 20
        self.survey = dict(zone='sunmeadow_march', actors=[
            dict(kind='npc', id='scout', identity=dict(npc_id='scout', display_name='Mira', city_role='guard', character_profile='exact_scout'),
                 mesh='/Game/Exact.Scout', materials=['body'], collision='NoCollision', animation=dict(asset='/Game/Idle.Idle', looping=True, playing=True)),
            dict(kind='resource', id='herb', identity=dict(zone_id='sunmeadow_march', node_id='herb', visual_prop_id='herb_visual'),
                 mesh='/Game/Herb.Herb', materials=['leaf', 'stem'], collision='NoCollision')])
        self.imports = dict(entries=[dict(profileKey='exact_scout', skeletalMeshPath='/Game/Exact.Scout', animationPaths=['/Game/Idle.Idle'])])
        self.catalog = dict(bindings=[dict(purpose='resource', zone='sunmeadow_march', entity='herb', visualProp='herb_visual',
                            mesh='/Game/Herb.Herb', materials=['leaf','stem'], collision='NoCollision', sourceModel='herb.glb', sourceSha256='a'*64)])
        self.review = dict(schemaVersion=1, reviewState='development', productionAccepted=False, bindings=[dict(zone='sunmeadow_march', entity='herb',
            visualProp='herb_visual', sourceSha256='a'*64, model='herb.glb', assetKey='herb_asset', sourceKind='herb_cluster', resourceKind='herb', heightMode='terrain')])
        self.registry = dict(herb_asset=dict(approvalState='approved', runtimeReady=True, model='herb.glb', modelSha256='a'*64))

    def plan(self):
        return population_plan(self.candidate, self.canonical, self.survey, self.catalog, self.imports, self.registry, self.review)

    def test_coordinates_change_without_mutating_rules_or_inputs(self):
        before = copy.deepcopy(self.candidate); plan = self.plan()
        self.assertEqual(self.candidate, before); self.assertEqual(len(plan['ready']), 2)
        self.assertEqual(plan['ready'][0]['point'], [-1800,1100,0]); self.assertFalse(plan['gameplayAccepted'])

    def test_missing_exact_profile_stays_pending_without_substitution(self):
        self.imports['entries'][0]['profileKey'] = 'another_scout'
        plan = self.plan(); self.assertEqual([r['kind'] for r in plan['ready']], ['resource'])
        self.assertEqual(plan['pending'][0]['id'], 'scout')

    def test_changed_quest_role_reward_and_resource_rules_fail(self):
        for key, value in [('role','vendor'), ('name','Different'), ('characterProfileKey','another')]:
            original = self.candidate['npcs'][0][key]; self.candidate['npcs'][0][key] = value
            with self.assertRaises(ValueError): self.plan()
            self.candidate['npcs'][0][key] = original
        self.candidate['resourceNodes'][0]['loot'][0]['chance'] = 1
        with self.assertRaises(ValueError): self.plan()

    def test_native_slots_animation_and_duplicate_identity_fail_closed(self):
        self.survey['actors'][1]['materials'].reverse()
        with self.assertRaises(ValueError): self.plan()
        self.survey['actors'][1]['materials'].reverse(); self.survey['actors'][0]['animation']['asset'] = '/Game/Other.Other'
        with self.assertRaises(ValueError): self.plan()
        self.survey['actors'][0]['animation']['asset'] = '/Game/Idle.Idle'; self.candidate['npcs'].append(copy.deepcopy(self.npc))
        with self.assertRaises(ValueError): self.plan()

    def test_resource_coordinates_and_identity_inventory_stay_coherent(self):
        self.candidate['props'][0]['x'] += 1
        with self.assertRaises(ValueError): self.plan()
        self.candidate['props'][0]['x'] -= 1; self.candidate['resourceNodes'].clear()
        with self.assertRaises(ValueError): self.plan()

    def test_staged_npc_addition_cannot_admit_itself(self):
        self.candidate['npcs'].append({**self.npc, 'id':'staged_camp_addition'})
        plan = self.plan()
        self.assertEqual(len(plan['ready']), 2)
        self.assertEqual(plan['pending'][0]['reason'], 'canonical-content-identity-pending')
        self.candidate['npcs'].pop(0)
        with self.assertRaises(ValueError): self.plan()

    def test_concave_outline_and_nearest_segment_projection(self):
        outline = [dict(z=x,x=y) for x,y in [(0,0),(4,0),(4,1),(1,1),(1,4),(0,4)]]
        self.assertTrue(inside_outline([50,350,0],outline)); self.assertFalse(inside_outline([350,350,0],outline))
        self.assertTrue(inside_outline([100,200,0],outline))
        paths = [dict(id='road',points=[dict(z=0,x=0),dict(z=10,x=0)])]
        result = nearest_route_points([500,200,0], paths)[0]
        self.assertEqual(result['point'], [500,0,0]); self.assertEqual(result['distanceCm'], 200)
        with self.assertRaises(ValueError): nearest_route_points([0,0,0], [])


if __name__ == '__main__': unittest.main()
