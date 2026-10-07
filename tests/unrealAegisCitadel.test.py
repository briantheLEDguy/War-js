"""Reference topology, structural passages and gate coverage without Unreal."""
import copy
import hashlib
import json
import math
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/unreal'))
from aegis_citadel_blueprint import plan, validate, upper_enclosure_edits, enclosure_edit_bounds, crossing_ledger, route_clearance, LIGHTING_FIXTURES
from aegis_citadel_mesh import (MATERIALS,MATERIAL_SPECS,UV_PERIOD_CM,Mesh,architecture,
    pointed_profile,wall_cut,path_floor,tower,final_banner,banner,floor_solid,cross,
    polygon_area,clip_floor_half_plane,union_floor_polygons,floor_union_boundary,emit_united_flat_floors,
    BLENDER_EXPORT_CONVENTION,blender_export_point,blender_export_normal,blender_export_indices,
    placed_sentinel,append_mesh,blind_bay,portal_roll_details)
from aegis_citadel_supports import prism,route_vault,subtract_solid,planes,dot,volume,junction_vault,emit_support,reservations,gate_portal_reservation
from aegis_citadel_surfaces import profile_height,surface_geometry,emit_surface,profile_capsule_offset
from citadel_route_surface_evidence import checked_surface_bindings
from citadel_stage_contract import (canonical_city_payload,canonical_city_revision,
    require_final_city_hashes,expected_misowned_review_start,SOURCE_TRIANGLE_CONVENTION,
    NATIVE_IMPORT_CONVENTION,NATIVE_MESH_BUILD_SETTINGS,native_triangle_indices,proof_start_position,
    expected_overlay_light,checked_render_audit,checked_terrain_render_audit,source_array_sha256,expected_shared_lighting_fixture,lighting_readback,
    checked_lighting_exposure,native_lighting_value)


def tangent_basis_fixture(vertices):
    f32=lambda v:struct.unpack('f',struct.pack('f',v))[0]
    return dict(version=1,diagnosticOnly=True,highPrecision=True,
        basisSource='actual_render_buffer_x_z_and_native_reconstructed_y',
        nearZeroComponentTolerance=f32(1e-4),orthogonalityAbsoluteNormalizedDotTolerance=f32(.02),
        invalidVertices=0,orthogonalVertices=vertices,badVertexSamples=[],badVertexSampleLimit=64,
        badVertexSamplesTruncated=False,sampleComponentPolicy='actual_buffer_values_nonfinite_as_null',
        axes={axis:dict(finite=vertices,nonFinite=0,nearZero=0,unit=vertices,nonUnit=0,
            unitSquaredTolerance=f32(.04 if axis=='y' else .02),minimumLength=1.,maximumLength=1.)
            for axis in ('x','y','z')},
        pairs={pair:dict(evaluated=vertices,skipped=0,orthogonal=vertices,nonOrthogonal=0,
            maximumAbsoluteNormalizedDot=0.) for pair in ('xy','xz','yz')})


class CitadelBlueprintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Topology tests need no private native packages or user's Downloads folder.
        evidence=[dict(actor='Fixture_'+str(i),identity='castle_fixture_'+str(i),stateHash='0'*64) for i in range(2267)]
        cls.plan=plan(reference_hash='0'*64,castle_removals=evidence)
        cls.structure,cls.gates,cls.props=architecture(cls.plan)

    def test_inherited_terrain_buffers_require_actual_full_lod_and_source_face_readbacks(self):
        lod=dict(lod=0,cpuReadable=True,vertices=3,indices=3,uvChannels=2,
            invalidPositions=0,invalidNormals=0,nonUnitNormals=0,invalidUVs=0,
            tangentBasis=dict(invalidVertices=0,orthogonalVertices=3),committedSourceTriangleMatches=1)
        audit=dict(readOnly=True,available=True,mesh='/owned/mountain',lods=[lod])
        comparison=dict(uvChannels=2,referencedTriangles=1)
        rendered=dict(targetMesh=audit['mesh'],cloneTriangles=1,nativeExteriorRenderPreserved=True,
                      nativeExteriorComputedBasisPreserved=True,committedTopologyComparisonRequired=True)
        self.assertIs(checked_terrain_render_audit(audit,audit['mesh'],1,comparison,rendered),audit)
        # Recomputed inherited terrain need not match its authored normals. Both
        # committed topology and actual original/clone exterior basis are required.
        audit['lods'][0]['committedSourceTriangleMatches']=0
        self.assertIs(checked_terrain_render_audit(audit,audit['mesh'],1,comparison,rendered),audit)
        for change in (dict(cpuReadable=False),dict(uvChannels=1),dict(invalidNormals=1),
                       dict(tangentBasis=dict(invalidVertices=1,orthogonalVertices=2))):
            broken=copy.deepcopy(audit);broken['lods'][0].update(change)
            with self.assertRaises(ValueError):checked_terrain_render_audit(broken,audit['mesh'],1,comparison,rendered)
        for key in ('nativeExteriorRenderPreserved','nativeExteriorComputedBasisPreserved','committedTopologyComparisonRequired'):
            with self.assertRaises(ValueError):
                checked_terrain_render_audit(audit,audit['mesh'],1,comparison,{**rendered,key:False})
        with self.assertRaises(ValueError):checked_terrain_render_audit(audit,audit['mesh'],2,comparison,rendered)

    def test_ramp_plateau_turn_does_not_roof_the_incoming_full_width_rise(self):
        mesh=Mesh('ramp_and_turn');path_floor(mesh,[[0,0,0],[600,0,160],[1350,0,160],[1350,900,160]],1200)
        # The first 750 cm of level paving continues straight; the turn begins
        # beyond the full incoming half-width, so its slab cannot overhang it.
        high=[]
        for offset in range(len(mesh.triangle_materials)):
            points=[mesh.positions[i] for i in mesh.indices[offset*3:offset*3+3]]
            if all(p[2]==160 for p in points):high.extend(points)
        self.assertTrue(high);self.assertGreaterEqual(min(p[0] for p in high),600)

    def test_original_navy_cloth_has_no_unrelated_normal_or_packed_maps(self):
        self.assertEqual(MATERIAL_SPECS['blue'],dict(tint=[.0035,.012,.034],roughness=.92,metallic=0,specular=.25))
        for role,tint in [('stone',[.45,.50,.57]),('limestone',[.60,.66,.74]),
                          ('flagstone',[.68,.73,.80])]:
            self.assertEqual(MATERIAL_SPECS[role]['tint'],tint)
            self.assertIn('height',MATERIAL_SPECS[role])

    def test_reference_composition_camera_keeps_the_street_view_separate(self):
        self.assertEqual(len(self.plan['reviewViews']),8)
        hero=next(r for r in self.plan['reviewViews'] if r['id']=='hero')
        self.assertEqual(hero['eyeCm'],[-4000,-21500,12000])
        self.assertEqual(hero['targetCm'],[24500,0,7500])
        self.assertEqual(hero['focalLengthMm'],30)
        self.assertEqual(self.plan['diagnosticReviewViews'][0]['id'],'street_hero')
        self.assertEqual(self.plan['diagnosticReviewViews'][0]['eyeCm'][2],11000)

    def test_front_blind_arcades_preserve_the_bounded_outward_relief(self):
        mesh=Mesh('blind_front');receipt=blind_bay(mesh,14080,5350,4335,500,940,30)
        self.assertTrue(receipt['wallAndWalkingFloorsUnchanged'])
        self.assertGreaterEqual(min(p[0] for p in mesh.positions),14050)
        self.assertLessEqual(max(p[0] for p in mesh.positions),14080)
        self.assertLess(max(p[1] for p in mesh.positions),5900)
        self.assertGreaterEqual(min(p[2] for p in mesh.positions),4335)
        with self.assertRaises(ValueError):blind_bay(Mesh('oversize'),0,0,0,500,940,41)

    def test_fine_portal_rolls_do_not_narrow_the_usable_passage(self):
        mesh=Mesh('portal_rolls');receipt=portal_roll_details(mesh)
        self.assertEqual(receipt['usableOpeningCm'],[1800,2600])
        for point in mesh.positions:
            if point[2]<8610:self.assertGreater(abs(point[1]),950)

    def test_supported_approaches_preserve_endpoints_and_pass_the_retained_apertures(self):
        for leaf in self.plan['gates'][0]['leaves'][1:]:
            clearance=leaf['approachClearance']
            self.assertEqual(clearance['localSweepHalfSpanCm'],min(400,
                clearance['incomingFlatLengthCm']-clearance['pedestrianCapsuleRadiusCm']-
                clearance['requiredCapsuleFloorMarginCm']))
        for side in ('west','east'):
            route=next(r for r in self.plan['routes'] if r['id']==side+'_approach')
            correction=next(r for r in self.plan['physicalCorrections']['approachWaypointCorrections'] if r['route']==route['id'])
            self.assertEqual(route['points'][0],correction['oldPointsCm'][0])
            self.assertEqual(route['width'],1200);self.assertEqual(route['gate'],0)
            self.assertEqual(route['points'][1][0],12200)
            self.assertEqual(abs(route['points'][2][1]),6200)
            self.assertEqual(route['points'][2][2],4205.5)
            self.assertLess(route['points'][2][2],correction['retainedWallTopCm'])
            self.assertEqual(route['points'][-2][2],4210)
            self.assertEqual(route['points'][-2][1],route['points'][-1][1])
            self.assertTrue(correction['originalActorsPreserved'])

    def test_fan_surfaces_have_one_signed_height_across_the_actual_full_width(self):
        paths=next(m for m in self.structure if m.key=='stairs_and_balconies')
        for profile in self.plan['routeSurfaceProfiles']:
            route=next(r for r in self.plan['routes'] if r['id']==profile['routeId'])
            binding=next(r for r in paths.surface_bindings if r['routeId']==route['id'])
            self.assertGreater(len(binding['topTriangleIndices']),20)
            self.assertEqual(len(set(binding['topTriangleIndices'])),len(binding['topTriangleIndices']))
            for point in route['points']:self.assertAlmostEqual(point[2],profile_height(profile,point[0]),places=2)
            for ordinal in binding['topTriangleIndices']:
                face=[paths.positions[i] for i in paths.indices[ordinal*3:ordinal*3+3]]
                n=cross([face[1][j]-face[0][j] for j in range(3)],[face[2][j]-face[0][j] for j in range(3)])
                self.assertGreaterEqual(n[2]/math.sqrt(sum(v*v for v in n)),.7)
                for p in face:self.assertLessEqual(abs(p[2]-profile_height(profile,p[0])),.01)
                self.assertFalse(any(min(p[0] for p in face)+.01<x<max(p[0] for p in face)-.01 for x,z in profile['knotsCm']))
            # Lateral heights really differ on the retained grade; the source
            # cannot silently substitute a high flat deck or a larger tolerance.
            self.assertGreater(profile_height(profile,12300)-profile_height(profile,11800),250)
            with self.assertRaises(ValueError):profile_height(profile,10900)
            for escaped in (profile['knotsCm'][0][0]-1e-9,profile['knotsCm'][-1][0]+1e-9,float('nan'),True):
                with self.assertRaises(ValueError):profile_height(profile,escaped)

    def test_fan_export_preserves_exact_declared_outer_edges_and_turns(self):
        paths=next(m for m in self.structure if m.key=='stairs_and_balconies')
        bindings=[dict(row,sourceMeshSha256='0'*64) for row in paths.surface_bindings]
        source=dict(assets=[dict(id=paths.key,sha256='0'*64)],surfaceBindings=bindings)
        self.assertEqual(set(checked_surface_bindings(source,self.plan,{paths.key:paths.export()})),
                         {'west_approach','east_approach'})

    def test_blender_reflection_preserves_outward_corners_and_native_camera_handedness(self):
        mesh=Mesh('oriented_export');mesh.face([[100,200,0],[300,200,0],[100,500,150]],'gold')
        original=copy.deepcopy(mesh.export());ids=blender_export_indices(mesh.indices)
        self.assertEqual(ids,[0,2,1]);self.assertEqual(BLENDER_EXPORT_CONVENTION['determinant'],-1)
        a,b,c=[blender_export_point(mesh.positions[i]) for i in ids]
        n=cross([b[j]-a[j] for j in range(3)],[c[j]-a[j] for j in range(3)])
        n=[v/math.sqrt(sum(q*q for q in n)) for v in n]
        for index in ids:
            self.assertGreater(sum(n[j]*blender_export_normal(mesh.normals[index])[j] for j in range(3)),.99999)
            self.assertEqual(mesh.uvs[index],original['uvs'][index])
        # Native camera along +X has +Y screen-right. The reflected Blender
        # camera along +Y has +X screen-right; both point to the same corner.
        self.assertGreater(blender_export_point([0,100,0])[0],blender_export_point([0,-100,0])[0])
        self.assertEqual(mesh.export(),original)

    def test_solid_support_subtraction_keeps_full_width_and_a_real_vault(self):
        solid=prism([-1000,0,1400],[1000,0,1400],1400,0)
        cutter=route_vault([0,-1500,300],[0,1500,300],600)
        pieces=subtract_solid(solid,cutter)
        self.assertGreater(len(pieces),1);self.assertLess(sum(volume(p) for p in pieces),volume(solid))
        for y in (-600,0,600):
            for x in (-342,0,342):
                for z in (300,492,650):
                    point=[x,y,z]
                    self.assertFalse(any(all(dot(n,point)<d-1e-5 for n,d in planes(p)) for p in pieces))
        # Masonry remains above the 6.5 m apex and outside the whole lane.
        self.assertTrue(any(all(dot(n,[0,0,1100])<=d+1e-5 for n,d in planes(p)) for p in pieces))
        self.assertTrue(any(all(dot(n,[600,0,500])<=d+1e-5 for n,d in planes(p)) for p in pieces))
        self.assertAlmostEqual(sum(volume(p) for p in subtract_solid(solid,prism([5000,0,900],[6000,0,900],100,0))),volume(solid))

    def test_portal_reservations_clear_the_full_gate_height_inside_support_masonry(self):
        for sign in (-1,1):
            leaf=dict(point=[26000,sign*3100,6010],width=600,height=1100)
            # The actual native high-level sweep hit stair masonry near this
            # opening even though its standing-character lane was clear.
            solid=prism([25500,sign*3100,7300],[26500,sign*3100,7300],1400,6010)
            pieces=subtract_solid(solid,gate_portal_reservation(leaf))
            for x in (25800,26000,26200):
                for dy in (-258,0,258):
                    for z in (6013,6785.5,6881.5,7100):
                        point=[x,sign*3100+dy,z]
                        self.assertFalse(any(all(dot(n,point)<d-1e-5 for n,d in planes(p)) for p in pieces))
            self.assertTrue(any(all(dot(n,[26000,sign*3100,7200])<=d+1e-5 for n,d in planes(p)) for p in pieces))

    def test_gallery_entry_clears_the_north_switchback_and_straightens_before_the_wall(self):
        for side,sign in (('west',-1),('east',1)):
            route=next(row for row in self.plan['routes'] if row['id']==side+'_gallery_stair')
            self.assertEqual(route['points'][0],[23700,sign*5550,5410])
            self.assertEqual(route['points'][2],[24022,sign*5550,5410])
            entry,rise_start,rise_end=route['points'][1:4]
            self.assertAlmostEqual(math.dist(entry[:2],rise_start[:2]),600,places=3)
            flat=[rise_start[j]-entry[j] for j in range(2)]
            rise=[rise_end[j]-rise_start[j] for j in range(2)]
            self.assertAlmostEqual((flat[0]*rise[1]-flat[1]*rise[0])/(math.hypot(*flat)*math.hypot(*rise)),0,places=6)
            self.assertEqual(entry[2],5410)
            self.assertEqual(route['points'][-1],[26000,sign*3500,7210])
            self.assertEqual(route['points'][-2],[25600,sign*3500,7210])
            self.assertEqual(route['width'],600)
            # The entire diagonal capsule footprint ends before the wall's
            # exterior face at X25860; a centerline-only landing was too short.
            a,b=route['points'][-3:-1];dx,dy=b[0]-a[0],b[1]-a[1]
            self.assertLess(b[0]+abs(dy)/math.hypot(dx,dy)*258+42,25860)
            self.assertGreater(5550-300,4900+300)

    def test_gallery_tangent_entry_keeps_risers_out_of_both_incoming_flat_lanes(self):
        from citadel_capsule_distance import capsule_triangle_clearance
        for side in ('west','east'):
            route=next(row for row in self.plan['routes'] if row['id']==side+'_gallery_stair')
            mesh=Mesh('gallery_entry');path_floor(mesh,route['points'],600,stairs=True)
            faces=[[mesh.positions[i] for i in mesh.indices[j:j+3]] for j in range(0,len(mesh.indices),3)]
            # The old right-angle flat lane intersected the rising flight before
            # its first junction. Test full capsules before the lawful step-up,
            # including both outer width lanes, against every authored face.
            for a,b in zip(route['points'][:2],route['points'][1:3]):
                dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
                for t in (.1,.25,.5,.75):
                    for lane in (-258,-129,0,129,258):
                        x=a[0]+dx*t-dy/length*lane;y=a[1]+dy*t+dx/length*lane
                        lower=[x,y,5410+44.4];upper=[x,y,5410+152.4]
                        self.assertGreater(min(capsule_triangle_clearance(lower,upper,42,face) for face in faces),0)

    def test_spawn_support_reserves_the_original_pad_and_full_width_exit(self):
        point=self.plan['teamSpawns'][3]
        self.assertEqual(point,[15300,-4500,4210])
        # This real upper return support enclosed the defender spawn before
        # spawn reservations were authored separately from route centerlines.
        solid=prism([15400,-4900,5410],[14800,-4900,5410],1000,2400)
        self.assertTrue(all(dot(n,[point[0],point[1],point[2]+96])<d for n,d in planes(solid)))
        pieces=[solid]
        for row in reservations(self.plan):
            pieces=[q for p in pieces for q in subtract_solid(p,row['solid'])]
        for dx,dy in ((0,0),(-258,0),(258,0),(0,-258),(0,258),(-258,-258),(258,258)):
            for dz in (3,96,195):
                probe=[point[0]+dx,point[1]+dy,point[2]+dz]
                self.assertFalse(any(all(dot(n,probe)<d-1e-5 for n,d in planes(p)) for p in pieces))
        self.assertTrue(any(all(dot(n,[15300,-4500,4910])<=d+1e-5 for n,d in planes(p)) for p in pieces))
        approach=next(row for row in self.plan['spawnApproaches'] if row['index']==3)
        self.assertEqual(approach['widthCm'],600)
        self.assertEqual(approach['points'][-1],[14800,-3500,4210])
        for row in self.plan['spawnApproaches']:
            self.assertFalse(route_clearance(self.plan,row['points'][0],42,192))
        # The first walking flight itself must clear the pad; removing only
        # masonry would leave its low treads obstructing the spawn's exit.
        route=next(row for row in self.plan['routes'] if row['id']=='west_south_stair')
        self.assertIn([15100,-3500,4210],route['points'])
        self.assertIn([16600,-3500,4810],route['points'])

    def test_spawn_approaches_cannot_move_anchors_or_claim_unconnected_routes(self):
        for change in ('missing','moved','narrow','unconnected','lower_edit'):
            broken=copy.deepcopy(self.plan)
            if change=='missing':broken['spawnApproaches'].pop()
            elif change=='moved':broken['spawnApproaches'][3]['points'][0][0]+=100
            elif change=='narrow':broken['spawnApproaches'][3]['widthCm']=599
            elif change=='unconnected':broken['spawnApproaches'][3]['points'][-1][0]+=1000
            else:broken['spawnApproaches'][0]['points'].append([6000,-4800,910])
            from aegis_citadel_blueprint import digest
            broken['signature']=digest({k:v for k,v in broken.items() if k not in ('signature','revision','acceptance')})
            with self.assertRaises(ValueError):validate(broken)

    def test_historical_recipe_keeps_its_recorded_geometry_without_new_spawn_claims(self):
        from aegis_citadel_blueprint import digest
        historical=copy.deepcopy(self.plan)
        historical['recipeVersion']=4
        historical.pop('spawnApproaches')
        historical['signature']=digest({k:v for k,v in historical.items() if k not in ('signature','revision','acceptance')})
        validate(historical)
        self.assertNotIn('spawnApproaches',historical)

    def test_quantized_support_faces_keep_the_exact_clipping_plane(self):
        # This thin fan occurred in the real convex stair-vault subtraction.
        # Its rounded positions remain unchanged; its supporting plane stays
        # vertical instead of acquiring a normal from amplified corner rounding.
        points=[[23733.133,-5375.2985,4860.0579],
                [23731.712,-5374.9177,4860],
                [23457.66,-5301.4857,4860]]
        n=[math.sin(math.pi/12),math.cos(math.pi/12),0]
        d=sum(n[j]*points[0][j] for j in range(3))
        exact=[[p[0],(d-n[0]*p[0])/n[1],p[2]] for p in points]
        mesh=Mesh('support_plane');emit_support(mesh,[exact],[])
        self.assertEqual(len(mesh.indices),3)
        self.assertTrue(all(abs(v[2])<1e-8 for v in mesh.normals))
        self.assertTrue(all(sum(n[j]*v[j] for j in range(3))>1-1e-6 for v in mesh.normals))

    def test_square_floor_blocks_have_no_bevel_or_degenerate_faces(self):
        mesh=Mesh('square_floor');mesh.block([0,0,5910],[2000,2000,200],'flagstone',0)
        self.assertEqual(len(mesh.indices)//3,12)
        for offset in range(0,len(mesh.indices),3):
            ids=mesh.indices[offset:offset+3];points=[mesh.positions[i] for i in ids]
            if all(p[2]==6010 for p in points):
                self.assertTrue(all(mesh.normals[i]==[0.,0.,1.] for i in ids))
            a,b,c=points
            self.assertGreater(sum(v*v for v in cross([b[j]-a[j] for j in range(3)],[c[j]-a[j] for j in range(3)])),0)

    def test_hall_and_thin_landings_share_one_top_and_keep_original_deep_slab(self):
        mesh=Mesh('hall_union',defer_flat_floors=True)
        floor_solid(mesh,[[0,0,6010],[1000,0,6010],[1000,1000,6010],[0,1000,6010]],220)
        floor_solid(mesh,[[500,0,6010],[1500,0,6010],[1500,1000,6010],[500,1000,6010]],80)
        # A lower balcony must remain separate even where its plan overlaps.
        floor_solid(mesh,[[0,0,5410],[1000,0,5410],[1000,1000,5410],[0,1000,5410]],80)
        receipt=emit_united_flat_floors(mesh)
        areas={row['heightCm']:row for row in receipt['sameHeightAreas']}
        self.assertEqual(areas[6010]['originalUnionAreaCm2'],1500000)
        self.assertEqual(areas[6010]['emittedTopAreaCm2'],1500000)
        self.assertEqual(areas[5410]['emittedTopAreaCm2'],1000000)
        self.assertTrue(any(p==[0,0,5790] for p in mesh.positions))
        self.assertTrue(any(p==[1500,0,5930] for p in mesh.positions))

    def test_repaired_stair_turns_have_actual_level_landing_and_explicit_shared_plaza(self):
        for side,sign in [('west',-1),('east',1)]:
            route=next(r for r in self.plan['routes'] if r['id']==side+'_ground_portal_stair')
            flight=next((a,b) for a,b in zip(route['points'],route['points'][1:]) if b[2]-a[2]==1800)
            old=next(r for r in self.plan['physicalCorrections']['flightLandingCorrections'] if r['route']==route['id'])
            self.assertAlmostEqual(math.dist(flight[0][:2],flight[1][:2]),old['risingRunPreservedCm'],places=3)
            self.assertAlmostEqual(math.dist(route['points'][-3][:2],route['points'][-2][:2]),350,places=3)
            north=next(r for r in self.plan['routes'] if r['id']==side+'_north_main')
            self.assertEqual(north['points'][-2:],[[23100,0,4210],[23700,0,4210]])
        self.assertTrue(any(r['kind']=='shared_segment' and r['connects'] and
            set(r['routes'])=={'west_north_main','east_north_main'} for r in self.plan['crossingLedger']))

    def test_scaled_sentinel_retains_effective_height_feet_and_authored_patch_normals(self):
        from aegis_citadel_statue import build_sentinel,LEGACY_NODE_SCALE
        placement=next(p for p in self.props if p['id']=='court_oath')
        local=build_sentinel(LEGACY_NODE_SCALE*placement['scale']);placed=placed_sentinel(placement)
        self.assertEqual(local.indices,placed.indices);self.assertEqual(local.normals,placed.normals)
        self.assertEqual(local.uvs,placed.uvs)
        self.assertAlmostEqual(max(p[2] for p in placed.positions)-placement['point'][2],1033.4948,places=3)
        self.assertEqual(min(p[2] for p in placed.positions),placement['point'][2])
        joined=Mesh('joined');append_mesh(joined,placed)
        self.assertEqual(joined.export()['normals'],placed.normals)

    def test_new_crown_replaces_old_solid_roof_and_hall_is_physically_closed(self):
        facade=next(m for m in self.structure if m.key=='gothic_facade_and_spires')
        self.assertEqual(len(facade.crown_replacement['belfries']),3)
        self.assertTrue(all(b['trueOpenings'] for b in facade.crown_replacement['belfries']))
        shell=next(m for m in self.structure if m.key=='fortress_keep_shell')
        self.assertNotIn(MATERIALS.index('slate'),shell.triangle_materials)
        interior=next(m for m in self.structure if m.key=='ribbed_interiors')
        self.assertTrue(any(p[2]==9098 for p in interior.positions))
        self.assertGreater(min(p[2] for p in facade.positions[-100:]),9000)

    def test_independent_sides_primary_and_commander_match_native_contract(self):
        self.assertEqual(self.plan['objectives'][4:8],[[20800,-5000,4210],[20800,5000,4210],[20800,-1000,4210],[30600,0,6010]])
        self.assertEqual(len(self.plan['editMask']['removeActors']),2267)
        self.assertEqual(len({r['identity'] for r in self.plan['editMask']['removeActors']}),2267)

    def test_signed_gameplay_pads_keep_winches_outside_capture_rings_and_routes(self):
        pads=self.plan['gameplayPads']
        self.assertEqual(len(pads),5)
        self.assertTrue(next(p for p in pads if p['id']=='lower_ammunition')['preserveTransform'])
        for pad in pads:
            if pad.get('preserveTransform'):continue
            point=pad['footprintCentreFloorCm'];radius=pad['maximumFootprintRadiusCm']
            self.assertTrue(route_clearance(self.plan,point,radius,pad['maximumHeightCm']),pad['id'])
            if pad['binding']=='gate_mechanisms':
                for anchor in self.plan['objectives'][4:7]+self.plan['optionalObjectives'][1:2]:
                    self.assertGreater(math.dist(point[:2],anchor[:2]),radius+650+50,pad['id'])
            else:
                anchor=self.plan['optionalObjectives'][pad['optionalIndex']]
                self.assertGreater(math.dist(point[:2],anchor[:2]),radius+100,pad['id'])

    def test_full_realm_formations_are_explicit_spaced_and_outside_stage_capture_rings(self):
        for formation in self.plan['performanceFormations']:
            points=formation['positions'];self.assertEqual(len(points),36)
            self.assertFalse(formation['nativeFloorVerified']);self.assertFalse(formation['nativeTraversalVerified'])
            stage=formation['stage'];anchors=self.plan['objectives'][0:4] if stage==0 else self.plan['objectives'][4:7] if stage==1 else self.plan['objectives'][7:8]
            for i,p in enumerate(points):
                for q in points[i+1:]:self.assertGreaterEqual(math.dist(p[:2],q[:2]),134)
                for anchor in anchors:self.assertGreater(math.dist(p[:2],anchor[:2]),650+42+50)

    def test_upper_mass_preserves_low_surfaces_and_measured_height(self):
        self.assertAlmostEqual(max(p[2] for m in self.structure for p in m.positions),17200,places=3)
        self.assertEqual(self.plan['upperMassing']['coreCompressionHighestZCm'],14200)
        mesh=Mesh('upper_clip_fixture')
        mesh.face([[0,0,8500],[100,0,9500],[0,100,8500]])
        original=[p[:] for p in mesh.positions]
        mesh.reshape_upper(9000,10000,9500)
        self.assertEqual(mesh.positions[0],original[0]);self.assertEqual(mesh.positions[2],original[2])
        self.assertIn([50.,0.,9000.],mesh.positions)
        self.assertIn([50.,50.,9000.],mesh.positions)
        self.assertIn([100,0,9250.],mesh.positions)
        self.assertGreater(len(mesh.indices),3)

    def test_cutoff_upper_face_owns_transformed_boundary_normals_and_coherent_uvs(self):
        mesh=Mesh('cutoff_bevel')
        mesh.face([[0,0,9000],[100,0,9000],[100,-8,9008]])
        mesh.face([[0,0,9000],[100,0,9000],[100,8,8992]])
        original=copy.deepcopy(mesh.export())
        mesh.reshape_upper(9000,22220,14200);mesh.reproject_stone_uvs()
        # Upper-cut copies must not mutate the original retained boundary data.
        for i in (0,1,3,4,5):
            self.assertEqual(mesh.positions[i],original['positions'][i])
            self.assertEqual(mesh.normals[i],original['normals'][i])
        upper=mesh.indices[:3]
        self.assertNotIn(0,upper);self.assertNotIn(1,upper)
        a,b,c=[mesh.positions[i] for i in upper]
        n=cross([b[j]-a[j] for j in range(3)],[c[j]-a[j] for j in range(3)])
        length=math.sqrt(sum(v*v for v in n));n=[v/length for v in n]
        axes=set()
        for i in upper:
            self.assertGreater(sum(n[j]*mesh.normals[i][j] for j in range(3)),.99999)
            axes.add(max(range(3),key=lambda j:abs(mesh.normals[i][j])))
        self.assertEqual(len(axes),1)

    def test_draped_sun_rays_retain_solid_depth_and_nondegenerate_cap_uvs(self):
        mesh=Mesh('actual_failed_standard')
        banner(mesh,14210,-7440,7480,600,3000)
        f32=lambda v:struct.unpack('f',struct.pack('f',v))[0]
        for offset,role in enumerate(mesh.triangle_materials):
            if MATERIALS[role]!='gold':continue
            ids=mesh.indices[offset*3:offset*3+3]
            a,b,c=[mesh.positions[i] for i in ids]
            n=cross([b[j]-a[j] for j in range(3)],[c[j]-a[j] for j in range(3)])
            self.assertGreater(math.sqrt(sum(v*v for v in n)),.1)
            uv=[[f32(v) for v in mesh.uvs[i]] for i in ids]
            det=(uv[1][0]-uv[0][0])*(uv[2][1]-uv[0][1])-(uv[1][1]-uv[0][1])*(uv[2][0]-uv[0][0])
            self.assertGreater(abs(det),1e-6)

    def test_floor_polygon_weld_removes_only_submillimetre_duplicate_corners(self):
        mesh=Mesh('native_failed_micro_turn')
        floor_solid(mesh,[[24510,-5082.273,4210],[24783.6808,-5205.1502,4210],
                         [24783.6809,-5205.1501,4210]])
        self.assertFalse(mesh.indices)
        floor_solid(mesh,[[0,-300,4210],[100,-300,4210],[100.0001,-299.9999,4210],
                         [100,300,4210],[0,300,4210]])
        self.assertTrue(mesh.indices)
        top=[p for p in mesh.positions if p[2]==4210]
        self.assertEqual(min(p[1] for p in top),-300);self.assertEqual(max(p[1] for p in top),300)
        self.assertEqual(min(p[0] for p in top),0);self.assertEqual(max(p[0] for p in top),100)

    def test_landing_union_removes_overlap_without_filling_concave_missing_floor(self):
        a=[[0,0],[600,0],[600,600],[0,600]]
        b=[[300,300],[900,300],[900,900],[300,900]]
        fragments=union_floor_polygons([a,b,a])
        self.assertAlmostEqual(sum(polygon_area(p) for p in fragments),630000)
        for i,p in enumerate(fragments):
            for q in fragments[i+1:]:
                intersection=p
                for x,y in zip(q,q[1:]+q[:1]):
                    intersection=clip_floor_half_plane(intersection,x,y)
                    if not intersection:break
                self.assertLess(abs(polygon_area(intersection)),1e-5)
        self.assertTrue(floor_union_boundary(fragments))
        # The diagonal of a bounding hull would invent floor at this L-shaped gap.
        for p in fragments:
            self.assertFalse(all((y[0]-x[0])*(150-x[1])-(y[1]-x[1])*(800-x[0])>=0
                                 for x,y in zip(p,p[1:]+p[:1])))

    def test_flat_floor_union_keeps_raised_flights_separate_and_mirrors_exactly(self):
        for mirror in (1,-1):
            mesh=Mesh('joined_turn',defer_flat_floors=True)
            floor_solid(mesh,[[0,mirror*-300,4210],[600,mirror*-300,4210],
                             [600,mirror*300,4210],[0,mirror*300,4210]])
            floor_solid(mesh,[[300,mirror*0,4210],[900,mirror*0,4210],
                             [900,mirror*600,4210],[300,mirror*600,4210]])
            floor_solid(mesh,[[0,mirror*-300,4225],[600,mirror*-300,4225],
                             [600,mirror*300,4225],[0,mirror*300,4225]])
            receipt=emit_united_flat_floors(mesh)
            self.assertEqual(receipt['originalContributions'],3)
            self.assertFalse(mesh.flat_floors)
            for z,area in ((4210,630000),(4225,360000)):
                triangles=[]
                for k,material in enumerate(mesh.triangle_materials):
                    if MATERIALS[material]!='flagstone':continue
                    points=[mesh.positions[i] for i in mesh.indices[k*3:k*3+3]]
                    if all(p[2]==z for p in points):triangles.append(points)
                self.assertAlmostEqual(sum(abs(polygon_area(p)) for p in triangles),area)

    def test_throne_plane_coherence_preserves_shape_and_genuine_hard_edges(self):
        mesh=Mesh('furnishing_throne')
        a,b,c,d=[0,0,0],[929,0,.002],[929,.17,.00205],[0,.17,0]
        mesh.face([a,b,c],'gold');mesh.face([a,c,d],'gold')
        mesh.face([a,d,[0,.17,10]],'gold')
        mesh.face([a,b,c],'stone')
        before=copy.deepcopy(mesh.export());receipt=mesh.cohere_throne_gold_faces()
        self.assertEqual(receipt['triangles'],2)
        self.assertLessEqual(receipt['maximumActualPlaneDistanceCm'],.01)
        for key in ('positions','indices','triangleMaterials','materials'):
            self.assertEqual(mesh.export()[key],before[key])
        self.assertEqual(mesh.normals[0],mesh.normals[3])
        for i in range(6,len(mesh.positions)):
            self.assertEqual(mesh.normals[i],before['normals'][i])
            self.assertEqual(mesh.uvs[i],before['uvs'][i])

    def test_post_union_rounding_cannot_emit_the_actual_collapsed_native_fragment(self):
        mesh=Mesh('union_micro_fragment',defer_flat_floors=True)
        mesh.flat_floors[(6010,80)]=[[[25673.6809,3222.8771],[25700,3234.6938],
                                    [25700,3234.6939],[25673.6809,3222.8771]]]
        emit_united_flat_floors(mesh)
        self.assertFalse(mesh.indices)

    def test_integrity_repair_removes_only_the_exact_misowned_start(self):
        state=dict(**{'class':'PlayerStart'},transform=[15300,0,4310])
        self.assertTrue(expected_misowned_review_start('PlayerStart_0',state))
        self.assertFalse(expected_misowned_review_start('PlayerStart_1',state))
        self.assertFalse(expected_misowned_review_start('PlayerStart_0',{**state,'class':'WarCityNpc'}))
        self.assertFalse(expected_misowned_review_start('PlayerStart_0',{**state,'transform':[15301,0,4310]}))

    def test_shared_lighting_replaces_only_exact_private_overlay_fixtures(self):
        fixture=dict(**{'class':'DirectionalLight'},label='Siege daylight',tags=['WarSiegeLighting'])
        self.assertTrue(expected_overlay_light('DirectionalLight_0',fixture))
        self.assertFalse(expected_overlay_light('DirectionalLight_1',fixture))
        self.assertFalse(expected_overlay_light('DirectionalLight_0',{**fixture,'label':'Shared city daylight'}))
        self.assertFalse(expected_overlay_light('DirectionalLight_0',{**fixture,'tags':['WarCapitalLighting']}))

    def test_cinematic_lighting_changes_only_exact_shared_fixtures_and_requires_readback(self):
        spec=dict(actor='DirectionalLight_0',klass='DirectionalLight',label='Aegis workbench sun')
        state=dict(**{'class':'DirectionalLight'},label=spec['label'],
            tags=['WarZoneObject_aegis_capital_DirectionalLight_0'])
        self.assertTrue(expected_shared_lighting_fixture(spec,spec['actor'],state))
        self.assertFalse(expected_shared_lighting_fixture(spec,'DirectionalLight_1',state))
        self.assertFalse(expected_shared_lighting_fixture(spec,spec['actor'],{**state,'label':'Another sun'}))
        self.assertEqual(lighting_readback(.003000000026,.003),.003000000026)
        with self.assertRaises(ValueError):lighting_readback(.005,.003)
        treatment=self.plan['lightingTreatment']
        self.assertEqual(treatment['exposureUnits'],'native_luminance')
        self.assertIs(checked_lighting_exposure(treatment,False),False)
        for edited,actual in ((treatment,True),({**treatment,'expectedExtendedEV100':True},False),
                              ({**treatment,'exposureUnits':'extended_ev100'},False)):
            with self.assertRaises(ValueError):checked_lighting_exposure(edited,actual)
        exposure=next(row for row in LIGHTING_FIXTURES if row['actor']=='PostProcessVolume_0')['properties']
        self.assertEqual([exposure['auto_exposure_min_brightness'],exposure['auto_exposure_max_brightness']],[2**6,2**12])
        self.assertEqual([exposure['histogram_log_min'],exposure['histogram_log_max']],[1,14])
        self.assertEqual(treatment['schemaVersion'],2)
        self.assertFalse(treatment['existingAtmospherePreserved'])
        self.assertEqual(len(LIGHTING_FIXTURES),7)
        atmosphere=next(row for row in LIGHTING_FIXTURES if row['id']=='atmosphere')['properties']
        self.assertEqual(atmosphere,dict(rayleigh_scattering_scale=.0331,rayleigh_exponential_distribution=8))
        self.assertTrue(all(row['mobility']=='movable' for row in self.plan['architecturalLights']))
        self.assertTrue(all(row['castShadows'] for row in self.plan['architecturalLights']))

    def test_shadowed_practical_lights_stand_outside_opaque_gate_surfaces(self):
        rows={row['id']:row for row in self.plan['architecturalLights']}
        for i in (0,1):
            portal=rows['portal_reveal_'+str(i)]
            # The main wall is 280 cm deep around X26000. A shadowed light
            # beyond its inner face can illuminate the doorway instead of stone.
            self.assertGreater(portal['pointCm'][0]-portal['sourceRadiusCm'],26140)
            outer=rows['gate_fire_pool_'+str(i)]
            self.assertLess(outer['pointCm'][0]+outer['sourceRadiusCm'],13600)
            inner=rows['gate_fire_pool_'+str(i+2)]
            self.assertLess(inner['pointCm'][0]+inner['sourceRadiusCm'],24413)
        for row in (r for r in rows.values() if r['id'].startswith('hall_sconce_')):
            # Each paired practical reaches its actual central-aisle floor;
            # a 27 m radius at Y39 m leaves the entire aisle unlit.
            self.assertLess(math.hypot(row['pointCm'][1],row['pointCm'][2]-6010),row['attenuationRadiusCm'])

    def test_native_color_constructor_preserves_rgba_despite_reflected_bgra_order(self):
        def color(b=0,g=0,r=0,a=0):return SimpleNamespace(r=r,g=g,b=b,a=a)
        def linear_color(r=0,g=0,b=0,a=0):return SimpleNamespace(r=r,g=g,b=b,a=a)
        def vector4(x=0,y=0,z=0,w=0):return SimpleNamespace(x=x,y=y,z=z,w=w)
        rgba=[158,187,226,255]
        self.assertEqual([color(*rgba).r,color(*rgba).g,color(*rgba).b,color(*rgba).a],[226,187,158,255])
        stub=SimpleNamespace(Color=color,LinearColor=linear_color,Vector4=vector4,
            AutoExposureMethod=SimpleNamespace(AEM_HISTOGRAM='AutoExposureMethod.AEM_HISTOGRAM'))
        with patch.dict(sys.modules,unreal=stub):
            for kind,values in (('color',rgba),('linear_color',[.065,.08,.115,1]),('vector4',[.92,.92,.92,1])):
                wanted=dict(kind=kind,value=values)
                self.assertEqual(lighting_readback(native_lighting_value(wanted),wanted),values)
            wanted=dict(kind='enum',type='AutoExposureMethod',value='AEM_HISTOGRAM')
            self.assertEqual(lighting_readback(native_lighting_value(wanted),wanted),'AutoExposureMethod.AEM_HISTOGRAM')

    def test_actual_render_buffer_audit_rejects_missing_uvs_or_changed_normals(self):
        lod=dict(lod=0,vertices=3,uvChannels=2,indices=3,cpuReadable=True,invalidPositions=0,
            invalidNormals=0,nonUnitNormals=0,invalidUVs=0,committedSourcePositionMissing=0,
            committedSourceNormalDifferent=0,committedSourceNormalMatches=3,
            sourceMatchingPolicy='oriented_triangle_corners_material_and_uv0',committedSourceTriangleMatches=1,
            committedSourceTrianglesMissing=0,committedSourceTrianglesDifferent=0,
            sourcePositionToleranceCm=.1,sourceNormalDotThreshold=.995,
            sourceUvAbsoluteTolerance=.0005,sourceUvRelativeTolerance=.001,tangentBasis=tangent_basis_fixture(3))
        audit=dict(readOnly=True,mesh='/Private/Mesh.Mesh',available=True,lods=[lod])
        self.assertEqual(checked_render_audit(audit,audit['mesh']),audit)
        for field,value in [('uvChannels',0),('cpuReadable',False),('invalidNormals',1),('committedSourceNormalDifferent',1),
                ('sourceMatchingPolicy','position_only'),('committedSourceTriangleMatches',0),
                ('committedSourceTrianglesMissing',1),('committedSourceTrianglesDifferent',1),
                ('sourcePositionToleranceCm',1),('sourceNormalDotThreshold',.98),
                ('sourceUvAbsoluteTolerance',.005),('sourceUvRelativeTolerance',.01)]:
            bad={**audit,'lods':[{**lod,field:value}]}
            with self.assertRaises(ValueError):checked_render_audit(bad,audit['mesh'])
        with self.assertRaises(ValueError):checked_render_audit(audit,'/Another/Mesh.Mesh')
        self.assertFalse(NATIVE_MESH_BUILD_SETTINGS['recompute_normals'])

    def test_actual_tangent_basis_checks_every_lod_and_rejects_counter_or_threshold_drift(self):
        lod=dict(lod=0,vertices=3,uvChannels=2,indices=3,cpuReadable=True,invalidPositions=0,
            invalidNormals=0,nonUnitNormals=0,invalidUVs=0,committedSourcePositionMissing=0,
            committedSourceNormalDifferent=0,committedSourceNormalMatches=3,
            sourceMatchingPolicy='oriented_triangle_corners_material_and_uv0',committedSourceTriangleMatches=1,
            committedSourceTrianglesMissing=0,committedSourceTrianglesDifferent=0,
            sourcePositionToleranceCm=.1,sourceNormalDotThreshold=.995,sourceUvAbsoluteTolerance=.0005,
            sourceUvRelativeTolerance=.001,tangentBasis=tangent_basis_fixture(3))
        audit=dict(readOnly=True,mesh='/Private/Mesh.Mesh',available=True,lods=[lod,{**lod,'lod':1}])
        self.assertEqual(checked_render_audit(audit,audit['mesh']),audit)
        edits=[(('basisSource',),'source_prediction'),(('highPrecision',),False),
            (('nearZeroComponentTolerance',),.001),(('orthogonalityAbsoluteNormalizedDotTolerance',),.021),
            (('axes','x','unitSquaredTolerance'),.021),(('axes','y','unitSquaredTolerance'),.041),
            (('axes','x','nearZero'),1),(('axes','z','unit'),2),(('axes','y','finite'),2),
            (('axes','x','minimumLength'),0.),(('axes','z','maximumLength'),float('nan')),
            (('pairs','xz','nonOrthogonal'),1),(('pairs','xy','skipped'),1),
            (('pairs','yz','maximumAbsoluteNormalizedDot'),.021),(('orthogonalVertices',),2),
            (('badVertexSamples',),[{'index':0}]),(('badVertexSamplesTruncated',),True)]
        for path,value in edits:
            bad=copy.deepcopy(audit);target=bad['lods'][1]['tangentBasis']
            for key in path[:-1]:target=target[key]
            target[path[-1]]=value
            with self.subTest(path=path),self.assertRaises(ValueError):checked_render_audit(bad,audit['mesh'])
        bad=copy.deepcopy(audit);del bad['lods'][1]['tangentBasis']
        with self.assertRaises(ValueError):checked_render_audit(bad,audit['mesh'])

    def test_array_hash_binds_exact_source_float_bytes_without_reserialization(self):
        import hashlib
        text='{"positions":[[0.0,1e-08,2]],"normals":[[0,0,1.0]]}'
        expected=hashlib.sha256(b'[[0.0,1e-08,2]]').hexdigest()
        self.assertEqual(source_array_sha256(text,'positions'),expected)
        self.assertNotEqual(source_array_sha256(text.replace('0.0','0'),'positions'),expected)
        with self.assertRaises(ValueError):source_array_sha256(text,'unknown')

    def test_native_boundary_reverses_faces_and_preserves_outward_source_data(self):
        source=Mesh('native_floor');source.face([[0,0,6010],[100,0,6010],[0,100,6010]])
        data=source.export();original=copy.deepcopy(data)
        indices=native_triangle_indices(data,SOURCE_TRIANGLE_CONVENTION)
        self.assertEqual(indices,[0,2,1]);self.assertEqual(data,original)
        a,b,c=[data['positions'][i] for i in indices]
        self.assertLess((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]),0)
        self.assertEqual(data['normals'],[[0.,0.,1.]]*3)
        self.assertEqual(NATIVE_IMPORT_CONVENTION['normalPolicy'],'preserve_outward_source_normals')

    def test_native_boundary_rejects_unknown_or_inconsistent_source_conventions(self):
        source=Mesh('mixed_faces');source.face([[0,0,0],[100,0,0],[0,100,0]])
        data=source.export()
        with self.assertRaises(ValueError):native_triangle_indices(data,'unknown')
        data['indices']=[0,2,1]
        with self.assertRaises(ValueError):native_triangle_indices(data,SOURCE_TRIANGLE_CONVENTION)
        data['indices']=[0,0,1]
        with self.assertRaises(ValueError):native_triangle_indices(data,SOURCE_TRIANGLE_CONVENTION)

    def test_private_proof_start_uses_the_signed_retained_spawn_with_capsule_clearance(self):
        self.assertEqual(proof_start_position(self.plan),[-15800,0,109])
        self.assertEqual(self.plan['teamSpawns'][1],[-15800,0,10])

    def test_city_revision_binds_final_saved_scenery_and_exact_json_payload(self):
        private={'/Private/Geometry':'a'*64,'/Private/City':'d'*64}
        source={'/Shared/Population':'b'*64};scenery={**source,'/Private/Geometry':'a'*64}
        dependencies={'/Private/Mesh':'c'*64};origin=[0.,-0.,0.]
        city=dict(sceneryLevels=list(scenery),definition='/Private/City',packageHashes={**scenery,'/Private/City':'d'*64},
            dependencyHashes=dependencies,origin=origin,revision=canonical_city_revision(scenery,dependencies,origin),
            revisionPayload=canonical_city_payload(scenery,dependencies,origin))
        require_final_city_hashes(city,private,source)
        with self.assertRaises(ValueError):require_final_city_hashes(city,{**private,'/Private/Geometry':'e'*64},source)
        with self.assertRaises(ValueError):require_final_city_hashes(city,{**private,'/Shared/Population':'e'*64},source)
        with self.assertRaises(ValueError):require_final_city_hashes({**city,'revisionPayload':city['revisionPayload']+' '},private,source)

    def test_every_raised_platform_has_actual_stair_and_balcony_access(self):
        for side in ('west','east'):
            for position in ('south','north'):
                target=side+'_'+position+'_high'
                self.assertTrue(any(r['end']==target and r['kind']=='stair' for r in self.plan['routes']))
            self.assertTrue(any(r['id']==side+'_wall_balcony' for r in self.plan['routes']))
            self.assertTrue(any(r['id']==side+'_gallery_descent' for r in self.plan['routes']))
        for r in self.plan['routes']:
            for a,b in zip(r['points'],r['points'][1:]):
                run=math.dist(a[:2],b[:2]);rise=abs(a[2]-b[2])
                self.assertTrue(run>0 or rise==0, r['id'])
                if r['kind']=='stair' and rise:self.assertGreaterEqual(run/math.ceil(rise/15),18,r['id'])

    def test_all_outer_and_inner_stage_crossings_have_physical_gate_leaves(self):
        self.assertEqual(len(self.gates),8)
        for gate in self.plan['gates']:
            x=gate['leaves'][0]['point'][0]
            for route in self.plan['routes']:
                for a,b in zip(route['points'],route['points'][1:]):
                    if min(a[0],b[0])<=x<=max(a[0],b[0]) and a[0]!=b[0]:
                        # Routes immediately adjoining the gate are deliberately restricted.
                        t=(x-a[0])/(b[0]-a[0]);y=a[1]+t*(b[1]-a[1]);z=a[2]+t*(b[2]-a[2])
                        self.assertTrue(any(abs(y-l['point'][1])<=l['width']/2 and abs(z-l['point'][2])<2 for l in gate['leaves']),route['id'])

    def test_portcullises_use_fitted_bars_and_masonry_has_valid_geometry(self):
        for mesh in [*self.structure,*self.gates]:
            data=mesh.export();self.assertEqual(len(data['indices'])//3,len(data['triangleMaterials']))
            self.assertEqual(len(data['positions']),len(data['uvs']))
            self.assertTrue(all(math.isfinite(v) for p in data['positions'] for v in p))
            self.assertGreater(len(data['indices']),100)
        main_gate=self.gates[0]
        self.assertLessEqual(max(p[1] for p in main_gate.positions)-min(p[1] for p in main_gate.positions),1860)

    def test_zero_run_stair_is_rejected_and_doorway_graph_cannot_drift(self):
        bad=copy.deepcopy(self.plan);bad['routes'][0]['points'][-1]=[14201,0,4210]
        with self.assertRaises(ValueError):validate(bad)
        self.assertAlmostEqual(max(p[1] for p in pointed_profile(1800,2600)),2600)

    def test_side_wall_opening_clipping_never_seals_the_main_portal(self):
        side=Mesh('negative_flank')
        wall_cut(side,26000,-7300,-4600,6010,11200,self.plan['gates'][1]['leaves'],280)
        self.assertGreaterEqual(min(p[1] for p in side.positions),-7300)
        self.assertLessEqual(max(p[1] for p in side.positions),-4600)
        shell=next(m for m in self.structure if m.key=='fortress_keep_shell')
        # A +X ray at capsule/head heights must pass the entire front wall.
        for z in (6106,6202,7010,8010):
            for i in range(0,len(shell.indices),3):
                a,b,c=[shell.positions[j] for j in shell.indices[i:i+3]]
                den=(b[1]-a[1])*(c[2]-a[2])-(b[2]-a[2])*(c[1]-a[1])
                if abs(den)<.01:continue
                u=((0-a[1])*(c[2]-a[2])-(z-a[2])*(c[1]-a[1]))/den
                v=((b[1]-a[1])*(z-a[2])-(b[2]-a[2])*(0-a[1]))/den
                if u>=0 and v>=0 and u+v<=1:
                    x=a[0]+u*(b[0]-a[0])+v*(c[0]-a[0])
                    self.assertFalse(25700<x<26400,'Main portal contains solid front masonry')

    def test_all_route_centerlines_have_headroom_below_authored_decks(self):
        # Spatially index projected triangles. This catches a deck roofing over
        # a switchback flight even when its route endpoints and graph are valid.
        bins={}
        lowest=min(p[2] for route in self.plan['routes'] for p in route['points'])
        highest=max(p[2] for route in self.plan['routes'] for p in route['points'])
        for mesh in self.structure:
            for i in range(0,len(mesh.indices),3):
                a,b,c=[mesh.positions[j] for j in mesh.indices[i:i+3]]
                if min(a[2],b[2],c[2])>highest+200 or max(a[2],b[2],c[2])<lowest+25:continue
                den=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
                if abs(den)<.01:continue
                tri=(a,b,c,den,mesh.key)
                for x in range(math.floor(min(p[0] for p in (a,b,c))/1000),math.floor(max(p[0] for p in (a,b,c))/1000)+1):
                    for y in range(math.floor(min(p[1] for p in (a,b,c))/1000),math.floor(max(p[1] for p in (a,b,c))/1000)+1):
                        bins.setdefault((x,y),[]).append(tri)
        for route in self.plan['routes']:
            for start,end in zip(route['points'],route['points'][1:]):
                dx,dy=end[0]-start[0],end[1]-start[1];length=math.hypot(dx,dy)
                for j in range(max(2,math.ceil(length/200))):
                    t=(j+.5)/max(2,math.ceil(length/200));floor=start[2]+(end[2]-start[2])*t
                    # At angled landings, lateral samples legitimately stand on
                    # different treads. Native capsule/navigation review measures
                    # the full lane on its actual floor; this test checks the
                    # signed centerline against genuine overhanging decks.
                    for lateral in (0,):
                        x=start[0]+dx*t-dy/length*lateral;y=start[1]+dy*t+dx/length*lateral
                        for a,b,c,den,key in bins.get((math.floor(x/1000),math.floor(y/1000)),[]):
                            u=((x-a[0])*(c[1]-a[1])-(y-a[1])*(c[0]-a[0]))/den
                            v=((b[0]-a[0])*(y-a[1])-(b[1]-a[1])*(x-a[0]))/den
                            if u<0 or v<0 or u+v>1:continue
                            z=a[2]+u*(b[2]-a[2])+v*(c[2]-a[2])
                            self.assertFalse(floor+25<z<floor+200,
                                f'{route["id"]}: {key} overhead at {x:.0f},{y:.0f},{z:.0f}; floor {floor:.0f}')

    def test_furnishings_are_actual_retained_sources(self):
        self.assertTrue(all((ROOT/p['source']).is_file() for p in self.props))
        sculpture=next(p for p in self.props if p['id']=='court_oath')
        self.assertGreater(math.dist(sculpture['point'][:2],self.plan['objectives'][6][:2]),650)
        self.assertEqual(sculpture['point'][:2],[20800,0])
        for prop in self.props:
            if prop['id'].startswith('brazier_'):self.assertTrue(route_clearance(self.plan,prop['point'],75,190),prop['id'])

    def test_centered_monument_keeps_capture_target_and_all_plaza_lanes_clear(self):
        # Slab clipping catches a route passing through the physical 10 m base,
        # including its full advertised width and the capsule's edge clearance.
        for route in self.plan['routes']:
            margin=500+route['width']/2+42
            for a,b in zip(route['points'],route['points'][1:]):
                if min(a[2],b[2])>4510:continue
                lo,hi=0.,1.
                for axis,center in ((0,20800),(1,0)):
                    delta=b[axis]-a[axis]
                    if abs(delta)<.01:
                        if not center-margin<=a[axis]<=center+margin:lo=2;break
                    else:
                        t0,t1=(center-margin-a[axis])/delta,(center+margin-a[axis])/delta
                        lo=max(lo,min(t0,t1));hi=min(hi,max(t0,t1))
                self.assertGreater(lo,hi,route['id'])

    def test_crossing_ledger_records_shared_segments_and_separated_levels(self):
        routes=[dict(id='west_east',points=[[-10,0,0],[10,0,0]]),
                dict(id='south_north',points=[[0,-10,0],[0,10,0]]),
                dict(id='upper',points=[[-10,0,100],[10,0,100]]),
                dict(id='shared',points=[[-5,0,0],[5,0,0]])]
        crossings=crossing_ledger(routes)
        self.assertTrue(any(r['routes']==['west_east','south_north'] and r['connects'] for r in crossings))
        self.assertTrue(any(r['routes']==['west_east','upper'] and r['kind']=='shared_segment' and not r['connects'] for r in crossings))
        self.assertTrue(any(r['routes']==['west_east','shared'] and r['kind']=='shared_segment' and r['connects'] for r in crossings))
        self.assertEqual(self.plan['crossingLedger'],crossing_ledger(self.plan['routes']))
        for point in ([19400,-1000,4210],[22200,-1000,4210]):
            self.assertTrue(any(r['connects'] and r['kind']=='point' and point in r['positionsCm'] for r in self.plan['crossingLedger']))

    def test_reference_groups_account_for_every_route_and_do_not_bypass_stage_cuts(self):
        groups=self.plan['referenceCoverage'];routes={r['id']:r for r in self.plan['routes']}
        self.assertEqual({key for group in groups for key in group['routes']},set(routes))
        corners=[g for g in groups if g['id'].startswith('inset_') and g['id'].endswith('_raised_corner')]
        self.assertEqual(len(corners),4)
        for group in corners:
            self.assertTrue(any(routes[key]['kind']=='stair' for key in group['routes']))
            self.assertTrue(any(routes[key]['kind']=='balcony' for key in group['routes']))
        for route in routes.values():
            if route['id'].endswith(('_approach','_main_gate')):self.assertEqual(route['gate'],0)
            if route['id'].endswith(('_portal_stair','_gallery_stair','_gallery_aisle','_hall_side_aisle')):
                self.assertEqual(route['gate'],1)
        self.assertFalse(self.plan['interpretation']['scaleAssumption']['measuredDrawing'])

    def test_additional_enclosure_edit_mask_preserves_outside_components(self):
        state=dict(tags=['WarWorldObject_aegis_battle_enclosure_fixture'])
        rows=[dict(actor='outside',state=state,bounds=[[10000,-100,4200],[11000,100,5500]],componentBounds=[]),
              dict(actor='inside',state=state,bounds=[[24000,-100,4200],[25000,100,5500]],componentBounds=[]),
              dict(actor='compound',state=state,bounds=[[11000,-100,4200],[25000,100,5500]],
                   componentBounds=[dict(name='lower',bounds=[[11000,-100,4200],[12000,100,5500]]),
                                    dict(name='upper',bounds=[[24000,-100,4200],[25000,100,5500]])])]
        edits,preserved=upper_enclosure_edits(dict(actors={'/fixture':rows}))
        self.assertEqual([r['actor'] for r in preserved],['outside'])
        self.assertEqual(edits[0]['mode'],'actor')
        self.assertEqual(edits[1]['mode'],'components')
        self.assertEqual(edits[1]['removeComponents'],['upper'])
        self.assertEqual(edits[1]['clipRequired'],[])

    def test_lower_road_entry_retains_a_square_full_height_foundation_edge(self):
        court=next(mesh for mesh in self.structure if mesh.key=='court_and_foundations')
        top_faces=[]
        for index in range(0,len(court.indices),3):
            triangle=[court.positions[i] for i in court.indices[index:index+3]]
            if all(abs(point[2]-4210)<.001 for point in triangle):top_faces.append(triangle)
        # The actual failed seam is X14200/Y429, where the retained road is 6.5 cm
        # below the deck. An inset/chamfered deck must not erase that top boundary.
        boundary=[point for triangle in top_faces for point in triangle if abs(point[0]-14200)<.001]
        self.assertTrue(any(point[1]<=429 for point in boundary))
        self.assertTrue(any(point[1]>=429 for point in boundary))
        self.assertFalse(any(4200<point[2]<4210 and abs(point[0]-14200)<.001
            for point in court.positions))

    def test_approach_wall_toes_require_surveyed_enclosure_identity_and_exact_bounded_modules(self):
        state=dict(tags=['WarWorldObject_aegis_battle_enclosure_front_fixture'])
        bounds=[[13276.9,-7101.25,4200],[13323.1,-6830,4500.1]]
        rows=[dict(actor='toe',state=state,bounds=bounds,componentBounds=[]),
              dict(actor='above',state=state,bounds=[[13276.9,-7101.25,4500],[13323.1,-6830,4800.1]],componentBounds=[]),
              dict(actor='spanning',state=state,bounds=[[13100,-7101.25,4200],[13323.1,-6830,4500.1]],componentBounds=[]),
              dict(actor='city_service',state=dict(tags=['WarCapitalNpc']),bounds=bounds,componentBounds=[])]
        edits,preserved=upper_enclosure_edits(dict(actors={'/fixture':rows}))
        self.assertEqual([row['actor'] for row in edits],['toe'])
        self.assertEqual(edits[0]['editVolume'],'west_approach_wall_toe')
        self.assertEqual({row['actor'] for row in preserved},{'above','spanning'})
        self.assertNotIn('city_service',{row['actor'] for row in edits})
        mask=self.plan['editMask'];toe=edits[0]
        self.assertEqual(enclosure_edit_bounds(mask,toe),[[13250,-7120,4190],[13350,-6810,4520]])
        for changed in ({**toe,'mode':'components'},{**toe,'identity':'aegis_city_service'},
                        {**toe,'editVolume':'unbounded'},{**toe,'bounds':rows[2]['bounds']}):
            with self.assertRaises(ValueError):enclosure_edit_bounds(mask,changed)
        enlarged=copy.deepcopy(mask);enlarged['approachEnclosureBounds'][0]['bounds'][0][0]=13000
        with self.assertRaises(ValueError):enclosure_edit_bounds(enlarged,toe)

    def test_original_pbr_channels_and_legible_gold_cloth_survive_native_staging(self):
        for spec in MATERIAL_SPECS.values():
            for key in ('baseColor','normal','orm','height','provenance'):
                if key in spec:self.assertTrue((ROOT/spec[key]).is_file())
        self.assertNotIn('baseColor',MATERIAL_SPECS['blue'])
        self.assertNotIn('baseColor',MATERIAL_SPECS['gold'])
        self.assertGreater(max(MATERIAL_SPECS['glass']['emission']),0)

    def test_matching_ashlar_height_is_fine_scaled_and_not_mixed_with_another_atlas(self):
        for role in ('stone','limestone'):
            spec=MATERIAL_SPECS[role]
            self.assertIn('height',spec);self.assertNotIn('normal',spec);self.assertNotIn('orm',spec)
            self.assertEqual(UV_PERIOD_CM[role],360)
            self.assertEqual(spec['texturePowerOfTwo'],'stretch_to_2048')
        mesh=Mesh('physical_uv');mesh.face([[0,0,9000],[360,0,9000],[0,360,9500]])
        mesh.reshape_upper(9000,10000,9500);mesh.reproject_stone_uvs()
        for p,uv,n in zip(mesh.positions,mesh.uvs,mesh.normals):
            axis=max(range(3),key=lambda j:abs(n[j]));axes=[j for j in range(3) if j!=axis]
            self.assertEqual(uv,[p[j]/360 for j in axes])

    def test_final_spire_and_pointed_cloth_keep_their_authored_slender_proportions(self):
        mesh=Mesh('skyline');tower(mesh,30400,0,17700,1100,2200,2100,'lantern')
        mesh.reshape_upper(9000,22220,14200)
        self.assertAlmostEqual(max(p[2] for p in mesh.positions),14200,places=3)
        roof=[mesh.positions[i] for offset,role in enumerate(mesh.triangle_materials)
              if MATERIALS[role]=='slate' for i in mesh.indices[offset*3:offset*3+3]]
        cap=mesh.articulated_spire_details[0]
        self.assertGreaterEqual(cap['widthCm'],1100)
        extent=cap['maximumEnvelopeHalfWidthCm']
        central=[p for p in roof if abs(p[0]-30400)<=extent and abs(p[1])<=extent]
        self.assertGreater(max(p[2] for p in central)-min(p[2] for p in central),1800)
        cloth=Mesh('standard');final_banner(cloth,25620,0,11100,950,2050)
        cloth.reshape_upper(9000,22220,14200)
        blue=[cloth.positions[i] for offset,role in enumerate(cloth.triangle_materials)
              if MATERIALS[role]=='blue' for i in cloth.indices[offset*3:offset*3+3]]
        center=min(p[2] for p in blue if abs(p[1])<1)
        edge=min(p[2] for p in blue if abs(p[1])>470)
        self.assertLess(center,edge-300);self.assertGreater(center,8610+90)
        self.assertGreater(max(p[0] for p in blue)-min(p[0] for p in blue),60)
        self.assertLess(max(p[0] for p in blue)-min(p[0] for p in blue),140)

    def test_integrated_central_standard_is_supported_and_replaces_the_squat_cloth(self):
        facade=next(mesh for mesh in self.structure if mesh.key=='gothic_facade_and_spires')
        receipt=facade.central_standard_replacement
        blue=[facade.positions[i] for offset,role in enumerate(facade.triangle_materials)
              if MATERIALS[role]=='blue' for i in facade.indices[offset*3:offset*3+3]
              if abs(facade.positions[i][1])<=950 and facade.positions[i][2]>9400]
        self.assertTrue(blue)
        self.assertGreater(min(p[0] for p in blue),25600)
        self.assertAlmostEqual(min(p[2] for p in blue),9732,places=3)
        self.assertAlmostEqual(max(p[2] for p in blue),12400,places=3)
        self.assertGreater(receipt['minimumRollClearanceCm'],300)
        self.assertGreater(receipt['minimumClothWallGapCm'],30)
        self.assertEqual(receipt['bracketCount'],2)
        # The raised strip intersects the old wall; it is not a floating shield.
        self.assertLess(receipt['wallJoinBottomCm'],receipt['retainedWallTopCm'])
        self.assertFalse(receipt['nativeApproved'])

    def test_wing_repairs_join_the_existing_base_without_intersecting_reserved_lanes(self):
        mesh=next(m for m in self.structure if m.key=='wing_foundation_repairs')
        receipt=mesh.wing_foundation_repairs
        self.assertEqual(len(receipt['rows']),10)
        self.assertEqual(min(p[2] for p in mesh.positions),2400)
        self.assertEqual(max(p[2] for p in mesh.positions),6010)
        self.assertTrue(receipt['existingFoundationPreserved'])
        self.assertTrue(receipt['retainedTerrainPreserved'])
        self.assertEqual(receipt['requiredNativeGroundSamples'],144)
        self.assertTrue(all(r['subtractions']==0 for r in receipt['rows']))
        for r in receipt['rows']:
            a,b=r['boundsCm']
            if r['id'].startswith('wing_connection'):
                self.assertEqual(a[2],5788-12)
                self.assertEqual(b[0],33400)
            elif r['id'].startswith('wing_rear'):
                self.assertEqual(a[0],33400)
                self.assertEqual(b[0],34400)
            else:
                self.assertTrue(a[1]>=9100 or b[1]<=-9100)
        self.assertFalse(receipt['nativeApproved'])

    def test_integrated_wing_cornices_clear_window_crowns_and_preserve_bay_positions(self):
        facade=next(m for m in self.structure if m.key=='gothic_facade_and_spires')
        rows=facade.wing_hierarchy
        self.assertEqual(len(rows),6)
        self.assertEqual({(r['side'],r['tier']) for r in rows},
                         {(s,t) for s in (-1,1) for t in range(3)})
        for r in rows:
            self.assertTrue(r['integrated'])
            self.assertTrue(r['structuralBayPositionsUnchanged'])
            self.assertGreaterEqual(r['cornice']['finalBottomCm']-r['finalWindowRevealTopCm'],30-1e-9)
            self.assertAlmostEqual(r['cornice']['finalTopCm']-r['cornice']['finalBottomCm'],80)
            self.assertFalse(r['nativeApproved'])

    def test_full_gallery_width_places_rails_outside_the_reserved_capsule_envelope(self):
        mesh=Mesh('gallery');path_floor(mesh,[[0,0,7210],[1800,0,7210]],600,rails=True)
        iron=[mesh.positions[i] for offset,role in enumerate(mesh.triangle_materials)
              if MATERIALS[role]=='iron' for i in mesh.indices[offset*3:offset*3+3]]
        self.assertGreaterEqual(min(abs(p[1]) for p in iron),305)

    def test_diagonal_stair_landing_cannot_insert_a_high_wall_before_its_final_tread(self):
        for sign in (-1,1):
            mesh=Mesh('portal_landing')
            points=[[24510,sign*5082.273,4210],[25400,sign*3100,6010],[26000,sign*3100,6010]]
            path_floor(mesh,points,600,stairs=True)
            # Actual native stall: former rectangular landing was 145 cm above
            # the feet here. A joined flight must expose only its proper tread.
            x,y=25357.901,sign*3312.226;heights=[]
            for offset,role in enumerate(mesh.triangle_materials):
                if MATERIALS[role]!='flagstone':continue
                a,b,c=[mesh.positions[i] for i in mesh.indices[offset*3:offset*3+3]]
                den=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
                if abs(den)<.001:continue
                u=((x-a[0])*(c[1]-a[1])-(y-a[1])*(c[0]-a[0]))/den
                v=((b[0]-a[0])*(y-a[1])-(b[1]-a[1])*(x-a[0]))/den
                if min(u,v)>=0 and u+v<=1:heights.append(a[2]+u*(b[2]-a[2])+v*(c[2]-a[2]))
            self.assertTrue(heights)
            self.assertLess(max(heights),5890)


class SurfaceCapsulePoseTests(unittest.TestCase):
    def profile(self,knots):return dict(knotsCm=knots)

    def test_flat_and_both_slope_directions_keep_full_capsule_dimensions(self):
        for slope in (0,.6365,-.6365):
            p=self.profile([[-1000,-1000*slope],[1000,1000*slope]])
            self.assertAlmostEqual(profile_capsule_offset(p,0),54+42*math.hypot(1,slope)+5,places=10)
        self.assertEqual(profile_capsule_offset(self.profile([[-1000,0],[1000,0]]),0),101)

    def test_piecewise_knots_use_the_actual_sphere_support_envelope(self):
        valley=self.profile([[-1000,500],[0,0],[1000,500]])
        crest=self.profile([[-1000,-500],[0,0],[1000,-500]])
        self.assertAlmostEqual(profile_capsule_offset(valley,0),54+42*math.hypot(1,.5)+5,places=10)
        self.assertEqual(profile_capsule_offset(crest,0),101)
        elbow=self.profile([[-1000,0],[0,0],[1000,500]])
        for x in (-35,-10,0,10,35):
            actual=profile_capsule_offset(elbow,x);floor=profile_height(elbow,x)
            sampled=max(profile_height(elbow,x+dx)-floor+math.sqrt(max(0,42*42-dx*dx))
                        for dx in (-42+i*84/4000 for i in range(4001)))+59
            self.assertGreaterEqual(actual+1e-10,sampled)
            self.assertLess(actual-sampled,.001)

    def test_closed_domain_requires_the_complete_capsule_footprint(self):
        p=self.profile([[-1000,0],[1000,0]])
        self.assertEqual(profile_capsule_offset(p,-958),101)
        for x in (-958-1e-9,958+1e-9,float('nan'),True):
            with self.assertRaises(ValueError):profile_capsule_offset(p,x)

    def test_measured_east_fan_rest_matches_the_real_native_contact_pose(self):
        p=plan()['routeSurfaceProfiles'][1]
        self.assertAlmostEqual(profile_capsule_offset(p,11600),108.78607525202187,places=10)
        self.assertGreater(profile_capsule_offset(p,11600),101)


class SpawnSurfaceTests(unittest.TestCase):
    def test_native_relocation_witness_binds_unchanged_actors_paths_and_complete_footprint(self):
        import citadel_spawn_surface as surfaces
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);baseline_file=root/'artifacts/unreal/aegis-citadel/baseline.json'
            baseline_file.parent.mkdir(parents=True)
            floor='/Game/OriginalFloor';city='/Game/OriginalCity'
            copied='/Game/PrivateCandidate/Layers/RetainedCity_0';actor=copied+'.RetainedCity_0:PersistentLevel.FloorActor'
            state=dict(location=[0,0,0],components=[dict(name='FloorComponent',class_='StaticMeshComponent',mesh=floor+'.OriginalFloor')])
            state['components'][0]['class']=state['components'][0].pop('class_')
            state_hash=hashlib.sha256(json.dumps(state,sort_keys=True,separators=(',', ':')).encode()).hexdigest()
            baseline=dict(file=baseline_file.relative_to(root).as_posix(),packageHashes={floor:'a'*64,city:'b'*64},
                city=dict(sceneryLevels=[city]),
                battlefield=dict(team_spawns=[[5800,-4800,910],[-15800,0,10]],
                    objectives=[[-11600,0,10],[-1000,0,10],[11900,-400,4000]],optional_objectives=[[-7900,3400,10]]),
                actors={city:[dict(actor='FloorActor',state=state)]},spawnPadSurfaces=[])
            for index,point in enumerate(baseline['battlefield']['team_spawns']):
                baseline['spawnPadSurfaces'].append(dict(schemaVersion=1,index=index,point=point,widthCm=600,
                    groundGradient=[0,0],capsuleRadiusCm=42,capsuleHalfHeightCm=96,diagnosticOnly=True,
                    samples=[dict(x=x,y=y,floor=surfaces.seed(point,x,y,258,[0,0]),normal=[0,0,1],capsuleClear=True,
                        source=dict(meshPackage=floor,meshSha256='a'*64,actorPackage=city,actorPath='original.actor',
                            componentPath='original.actor.mesh',actorStateSha256=state_hash)) for x in range(-2,3) for y in range(-2,3)]))
            baseline_file.write_text(json.dumps(baseline))
            destination=[3000,-6500,3.5];convoy=[[-1000,0,10],[11900,-400,4000]]
            delta=[convoy[1][i]-convoy[0][i] for i in range(3)]
            t=sum((destination[i]-convoy[0][i])*delta[i] for i in range(3))/sum(v*v for v in delta)
            gap=math.dist(destination,[convoy[0][i]+t*delta[i] for i in range(3)])
            pad=dict(pointCm=destination,widthCm=600,groundGradient=[0,0],minimumConvoyCentrePathDistanceCm=gap,
                diagnosticFootprintComplete=True,samples=[dict(x=x,y=y,pointCm=surfaces.seed(destination,x,y,258,[0,0]),
                    normal=[0,0,1],capsuleClear=True,source=dict(meshPackage=floor,meshSha256='a'*64,
                        actorPackage=copied,actorPath=actor,componentPath=actor+'.FloorComponent',
                        originalActorPackage=city,originalActorName='FloorActor',actorStateSha256=state_hash))
                    for x in range(-2,3) for y in range(-2,3)])
            for key,end in (('characterPathToOriginalSpawn',baseline['battlefield']['team_spawns'][0]),
                            ('characterPathToCheckpoint',baseline['battlefield']['objectives'][2])):
                pad[key]=dict(valid=True,partial=False,pointsCm=[destination,end])
            report=dict(schemaVersion=1,packagesUnchanged=True,diagnosticOnly=True,traversalApproved=False,visualApproved=False,
                protectionRadiusCm=750,spawnsCm=baseline['battlefield']['team_spawns'],
                baselineSha256=hashlib.sha256(baseline_file.read_bytes()).hexdigest(),packageHashes={**baseline['packageHashes'],copied:'d'*64},
                spawnPadCandidates=[pad],paths=[dict(kind='direct',segments=[dict(valid=True,partial=False,pointsCm=convoy)])],
                map='/Game/PrivateCandidate/SiegeCandidate',revision='fixture')
            survey=root/'artifacts/unreal/citadel-reference/survey.json';survey.parent.mkdir(parents=True)
            def save(value):survey.write_text(json.dumps(value))
            with patch.object(surfaces,'ROOT',root):
                save(report);relocation=surfaces.relocation_witness(survey,baseline)
                approaches=[dict(index=index,points=[destination if index==0 else point],widthCm=600,groundGradient=[0,0])
                    for index,point in enumerate(baseline['battlefield']['team_spawns'])]
                surfaces.validate_retained_surfaces(baseline,approaches,[relocation],11)
                self.assertEqual(baseline['spawnPadSurfaces'][0]['point'],[5800,-4800,910])
                with self.assertRaises(ValueError):surfaces.validate_retained_surfaces(baseline,approaches,[relocation],10)
                for change in ('baseline','actor','gap','blocked','missing','partial','source','mesh','actor_path','component_path','actor_package','coherent_copy'):
                    bad=copy.deepcopy(report)
                    if change=='baseline':bad['baselineSha256']='c'*64
                    elif change=='actor':bad['spawnPadCandidates'][0]['samples'][0]['source']['actorStateSha256']='c'*64
                    elif change=='gap':bad['spawnPadCandidates'][0]['minimumConvoyCentrePathDistanceCm']+=1
                    elif change=='blocked':bad['spawnPadCandidates'][0]['samples'][0]['capsuleClear']=False
                    elif change=='missing':bad['spawnPadCandidates'][0]['samples'].pop()
                    elif change=='partial':bad['spawnPadCandidates'][0]['characterPathToCheckpoint']['partial']=True
                    elif change=='source':bad['packageHashes'][floor]='c'*64
                    elif change=='mesh':
                        bad['spawnPadCandidates'][0]['samples'][0]['source'].update(meshPackage=city,meshSha256='b'*64)
                    elif change=='actor_path':bad['spawnPadCandidates'][0]['samples'][0]['source']['actorPath']=actor+'Wrong'
                    elif change=='component_path':bad['spawnPadCandidates'][0]['samples'][0]['source']['componentPath']=actor+'.OtherComponent'
                    elif change=='actor_package':
                        wrong='/Game/PrivateCandidate/Layers/OtherCity';bad['packageHashes'][wrong]='e'*64
                        bad['spawnPadCandidates'][0]['samples'][0]['source']['actorPackage']=wrong
                    else:
                        wrong='/Game/PrivateCandidate/Layers/RetainedCity_1';bad['packageHashes'][wrong]='e'*64
                        wrong_actor=wrong+'.RetainedCity_1:PersistentLevel.FloorActor'
                        bad['spawnPadCandidates'][0]['samples'][0]['source'].update(actorPackage=wrong,
                            actorPath=wrong_actor,componentPath=wrong_actor+'.FloorComponent')
                    save(bad)
                    with self.subTest(change=change),self.assertRaises(ValueError):
                        row=surfaces.relocation_witness(survey,baseline)
                        surfaces.validate_retained_surfaces(baseline,approaches,[row],11)

    def test_relocation_retains_protection_and_requires_both_actual_native_connections(self):
        from citadel_spawn_surface import _validate_relocation
        baseline=dict(battlefield=dict(team_spawns=[[5800,-4800,910]],objectives=[None,None,[11900,-400,4000]]))
        row=dict(schemaVersion=1,index=0,fromPoint=[5800,-4800,910],point=[5500,-8000,778.5],
            measuredSurface=dict(point=[5500,-8000,778.5]),protectionRadiusCm=750,
            minimumConvoyCentrePathDistanceCm=3310.99,freshNativeReplayRequired=True,nativeTraversalApproved=False)
        for key,end in (('characterPathToOriginalSpawn',row['fromPoint']),
                        ('characterPathToCheckpoint',baseline['battlefield']['objectives'][2])):
            row[key]=dict(valid=True,partial=False,pointsCm=[row['point'],end])
        _validate_relocation(row,baseline)
        for change in ('protection','gap','partial','invalid','start','end','nan','approval','old_anchor'):
            bad=copy.deepcopy(row)
            if change=='protection':bad['protectionRadiusCm']=100
            elif change=='gap':bad['minimumConvoyCentrePathDistanceCm']=1299
            elif change=='partial':bad['characterPathToOriginalSpawn']['partial']=True
            elif change=='invalid':bad['characterPathToCheckpoint']['valid']=False
            elif change=='start':bad['characterPathToCheckpoint']['pointsCm'][0]=[0,0,0]
            elif change=='end':bad['characterPathToOriginalSpawn']['pointsCm'][-1]=[0,0,0]
            elif change=='nan':bad['characterPathToCheckpoint']['pointsCm'][-1][0]=float('nan')
            elif change=='approval':bad['nativeTraversalApproved']=True
            else:bad['fromPoint']=[5800,-4800,9]
            with self.subTest(change=change),self.assertRaises(ValueError):_validate_relocation(bad,baseline)

    def test_retained_ramp_requires_complete_native_source_and_clearance_witness(self):
        from citadel_spawn_surface import validate_retained_surfaces,seed
        pads=plan()['spawnApproaches'];hashes={'/Game/OriginalFloor':'a'*64,'/Game/OriginalCity':'b'*64}
        rows=[]
        for pad in pads[:2]:
            slope=pad['groundGradient'];nz=1/math.sqrt(1+sum(v*v for v in slope))
            rows.append(dict(schemaVersion=1,index=pad['index'],point=pad['points'][0],widthCm=600,
                groundGradient=slope,capsuleRadiusCm=42,capsuleHalfHeightCm=96,diagnosticOnly=True,
                samples=[dict(x=x,y=y,floor=seed(pad['points'][0],x,y,258,slope),
                    normal=[-slope[0]*nz,-slope[1]*nz,nz],capsuleClear=True,
                    source=dict(meshPackage='/Game/OriginalFloor',meshSha256='a'*64,
                        actorPackage='/Game/OriginalCity',actorPath='original.actor',componentPath='original.actor.mesh',
                        actorStateSha256='c'*64)) for x in range(-2,3) for y in range(-2,3)]))
        baseline=dict(packageHashes=hashes,spawnPadSurfaces=rows)
        validate_retained_surfaces(baseline,pads)
        for change in ('missing','duplicate','hash','blocked','floor','slope'):
            bad=copy.deepcopy(baseline);sample=bad['spawnPadSurfaces'][0]['samples'][0]
            if change=='missing':bad['spawnPadSurfaces'].pop()
            if change=='duplicate':bad['spawnPadSurfaces'][0]['samples'][-1]=copy.deepcopy(sample)
            if change=='hash':sample['source']['meshSha256']='d'*64
            if change=='blocked':sample['capsuleClear']=False
            if change=='floor':sample['floor'][2]+=26
            if change=='slope':sample['normal']=[0,0,1]
            with self.subTest(change=change),self.assertRaises(ValueError):
                validate_retained_surfaces(bad,pads)

    def test_versioned_spawn_gradient_preserves_old_flat_footprints(self):
        from citadel_spawn_surface import gradient,seed
        old=dict(index=0)
        self.assertEqual(gradient(old,5),[0,0])
        with self.assertRaises(ValueError):gradient(old,6)
        self.assertEqual(seed([5800,-4800,910],-2,2,258,[.5,0]),[5542,-4542,781])
        for value in ([2,0],[float('nan'),0],[0],None):
            with self.subTest(value=value),self.assertRaises(ValueError):
                gradient(dict(index=0,groundGradient=value),6)
        with self.assertRaises(ValueError):gradient(dict(index=2,groundGradient=[.5,0]),6)


if __name__=='__main__':unittest.main()
