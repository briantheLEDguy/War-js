"""Focused invariants for original source, foliage thickness and painted normals."""
import hashlib,json,math,re,unittest
from pathlib import Path
from collections import Counter
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
SOURCE=json.loads((ROOT/'source/nature.json').read_text())
class NatureSource(unittest.TestCase):
    def test_no_primitive_constructors_in_any_tool(self):
        banned=re.compile(r'primitive_\w+_add|bmesh\.ops\.create_(?:cube|cone|grid|icosphere|uvsphere)|bpy\.ops\.mesh\.add_')
        for file in (ROOT/'tools').rglob('*.py'):
            if file.name==Path(__file__).name:continue
            self.assertIsNone(banned.search(file.read_text()),str(file))
    def test_all_lods_have_explicit_closed_source_shells(self):
        for key,asset in SOURCE['assets'].items():
            self.assertEqual([r['level'] for r in asset['lods']],[0,1,2])
            for lod in asset['lods']:
                for mesh in lod['objects']:
                    edges=Counter();self.assertEqual(len(mesh['faces']),len(mesh['corner_uv']))
                    for face,uv in zip(mesh['faces'],mesh['corner_uv']):
                        self.assertEqual(len(face),len(uv));self.assertGreaterEqual(len(face),3)
                        self.assertTrue(all(0<=i<len(mesh['vertices']) for i in face))
                        self.assertTrue(all(math.isfinite(v) for point in uv for v in point))
                        for a,b in zip(face,face[1:]+face[:1]):edges[tuple(sorted((a,b)))]+=1
                    self.assertEqual(set(edges.values()),{2},(key,lod['level'],mesh['name']))
    def test_distance_geometry_reduces_without_collapsed_plant_height(self):
        for key,asset in SOURCE['assets'].items():
            counts=[];heights=[]
            for lod in asset['lods']:
                points=[p for mesh in lod['objects'] for p in mesh['vertices']];counts.append(len(points));heights.append(max(p[2] for p in points)-min(p[2] for p in points))
            self.assertLess(counts[2],counts[0]*.45,key)
            self.assertGreaterEqual(heights[2],heights[0]*.93,key)
    def test_painted_normals_follow_signed_gradient(self):
        records=json.loads((ROOT/'textures/paint-records.json').read_text())
        self.assertEqual(records['painterSha256'],hashlib.sha256((ROOT/'tools/paint_nature.py').read_bytes()).hexdigest())
        for record in records['records']:
            for channel in record['channels'].values():self.assertEqual(channel['sha256'],hashlib.sha256((ROOT/channel['file']).read_bytes()).hexdigest())
            height=np.asarray(Image.open(ROOT/record['channels']['height']['file']),np.float32)/255
            rgb=np.asarray(Image.open(ROOT/record['channels']['normal']['file']),np.float32)/255
            kind=SOURCE['materials'][record['material']]['kind'];strength=2.5 if kind in ('bark','rock','mineral') else 1.1
            dy,dx=np.gradient(height);expected=np.stack((-dx*strength,dy*strength,np.ones_like(dx)),axis=-1);expected/=np.linalg.norm(expected,axis=-1)[...,None]
            self.assertLess(float(np.max(np.abs(rgb-(expected*.5+.5)))),.0021,record['material'])
    def test_only_trunk_and_rock_block_movement(self):
        for key,asset in SOURCE['assets'].items():
            contract=asset['contract']
            self.assertEqual(bool(contract['colliders']),contract['kind'] in ('tree','rock'))
            self.assertEqual(contract['walkableSurfaces'],[])
if __name__=='__main__':unittest.main()
