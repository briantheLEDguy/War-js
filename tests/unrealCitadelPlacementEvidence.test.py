import copy
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/unreal'))
from citadel_placement_evidence import validate_route_placement_overlaps as validate


def evidence():
    # Synthetic validation control; this receipt never grants native admission.
    triangle = dict(internalTriangle=0, finite=True, certificateVersion=1,
        guardPolicyVersion=1, projectionAxisRecorded=True, fullCapsuleSeparationCertified=True,
        worldVertices=[[-100, -100, 0], [100, -100, 0], [0, 100, 0]],
        separatingUnitAxis=[0, 0, 1], projectionOriginCm=[0, 0, 98.4],
        separatingAxisSquaredLength=1, capsuleProjectionCm=[-96, 96],
        triangleProjectionCm=[-98.4, -98.4], numericalGuardCm=.01,
        separatingPlaneGapCm=2.4, gapTriangleAfterCapsuleCm=-194.4,
        gapCapsuleAfterTriangleCm=2.4, projectionGapDirection='capsule_above_triangle')
    shape = dict(shapeIndex=0, selected=True, boundToQueriedBody=True, queryShape=True,
        rigidUnitSeparationPolicySupported=True, collisionMarginCm=0,
        affineQueryBoundsVerified=True, triangleWitnessComplete=True, truncated=False,
        finiteTriangles=True, candidateTriangleCount=1, liveCookedTriangleCount=1,
        triangles=[triangle])
    witness = dict(schemaVersion=2, source='live_physics_shape_geometry_under_execute_read',
        readLockEntered=True, complete=True, staticSingleBodyPolicySupported=True,
        sameReadLockMtdBlocking=False, separatedContactDiagnostic=True, admissionGranted=False,
        capsuleAxisStart=[0, 0, 44.4], capsuleAxisEnd=[0, 0, 152.4], capsuleRadiusCm=42,
        liveShapeCount=1, selectedShapeCount=1, shapes=[shape])
    resolution = dict(diagnosticOnly=True, admissionGranted=False, capsuleInputValid=True,
        rawBlockingHitCount=1, uniqueBlockingBodyCount=1, resolvedSeparatedBodyCount=1,
        blockedBodyCount=0, unresolvedBodyCount=0, inconsistentDuplicateCount=0,
        proposalDecision='all_raw_contacts_proven_separated',
        perBodyDecisions=[dict(originalBodyBindingVerified=True, decision='separated', liveWitness=witness)])
    return dict(queries=2, rawClear=1, separated=1, blocked=0, unresolved=0, rawBlockingHits=1,
        lastDisposition='raw_clear', contacts=[dict(query=dict(center=[0, 0, 98.4],
        quaternion=[0, 0, 0, 1], radiusCm=42, halfHeightCm=96, role='floor_adjusted'), resolution=resolution)])


