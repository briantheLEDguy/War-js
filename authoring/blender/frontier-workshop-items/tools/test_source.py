"""Independent construction, receiving-socket and frontage checks."""
import json,math,unittest
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=json.loads((ROOT/'source/items.json').read_text())

class WorkshopSourceTests(unittest.TestCase):
    def test_original_cages_are_closed_and_finite(self):
        for asset in SOURCE['assets'].values():
            for lod in asset['lods']:
                for obj in lod['objects']:
                    self.assertEqual(len(obj['vertices']),len(obj['grain_coordinates']))
                    self.assertTrue(all(len(p)==3 and all(math.isfinite(v) for v in p) for p in obj['vertices']+obj['grain_coordinates']))
                    self.assertEqual(len(obj['faces']),len(obj['corner_uv']));self.assertEqual(len(obj['faces']),len(obj['face_materials']))
                    edges=Counter()
                    for face,uv,material in zip(obj['faces'],obj['corner_uv'],obj['face_materials']):
                        self.assertGreaterEqual(len(face),3);self.assertEqual(len(face),len(set(face)));self.assertEqual(len(face),len(uv));self.assertIn(material,SOURCE['materials'])
                        self.assertTrue(all(0<=i<len(obj['vertices']) for i in face));self.assertTrue(all(len(p)==2 and all(math.isfinite(v) for v in p) for p in uv))
                        edges.update(tuple(sorted((a,b))) for a,b in zip(face,face[1:]+face[:1]))
                    self.assertTrue(all(count==2 for count in edges.values()),obj['name'])

    def test_cutters_have_visible_receivers(self):
        for asset in SOURCE['assets'].values():
            for lod in asset['lods']:
                by_name={obj['name']:obj for obj in lod['objects']};used=set()
                self.assertEqual(len(by_name),len(lod['objects']))
                for obj in lod['objects']:
                    for name in obj['cutters']:
                        self.assertEqual(obj['role'],'visible');self.assertEqual(by_name[name]['role'],'cutter');used.add(name)
                self.assertEqual(used,{name for name,obj in by_name.items() if obj['role']=='cutter'})
                for joint in asset['joints']:
                    self.assertIn(joint['part'],by_name)
                    for name in joint['receivers']:self.assertIn(name,by_name)

    def test_low_prop_scale_and_open_frontage(self):
        for key,asset in SOURCE['assets'].items():
            approach=asset['contract']['approachSource'];lo=approach['minimum'];hi=approach['maximum'];counts=[]
            for lod in asset['lods']:
                visible=[o for o in lod['objects'] if o['role']=='visible'];vertices=[v for o in visible for v in o['vertices']]
                self.assertGreaterEqual(min(v[2] for v in vertices),-.02);self.assertLess(max(v[2] for v in vertices),1.6)
                self.assertFalse(any(all(lo[i]<v[i]<hi[i] for i in range(3)) for v in vertices),key)
                counts.append(sum(sum(len(face)-2 for face in obj['faces']) for obj in visible))
            self.assertGreater(counts[0],counts[1]);self.assertGreater(counts[1],counts[2])

    def test_finished_source_ground_and_load_support(self):
        for key in SOURCE['assets']:
            for lod in range(3):
                report=json.loads((ROOT/'review'/f'{key}_lod{lod}_source.json').read_text())
                self.assertGreaterEqual(report['audit']['bounds_z_up']['minimum'][2],-.001)
                self.assertEqual([report['audit'][n] for n in ('totalBoundaryEdges','totalMultiFaceEdges','totalLooseEdges')],[0,0,0])
                self.assertEqual(len(report['cutSockets']),17 if key.endswith('repair_bench') else 6)
                for support in report['stoneSupports']:
                    self.assertGreaterEqual(support['minimumGapM'],-.001);self.assertLessEqual(support['minimumGapM'],.001)
                    if int(support['part'].rsplit('_',1)[1])>=6:self.assertGreaterEqual(len(support['nearestSupports']),3)

if __name__=='__main__':unittest.main()
