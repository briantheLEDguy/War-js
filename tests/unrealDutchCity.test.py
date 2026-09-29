"""Offline Shapely authoring tests; install requirements-dutch-bastion.txt."""
import copy
import importlib.util
import math
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/unreal'))
sys.path.insert(0,str(ROOT/'artifacts/unreal/dutch-bastion/python'))
from shapely.geometry import Polygon, LineString, box
from dutch_bastion import block
from dutch_city_validation import canonical_block_id, validate_block, validate_streets, validate_retained_clearance
from dutch_polygon_architecture import Mesh, slab, house
from dutch_mesh_clipping import clip_mesh, city_envelopes, clip_legacy_roads, retained_road_region

spec=importlib.util.spec_from_file_location('dutch_city_plan',ROOT/'scripts/unreal/plan-dutch-city.py')
planner=importlib.util.module_from_spec(spec);spec.loader.exec_module(planner)


class DutchCityTests(unittest.TestCase):
    def test_replacing_city_roads_keeps_bridge_collision_but_never_room_paving(self):
        from shapely.ops import unary_union
        decks=unary_union([box(9,-2,11,22),box(3,3,7,7)])
        house=box(2,2,8,8);interior=box(14,14,19,19)
        retained=retained_road_region(box(0,0,20,20),house,interior,decks)
        self.assertTrue(retained.covers(LineString([(10,-2),(10,22)])))
        self.assertTrue(retained.covers(box(21,0,30,20)))
        self.assertLess(retained.intersection(house).area,1e-8)
        self.assertLess(retained.intersection(interior).area,1e-8)
        self.assertFalse(retained.intersects(box(12,2,13,8)))

    def test_old_road_clipping_preserves_winding_and_uvs_outside_the_city(self):
        source=dict(positions=[[0,0,3],[100,0,3],[100,100,3],[0,100,3]],
                    normals=[[0,0,1]]*4,uvs=[[0,0],[1,0],[1,1],[0,1]],indices=[0,2,1,0,3,2])
        mesh=clip_legacy_roads(source,box(.5,0,1,1))
        area=0
        for i in range(0,len(mesh['indices']),3):
            a,b,c=[mesh['positions'][j] for j in mesh['indices'][i:i+3]]
            cross=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
            self.assertLess(cross,0)
            area-=cross/2
        self.assertAlmostEqual(area,5000)
        for p,uv,n in zip(mesh['positions'],mesh['uvs'],mesh['normals']):
            self.assertGreaterEqual(p[1],50)
            self.assertAlmostEqual(uv[0],p[0]/100);self.assertAlmostEqual(uv[1],p[1]/100)
            self.assertEqual(n,[0,0,1])

    def test_foundation_top_does_not_share_the_public_timber_floor_plane(self):
        lot=dict(id='floor',actorId='floor',polygon=[[-100,-100],[-94,-100],[-94,-93],[-100,-93]],
                 frontages=[[[-100,-100],[-94,-100]]],storeys=2,gable='step',palette=0,
                 publicInterior=dict(kind='cafe',name='Test',service='atmosphere_only'))
        data=house(lot)['mesh']
        for index,material in enumerate(data['triangleMaterials']):
            points=[data['positions'][j] for j in data['indices'][index*3:index*3+3]]
            if material==1 and all(abs(p[2])<1e-6 for p in points):
                area=Polygon([(p[1]/100,p[0]/100) for p in points])
                self.assertLess(area.intersection(box(.4,.4,5.6,6.6)).area,1e-8)
            if material==3 and all(-12.01<=p[2]<=0 for p in points):
                # Ground-floor timber stays within the walls; thresholds use stone.
                self.assertTrue(all(.11999<=p[0]/100<=6.88001 and .11999<=p[1]/100<=5.88001 for p in points))

    def test_finished_corner_trim_cannot_enter_adjacent_lots(self):
        import json
        plan=json.loads((ROOT/'artifacts/unreal/dutch-bastion/city-plan.json').read_text())
        lots=[lot for block in plan['blocks'] for lot in block['lots']]
        envelopes=city_envelopes(lots)
        from shapely.strtree import STRtree
        shapes=list(envelopes.values());tree=STRtree(shapes)
        for i,p in enumerate(shapes):
            for j in tree.query(p,predicate='intersects'):
                if i<j: self.assertLess(p.intersection(shapes[j],grid_size=1e-7).area,1e-6)
        for lot in lots:
            self.assertLess(Polygon(lot['polygon']).difference(envelopes[lot['id']]).area,1e-5)

    def test_clipping_preserves_vertical_faces_uvs_and_concave_openings(self):
        mesh=Mesh();mesh.box(-1,9,-1,9,0,3,'brick')
        # Include a floor, as well as vertical stone bands crossing the lot edge.
        mesh.face([[-1,-1,1],[9,-1,1],[9,9,1],[-1,9,1]],'timber')
        envelope=Polygon([[0,0],[8,0],[8,4],[4,4],[4,8],[0,8]])
        clipped,count=clip_mesh(mesh,envelope)
        self.assertGreater(count,0)
        self.assertEqual(len(clipped.positions),len(clipped.uvs))
        for i in range(0,len(clipped.indices),3):
            points=[clipped.positions[j] for j in clipped.indices[i:i+3]]
            shape=Polygon([p[:2] for p in points]).convex_hull
            self.assertTrue(envelope.buffer(1e-7).covers(shape))
        self.assertTrue(all(math.isfinite(v) for uv in clipped.uvs for v in uv))

    def test_city_reruns_keep_ids_venues_bridges_and_declared_spaces(self):
        a=planner.compile_city(write=False);b=planner.compile_city(write=False)
        self.assertEqual(a,b)
        self.assertEqual(a['zone'],'aegis_capital')
        ids=[lot['actorId'] for block in a['blocks'] for lot in block['lots']]
        self.assertEqual(len(ids),len(set(ids)))
        self.assertTrue(a['streetReview']['connected'])
        self.assertEqual(len(a['streetReview']['bridges']),6)
        self.assertFalse(any('bridge' in r['reason'] for r in a['streetReview']['pending']))
        self.assertFalse(a['publicVenues']['pending'])
        for district in ('gateward','cinderbank','lantern_quays','bellfound','crownwatch'):
            self.assertEqual({v['kind'] for v in a['publicVenues']['assigned'] if v['district']==district},{'inn','cafe','shop'})
        self.assertGreaterEqual(len(a['intentionalSpaces']),10)
        self.assertEqual(len(a['gatheringAreas']),5)
        self.assertEqual(len(a['protectedSites']),31)
        self.assertFalse(any(not r.get('geometryResolved') for r in a['pendingBlocks']))
        self.assertFalse(a['acceptance']['live'])
        for block in a['blocks']: validate_block(block)

    def test_graded_paving_is_continuous_above_retained_terrain(self):
        from dutch_city_ground import paving_height, data, SIZE, GRADE
        from capital_geography import height
        values=data()['heights']
        for z in range(SIZE-1):
            for x in range(SIZE-1):
                index=z*SIZE+x
                self.assertLessEqual(abs(values[index]-values[index+1]),GRADE+1e-8)
                self.assertLessEqual(abs(values[index]-values[index+SIZE]),GRADE+1e-8)
        for x in range(-130,131,5):
            for z in range(-130,126,5):
                self.assertGreaterEqual(paving_height(x,z)+1e-8,height(x,z))
        for x,z in ((118,24),(118,28),(118,32),(118,35),(-117,27)):
            self.assertAlmostEqual(paving_height(x,z),0,places=6)

    def test_near_collinear_western_block_still_has_no_overlap_or_gap(self):
        polygon=Polygon([[-106.33333333333334,116.22222222222221],[-132,103],[-139.5,66],[-139.5,30],
                         [-120.6,30],[-120.6,40.69329665284209],[-110.93097125623703,64.8658685122495],[-124.19278044945466,92.40962606739379]])
        result=planner.corner_parcels('western','bellfound',polygon)
        self.assertTrue(validate_block(result)['coverage'])

    def test_concave_block_has_complete_coverage_and_a_court_passage(self):
        shape=Polygon([[0,0],[44,0],[44,25],[29,25],[29,44],[0,44]])
        a=planner.corner_parcels('test','cinderbank',shape)
        self.assertEqual(a,planner.corner_parcels('test','cinderbank',shape))
        self.assertTrue(validate_block(a)['coverage'])
        self.assertEqual(len(a['openings']),1)
        self.assertGreaterEqual(a['openings'][0]['width'],2.8)

    def test_one_centimetre_seam_and_overlap_are_rejected(self):
        b=block('test','cinderbank',[[0,0],[44,0],[44,44],[0,44]],7.2,0)
        validate_block(b)
        for delta in (-.01,.01):
            broken=copy.deepcopy(b)
            point=broken['lots'][1]['polygon'][0]
            broken['lots'][1]['polygon'][0]=[point[0]+delta,point[1]]
            with self.assertRaises(ValueError): validate_block(broken)

    def test_undeclared_gap_and_inaccessible_court_are_rejected(self):
        b=block('test','cinderbank',[[0,0],[44,0],[44,44],[0,44]],7.2,0)
        b['openings']=[]
        with self.assertRaises(ValueError): validate_block(b)

    def test_passage_keeps_clear_width_at_the_court_and_rejects_a_pinched_exit(self):
        b=block('tapered','bellfound',[[0,0],[44,0],[44,44],[0,44]],7.2,0)
        opening=b['openings'][0];a,z=opening['polygon'][2:]
        self.assertAlmostEqual(math.dist(a,z),2.8)
        validate_block(b)
        midpoint=[(a[i]+z[i])/2 for i in (0,1)]
        new_a=[midpoint[i]+(a[i]-midpoint[i])*.2 for i in (0,1)]
        new_z=[midpoint[i]+(z[i]-midpoint[i])*.2 for i in (0,1)]
        for lot in b['lots']:
            for index,point in enumerate(lot['polygon']):
                if point==a: lot['polygon'][index]=new_a
                elif point==z: lot['polygon'][index]=new_z
        opening['polygon'][2:]=[new_a,new_z]
        with self.assertRaisesRegex(ValueError,'pinches'): validate_block(b)

    def test_block_identity_ignores_ring_start_winding_and_enumeration(self):
        points=[[0,0],[44,0],[44,44],[0,44]]
        expected=canonical_block_id(Polygon(points))
        for i in range(len(points)):
            self.assertEqual(expected,canonical_block_id(Polygon(points[i:]+points[:i])))
        self.assertEqual(expected,canonical_block_id(Polygon(list(reversed(points)))))
        self.assertNotEqual(expected,canonical_block_id(box(0,0,45,44)))

    def test_a_route_cannot_cross_water_without_a_bridge(self):
        streets=[dict(id='test',width=6,points=[[-100,-100],[-100,-70]])]
        canal=box(-110,-89,-90,-81)
        source=dict(props=[])
        report=validate_streets(streets,source,canal)
        self.assertFalse(report['connected'])
        self.assertTrue(any('bridge' in p['reason'] for p in report['pending']))
        source['props']=[dict(id='bridge',kind='aegis_bridge_narrow',x=-100,z=-85,
                            scale=1,scaleX=1.5,walkableSurfaces=[dict(width=3.5,depth=12)])]
        report=validate_streets(streets,source,canal)
        self.assertTrue(report['connected'])
        self.assertFalse(report['pending'])

    def test_a_street_cannot_pass_through_a_preserved_public_room(self):
        site=dict(id='inn',kind='existing_interior',polygon=[[-2,-2],[12,-2],[12,12],[-2,12]])
        with self.assertRaisesRegex(ValueError,'preserved interior'):
            validate_retained_clearance([dict(id='cut',width=3,points=[[-5,5],[15,5]])],[site])
        validate_retained_clearance([dict(id='cut',width=3,points=[[-5,-3],[15,-3]])],[site])

    def test_triangulated_floors_never_span_a_concave_court_or_hole(self):
        polygon=Polygon([[0,0],[8,0],[8,4],[4,4],[4,8],[0,8]],holes=[[[1,1],[2,1],[2,2],[1,2]]])
        mesh=Mesh();slab(mesh,polygon,-.2,0,'timber');area=0
        for index in range(0,len(mesh.indices),3):
            points=[mesh.positions[i] for i in mesh.indices[index:index+3]]
            if not all(p[2]==0 for p in points): continue
            triangle=Polygon([p[:2] for p in points]);area+=triangle.area
            self.assertTrue(polygon.buffer(1e-8).covers(triangle))
        self.assertAlmostEqual(area,polygon.area,places=7)

    def test_polygonal_corner_mesh_is_finite_and_has_a_real_public_door(self):
        lot=dict(id='corner',actorId='bastion_dutch_corner',polygon=[[-100,-100],[-94,-100],[-94,-96],[-92,-96],[-92,-92],[-100,-92]],
                 frontages=[[[-100,-100],[-94,-100]]],storeys=3,gable='step',palette=0,
                 publicInterior=dict(kind='cafe',name='Test',service='atmosphere_only'))
        row=house(lot);mesh=row['mesh']
        self.assertEqual(row,house(lot))
        self.assertTrue(all(math.isfinite(v) for p in mesh['positions'] for v in p))
        self.assertEqual(len(mesh['indices'])//3,len(mesh['triangleMaterials']))
        roof_vertices=[mesh['positions'][vertex] for i,material in enumerate(mesh['triangleMaterials'])
                       if material==2 for vertex in mesh['indices'][i*3:i*3+3]]
        self.assertAlmostEqual(max(p[2] for p in roof_vertices), (9+6*.62)*100,places=4)
        # The front plane maps to Unreal local X=0; doorway centre is Y=150.
        for index in range(0,len(mesh['indices']),3):
            points=[mesh['positions'][j] for j in mesh['indices'][index:index+3]]
            if not all(-30<=p[0]<=30 for p in points): continue
            ys=[p[1] for p in points];zs=[p[2] for p in points]
            self.assertFalse(min(ys)<150<max(ys) and max(zs)>10 and min(zs)<230)


if __name__=='__main__': unittest.main()