class PlacementEvidenceTests(unittest.TestCase):
    def test_full_capsule_and_complete_body_are_audited(self):
        validate(evidence(), None, 42, 96)
        changes = [('contacts', []), ('rawBlockingHits', 0), ('lastDisposition', 'unresolved'), ('queries', True)]
        for key, value in changes:
            changed = evidence(); changed[key] = value
            with self.assertRaises(ValueError, msg=key): validate(changed, None, 42, 96)

    def test_mtd_unknown_binding_and_missing_bodies_cannot_be_hidden(self):
        changes = [lambda r: r.update(inconsistentDuplicateCount=1),
            lambda r: r.update(unresolvedBodyCount=1), lambda r: r.update(perBodyDecisions=[]),
            lambda r: r['perBodyDecisions'][0].update(originalBodyBindingVerified=False),
            lambda r: r['perBodyDecisions'][0]['liveWitness'].update(sameReadLockMtdBlocking=True)]
        for change in changes:
            changed = evidence(); change(changed['contacts'][0]['resolution'])
            with self.assertRaises(ValueError): validate(changed, None, 42, 96)

    def test_complete_selected_shapes_have_strict_counts_and_flags(self):
        for key, value in [('selected', 1), ('collisionMarginCm', False), ('collisionMarginCm', .1),
                ('truncated', True), ('candidateTriangleCount', True), ('liveCookedTriangleCount', 0),
                ('liveCookedTriangleCount', None), ('liveCookedTriangleCount', math.nan),
                ('liveCookedTriangleCount', math.inf), ('liveCookedTriangleCount', .5), ('shapeIndex', 1),
                ('triangleWitnessComplete', False)]:
            changed = evidence(); changed['contacts'][0]['resolution']['perBodyDecisions'][0]['liveWitness']['shapes'][0][key] = value
            with self.assertRaises(ValueError, msg=key): validate(changed, None, 42, 96)

    def test_projection_tampering_and_degenerate_faces_fail(self):
        for key, value in [('numericalGuardCm', 0), ('separatingPlaneGapCm', math.nan),
                ('capsuleProjectionCm', [-54, 54]), ('worldVertices', [[0, 0, 0]] * 3),
                ('worldVertices', [[-100, -100, 0], [100, -100, 0], [0, 0, 30]])]:
            changed = evidence(); changed['contacts'][0]['resolution']['perBodyDecisions'][0]['liveWitness']['shapes'][0]['triangles'][0][key] = value
            with self.assertRaises(ValueError, msg=key): validate(changed, None, 42, 96)

    def test_exact_pose_dimensions_and_all_triangle_identities_are_bound(self):
        changed = evidence(); changed['contacts'][0]['query']['radiusCm'] = 43
        with self.assertRaises(ValueError): validate(changed, None, 42, 96)
        changed = evidence(); changed['contacts'][0]['query']['center'][0] = 1
        with self.assertRaises(ValueError): validate(changed, None, 42, 96)
        changed = evidence(); shape = changed['contacts'][0]['resolution']['perBodyDecisions'][0]['liveWitness']['shapes'][0]
        shape['triangles'].append(copy.deepcopy(shape['triangles'][0])); shape['candidateTriangleCount'] = 2; shape['liveCookedTriangleCount'] = 2
        with self.assertRaises(ValueError): validate(changed, None, 42, 96)

    def test_rejected_seed_never_overrides_final_floor_or_movement_pose(self):
        for disposition in ('blocked', 'unresolved'):
            changed = evidence(); changed['separated'] = 0; changed[disposition] = 1
            record = changed['contacts'][0]; record['query']['role'] = 'seed_probe'
            record['resolution'].update(proposalDecision=disposition, resolvedSeparatedBodyCount=0)
            record['resolution'][disposition+'BodyCount'] = 1
            record['resolution']['perBodyDecisions'][0]['decision'] = disposition
            validate(changed, None, 42, 96)
            record['query']['role'] = 'native_movement_pose'
            with self.assertRaises(ValueError): validate(changed, None, 42, 96)
        with self.assertRaises(ValueError): validate(evidence(), 1, 42, 96)
        with self.assertRaises(ValueError): validate(evidence(), -1, 42, 96)

    def test_duplicate_shapes_and_inconsistent_rejected_seed_accounting_fail(self):
        changed = evidence(); w = changed['contacts'][0]['resolution']['perBodyDecisions'][0]['liveWitness']
        w['shapes'].append(copy.deepcopy(w['shapes'][0])); w['liveShapeCount'] = 2; w['selectedShapeCount'] = 2
        with self.assertRaises(ValueError): validate(changed, None, 42, 96)
        changed = evidence(); changed['blocked'] = 1; changed['separated'] = 0
        changed['contacts'][0]['query']['role'] = 'seed_probe'
        changed['contacts'][0]['resolution']['proposalDecision'] = 'blocked'
        with self.assertRaises(ValueError): validate(changed, None, 42, 96)


if __name__ == '__main__':
    unittest.main()
