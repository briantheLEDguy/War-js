from fixtures.citadelCapsulePolicy import capsule_collision_policy,capsule_kinematics_policy
"""Portable fixtures only: these guards do not assert native traversal acceptance."""
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/unreal'))
from citadel_route_surface_evidence import (ABSENT, SURFACE_METHOD, checked_profile, checked_profiles,
    checked_surface_bindings, checked_surface_report, surface_height, width_seed)
spec=importlib.util.spec_from_file_location('surface_publisher',ROOT/'scripts/unreal/publish-aegis-citadel.py')
publisher=importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)

PROFILE=dict(schemaVersion=1,routeId='west_approach',kind='world_x_piecewise_linear',meshId='stairs_and_balconies',
    knotsCm=[[-200,0],[400,300],[1000,450]],boundaryPolicy='closed_profile_domain_shared_boundaries_same_height',
    construction='continuous_paved_fan_ramp')
ROUTE=dict(id='west_approach',points=[[400,100,300],[400,900,300]],width=1200)
PROOF=dict(id='west_approach:forward',points=ROUTE['points'],clearWidthCm=1200,surfaceProfile=PROFILE)


def source_fixture():
    positions,indices=[],[]
    for a,b in ((-200,400),(400,1000)):
        i=len(positions)
        positions.extend([[a,0,surface_height(PROFILE,a)],[b,0,surface_height(PROFILE,b)],
            [b,1000,surface_height(PROFILE,b)],[a,1000,surface_height(PROFILE,a)]])
        indices.extend([i,i+1,i+2,i,i+2,i+3])
    payload=json.dumps(PROFILE)
    source=dict(assets=[dict(id='stairs_and_balconies',sha256='a'*64)],surfaceBindings=[dict(routeId=ROUTE['id'],
        profilePayload=payload,profileSha256=hashlib.sha256(payload.encode()).hexdigest(),meshId='stairs_and_balconies',
        sourceMeshSha256='a'*64,topTriangleIndices=[0,1,2,3])])
    return source,dict(routes=[ROUTE],routeSurfaceProfiles=[PROFILE]),dict(stairs_and_balconies=dict(positions=positions,indices=indices))


def width_evidence(routes):
    setup=dict(version=4,placementOverlapPolicy='fresh_live_static_single_body_unit_zero_margin_full_capsule_planes_v1',
        gateOverlapAdmissionRemainsRaw=True,
    capsulePolicyCheckedEveryTick=True,capsulePolicyCheckedEveryPlacementQuery=True,capsuleCollisionPolicy=capsule_collision_policy(),capsuleKinematicsPolicy=capsule_kinematics_policy(),laneFractions=[-1,-.5,0,.5,1],maxSpacingCm=100,movementSpacingCm=10,
        edgeInsetCm=0,maxFloorDeviationCm=120,groundClearanceCm=2.4,minFloorDistanceCm=1.9,maxFloorDistanceCm=2.4,
        capsuleRadiusCm=42,capsuleHalfHeightCm=96,maxStepHeightCm=45,walkableFloorZ=0.7100000381469727,collisionChannel='ECC_Pawn',
        collisionProfile='Custom',simpleCollision=True,movementMethod='ComputeGroundMovementDelta/ramp-resweep/StepUp-floor-handoff/FindFloor/AdjustFloorHeight',
        surfaceSamplingMethod=SURFACE_METHOD,surfaceProfiles=[dict(id=r['id'],surfaceProfile=r['surfaceProfile']) for r in routes])
    rows=[]
    for route in routes:
        previous={}
        for segment,(a,b) in enumerate(zip(route['points'],route['points'][1:])):
            count=math.ceil(math.dist(a[:2],b[:2])/100)
            for sample in range(count+1):
                for lane in setup['laneFractions']:
                    seed=width_seed(route,segment,sample/count,lane,42)
                    before=previous.get(lane)
                    previous[lane]=seed
                    movement_steps=math.ceil(math.dist(seed[:2],before[:2])/10) if before else 0
                    def raw_evidence(queries):
                        return dict(queries=queries,rawClear=queries,separated=0,blocked=0,unresolved=0,
                            rawBlockingHits=0,lastDisposition='raw_clear' if queries else 'unused',contacts=[])
                    rows.append(dict(id=route['id'],segment=segment,sample=sample,lane=lane,alpha=sample/count,
                        clearWidthCm=route['clearWidthCm'],lateralOffsetCm=lane*(route['clearWidthCm']/2-42),seed=seed,
                        center=[seed[0],seed[1],seed[2]+98.4],floorImpact=seed[:],floorZCm=seed[2],floorNormalZ=.8,
                        floorDistanceCm=2.4,floor=True,placementClear=True,transitionClear=True,passed=True,
                        stepAttempted=False,stepSucceeded=False,movementSteps=movement_steps,
                        placementOverlapEvidence=raw_evidence(2),movementOverlapEvidence=raw_evidence(2+3*movement_steps if movement_steps else 0)))
    return dict(capsuleRadiusCm=42,capsuleHeightCm=192,routeWidthConfig=setup,routeWidthSamples=rows,
        routeWidthComplete=True,routeWidthPassed=True)


