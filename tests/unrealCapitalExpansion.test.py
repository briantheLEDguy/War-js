"""Expansion safety and spatial contracts; rendered/native evidence is separate."""
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from capital_expansion import (recipes, INTERIORS, PALETTES, rectangle, overlaps,
                               SpatialIndex, require_unchanged, source_obstacles, validate_plan,
                               admit_mesh, plan_city, walking_route, digest, ZONES, DISTRICTS, canonical_actor_state)


class ExpansionTests(unittest.TestCase):
    def test_attachment_reload_accepts_only_equivalent_quaternion_signs(self):
        state={'transform':[1,2,3,0,0,.707107,.707107,1,1,1],
               'components':[{'transform':[0,0,0,0,0,1,0,1,1,1]}]}
        opposite=copy.deepcopy(state)
        opposite['transform'][3:7]=[-n for n in opposite['transform'][3:7]]
        opposite['components'][0]['transform'][3:7]=[-n for n in opposite['components'][0]['transform'][3:7]]
        self.assertEqual(canonical_actor_state(state),canonical_actor_state(opposite))
        for index in (0,3,7):
            edited=copy.deepcopy(opposite);edited['transform'][index]+=.001
            self.assertNotEqual(canonical_actor_state(state),canonical_actor_state(edited))

    def valid_plan(self):
        rows=[]
        for zone in ZONES:
            for i in range(120):
                rows.append(dict(id=f'{zone}_{i}',zone=zone, district=DISTRICTS[zone][i%len(DISTRICTS[zone])],
                                 recipe=f'{zone}_{i%12}',kind=INTERIORS[i] if i<12 else 'residence',
                                 interior=i<12,upperFloor=i<7,position=[i*3000,0,0],yaw=0,
                                 footprint=rectangle((i*3000,0),(500,500),0),height=600))
        return {'placements':rows}

    def test_plan_enforces_counts_variety_and_unique_identities(self):
        validate_plan(self.valid_plan())
        for mutation in ('duplicate','count','composition','district','upper'):
            plan=self.valid_plan(); rows=plan['placements']
            if mutation=='duplicate': rows[1]['id']=rows[0]['id']
            elif mutation=='count': rows.pop()
            elif mutation=='composition':
                for row in rows[:30]: row['recipe']='repeated'
            elif mutation=='district':
                for row in rows[:12]: row['district']='gateward'
            elif mutation=='upper':
                for row in rows[:12]: row['upperFloor']=False
            with self.subTest(mutation=mutation),self.assertRaises(ValueError): validate_plan(plan)

    def test_asset_admission_rejects_ambiguous_unfingerprinted_and_blueprint_sources(self):
        row=dict(name='SM_Bench',path='/Game/Medieval_Mod_Town/Meshes/SM_Bench.SM_Bench',
                 materials=['/Game/Medieval_Mod_Town/M_Wood'],sha256='a'*64)
        self.assertEqual(admit_mesh([row],'SM_Bench'),row)
        bad=[[],[row,row],[{**row,'sha256':''}],[{**row,'materials':[None]}],
             [{**row,'path':'/Game/Arbitrary/BP_Bench.BP_Bench'}]]
        for inventory in bad:
            with self.assertRaises(ValueError): admit_mesh(inventory,'SM_Bench')

    def test_reviewed_plan_cannot_be_silently_moved(self):
        plan=self.valid_plan(); plan['signature']=digest(plan)
        validate_plan(plan)
        plan['placements'][0]['position'][0]+=1
        with self.assertRaisesRegex(ValueError,'fingerprint'): validate_plan(plan)

    def test_spatial_planning_rerun_preserves_ids_transforms_and_variation(self):
        templates={r['id']:{**r,'extent':[150,150,300]} for r in recipes()}
        candidates=[dict(xy=[i*3000,0],z=0,yaw=0,district=DISTRICTS['riftspire_capital'][i%6],score=i)
                    for i in range(120)]
        source={'spawnPoint':{'x':-1000,'z':-1000}}
        baseline={'origin':[0,0,0],'actors':[]}
        with patch('capital_expansion.city_candidates',return_value=candidates):
            first=plan_city('riftspire_capital',source,baseline,templates,lambda *args: 0)
            second=plan_city('riftspire_capital',source,baseline,templates,lambda *args: 0)
        self.assertEqual(first,second)
        self.assertEqual(len(first[0]),120)
        self.assertEqual(first[1],[])

    def test_walking_routes_return_through_the_door_and_reach_upper_landings(self):
        for row in recipes():
            if not row['interior']: continue
            route=walking_route(row)
            self.assertEqual(route[0],route[-1])
            self.assertEqual(route[0][0],row['entrance'][0])
            self.assertEqual(max(p[2] for p in route),310 if row['upperFloor'] else 10)

    def test_real_composition_variety_and_room_mix(self):
        rows=recipes()
        self.assertEqual(rows,recipes())
        self.assertEqual(len(rows),len({r['id'] for r in rows}))
        for realm in ('aegis','riftspire'):
            city=[r for r in rows if r['id'].startswith(realm+'_')]
            self.assertEqual(len(city),36)
            interiors=[r for r in city if r['interior']]
            self.assertEqual([r['kind'] for r in interiors],list(INTERIORS))
            self.assertGreaterEqual(sum(r['upperFloor'] for r in interiors),4)
            exteriors=[r for r in city if '_residence_' in r['id']]
            self.assertEqual(len({r['components'][0]['mesh'] for r in exteriors}),12)
            self.assertGreaterEqual(len({tuple(r['roomSize']) for r in interiors}),6)

    def test_no_door_leaf_can_seal_interiors(self):
        for recipe in recipes():
            if not recipe['interior']: continue
            names=[p['mesh'] for p in recipe['components']]
            self.assertNotIn('SM_Door',names)
            self.assertNotIn('SM_MH_02_Wood_Door_01',names)
            self.assertIn('SM_MH_02_Stone_Wall_Door_01',names)
            self.assertGreaterEqual(len(recipe['routes']),5)
            if recipe['upperFloor']:
                self.assertTrue(any(p[2]==310 for p in recipe['routes']))

    def test_oriented_footprints_keep_diagonal_street_space(self):
        a=rectangle((0,0),(1000,100),45)
        self.assertTrue(overlaps(a,rectangle((0,0),(50,50),0)))
        self.assertFalse(overlaps(a,rectangle((300,-300),(50,50),0)))

    def test_vertical_terraces_do_not_block_one_another(self):
        index=SpatialIndex(); shape=rectangle((0,0),(1000,1000),0)
        index.add(shape,-1000,-500)
        self.assertFalse(index.blocked(shape,0,500))
        self.assertTrue(index.blocked(shape,-800,-600))

    def test_changed_city_refuses_rebuild(self):
        require_unchanged({'map':'original'},{'map':'original'})
        with self.assertRaisesRegex(ValueError,'preserve owner edits'):
            require_unchanged({'map':'original'},{'map':'edited'})

    def test_roads_arrivals_and_services_are_reserved(self):
        source={'props':[],'paths':[{'width':4,'points':[{'x':0,'z':0},{'x':20,'z':0}]}],
                'npcs':[{'x':50,'z':50}],'spawnPoint':{'x':-50,'z':-50}}
        obstacles=source_obstacles(source)
        for point in ((1000,0),(5000,5000),(-5000,-5000)):
            self.assertTrue(any(overlaps(rectangle(point,(100,100),0),o) for o in obstacles))

    def test_palette_roles_are_distinct(self):
        self.assertEqual(len(PALETTES),11)
        self.assertEqual(len(set(PALETTES.values())),11)
        self.assertTrue(all(len(set(p))==3 for p in PALETTES.values()))


if __name__=='__main__': unittest.main()
