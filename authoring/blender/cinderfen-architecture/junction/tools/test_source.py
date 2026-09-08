"""Independent source and provenance checks for the courtyard corner module."""
import ast
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
SOURCE=json.loads((ROOT/'source/architecture.json').read_text())

class CornerSource(unittest.TestCase):
    def test_no_primitive_constructors(self):
        for path in (ROOT/'tools').glob('*.py'):
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node,ast.Call):
                    name=ast.unparse(node.func)
                    self.assertNotIn('primitive_',name,str(path));self.assertNotIn('bmesh.ops.create_',name,str(path))

    def test_closed_authored_cages_and_uv_corners(self):
        for name,part in SOURCE['parts'].items():
            for item in [part]+([part['lod2']] if 'lod2' in part else []):
                self.assertEqual(len(item['faces']),len(item['corner_uv']),name);edges=Counter()
                for face,uv in zip(item['faces'],item['corner_uv']):
                    self.assertEqual(len(face),len(uv),name)
                    self.assertTrue(all(0<=index<len(item['vertices']) for index in face),name)
                    self.assertTrue(all(math.isfinite(value) for point in uv for value in point),name)
                    for a,b in zip(face,face[1:]+face[:1]):edges[tuple(sorted((a,b)))]+=1
                self.assertTrue(all(count==2 for count in edges.values()),name)

    def test_exact_companion_construction_and_real_stair_offset(self):
        digest=hashlib.sha256((ROOT.parent/'source/architecture.json').read_bytes()).hexdigest()
        self.assertEqual(SOURCE['reused_authored_construction']['sha256'],digest)
        asset=SOURCE['assets']['frontier_cinderfen_corner_access'];contract=asset['contract']
        self.assertEqual(contract['stair_socket_runtime'],[-3.5,6.3,-3.5])
        self.assertEqual(contract['walkway_sockets_runtime'],[[-2.4,6.3,0],[0,6.3,-2.4]])
        self.assertTrue(any(surface['id']=='courtyard_stair_landing' for surface in contract['walkableSurfaces']))
        self.assertTrue(all(instance['part'] in SOURCE['parts'] for instance in asset['instances']))

if __name__=='__main__':unittest.main()
