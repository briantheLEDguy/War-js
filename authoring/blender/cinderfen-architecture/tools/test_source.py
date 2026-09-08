"""Independent source invariants for original Cinderfen construction."""
import ast
from collections import Counter
import json
import math
from pathlib import Path
import unittest
from PIL import Image,ImageFilter
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
SOURCE=json.loads((ROOT/'source/architecture.json').read_text())


class CinderfenConstruction(unittest.TestCase):
    def test_no_primitive_constructor_in_any_tool(self):
        for path in (ROOT/'tools').glob('*.py'):
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node,ast.Call):
                    name=ast.unparse(node.func)
                    self.assertNotIn('primitive_',name,str(path));self.assertNotIn('bmesh.ops.create_',name,str(path))

    def test_original_closed_cages_and_valid_corner_uvs(self):
        sun=json.loads((ROOT.parent/'sunmeadow-architecture/source/architecture.json').read_text())
        originals={json.dumps(part['vertices']) for part in sun['parts'].values()}
        for name,part in SOURCE['parts'].items():
            self.assertNotIn(json.dumps(part['vertices']),originals,name)
            for record in [part]+([part['lod2']] if 'lod2' in part else []):
                edges=Counter();vertices=record['vertices'];self.assertEqual(len(record['faces']),len(record['corner_uv']),name)
                if 'face_materials' in record:
                    self.assertEqual(len(record['face_materials']),len(record['faces']),name)
                    self.assertTrue(all(material in SOURCE['materials'] for material in record['face_materials']),name)
                for face,uv in zip(record['faces'],record['corner_uv']):
                    self.assertEqual(len(face),len(uv),name)
                    self.assertTrue(all(0<=index<len(vertices) for index in face),name)
                    self.assertTrue(all(math.isfinite(value) for point in uv for value in point),name)
                    area=abs(sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(uv,uv[1:]+uv[:1])));self.assertGreater(area,1e-10,name)
                    for a,b in zip(face,face[1:]+face[:1]):edges[tuple(sorted((a,b)))]+=1
                self.assertTrue(all(count==2 for count in edges.values()),name)

    def test_distant_boundaries_preserve_real_volume(self):
        for name,part in SOURCE['parts'].items():
            if 'lod2' not in part:continue
            for axis in range(3):
                span=lambda item:max(v[axis] for v in item['vertices'])-min(v[axis] for v in item['vertices'])
                self.assertGreater(span(part['lod2'])/span(part),.85,name)

    def test_all_seven_modules_have_exact_source_placements(self):
        self.assertEqual(len(SOURCE['assets']),7)
        for key,asset in SOURCE['assets'].items():
            self.assertTrue(key.startswith('frontier_cinderfen_'))
            self.assertGreater(len(asset['instances']),30,key)
            for instance in asset['instances']:
                self.assertIn(instance['part'],SOURCE['parts'])
                self.assertTrue(all(value>0 for value in instance['scale']))
                self.assertIn(instance.get('material',SOURCE['parts'][instance['part']]['material']),SOURCE['materials'])

    def test_pbr_channels_contain_authored_independent_surface_detail(self):
        for material in SOURCE['materials']:
            normal=Image.open(ROOT/'textures/source'/f'{material}_normal.png').convert('RGB')
            roughness=Image.open(ROOT/'textures/source'/f'{material}_roughness.png').convert('L')
            height=Image.open(ROOT/'textures/source'/f'{material}_height.png').convert('L')
            self.assertEqual(normal.size,(1024,1024));self.assertGreater(len(normal.getcolors(1048576)),8,material)
            self.assertGreater(roughness.getextrema()[1]-roughness.getextrema()[0],5,material)
            self.assertGreater(height.getextrema()[1]-height.getextrema()[0],5,material)
            self.assertNotEqual(height.tobytes(),roughness.tobytes(),material)
            relief=np.asarray(height.filter(ImageFilter.GaussianBlur(.38)),dtype=np.float32)
            dx=np.roll(relief,-1,axis=1)-np.roll(relief,1,axis=1);dy=np.roll(relief,-1,axis=0)-np.roll(relief,1,axis=0)
            encoded=np.asarray(normal,dtype=np.float32)-127.5
            self.assertLess(float(np.sum(encoded[:,:,0]*dx)),0,material+' tangent X opposes height slope')
            self.assertGreater(float(np.sum(encoded[:,:,1]*dy)),0,material+' tangent Y corrects top-left raster orientation')

    def test_stair_slabs_block_heads_below_but_leave_their_top_supported(self):
        stair=SOURCE['assets']['frontier_cinderfen_wall_stair']['contract']
        for tread in [s for s in stair['walkableSurfaces'] if s['id'].startswith('tread_')]:
            self.assertTrue(any(abs(c['x']-tread['x'])<1e-6 and abs(c['z']-tread['z'])<1e-6 and abs(c['maxY']-tread['fromY'])<1e-6 and .10<c['maxY']-c['minY']<.15 for c in stair['colliders']),tread['id'])

    def test_gate_has_six_metre_full_depth_opening_and_independent_hinges(self):
        gate=SOURCE['assets']['frontier_cinderfen_gatehouse'];self.assertEqual(gate['contract']['passage_clearance'],[6,4.8])
        arch=SOURCE['parts']['gate_arch']['vertices'];self.assertEqual(max(v[1] for v in arch)-min(v[1] for v in arch),12)
        leaves=SOURCE['assets']['frontier_cinderfen_gate_leaves'];self.assertEqual(leaves['contract']['hinges_z_up'],[[-3,0,0],[3,0,0]])
        groups=Counter(i['rigid_group'] for i in leaves['instances']);self.assertEqual(set(groups),{'gate_leaf_left','gate_leaf_right'});self.assertEqual(len(set(groups.values())),1)

    def test_stairs_and_defense_decks_share_six_point_three_level(self):
        gate=SOURCE['assets']['frontier_cinderfen_gatehouse']['contract'];wall=SOURCE['assets']['frontier_cinderfen_curtain_walk']['contract'];stair=SOURCE['assets']['frontier_cinderfen_wall_stair']['contract']
        self.assertEqual(gate['defense_deck_height'],wall['wall_walk_height']);self.assertEqual(stair['top_socket_runtime'][1],wall['wall_walk_height'])
        treads=[s for s in stair['walkableSurfaces'] if s['id'].startswith('tread_')]
        self.assertEqual(len(treads),36);self.assertAlmostEqual(min(s['toY'] for s in treads),.175);self.assertAlmostEqual(max(s['toY'] for s in treads),6.3)
        self.assertEqual(sum(i['part']=='step_tread' for i in SOURCE['assets']['frontier_cinderfen_wall_stair']['instances']),36)


if __name__=='__main__':unittest.main()
