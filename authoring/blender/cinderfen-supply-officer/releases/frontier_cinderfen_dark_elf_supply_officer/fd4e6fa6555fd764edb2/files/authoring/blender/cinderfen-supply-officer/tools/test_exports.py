"""Regression gates over current binary exports and exact-pose audit evidence."""
import hashlib
import json
import unittest
from pathlib import Path

WORK=Path(__file__).resolve().parents[1]
KEY='frontier_cinderfen_dark_elf_supply_officer'
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()


class InhabitantExportTests(unittest.TestCase):
    def test_suspension_has_real_load_bearing_contact_at_both_ends(self):
        for lod in range(3):
            report=json.loads((WORK/'review'/f'{KEY}_lod{lod}_equipment_attachment.json').read_text())
            self.assertEqual(report['sha256'],sha(WORK/'runtime'/report['model']))
            self.assertEqual(report['masterSha256'],sha(WORK/'sources'/f'{KEY}.blend'))
            self.assertEqual(len(report['clips']),9)
            groups=[report['sourceAttachments'],report['restAttachments']]
            for clip in report['clips']:
                self.assertGreater(len(clip['samples']),30)
                groups.extend(sample['attachments'] for sample in clip['samples'])
            for group in groups:
                self.assertEqual({(r['strap'],r['endpoint']) for r in group},{(s,e) for s in (0,1) for e in ('belt','case')})
                self.assertEqual(len(group),4)
                for row in group:
                    self.assertGreaterEqual(row['probeVertices'],3)
                    self.assertLessEqual(row['maximumGap'],.003)
                    self.assertLessEqual(row['minimumGap'],.0015)
                    self.assertGreaterEqual(row['contactCoverage'],.80)
                    self.assertGreaterEqual(row['minimumSignedDistance'],-.0015)
                    self.assertGreaterEqual(row['contactArea'],.00009)

    def test_editable_outfit_is_continuous_closed_weighted_and_current(self):
        build=json.loads((WORK/'review'/f'{KEY}_build.json').read_text())
        report=json.loads((WORK/'review/master-continuity.json').read_text())
        self.assertEqual(report['masterSha256'],build['masterSha256'])
        self.assertEqual(report['masterSha256'],sha(WORK/'sources'/f'{KEY}.blend'))
        self.assertEqual(report['skeletonId'],'cinderfen_supply_officer_humanoid_v1')
        self.assertEqual(report['bindPoseId'],'cinderfen_supply_officer_a_v1')
        self.assertLessEqual(report['hairAttachmentGap'],.0035)
        self.assertEqual(len(report['objects']),11)
        for row in report['objects']:
            self.assertEqual(len(row['components']),1,row['object'])
            self.assertEqual(row['nonManifoldEdges'],0,row['object'])
            self.assertEqual(row['unweightedVertices'],0,row['object'])
            self.assertGreater(row['uvLayers'],0,row['object'])
        for source in build['sourceFiles']:
            self.assertEqual(sha(WORK.parents[2]/source['path']),source['sha256'],source['path'])

    def test_ledger_and_tools_clear_all_animated_clothing(self):
        for lod in range(3):
            report=json.loads((WORK/'review'/f'{KEY}_lod{lod}_tool_clearance.json').read_text())
            self.assertEqual(report['sha256'],sha(WORK/'runtime'/report['model']))
            self.assertEqual(len(report['clips']),9)
            self.assertGreater(report['toolTriangles'],100)
            for clip in report['clips']:
                self.assertGreater(len(clip['samples']),30)
                self.assertEqual(clip['maximumCrossings'],0,clip['clip'])

    def test_three_current_valid_lods_keep_nine_clip_contract(self):
        report=json.loads((WORK/'review/draft-validation.json').read_text())
        build=json.loads((WORK/'review'/f'{KEY}_build.json').read_text())
        self.assertEqual([row['level'] for row in build['lods']],[0,1,2])
        for row in build['lods']:
            path=WORK/'runtime'/row['model'];digest=sha(path)
            self.assertEqual(row['sha256'],digest)
            validation=next(item for item in report['records'] if item['model']==row['model'])
            self.assertEqual(validation['sha256'],digest);self.assertEqual(validation['errors'],0)
            self.assertEqual(set(row['clips']),{'idle','walk','run','combat_idle','attack_melee','attack_ranged','cast','death','jump'})

    def test_each_audit_measures_the_expected_imported_mesh(self):
        build=json.loads((WORK/'review'/f'{KEY}_build.json').read_text())
        for row in build['lods']:
            lod=row['level']
            for filename in (f'arm-volume-lod{lod}.json',f'{KEY}_lod{lod}_motion.json',f'{KEY}_lod{lod}_garment_clearance.json',f'{KEY}_lod{lod}_welt.json',f'{KEY}_lod{lod}_equipment_attachment.json'):
                report=json.loads((WORK/'review'/filename).read_text())
                self.assertEqual(report['importedTriangles'],row['triangles'],filename)

    def test_closed_welts_follow_actual_animated_soles(self):
        for lod in range(3):
            report=json.loads((WORK/'review'/f'{KEY}_lod{lod}_welt.json').read_text())
            self.assertEqual(report['sha256'],sha(WORK/'runtime'/report['model']))
            self.assertEqual(report['components'],2);self.assertEqual(report['nonManifoldEdges'],0)
            self.assertLessEqual(report['maximumRestDistance'],.0035)
            self.assertEqual(len(report['animationChannelSha256']),9)
            self.assertEqual(len(report['clips']),9)
            for clip in report['clips']:
                self.assertGreater(len(clip['samples']),30)
                self.assertLessEqual(max(sample['maximumPoseDistance'] for sample in clip['samples']),.0035)

    def test_exposed_sections_are_complete_and_retain_volume(self):
        for lod in range(3):
            report=json.loads((WORK/'review'/f'arm-volume-lod{lod}.json').read_text())
            self.assertEqual(report['sourceSha256'],sha(WORK/'runtime'/f'{KEY}_lod{lod}.glb'))
            self.assertGreaterEqual(report['sampleCount'],200)
            self.assertEqual(report['foundationReportSha256'],sha(WORK/'review/female-arm-foundation.json'))
            self.assertGreaterEqual(report['minimumFoundationSpanRatio'],.90)
            self.assertLessEqual(report['maximumFoundationSpanRatio'],1.10)
            self.assertGreaterEqual(report['minimumAreaRatio'],.80)
            self.assertLessEqual(report['maximumAreaRatio'],1.20)
            self.assertLess(report['largestAngularGapDegrees'],75)

    def test_every_clip_has_current_contact_and_deformation_evidence(self):
        for lod in range(3):
            report=json.loads((WORK/'review'/f'{KEY}_lod{lod}_motion.json').read_text())
            self.assertEqual(report['sha256'],sha(WORK/'runtime'/report['model']))
            self.assertEqual(len(report['clips']),9)
            for clip in report['clips']:
                self.assertGreater(len(clip['samples']),30)
                self.assertGreaterEqual(clip['minimumHeight'],-.004,clip['clip'])
                if clip['clip'] in ('walk','run'):
                    for side in ('L','R'):
                        self.assertLessEqual(min(sample['soleHeights'][side] for sample in clip['samples']),.012,
                                             f'{clip["clip"]}/{side} must have a grounded contact phase')
                for sample in clip['samples']:
                    if clip['clip']=='death' and sample['seconds']>clip['samples'][-1]['seconds']-.10:
                        for side,height in sample['handHeights'].items():
                            self.assertGreaterEqual(height,-.004,f'death/{side} hand')
                            self.assertLessEqual(height,.012,f'death/{side} hand must settle onto ground')
                    if clip['clip'] in ('idle','combat_idle','attack_melee','attack_ranged','cast'):
                        self.assertLessEqual(sample['minimumHeight'],.012,clip['clip'])
                        for side,height in sample['soleHeights'].items():
                            self.assertGreaterEqual(height,-.004,f'{clip["clip"]}/{side} sole')
                            self.assertLessEqual(height,.012,f'{clip["clip"]}/{side} sole')
                    for material,measurement in sample['materials'].items():
                        self.assertLess(measurement['p99'],2.2,f'{clip["clip"]}/{material}')
                        self.assertLess(measurement['maximumEdgeExtensionMetres'],.06,f'{clip["clip"]}/{material}')

    def test_actual_coat_clears_raised_knees(self):
        for lod in range(3):
            report=json.loads((WORK/'review'/f'{KEY}_lod{lod}_garment_clearance.json').read_text())
            self.assertEqual(report['sha256'],sha(WORK/'runtime'/report['model']))
            self.assertGreater(report['probeVertices'],100)
            self.assertEqual({clip['clip'] for clip in report['clips']},{'walk','run','jump'})
            for clip in report['clips']:
                self.assertGreater(len(clip['samples']),30)
                self.assertLessEqual(clip['maximumPenetration'],.002,clip['clip'])

    def test_trouser_hems_remain_inside_boot_cuffs(self):
        for lod in range(3):
            report=json.loads((WORK/'review'/f'{KEY}_lod{lod}_garment_clearance.json').read_text())
            self.assertEqual(report['sha256'],sha(WORK/'runtime'/report['model']))
            self.assertEqual(len(report['bootClips']),9)
            for clip in report['bootClips']:
                self.assertLessEqual(clip['maximumPenetration'],.002,clip['clip'])
                for sample in clip['samples']:
                    for side,measurement in sample['sides'].items():
                        self.assertGreater(measurement['raysIntersectingBoot'],report['bootHemProbeVertices'][side]*.60,
                                           f'{clip["clip"]}/{side} boot coverage')

    def test_run_has_bent_alternating_arms(self):
        for lod in range(3):
            report=json.loads((WORK/'review'/f'{KEY}_lod{lod}_motion.json').read_text())
            clip=next(clip for clip in report['clips'] if clip['clip']=='run')
            for side in ('L','R'):
                poses=[sample['arms'][side] for sample in clip['samples']]
                self.assertGreater(min(pose['elbowFlexDegrees'] for pose in poses),25)
                forward=[pose['wristFromShoulder'][1] for pose in poses]
                self.assertGreater(max(forward)-min(forward),.30)
            alternating=[sample['arms']['L']['wristFromShoulder'][1]-sample['arms']['R']['wristFromShoulder'][1]
                         for sample in clip['samples']]
            self.assertGreater(max(alternating),.30)
            self.assertLess(min(alternating),-.30)

    def test_joined_coat_tails_clear_trousers_in_all_clips(self):
        for lod in range(3):
            report=json.loads((WORK/'review'/f'{KEY}_lod{lod}_garment_clearance.json').read_text())
            self.assertEqual(report['sha256'],sha(WORK/'runtime'/report['model']))
            self.assertGreater(report['coatTailEdges'],100)
            self.assertEqual(len(report['coatTailClips']),9)
            for clip in report['coatTailClips']:
                self.assertGreater(len(clip['samples']),30)
                self.assertEqual(clip['maximumCrossings'],0,clip['clip'])

    def test_belt_never_crosses_the_coat(self):
        for lod in range(3):
            report=json.loads((WORK/'review'/f'{KEY}_lod{lod}_garment_clearance.json').read_text())
            self.assertEqual(report['sha256'],sha(WORK/'runtime'/report['model']))
            self.assertGreater(report['beltEdges'],100)
            self.assertEqual(len(report['beltClips']),9)
            for clip in report['beltClips']:
                self.assertGreater(len(clip['samples']),30)
                self.assertEqual(clip['maximumIntersections'],0,clip['clip'])


if __name__=='__main__':unittest.main()
