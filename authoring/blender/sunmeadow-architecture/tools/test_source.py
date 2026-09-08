"""Authoring invariants independent of Blender's exporter."""
import ast
from collections import Counter
import json
import math
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
SOURCE=json.loads((ROOT/'source/architecture.json').read_text())


class OriginalArchitectureSource(unittest.TestCase):
    def test_every_tool_avoids_stock_primitive_constructors(self):
        for path in (ROOT/'tools').glob('*.py'):
            tree=ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node,ast.Call):
                    function=ast.unparse(node.func)
                    self.assertNotIn('primitive_',function,str(path))
                    self.assertNotIn('bmesh.ops.create_',function,str(path))

    def test_control_cages_are_explicit_closed_surfaces_with_corner_uvs(self):
        for name,part in SOURCE['parts'].items():
            vertices=part['vertices'];edges=Counter()
            self.assertGreaterEqual(len(vertices),8,name)
            self.assertTrue(any(len({v[axis] for v in vertices})>2 for axis in range(3)),name)
            self.assertEqual(part['source'],'literal_authored_mesh')
            for face,uv in zip(part['faces'],part['corner_uv']):
                self.assertEqual(len(face),len(uv),name)
                self.assertTrue(all(0<=i<len(vertices) for i in face),name)
                self.assertTrue(all(math.isfinite(x) for coord in uv for x in coord),name)
                area=abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(uv,uv[1:]+uv[:1])))
                self.assertGreater(area,1e-9,name)
                for a,b in zip(face,face[1:]+face[:1]):edges[tuple(sorted((a,b)))]+=1
            self.assertTrue(all(count==2 for count in edges.values()),name)

    def test_gate_pair_is_independently_hinged(self):
        asset=SOURCE['assets']['frontier_sunmeadow_gate_leaves']
        self.assertEqual(asset['contract']['hinges_z_up'],[[-3,0,0],[3,0,0]])
        groups=Counter(item['rigid_group'] for item in asset['instances'])
        self.assertEqual(set(groups),{'gate_leaf_left','gate_leaf_right'})
        self.assertEqual(groups['gate_leaf_left'],groups['gate_leaf_right'])

    def test_distant_boundaries_keep_construction_volume(self):
        for name in ('coursed_ashlar','quoin_stone','slate_course','threshold'):
            base=SOURCE['parts'][name];coarse=base['lod2'];edges=Counter()
            for axis in range(3):
                original=max(v[axis] for v in base['vertices'])-min(v[axis] for v in base['vertices'])
                retained=max(v[axis] for v in coarse['vertices'])-min(v[axis] for v in coarse['vertices'])
                self.assertGreater(retained/original,.90,name)
            for face in coarse['faces']:
                for a,b in zip(face,face[1:]+face[:1]):edges[tuple(sorted((a,b)))]+=1
            self.assertTrue(all(count==2 for count in edges.values()),name)

    def test_gatehouse_has_full_depth_authored_arch(self):
        asset=SOURCE['assets']['frontier_sunmeadow_gatehouse']
        self.assertEqual(asset['contract']['passage_clearance'],[6,4.8])
        arches=[item for item in asset['instances'] if item['part']=='arch_spandrel']
        self.assertEqual(len(arches),1)
        self.assertAlmostEqual(arches[0]['scale'][1]*.44,12)

    def test_instances_preserve_authored_geometry_and_known_materials(self):
        for asset in SOURCE['assets'].values():
            for item in asset['instances']:
                self.assertIn(item['part'],SOURCE['parts'])
                self.assertTrue(all(value>0 for value in item['scale']))
                self.assertIn(item.get('material',SOURCE['parts'][item['part']]['material']),SOURCE['materials'])


if __name__=='__main__':unittest.main()
