"""Original furniture transforms/PBR and route reservations; no native art approval."""
import copy
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from aegis_citadel_furnishings import (ROOT, source_furnishing, source_document, authored_material,
    transform_vector, dressing_requests, checked_dressing, DRESSING_GROUPS, repair_collapsed_uvs)
from aegis_citadel_mesh import MATERIALS, MATERIAL_SPECS, Mesh, outer_crest_support, foundation_courses


def dressing_architecture(*obstacles, z=6010):
    from aegis_citadel_furnishing_density import ARCHITECTURE_GROUPS
    meshes=[Mesh(key) for key in sorted(ARCHITECTURE_GROUPS)]
    for mesh in meshes:
        mesh.face([[25000,-7000,z],[34000,-7000,z],[34000,7000,z],[25000,7000,z]])
    for triangle in obstacles: meshes[0].face(triangle)
    return meshes


class FurnishingTests(unittest.TestCase):
    def test_gate_crest_has_masonry_behind_it_and_keeps_the_existing_aperture(self):
        mesh=Mesh('gate_crest');receipt=outer_crest_support(mesh)
        # Test the front-most actual surface at the crest centre, independently
        # of the declared envelope. The sun's 8 cm rods stay in front of it.
        covering=[]
        for offset in range(0,len(mesh.indices),3):
            p=[mesh.positions[i] for i in mesh.indices[offset:offset+3]]
            if all(abs(v[0]-14090)<.001 for v in p) and min(v[1] for v in p)<=0<=max(v[1] for v in p) and min(v[2] for v in p)<=6790<=max(v[2] for v in p):
                covering.append(p)
        self.assertTrue(covering)
        self.assertLess(receipt['crestPlaneXCm']+8,receipt['backingFaceXCm'])
        # No new triangle's bounds enter the actual full gate opening.
        for offset in range(0,len(mesh.indices),3):
            p=[mesh.positions[i] for i in mesh.indices[offset:offset+3]]
            self.assertFalse(min(v[1] for v in p)<920 and max(v[1] for v in p)>-920
                and min(v[2] for v in p)<6010 and max(v[2] for v in p)>4210)

    def test_keep_foundation_relief_stays_below_occupied_floors_and_outside_the_grand_stair(self):
        mesh=Mesh('foundation');receipt=foundation_courses(mesh)
        self.assertEqual(max(p[2] for p in mesh.positions),receipt['maximumZCm'])
        self.assertLess(receipt['maximumZCm'],5790)
        self.assertTrue(all(abs(p[1])>=2100 for p in mesh.positions))

    def test_collapsed_seam_repair_preserves_geometry_normals_and_healthy_uvs(self):
        mesh=Mesh('seam');mesh.face([[0,0,0],[100,0,0],[0,100,0]],'gold')
        mesh.face([[200,0,0],[300,0,0],[200,100,0]],'gold')
        mesh.uvs[:3]=[[.25,.5],[.25,.5],[.25,.5]]
        before=copy.deepcopy(mesh)
        receipt=repair_collapsed_uvs(mesh)
        self.assertEqual(len(receipt['faces']),1)
        self.assertEqual(mesh.indices[3:],before.indices[3:])
        self.assertEqual(mesh.uvs[3:6],before.uvs[3:6])
        for old,new in zip(before.indices[:3],mesh.indices[:3]):
            self.assertEqual(mesh.positions[new],before.positions[old])
            self.assertEqual(mesh.normals[new],before.normals[old])
            self.assertLessEqual(max(abs(mesh.uvs[new][i]-before.uvs[old][i]) for i in range(2)),1/16384)
        self.assertEqual(repair_collapsed_uvs(mesh)['faces'],[])

    def test_repeated_surface_repair_preserves_relief_and_opposite_solid_boundaries(self):
        mesh=Mesh('joint');face=[[0,0,0],[100,0,0],[0,100,0]]
        mesh.face(face);mesh.face(face);mesh.face(list(reversed(face)))
        mesh.face([[p[0],p[1],p[2]+.0001] for p in face])
        mesh.surface_bindings=[dict(topTriangleIndices=[0,1,3])]
        before=copy.deepcopy(mesh.positions)
        receipt=mesh.remove_identical_faces()
        self.assertEqual(receipt['removedTriangles'],1)
        self.assertEqual(len(mesh.indices),9)
        self.assertEqual(mesh.positions,before)
        self.assertEqual(mesh.surface_bindings[0]['topTriangleIndices'],[0,2])
        self.assertEqual(sum(mesh.normals[i][2]>0 for i in mesh.indices),6)
        self.assertEqual(sum(mesh.normals[i][2]<0 for i in mesh.indices),3)

    def test_original_throne_front_faces_downhill_at_human_ceremonial_scale(self):
        placement=dict(id='throne',source='public/assets/models/prop_aegis_citadel_throne.glb',
            point=[32630,0,6010],scale=.55,yawDegrees=180)
        mesh,receipt=source_furnishing(placement)
        front=transform_vector([1,0,0],receipt['yawDegrees'])
        self.assertAlmostEqual(front[0],-1);self.assertAlmostEqual(front[1],0)
        self.assertAlmostEqual(min(p[2] for p in mesh.positions),6010)
        self.assertGreater(receipt['boundsCm'][1][2]-6010,450)
        self.assertLess(receipt['boundsCm'][1][2]-6010,500)
        self.assertTrue(receipt['originalNormalsPreserved'])
        self.assertTrue(all(abs(sum(x*x for x in n)-1)<1e-5 for n in mesh.normals))
        self.assertGreater(len(mesh.indices)//3,10000)
        wine=next(s for s in receipt['materialSections'] if s['sourceMaterial']=='aegis_citadel_wine')
        spec=MATERIAL_SPECS[wine['role']]
        self.assertEqual(spec['metallic'],0)
        self.assertIn('aegis_citadel_interiors/citadel_baseColor.png',spec['baseColor'])
        self.assertEqual(spec['normalStrength'],.3)
        self.assertEqual(spec['normalConvention'],'gltf_opengl_positive_y')
        self.assertNotEqual(wine['role'],'carved_stone')

    def test_atlas_mapping_and_pbr_factors_are_original_and_mismatched_channels_rejected(self):
        source=ROOT/'public/assets/models/prop_aegis_citadel_throne.glb';doc=source_document(source)
        brass=next(m for m in doc['materials'] if m['name']=='aegis_citadel_brass')
        role,spec,uv=authored_material(source,doc,brass)
        self.assertAlmostEqual(spec['metallic'],.72,places=5)
        self.assertEqual(uv['offset'],[.0009765625,.5009765625])
        self.assertEqual(uv['scale'],[.33154296875,.498046875])
        bad=copy.deepcopy(brass);bad['normalTexture']['extensions']['KHR_texture_transform']['offset']=[0,0]
        with self.assertRaisesRegex(ValueError,'different UV'):authored_material(source,doc,bad)

    def test_dressing_rejects_signed_corridors_objectives_and_other_props(self):
        row=dressing_requests()[0]
        plan=dict(routes=[],spawnApproaches=[],objectives=[],optionalObjectives=[])
        with patch('aegis_citadel_furnishings.dressing_requests',return_value=[row]):
            meshes,ledger=checked_dressing(plan,[],dressing_architecture())
            self.assertEqual({m.key for m in meshes},{'dressing_'+k for k in DRESSING_GROUPS})
            bounds=ledger[0]['boundsCm']
            with self.assertRaisesRegex(ValueError,'overlaps'):checked_dressing(plan,[dict(boundsCm=bounds)],dressing_architecture())
            blocked=copy.deepcopy(plan);blocked['routes']=[dict(points=[[26000,-2400,6010],[28000,-2400,6010]],width=1200)]
            with self.assertRaisesRegex(ValueError,'signed route'):checked_dressing(blocked,[],dressing_architecture())
            occupied=copy.deepcopy(plan);occupied['optionalObjectives']=[row['point']]
            with self.assertRaisesRegex(ValueError,'objective'):checked_dressing(occupied,[],dressing_architecture())


    def test_forehall_table_clears_the_measured_facade_trim_after_repair(self):
        row=dressing_requests()[0]
        # Actual exported facade triangle 380544 from the reported intersection.
        trim=[[25933.6308,-2428,6010],[26666.3692,-2428,6010],[26678,-2440,6022]]
        plan=dict(routes=[],spawnApproaches=[],objectives=[],optionalObjectives=[])
        with patch('aegis_citadel_furnishings.dressing_requests',return_value=[row]):
            _,ledger=checked_dressing(plan,[],dressing_architecture(trim))
            self.assertEqual(len(ledger[0]['architectureClearance']['floorSamples']),9)
            self.assertFalse(ledger[0]['nativeClearanceVerified'])
        old={**row,'point':[26700,-2400,6010]}
        with patch('aegis_citadel_furnishings.dressing_requests',return_value=[old]):
            with self.assertRaisesRegex(ValueError,'Architecture intersection'):
                checked_dressing(plan,[],dressing_architecture(trim))

    def test_existing_dressing_rejects_missing_floor_or_incomplete_architecture(self):
        row=dressing_requests()[0]
        plan=dict(routes=[],spawnApproaches=[],objectives=[],optionalObjectives=[])
        with patch('aegis_citadel_furnishings.dressing_requests',return_value=[row]):
            with self.assertRaisesRegex(ValueError,'Unsupported floor'):
                checked_dressing(plan,[],dressing_architecture(z=5990))
            with self.assertRaisesRegex(ValueError,'eight-group'):
                checked_dressing(plan,[],dressing_architecture()[1:])

    def test_existing_dressing_rejects_service_gate_resident_and_room_intrusions(self):
        row=dressing_requests()[0];p=row['point']
        clean=dict(routes=[],spawnApproaches=[],objectives=[],optionalObjectives=[])
        service={**clean,'gameplayPads':[dict(id='retained_guard',footprintCentreFloorCm=p,
            maximumFootprintRadiusCm=165,maximumHeightCm=180)]}
        gate={**clean,'gates':[dict(leaves=[dict(point=p,width=600,height=1100)])]}
        room={**clean,'rooms':[dict(id=row['group'],bounds=[[p[0]-50,p[1]-500,p[2]],[p[0]+50,p[1]+500,p[2]+1000]])]}
        with patch('aegis_citadel_furnishings.dressing_requests',return_value=[row]):
            for plan,message in ((service,'service pad'),(gate,'gate reservation'),(room,'signed room')):
                with self.subTest(message=message):
                    with self.assertRaisesRegex(ValueError,message):
                        checked_dressing(plan,[],dressing_architecture())
            with patch('citadel_review_world.residents',return_value=[dict(id='porter',pointCm=p,clearanceRadiusCm=100,heightCm=240)]):
                with self.assertRaisesRegex(ValueError,'resident reservation'):
                    checked_dressing(clean,[],dressing_architecture())


if __name__=='__main__':unittest.main()
