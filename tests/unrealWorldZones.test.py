import copy
import importlib.util
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('world_zones', ROOT/'scripts/unreal/world_zones.py')
rules = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rules)


class WorldZoneTests(unittest.TestCase):
    def test_every_campaign_zone_has_exactly_one_batch(self):
        import json
        source = {p.stem for p in (ROOT/'public/assets/maps').glob('*.json')
                  if json.loads(p.read_text()).get('campaign')}
        ordered = [zone for batch in rules.BATCHES for zone in batch]
        self.assertEqual(set(ordered), source)
        self.assertEqual(len(ordered), len(source))

    def test_ownership_uses_bounds_and_rejects_ambiguity(self):
        zones = [{'id':'field', 'origin':[0,0,0], 'size':1200}]
        self.assertEqual(rules.owner_zone(zones, [60000,-60000,90000]), 'field')
        for position in ([60001,0,0], [math.nan,0,0]):
            with self.assertRaises(ValueError): rules.owner_zone(zones, position)
        with self.assertRaises(ValueError): rules.owner_zone(zones+zones, [0,0,0])

    def test_partition_rejects_lost_added_or_changed_authored_state(self):
        before = {'a':{'transform':[1,2,3], 'mesh':'original', 'materials':['stone']}}
        rules.validate_partition(before, copy.deepcopy(before))
        for after in ({}, {**before,'b':{}}, {'a':{**before['a'],'materials':['mud']}}):
            with self.assertRaises(ValueError): rules.validate_partition(before, after)


if __name__ == '__main__': unittest.main()
