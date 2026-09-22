import importlib.util
import json
import math
from pathlib import Path
import struct
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('world_static',ROOT/'scripts/unreal/world_static.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def fixture(path, change=lambda doc:None):
    values=[(0.,0.,0.),(1.,0.,0.),(0.,0.,1.)]
    binary=b''.join(struct.pack('<fff',*v) for v in values)+b''.join(struct.pack('<fff',0,1,0) for _ in values)+struct.pack('<III',0,1,2)
    doc={'nodes':[{'mesh':0}], 'meshes':[{'primitives':[{'attributes':{'POSITION':0,'NORMAL':1},'indices':2,'material':0}]}],
        'materials':[{'pbrMetallicRoughness':{'baseColorFactor':[.2,.3,.4,1]}}],
        'bufferViews':[{'byteOffset':0,'byteLength':36},{'byteOffset':36,'byteLength':36},{'byteOffset':72,'byteLength':12}],
        'accessors':[{'bufferView':0,'componentType':5126,'type':'VEC3','count':3},
            {'bufferView':1,'componentType':5126,'type':'VEC3','count':3},{'bufferView':2,'componentType':5125,'type':'SCALAR','count':3}]}
    change(doc)
    encoded=json.dumps(doc).encode();encoded+=b' '*((-len(encoded))%4)
    path.write_bytes(struct.pack('<III',0x46546c67,2,28+len(encoded)+len(binary))+struct.pack('<II',len(encoded),0x4e4f534a)+encoded+struct.pack('<II',len(binary),0x004e4942)+binary)

class WorldStaticTests(unittest.TestCase):
    def test_axes_units_normals_winding(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'source.glb';fixture(path)
            part=module.read_glb(path)['parts'][0]
            self.assertEqual(part['positions'],[[0,0,0],[0,100,0],[100,0,0]])
            self.assertEqual(part['indices'],[0,2,1]);self.assertEqual(part['normals'][0],[0,0,1])

    def test_source_node_rotation_is_applied_before_engine_conversion(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'source.glb'
            fixture(path,lambda d:d['nodes'][0].update(rotation=[0,math.sqrt(.5),0,math.sqrt(.5)],translation=[2,3,4]))
            point=module.read_glb(path)['parts'][0]['positions'][1]
            for actual,expected in zip(point,[300,200,300]):self.assertAlmostEqual(actual,expected)

    def test_skeletal_sources_and_invalid_accessors_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'source.glb'
            fixture(path,lambda d:d.update(skins=[{}]))
            with self.assertRaisesRegex(ValueError,'static'):module.read_glb(path)
            fixture(path,lambda d:d['accessors'][0].update(count=4))
            with self.assertRaisesRegex(ValueError,'buffer view'):module.read_glb(path)

    def test_separate_authored_parts_keep_their_transforms(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'source.glb'
            fixture(path,lambda d:d['nodes'].append({'mesh':0,'translation':[0,2,0]}))
            parts=module.read_glb(path)['parts']
            self.assertEqual(len(parts),2)
            self.assertEqual(parts[1]['positions'][0],[0,0,200])

    def test_normalized_vertex_colors_and_water_metadata_survive(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'source.glb'
            def change(doc):
                doc['nodes'][0].update(name='peat_water',extras={'noGroundSupport':True})
                doc['accessors'].append({'bufferView':2,'componentType':5121,'normalized':True,'type':'VEC4','count':3})
                doc['meshes'][0]['primitives'][0]['attributes']['COLOR_0']=3
                doc['materials'][0]['alphaMode']='BLEND'
            fixture(path,change)
            part=module.read_glb(path)['parts'][0]
            self.assertEqual(part['colors'][2],[2/255,0,0,0])
            self.assertTrue(part['extras']['noGroundSupport'])
            self.assertTrue(part['material']['vertexColors'])
            self.assertEqual(part['material']['alphaMode'],'BLEND')

    def test_composite_preserves_all_surfaces_materials_and_colors(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'source.glb'
            fixture(path,lambda d:d['nodes'].append({'mesh':0,'translation':[0,2,0]}))
            parts=module.read_glb(path)['parts']
            parts[1]['colors']=[[0.1,0.2,0.3,1]]*3
            parts[1]['material']['roughness']=0.7
            mesh=module.combine_parts(parts)
            self.assertEqual(mesh['positions'][3],[0,0,200])
            self.assertEqual(mesh['indices'],parts[0]['indices']+[i+3 for i in parts[1]['indices']])
            self.assertEqual(mesh['triangleMaterials'],[0,1])
            self.assertEqual(mesh['materials'][1]['roughness'],0.7)
            self.assertEqual(mesh['colors'][0],[1,1,1,1])
            self.assertEqual(mesh['colors'][3],[0.1,0.2,0.3,1])
            parts[1]['indices'][0]=9
            with self.assertRaisesRegex(ValueError,'topology'):module.combine_parts(parts)

if __name__=='__main__':unittest.main()
