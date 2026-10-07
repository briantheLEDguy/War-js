import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from citadel_review_world import review_packages,checked_residents,residents,routing_bindings


class Actor:
    def __init__(self,kind,**properties):self.kind=kind;self.properties=properties
    def get_class(self):return self
    def get_name(self):return self.kind
    def get_editor_property(self,key):return self.properties[key]


class ReviewWorldTests(unittest.TestCase):
    def test_exact_private_review_name_and_real_calendar_date(self):
        self.assertEqual(review_packages('abcdef123456','20261007')['map'],
            '/Game/WorldRebuild/CitadelHumanReview_20261007_abcdef123456/Walkthrough')
        self.assertEqual(review_packages('abcdef123456','20261007')['population'].rsplit('/',1)[1],
            'Residents_abcdef123456')
        for revision,date in [('ABCDEF123456','20261007'),('abcdef123456/extra','20261007'),
                              ('abcdef123456','20260230'),('abcdef123456','20261007/..')]:
            with self.assertRaises(ValueError):review_packages(revision,date)

    def test_explicit_routing_binding_includes_destinations_and_gate_radius(self):
        point=type('Vector',(),dict(x=1,y=2,z=3))()
        portal=Actor('WarZonePortal',route_id='from',destination_route_id='to',
            arrival_location=point,radius=900,destination_built=True)
        before=routing_bindings([portal])
        portal.properties['arrival_location']=type('Vector',(),dict(x=1,y=2,z=4))()
        self.assertNotEqual(routing_bindings([portal]),before)
        portal.properties['arrival_location']=point;portal.properties['destination_route_id']='other'
        self.assertNotEqual(routing_bindings([portal]),before)
        self.assertEqual(before[0]['radius'],900)
        self.assertTrue(before[0]['built'])

    def test_residents_reject_route_objective_and_furniture_overlap(self):
        row=copy.deepcopy(residents()[0]);point=row['pointCm']
        plan=dict(routes=[],spawnApproaches=[],objectives=[],optionalObjectives=[])
        with patch('citadel_review_world.residents',return_value=[row]):
            self.assertEqual(len(checked_residents(plan,[])),1)
            blocked=copy.deepcopy(plan);blocked['routes']=[dict(points=[[26000,-1400,6010],[28000,-1400,6010]],width=1200)]
            with self.assertRaisesRegex(ValueError,'signed route'):checked_residents(blocked,[])
            blocked=copy.deepcopy(plan);blocked['objectives']=[point]
            with self.assertRaisesRegex(ValueError,'objective'):checked_residents(blocked,[])
            bounds=[[point[0]-200,point[1]-200,point[2]],[point[0]+200,point[1]+200,point[2]+150]]
            with self.assertRaisesRegex(ValueError,'furnishings'):checked_residents(plan,[bounds])


if __name__=='__main__':unittest.main()
