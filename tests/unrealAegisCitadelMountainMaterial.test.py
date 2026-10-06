"""Bind alpine slope treatment to saved native render evidence, never guesses."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from aegis_citadel_mountain_material import mountain_render_normal_convention


class MountainMaterialTests(unittest.TestCase):
    def fixture(self,root,normals=None):
        mesh='/Game/WorldRebuild/AegisCitadel_0123456789ab/Meshes/SM_HallCarvedMountain.SM_HallCarvedMountain'
        document=dict(schemaVersion=1,readOnly=True,available=True,valid=True,invalidValues=0,
            mesh=mesh,lod=0,policy='actual_render_index_order_oriented_triangle_corners',
            triangles=[dict(positions=[[0,0,20000],[100,0,21000],[0,100,22000]],
                            normals=normals or [[0,0,-1]]*3)])
        file=root/'terrain-carves/hall-carve-rendered-faces.json';file.parent.mkdir(exist_ok=True)
        raw=json.dumps(document).encode();file.write_bytes(raw)
        row=dict(mesh=mesh,actorTransform=dict(translationCm=[25000,0,0],
            rotationQuaternion=[0,0,0,1],scale=[1,1,1]),
            actualActorState=dict(components=[dict(name='StaticMeshComponent0',mesh=mesh,
                transform=[25000,0,0,0,0,0,1,1,1,1])]),
            nativeReadback=dict(actualPolicy=dict(sourceLods=1,mesh=dict(nanite_settings=dict(bEnabled=False))),
                renderedFaces=dict(path='terrain-carves/hall-carve-rendered-faces.json',
                    sha256=hashlib.sha256(raw).hexdigest())))
        return dict(terrainCarves=[row]),document,file

    def test_actual_downward_render_normals_bind_the_slope_mask(self):
        with tempfile.TemporaryDirectory(prefix='citadel-mountain-material-') as directory:
            root=Path(directory);candidate,_,_=self.fixture(root)
            receipt=mountain_render_normal_convention(root,candidate)
            self.assertEqual(receipt['highlandCorners'],3)
            self.assertEqual(receipt['renderNormalZRange'],[-1,-1])
            self.assertEqual(receipt['slopeMaskNormalZSign'],-1)
            self.assertFalse(receipt['geometryChanged']);self.assertFalse(receipt['collisionChanged'])

    def test_upward_mixed_and_missing_render_normals_cannot_be_assumed_downward(self):
        with tempfile.TemporaryDirectory(prefix='citadel-mountain-material-') as directory:
            root=Path(directory)
            for normals in ([[0,0,1]]*3,[[0,0,-1],[0,0,1],[0,0,-1]],[[0,0,-1]]):
                candidate,_,_=self.fixture(root,normals)
                with self.assertRaises(ValueError):mountain_render_normal_convention(root,candidate)

    def test_changed_bytes_wrong_coordinate_frame_and_unbound_file_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix='citadel-mountain-material-') as directory:
            root=Path(directory);candidate,_,file=self.fixture(root)
            file.write_bytes(file.read_bytes()+b' ')
            with self.assertRaises(ValueError):mountain_render_normal_convention(root,candidate)
            candidate,_,_=self.fixture(root)
            for mutate in (lambda c:c['terrainCarves'][0]['actorTransform'].update(scale=[2,2,2]),
                           lambda c:c['terrainCarves'][0]['actualActorState']['components'][0]['transform'].__setitem__(3,1),
                           lambda c:c['terrainCarves'][0]['nativeReadback']['actualPolicy'].update(sourceLods=2),
                           lambda c:c['terrainCarves'][0]['nativeReadback']['actualPolicy']['mesh']['nanite_settings'].update(bEnabled=True),
                           lambda c:c['terrainCarves'][0]['nativeReadback']['renderedFaces'].update(path='../outside.json')):
                bad=copy.deepcopy(candidate);mutate(bad)
                with self.assertRaises(ValueError):mountain_render_normal_convention(root,bad)

    def test_noise_shifted_lower_snow_band_is_also_validated(self):
        with tempfile.TemporaryDirectory(prefix='citadel-mountain-material-') as directory:
            root=Path(directory);candidate,document,file=self.fixture(root)
            document['triangles'][0]['positions'][0][2]=16000
            document['triangles'][0]['normals'][0]=[0,0,1]
            raw=json.dumps(document).encode();file.write_bytes(raw)
            candidate['terrainCarves'][0]['nativeReadback']['renderedFaces']['sha256']=hashlib.sha256(raw).hexdigest()
            with self.assertRaises(ValueError):mountain_render_normal_convention(root,candidate)


if __name__=='__main__':unittest.main()
