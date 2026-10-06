import math
import sys
import unittest
import copy
import importlib.util
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from citadel_capsule_distance import capsule_triangle_clearance as clearance,segment_triangle_distance_squared as distance
from citadel_separation_certificate import audit_separating_plane
spec=importlib.util.spec_from_file_location('cooked_contact_analysis',Path(__file__).resolve().parents[1]/'scripts/unreal/analyze-citadel-cooked-contacts.py')
analysis=importlib.util.module_from_spec(spec);spec.loader.exec_module(analysis)


class CookedContactMathTests(unittest.TestCase):
    def test_exported_plane_audit_covers_both_capsule_endpoints_and_all_vertices(self):
        start,end=[0,0,44.4],[0,0,152.4]
        triangle=[[-100,-100,0],[100,-100,0],[0,100,0]]
        certificate=dict(certificateVersion=1,guardPolicyVersion=1,projectionAxisRecorded=True,separatingUnitAxis=[0,0,1],
            projectionOriginCm=[0,0,98.4],separatingAxisSquaredLength=1,
            capsuleProjectionCm=[-96,96],triangleProjectionCm=[-98.4,-98.4],
            separatingPlaneGapCm=2.4,projectionGapDirection='capsule_above_triangle',
            numericalGuardCm=.01,fullCapsuleSeparationCertified=True)
        certificate.update(gapTriangleAfterCapsuleCm=-194.4,gapCapsuleAfterTriangleCm=2.4)
        result=audit_separating_plane(start,end,42,triangle,certificate)
        self.assertTrue(result['independentProjectionAuditPassed'])
        self.assertTrue(result['fullCapsuleSeparated']);self.assertFalse(result['admissionGranted'])
        for field,value in (('certificateVersion',0),('certificateVersion',True),('guardPolicyVersion',2),('gapTriangleAfterCapsuleCm',-200),
                ('projectionAxisRecorded',False),('separatingUnitAxis',[0,0,.99]),
                ('projectionOriginCm',[0,0,97]),('capsuleProjectionCm',[-54,54]),
                ('triangleProjectionCm',[-98.4,-100]),('separatingPlaneGapCm',3),
                ('projectionGapDirection','triangle_above_capsule'),('numericalGuardCm',.0001),
                ('fullCapsuleSeparationCertified',False),('separatingAxisSquaredLength',math.nan)):
            changed=copy.deepcopy(certificate);changed[field]=value
            with self.assertRaises(ValueError,msg=field):audit_separating_plane(start,end,42,triangle,changed)
        # A third triangle vertex intruding into the capsule interval cannot be
        # hidden by exporting extrema from only the first two vertices.
        with self.assertRaises(ValueError):audit_separating_plane(start,end,42,[*triangle[:2],[0,0,30]],certificate)

    def test_exported_plane_audit_preserves_rotation_winding_and_guarded_contact(self):
        start,end=[10,44.4,20],[10,152.4,20]
        triangle=[[-90,0,-80],[110,0,-80],[10,0,120]]
        certificate=dict(certificateVersion=1,guardPolicyVersion=1,projectionAxisRecorded=True,separatingUnitAxis=[0,-1,0],
            projectionOriginCm=[10,98.4,20],separatingAxisSquaredLength=1,
            capsuleProjectionCm=[-96,96],triangleProjectionCm=[98.4,98.4],
            separatingPlaneGapCm=2.4,projectionGapDirection='triangle_above_capsule',
            numericalGuardCm=.01,fullCapsuleSeparationCertified=True)
        certificate.update(gapTriangleAfterCapsuleCm=2.4,gapCapsuleAfterTriangleCm=-194.4)
        for vertices in (triangle,list(reversed(triangle))):
            self.assertTrue(audit_separating_plane(start,end,42,vertices,certificate)['fullCapsuleSeparated'])
        certificate.update(numericalGuardCm=3,fullCapsuleSeparationCertified=False)
        self.assertFalse(audit_separating_plane(start,end,42,triangle,certificate)['fullCapsuleSeparated'])
        with self.assertRaises(ValueError):audit_separating_plane(start,end,42,[triangle[0]]*3,certificate)

    def test_full_capsule_flat_floor_and_positive_wall_controls(self):
        floor=[[-100,-100,0],[100,-100,0],[0,100,0]]
        self.assertAlmostEqual(clearance([0,0,44.4],[0,0,152.4],42,floor),2.4)
        wall=[[20,-100,-100],[20,100,-100],[20,0,200]]
        self.assertAlmostEqual(clearance([0,0,44.4],[0,0,152.4],42,wall),-22)

    def test_sloped_plane_uses_spherical_capsule_support(self):
        slope=.6365;n=math.hypot(1,slope)
        triangle=[[-200,-200,-200*slope],[200,-200,200*slope],[0,200,0]]
        bottom=42*n+2.4
        self.assertAlmostEqual(clearance([0,0,bottom],[0,0,bottom+108],42,triangle),2.4/n,places=9)

    def test_axis_crossing_and_an_interior_edge_minimum_are_retained(self):
        triangle=[[-5,-5,0],[5,-5,0],[0,5,0]]
        self.assertEqual(distance([0,0,-10],[0,0,10],triangle),0)
        # Both axis endpoints are far from the triangle, while its middle is 2 cm away.
        self.assertAlmostEqual(distance([-100,-7,0],[100,-7,0],triangle),4)

    def test_degenerate_triangle_falls_back_to_segments_and_points(self):
        self.assertEqual(distance([-1,2,0],[1,2,0],[[-5,0,0],[5,0,0],[0,0,0]]),4)
        self.assertEqual(distance([0,0,0],[0,0,0],[[3,4,0]]*3),25)

    def test_reversed_winding_and_large_world_translation_preserve_clearance(self):
        triangle=[[-50,-30,0],[80,-30,40],[0,100,10]];start=[3,4,90];end=[3,4,198]
        expected=clearance(start,end,42,triangle)
        self.assertAlmostEqual(clearance(start,end,42,list(reversed(triangle))),expected)
        offset=[12160,-5658,4148.24]
        shift=lambda p:[p[i]+offset[i] for i in range(3)]
        self.assertAlmostEqual(clearance(shift(start),shift(end),42,list(map(shift,triangle))),expected,places=9)
        with self.assertRaises(ValueError):clearance(start,end,41,[[math.nan,0,0]]*3)

    def test_near_parallel_crossing_is_not_reinterpreted_as_separation(self):
        a,b=[-54,-1e-6,0],[54,1e-6,0];triangle=[a,b,a]
        for start,end in (([-54,0,0],[54,0,0]),([54,0,0],[-54,0,0])):
            for vertices in (triangle,list(reversed(triangle)),[b,a,a]):
                self.assertEqual(distance(start,end,vertices),0)

    def test_tangent_vertex_sphere_and_coplanar_controls(self):
        face=[[-100,-100,0],[100,-100,0],[0,100,0]]
        self.assertEqual(clearance([0,0,42],[0,0,150],42,face),0)
        self.assertEqual(distance([-200,0,0],[200,0,0],face),0)
        self.assertEqual(distance([0,0,12],[0,0,12],face),144)
        self.assertEqual(distance([110,-110,0],[110,-110,0],face),200)

    def test_unsupported_magnitudes_and_invalid_dimensions_fail_explicitly(self):
        face=[[0,0,0],[0,1,0],[0,0,1]]
        with self.assertRaises(ValueError):distance([1e200,0,0],[1e200,1,0],face)
        for value in (0,-1,True,math.inf,math.nan,1e200):
            with self.assertRaises(ValueError):clearance([0,0,0],[0,0,1],value,face)
        for value in (None,[True,0,0],[math.inf,0,0],[0,0],[0,0,0,0]):
            with self.assertRaises(ValueError):distance(value,[0,0,1],face)

    def test_portable_witness_math_grants_no_admission_and_rejects_incomplete_native_coverage(self):
        # Artificial metadata tests validation only; it cannot establish a native receipt.
        triangle=dict(internalTriangle=0,externalFace=-1,finite=True,areaCm2=20000,
            worldVertices=[[-100,-100,0],[100,-100,0],[0,100,0]])
        shape=dict(selected=True,shapeIndex=0,boundToQueriedBody=True,queryShape=True,affineQueryBoundsVerified=True,
            triangleWitnessComplete=True,truncated=False,finiteTriangles=True,candidateTriangleCount=1,
            collisionMarginCm=0,liveCookedTriangleCount=1,triangles=[triangle])
        witness=dict(schemaVersion=2,source='live_physics_shape_geometry_under_execute_read',diagnosticOnly=True,complete=True,
            readLockEntered=True,liveShapeCount=1,selectedShapeCount=1,shapes=[shape],
            capsuleAxisStart=[0,0,44.4],capsuleAxisEnd=[0,0,152.4],capsuleRadiusCm=42)
        result=analysis.analyze(witness)
        self.assertAlmostEqual(result['minimumCandidateSurfaceGapCm'],2.4)
        self.assertFalse(result['gapIsGlobalMeshClearance'])
        self.assertFalse(result['admissionGranted']);self.assertFalse(result['gapIsMinimumTranslationDistance'])
        for field,value in (('schemaVersion',1),('complete',False),('readLockEntered',False),('liveShapeCount',2),('selectedShapeCount',0)):
            changed=copy.deepcopy(witness);changed[field]=value
            with self.assertRaises(ValueError):analysis.analyze(changed)
        for field,value in (('affineQueryBoundsVerified',False),('truncated',True),('candidateTriangleCount',2),('collisionMarginCm',1),('queryShape',False)):
            changed=copy.deepcopy(witness);changed['shapes'][0][field]=value
            with self.assertRaises(ValueError):analysis.analyze(changed)
        changed=copy.deepcopy(witness);changed['shapes'][0]['triangles'][0]['areaCm2']=math.nan
        with self.assertRaises(ValueError):analysis.analyze(changed)

    def test_destination_only_contact_is_retained_and_duplicates_are_counted_once(self):
        # Native receipt field names are part of diagnostic coverage.
        overlap=dict(component=dict(path='/test/body'),directBodyQuery=dict(withoutMTD=True,
            withMTD=True,mtdDistanceCm=3,overlapItemIndex=0,instanceBodyIndex=0,cookedTriangleWitness={}))
        contacts=dict(center=[1,2,3],quaternion=[0,0,0,1],radiusCm=42,halfHeightCm=96,admissionQuery=dict(overlaps=[overlap]))
        diagnostic=dict(capsuleContacts=contacts)
        report=dict(routeWidthSamples=[dict(passed=False,id='reverse:destination',
            destinationDiagnostic=diagnostic),dict(passed=False,id='reverse:duplicate',
            failedSubstepDiagnostic=diagnostic,destinationDiagnostic=diagnostic)])
        rows=analysis.analyze_report(report)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['route'],'reverse:destination')
        self.assertEqual(rows[0]['center'],[1,2,3])
        self.assertTrue(rows[0]['withMTD']);self.assertIn('unresolved',rows[0])
        second=copy.deepcopy(overlap);second['directBodyQuery'].update(overlapItemIndex=1,instanceBodyIndex=1)
        contacts['admissionQuery']['overlaps'].append(second)
        rows=analysis.analyze_report(report)
        self.assertEqual(len(rows),2)
        self.assertEqual([row['overlapItemIndex'] for row in rows],[0,1])
        changed=copy.deepcopy(diagnostic);changed['capsuleContacts']['quaternion']=[0,0,1,0]
        report['routeWidthSamples'].append(dict(passed=False,id='rotated',destinationDiagnostic=changed))
        self.assertEqual(len(analysis.analyze_report(report)),4)


if __name__=='__main__':unittest.main()
