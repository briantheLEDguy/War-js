"""Source identity and visual binding failures must stop city regeneration."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/unreal"))
from capital_geography import source_map
from capital_resources import resource_bindings, NODE_IDS


class ResourceBindingsTests(unittest.TestCase):
    def test_preserves_source_node_and_visual_fields(self):
        source=source_map()
        rows=resource_bindings(source)
        self.assertEqual([r["node"]["id"] for r in rows],list(NODE_IDS))
        self.assertTrue(all(r["node"] in source["resourceNodes"] and r["prop"] in source["props"] for r in rows))
        self.assertEqual(len(source["resourceNodes"])-len(rows),6)

    def test_missing_source_node_blocks_generation(self):
        source=deepcopy(source_map())
        source["resourceNodes"]=[n for n in source["resourceNodes"] if n["id"]!=NODE_IDS[0]]
        with self.assertRaises(KeyError): resource_bindings(source)

    def test_missing_duplicate_or_replaced_visual_blocks_generation(self):
        for change in ("missing","duplicate","replace","move","scale"):
            source=deepcopy(source_map())
            prop=next(p for p in source["props"] if p["id"]==NODE_IDS[0]+"_visual")
            if change=="missing": source["props"].remove(prop)
            elif change=="duplicate": source["props"].append(deepcopy(prop))
            elif change=="replace": prop["assetKey"]="training_dummy"
            elif change=="move": prop["x"]+=1
            else: prop["scale"]=float("nan")
            with self.subTest(change=change), self.assertRaises((KeyError,ValueError)):
                resource_bindings(source)


if __name__=="__main__": unittest.main()
