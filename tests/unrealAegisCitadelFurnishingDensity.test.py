"""CPU source bounds and negative collision controls; no native visual approval."""
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'public/assets/models/asset-index.json').is_file())
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'scripts/unreal'),str(ROOT/'scripts/unreal')]
import aegis_citadel_furnishing_density as density
from aegis_citadel_furnishings import source_furnishing, transform_vector
from aegis_citadel_mesh import Mesh


def architecture(*obstacles, z=6010):
    meshes=[Mesh(key) for key in sorted(density.ARCHITECTURE_GROUPS)]
    for mesh in meshes:
        mesh.face([[25000,-7000,z],[34000,-7000,z],[34000,7000,z],[25000,7000,z]])
    wall=next(m for m in meshes if m.key=='ribbed_interiors')
    for triangle in obstacles: wall.face(triangle)
    return meshes


class DensityTests(unittest.TestCase):
    def setUp(self):
        self.request=density.density_requests()[0]
        self.mesh,self.receipt=source_furnishing(self.request)
        self.bounds=self.receipt['boundsCm']
        self.study=dict(requests=[self.request],residentReservations=[])
        self.plan=dict(rooms=[dict(id='forehall',bounds=[[26000,-4300,6010],[28900,4300,10100]])],
            routes=[],spawnApproaches=[],objectives=[],optionalObjectives=[],gameplayPads=[],gates=[])

    def checked(self, meshes=None, existing=None):
        with patch.object(density,'study_plan',return_value=self.study):
            return density.checked_density(self.plan,meshes or architecture(),existing or [],self.study)

    def test_actual_rotated_vertices_determine_the_protected_extent(self):
        row={**self.request,'yawDegrees':90}
        mesh,receipt=source_furnishing(row)
        actual=density.bounds_of(mesh.positions)
        self.assertEqual(actual,receipt['boundsCm'])
        self.assertAlmostEqual(actual[1][0]-actual[0][0],419.7096128463745,places=3)
        # The desired center clears the 18 m lane; the transformed model does not.
        y=(actual[0][1]+actual[1][1])/2
        plan=dict(routes=[dict(id='commander',points=[[27000,y-1000,6010],[29000,y-1000,6010]],width=1800)],spawnApproaches=[])
        with self.assertRaisesRegex(ValueError,'Signed route'): density.route_witness(plan,actual)

    def test_elevation_clipping_protects_the_entire_rising_segment(self):
        plan=dict(routes=[dict(id='rising',points=[[0,0,0],[1000,0,1000]],width=600)],spawnApproaches=[])
        with self.assertRaisesRegex(ValueError,'rising'):
            density.route_witness(plan,[[450,-50,900],[550,50,1000]])

    def test_spawn_point_reservation_is_checked_without_a_route_segment(self):
        self.plan['spawnApproaches']=[dict(index=4,points=[self.request['point']],widthCm=600)]
        with self.assertRaisesRegex(ValueError,'spawn_4'): self.checked()

    def test_triangle_edge_axes_reject_false_aabb_hits(self):
        triangle=[[0,0,0],[10,0,0],[0,10,0]]
        self.assertFalse(density.triangle_box_intersection(triangle,[[8,8,-1],[9,9,1]]))
        self.assertTrue(density.triangle_box_intersection(triangle,[[3,3,-1],[4,4,1]]))
        self.assertTrue(density.triangle_box_intersection(list(reversed(triangle)),[[3,3,-1],[4,4,1]]))

    def test_wall_column_and_rising_stair_intersections_are_rejected(self):
        x,y,z=self.request['point']
        obstacles=[[[x+80,y-500,z],[x+80,y+500,z],[x+80,y,z+600]],
                   [[x-40,y-20,z],[x+40,y+20,z],[x,y,z+800]],
                   [[x-150,y-400,z],[x+150,y-400,z+400],[x,y+400,z]]]
        for obstacle in obstacles:
            with self.subTest(obstacle=obstacle):
                with self.assertRaisesRegex(ValueError,'Architecture intersection'): self.checked(architecture(obstacle))

    def test_clearance_margin_rejects_a_near_wall_and_low_ceiling(self):
        x=self.bounds[1][0]+10; y=self.request['point'][1]; z=self.request['point'][2]
        wall=[[x,y-500,z],[x,y+500,z],[x,y,z+800]]
        ceiling_z=self.bounds[1][2]+10
        ceiling=[[x-1000,y-1000,ceiling_z],[x+1000,y-1000,ceiling_z],[x,y+1000,ceiling_z]]
        for obstacle in (wall,ceiling):
            with self.assertRaisesRegex(ValueError,'Architecture intersection'): self.checked(architecture(obstacle))

    def test_missing_architecture_group_cannot_vacuously_pass(self):
        with self.assertRaisesRegex(ValueError,'eight-group'):
            self.checked(architecture()[1:])
        empty=architecture(); empty[0].indices=[]
        with self.assertRaisesRegex(ValueError,'Empty or incomplete'): self.checked(empty)

    def test_floating_floor_is_rejected_and_valid_floor_is_recorded(self):
        with self.assertRaisesRegex(ValueError,'Unsupported floor'): self.checked(architecture(z=5990))
        groups,ledger,inventory=self.checked()
        self.assertEqual(len(ledger[0]['architectureClearance']['floorSamples']),9)
        self.assertEqual(len(inventory),8)
        self.assertEqual(set(groups),{'forehall'})
        self.assertFalse(ledger[0]['nativeClearanceVerified'])
        self.assertFalse(ledger[0]['visualApproved'])
        self.assertFalse(ledger[0]['gameplayApproved'])

    def test_room_containment_uses_bounds_even_when_center_is_inside(self):
        p=self.request['point']
        self.plan['rooms'][0]['bounds']=[[p[0]-80,p[1]-500,p[2]],[p[0]+80,p[1]+500,p[2]+1000]]
        with self.assertRaisesRegex(ValueError,'signed room'): self.checked()

    def test_neighbor_overlap_uses_transformed_bounds_and_padding(self):
        b=copy.deepcopy(self.bounds)
        width=b[1][0]-b[0][0]
        for p in b: p[0]+=width+10
        with self.assertRaisesRegex(ValueError,'Furnishing overlap'):
            self.checked(existing=[dict(id='neighbor',boundsCm=b)])

    def test_capture_gameplay_gate_and_resident_reservations_fail_closed(self):
        p=self.request['point']
        self.plan['optionalObjectives']=[p]
        with self.assertRaisesRegex(ValueError,'objective'): self.checked()
        self.plan['optionalObjectives']=[]
        self.plan['gameplayPads']=[dict(id='service',footprintCentreFloorCm=p,maximumFootprintRadiusCm=165,maximumHeightCm=180)]
        with self.assertRaisesRegex(ValueError,'service pad'): self.checked()
        self.plan['gameplayPads']=[]
        self.plan['gates']=[dict(leaves=[dict(point=p,width=600,height=1100)])]
        with self.assertRaisesRegex(ValueError,'Gate reservation'): self.checked()
        self.plan['gates']=[]
        self.study['residentReservations']=[dict(id='porter',pointCm=p,clearanceRadiusCm=100,heightCm=240)]
        with self.assertRaisesRegex(ValueError,'Resident reservation'): self.checked()

    def test_changed_signed_plan_is_rejected_before_geometry(self):
        with self.assertRaisesRegex(ValueError,'signed source/resident'):
            density.checked_density(self.plan,[],[],self.study)

    def test_bounded_reviewed_sources_residents_and_throne_facing_are_retained(self):
        rows=density.density_requests(); study=density.study_plan()
        self.assertEqual(len(rows),26)
        self.assertEqual(len({r['id'] for r in rows}),26)
        self.assertEqual(len(study['residentReservations']),8)
        self.assertEqual({Path(r['source']).name for r in rows},
            {'prop_aegis_citadel_feast_table.glb','prop_aegis_civic_bench.glb','prop_aegis_barrel_cluster.glb'})
        self.assertTrue(all(r['scale'] in (.75,.8,.85) for r in rows))
        self.assertFalse(any('throne.glb' in r['source'] for r in rows))
        self.assertAlmostEqual(transform_vector([1,0,0],180)[0],-1)

    def test_opt_in_is_separately_signed_without_changing_gameplay_or_lighting(self):
        import aegis_citadel_blueprint as blueprint
        original_sha=blueprint.sha
        def bound_sha(file):
            # Proposal copies contain changed files only; unchanged dependencies
            # resolve to their owner-controlled sources during this portable test.
            if not file.is_file() and file.parent==Path(blueprint.__file__).parent:
                file=ROOT/'scripts/unreal'/file.name
            return original_sha(file)
        with patch.object(blueprint,'ROOT',ROOT),patch.object(blueprint,'sha',side_effect=bound_sha):
            normal=blueprint.plan(reference_hash='a'*64)
            study=blueprint.plan(reference_hash='a'*64,furnishing_density=True)
            protected=('nodes','routes','gates','routeSurfaceProfiles','routeSurfaceHeightField',
                'crossingLedger','objectives','optionalObjectives','gameplayPads','teamSpawns',
                'spawnApproaches','editMask','rooms','architecturalLights','retainedHallFixturePads',
                'terrainCarves','performanceFormations')
            self.assertTrue(all(normal[key]==study[key] for key in protected))
            self.assertNotIn('densityStudy',normal['furnishingPlan'])
            self.assertEqual(study['furnishingPlan']['densityStudy'],density.study_plan())
            self.assertNotEqual(normal['signature'],study['signature'])
            for invalid in (None,1,'1'):
                with self.assertRaisesRegex(ValueError,'boolean'):
                    blueprint.plan(reference_hash='a'*64,furnishing_density=invalid)


if __name__=='__main__': unittest.main()
