import copy
import math
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/unreal'))
from t1_candidate_rebase import grounded_inventory, conform_ground_overlay

class Plane:
    def __init__(self, x=0, z=0, offset=0): self.x, self.z, self.offset = x, z, offset
    def height_cm(self, x, z): return self.x*x + self.z*z + self.offset

class CandidateRebaseTests(unittest.TestCase):
    def setUp(self):
        self.states = {label: dict(location=p, materials=['private/stone'], rotation=[0,23,0]) for label,p in {
            'home': [100,200,300], 'home_light': [150,250,550], 'keep': [400,500,600],
            'keep_gate': [450,550,600], 'free_rock': [700,900,80], 'backdrop': [900000,0,0]}.items()}
        self.old, self.new = Plane(), Plane(20, 30, 7)

    def test_complete_assemblies_keep_internal_offsets_and_source_axes(self):
        old = copy.deepcopy(self.states)
        result, proof = grounded_inventory(self.states, self.old, self.new, {'home': 45, 'keep': -37}, ['backdrop'])
        self.assertEqual(self.states, old)
        for label,delta in {'home':45, 'home_light':45, 'keep':-37, 'keep_gate':-37, 'free_rock':397, 'backdrop':0}.items():
            expected=copy.deepcopy(old[label]);expected['location'][2]+=delta
            self.assertEqual(result[label],expected)
        self.assertEqual(result['home_light']['location'][2]-result['home']['location'][2],250)
        self.assertFalse(proof['terrainFootingAccepted']);self.assertFalse(proof['authorityIntegrated'])

    def test_rejects_ambiguous_nested_roots_or_fixed_assembly_members_atomically(self):
        old=copy.deepcopy(self.states)
        for groups,fixed in [({'home':1,'home_light':2},[]),({'keep':1},['keep_gate'])]:
            with self.assertRaises(ValueError):grounded_inventory(self.states,self.old,self.new,groups,fixed)
            self.assertEqual(self.states,old)

    def test_supports_keep_assemblies_without_a_synthetic_root_actor(self):
        states=copy.deepcopy(self.states);del states['keep']
        result,proof=grounded_inventory(states,self.old,self.new,{'keep':-37},['backdrop'])
        self.assertEqual(result['keep_gate']['location'][2],563)
        self.assertEqual(proof['actorDeltasCm']['keep_gate'],-37)

    def test_requires_exact_roots_and_fixed_actors(self):
        for groups,fixed in [({'missing':1},[]),({},['missing'])]:
            with self.assertRaises(ValueError):grounded_inventory(self.states,self.old,self.new,groups,fixed)

    def test_rejects_invalid_locations_and_unbounded_source_or_group_changes(self):
        for value in [math.nan,math.inf,True,'1',25001]:
            with self.assertRaises(ValueError):grounded_inventory(self.states,self.old,self.new,{'home':value})
        with self.assertRaises(ValueError):grounded_inventory(self.states,self.old,Plane(offset=25001),{})
        for value in [math.nan,True,'1']:
            states=copy.deepcopy(self.states);states['free_rock']['location'][0]=value
            with self.assertRaises(ValueError):grounded_inventory(states,self.old,self.new,{})

class GroundOverlayTests(unittest.TestCase):
    def overlay(self):
        return dict(positions=[[0,0,3],[100,0,3],[0,100,3]],normals=[[0,0,1]]*3,
            indices=[0,1,2],uvs=[[0,0],[1,0],[0,1]],vertexColors=[[1,1,1,0],[1,1,1,.5],[1,1,1,1]])

    def test_reconforms_corners_preserves_fade_uvs_and_upward_normal_orientation(self):
        data=self.overlay();old=copy.deepcopy(data)
        for order in ([0,1,2],[0,2,1]):
            data['indices']=order;result,proof=conform_ground_overlay(data,Plane(),Plane(20,30,7))
            self.assertEqual(result['positions'],[[0,0,10],[100,0,40],[0,100,30]])
            self.assertEqual(result['vertexColors'],data['vertexColors']);self.assertEqual(result['uvs'],data['uvs'])
            self.assertEqual(result['indices'],order)
            for n in result['normals']:
                for a,b in zip(n,[-.3/math.sqrt(1.13),-.2/math.sqrt(1.13),1/math.sqrt(1.13)]):self.assertAlmostEqual(a,b)
            self.assertFalse(proof['collisionAccepted'])
        data['indices']=old['indices'];self.assertEqual(data,old)

    def test_expanded_shared_authoring_vertices_each_receive_exactly_one_height_change(self):
        data=self.overlay();a,b,c=data['positions']
        data['positions']=[a,b,c,a,b,c];data['normals']*=2
        data['uvs']*=2;data['vertexColors']*=2;data['indices']=list(range(6))
        before=copy.deepcopy(data)
        result,proof=conform_ground_overlay(data,Plane(),Plane(offset=37))
        self.assertEqual(data,before)
        self.assertEqual(result['positions'],[[0,0,40],[100,0,40],[0,100,40]]*2)
        self.assertEqual(proof['maximumCornerDeltaCm'],37)
        self.assertIsNot(result['positions'][0],result['positions'][3])
        self.assertEqual(result['uvs'],data['uvs']);self.assertEqual(result['vertexColors'],data['vertexColors'])

    def test_retains_inherited_coincident_edge_corners(self):
        data=self.overlay();data['positions'][1]=data['positions'][0][:]
        result,proof=conform_ground_overlay(data,Plane(),Plane(offset=34))
        self.assertTrue(proof['requiresDegenerateSourceReconciliation'])
        self.assertEqual(proof['inheritedDegenerateTriangles'],1);self.assertEqual(result['normals'],data['normals'])
        self.assertEqual(result['indices'],data['indices'])

    def test_rejects_new_collapse_and_invalid_or_unbounded_corners_without_mutation(self):
        class Collapse:
            def height_cm(self,x,z):return -10 if z==.5 else 0
        data=self.overlay();data['positions']=[[0,0,0],[100,0,0],[50,0,10]];before=copy.deepcopy(data)
        with self.assertRaises(ValueError):conform_ground_overlay(data,Plane(),Collapse())
        self.assertEqual(data,before)
        for indices in ([0,1],[0,1,3],[False,1,2]):
            bad=self.overlay();bad['indices']=indices
            with self.assertRaises(ValueError):conform_ground_overlay(bad,Plane(),Plane())
        with self.assertRaises(ValueError):conform_ground_overlay(self.overlay(),Plane(),Plane(offset=25001))

if __name__ == '__main__': unittest.main()