class SurfaceTests(unittest.TestCase):
    def test_lane_height_reverse_and_domain(self):
        checked_profiles([PROFILE],[ROUTE])
        self.assertEqual(width_seed(PROOF,0,.5,1,42),[-158,500,21])
        reverse=dict(PROOF,id='west_approach:reverse',points=list(reversed(PROOF['points'])))
        self.assertEqual(width_seed(reverse,0,.5,-1,42),[-158,500,21])
        self.assertEqual(surface_height(PROFILE,400),300)
        with self.assertRaisesRegex(ValueError,'domain'):surface_height(PROFILE,-201)
        with self.assertRaisesRegex(ValueError,'domain'):surface_height(PROFILE,-200-1e-9)
        with self.assertRaisesRegex(ValueError,'domain'):surface_height(PROFILE,1000+1e-9)
        short=copy.deepcopy(PROFILE);short['knotsCm'][0][0]=-190
        with self.assertRaisesRegex(ValueError,'domain'):checked_profiles([short],[ROUTE])

    def test_schema_slope_and_historical_absence(self):
        checked_profiles(ABSENT,[ROUTE])
        with self.assertRaises(ValueError):checked_profiles(None,[ROUTE])
        with self.assertRaises(ValueError):checked_profile(dict(PROFILE,knotsCm=[[-1_000_001,0],[1_000_001,0]]))
        for change in (lambda p:p.update(schemaVersion=True),lambda p:p.update(extra=True),
                lambda p:p['knotsCm'].reverse(),lambda p:p['knotsCm'][1].__setitem__(1,10000)):
            bad=copy.deepcopy(PROFILE);change(bad)
            with self.assertRaises(ValueError):checked_profile(bad)
        ordinary=dict(PROOF);ordinary.pop('surfaceProfile')
        checked_surface_report({},[ordinary])
        checked_surface_report(dict(surfaceProfiles=[],surfaceSamplingMethod=SURFACE_METHOD),[ordinary])
        with self.assertRaises(ValueError):checked_surface_report(dict(surfaceProfiles=[PROFILE]),[ordinary])

    def test_source_hash_ordinals_height_seams_and_coverage(self):
        source,plan,meshes=source_fixture()
        checked_surface_bindings(source,plan,meshes)
        for change in (lambda s:s['surfaceBindings'][0].update(profilePayload=s['surfaceBindings'][0]['profilePayload']+' '),
                lambda s:s['surfaceBindings'][0].update(sourceMeshSha256='b'*64),
                lambda s:s['surfaceBindings'][0].update(topTriangleIndices=[0,1,2]),
                lambda s:s['surfaceBindings'][0].update(topTriangleIndices=[0,1,2,2]),
                lambda s:s['surfaceBindings'][0].update(topTriangleIndices=[0,1,2,True]),lambda s:s.update(surfaceBindings=[])):
            bad=copy.deepcopy(source);change(bad)
            with self.assertRaises(ValueError):checked_surface_bindings(bad,plan,meshes)
        bad=copy.deepcopy(meshes);bad['stairs_and_balconies']['positions'][0][2]=1
        with self.assertRaisesRegex(ValueError,r'h\(worldX\)'):checked_surface_bindings(source,plan,bad)
        crossing=copy.deepcopy(meshes);crossing['stairs_and_balconies']['indices']=[0,5,6]
        bound=copy.deepcopy(source);bound['surfaceBindings'][0]['topTriangleIndices']=[0]
        with self.assertRaisesRegex(ValueError,'knot seam'):checked_surface_bindings(bound,plan,crossing)

    def test_publisher_native_profile_witnesses_and_physics_thresholds(self):
        routes=[PROOF,dict(PROOF,id='west_approach:reverse',points=list(reversed(PROOF['points'])))]
        report=width_evidence(routes)
        publisher.route_width_proof(report,routes)
        for change in (lambda e:e['routeWidthConfig'].pop('surfaceProfiles'),
                lambda e:e['routeWidthConfig'].update(surfaceSamplingMethod='centerline'),
                lambda e:e['routeWidthConfig']['surfaceProfiles'][0]['surfaceProfile'].update(schemaVersion=True),
                lambda e:e['routeWidthSamples'][0]['seed'].__setitem__(2,300),
                lambda e:e['routeWidthConfig'].update(maxFloorDeviationCm=300),
                lambda e:e['routeWidthConfig'].update(maxStepHeightCm=46),
                lambda e:e['routeWidthConfig'].update(capsuleRadiusCm=20)):
            bad=copy.deepcopy(report);change(bad)
            with self.assertRaises(ValueError):publisher.route_width_proof(bad,routes)
        bad=copy.deepcopy(report);row=bad['routeWidthSamples'][0]
        row['floorZCm']+=120.01;row['floorImpact'][2]=row['floorZCm'];row['center'][2]+=120.01
        with self.assertRaises(ValueError):publisher.route_width_proof(bad,routes)


if __name__=='__main__':unittest.main()
