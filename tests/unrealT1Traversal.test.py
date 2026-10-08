import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_traversal import traversal_config, validate_traversal


class T1TraversalTest(unittest.TestCase):
    def fixture(self):
        receipt = dict(signature='a'*64)
        zone = dict(id='sunmeadow_march', map='/Game/WorldRebuild/T1Redesign_Homes_aaaaaaaaaaaa_123/sunmeadow_march/Review',
                    homes=[dict(id='home', approachPoints=1, route=[[0, i*100, 10] for i in range(7)])])
        source = dict(id=zone['id'], paths=[dict(id='advance', points=[dict(x=1, z=2, y=3), dict(x=4, z=5, y=6)])],
                      orvrLayout=dict(caravanRoutes=[]))
        return receipt, zone, source

    def test_complete_inventory_and_coordinate_conversion(self):
        args = self.fixture()
        config = traversal_config(*args, True)
        self.assertEqual([r['id'] for r in config['routes']], ['home', 'advance_forward', 'advance_reverse'])
        self.assertEqual(config['routes'][1]['points'][0]['position'], [200, 100, 300])
        self.assertEqual(config['routes'][1]['points'], list(reversed(config['routes'][2]['points'])))
        self.assertTrue(config['routes'][0]['points'][0]['terrain'])
        self.assertFalse(config['routes'][0]['points'][1]['indoor'])
        self.assertTrue(config['routes'][0]['points'][3]['indoor'])
        self.assertFalse(config['capture'])
        self.assertEqual(len(traversal_config(*args, False)['routes']), 1)
        for mutate in ('map', 'nan', 'duplicate'):
            receipt, zone, source = copy.deepcopy(args)
            if mutate == 'map': zone['map'] = '/Game/Capitals/AegisCapital'
            elif mutate == 'nan': zone['homes'][0]['route'][0][0] = float('nan')
            else: source['paths'] *= 2
            with self.assertRaises(ValueError): traversal_config(receipt, zone, source, True)

    def test_movement_evidence_does_not_grant_other_gates(self):
        config = traversal_config(*self.fixture(), False)
        row = dict(id='home', completed=True, reachedWaypoints=7, inRouteTeleports=0, jumps=0, longestAirborneSeconds=0, distanceCm=600)
        report = dict(passed=True, signature=config['signature'], map=config['map'], routes=[row], visibleCharacterReady=True,
                      developmentFlight=False, capsuleRadiusCm=42, capsuleHalfHeightCm=96, maxStepHeightCm=45, maxWalkSpeedCm=600,
                      drivingAccepted=False, visualApproved=False, cameraAccepted=False, gameplayAccepted=False)
        validate_traversal(report, config)
        for field, value in [('capsuleRadiusCm', 20), ('visualApproved', True), ('developmentFlight', True)]:
            invalid = copy.deepcopy(report); invalid[field] = value
            with self.assertRaises(ValueError): validate_traversal(invalid, config)
        for field, value in [('inRouteTeleports', 1), ('reachedWaypoints', 6), ('longestAirborneSeconds', 1)]:
            invalid = copy.deepcopy(report); invalid['routes'][0][field] = value
            with self.assertRaises(ValueError): validate_traversal(invalid, config)

    def test_material_candidate_requires_its_own_signature_and_namespace(self):
        receipt, zone, source = self.fixture()
        receipt['kind'] = 'materials'
        with self.assertRaises(ValueError): traversal_config(receipt, zone, source, True)
        zone['map'] = zone['map'].replace('T1Redesign_Homes_', 'T1Redesign_Materials_')
        self.assertEqual(traversal_config(receipt, zone, source, True)['map'], zone['map'])
        receipt['signature'] = 'b'*64
        with self.assertRaises(ValueError): traversal_config(receipt, zone, source, True)


if __name__ == '__main__':
    unittest.main()
