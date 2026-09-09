"""Independent source-shell, LOD and metric tangent-normal checks."""
import hashlib,json,math,unittest
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
SOURCE=json.loads((ROOT/'source/floor.json').read_text())

class FloorSourceTests(unittest.TestCase):
    def test_current_design_binding(self):
        self.assertEqual(SOURCE['designSha256'],hashlib.sha256((ROOT/'source/design.json').read_bytes()).hexdigest())

    def test_literal_source_shells_are_closed(self):
        for asset in SOURCE['assets'].values():
            for lod in asset['lods']:
                for obj in lod['objects']:
                    self.assertEqual(len(obj['faces']),len(obj['corner_uv']))
                    self.assertTrue(all(len(p)==3 and all(math.isfinite(c) for c in p) for p in obj['vertices']))
                    self.assertEqual(len(obj['vertices']),len(obj['grain_coordinates']))
                    self.assertTrue(all(len(p)==3 and all(math.isfinite(c) for c in p) for p in obj['grain_coordinates']))
                    edges=Counter()
                    for face,uv,material in zip(obj['faces'],obj['corner_uv'],obj['face_materials']):
                        self.assertGreaterEqual(len(face),3);self.assertEqual(len(set(face)),len(face));self.assertEqual(len(face),len(uv))
                        self.assertTrue(all(0<=i<len(obj['vertices']) for i in face));self.assertTrue(0<=material<len(obj['materials']))
                        self.assertTrue(all(len(p)==2 and all(math.isfinite(c) for c in p) for p in uv))
                        edges.update(tuple(sorted((a,b))) for a,b in zip(face,face[1:]+face[:1]))
                    self.assertTrue(all(n==2 for n in edges.values()),obj['name'])

    def test_low_floor_scale_and_independent_lods(self):
        for asset in SOURCE['assets'].values():
            counts=[]
            for lod in asset['lods']:
                count=sum(sum(len(f)-2 for f in obj['faces']) for obj in lod['objects']);counts.append(count)
                self.assertLessEqual(count,[40000,15000,4000][lod['level']])
                points=[p for obj in lod['objects'] for p in obj['vertices']]
                self.assertLess(min(p[2] for p in points),0)
                self.assertGreater(min(p[2] for p in points),-.06)
                self.assertLess(max(p[2] for p in points),.85)
            self.assertGreater(counts[0],counts[1]);self.assertGreater(counts[1],counts[2])

    def test_normal_maps_follow_saved_metric_height(self):
        record=json.loads((ROOT/'textures/paint-records.json').read_text())
        for material in record['materials']:
            info=material['height'];height=np.array(Image.open(ROOT/info['file']),dtype=np.float64)/65535*info['maximumM']
            rows,columns=height.shape;dx=np.gradient(height,axis=1)*columns/info['uSpanM'];dy=np.gradient(height,axis=0)*rows/info['vSpanM']
            normal=np.stack([-dx,dy,np.ones_like(dx)],axis=-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
            expected=np.clip((normal*.5+.5)*255,0,255);actual=np.array(Image.open(ROOT/material['channels']['normal']['file']),dtype=np.float64)
            self.assertLessEqual(float(np.max(np.abs(expected-actual))),1.1,material['material'])
            orm=np.array(Image.open(ROOT/material['channels']['orm']['file']))
            self.assertTrue(np.all(orm[:,:,2]==0));self.assertTrue(np.all(orm[:,:,1]>=160))

if __name__=='__main__':unittest.main()
