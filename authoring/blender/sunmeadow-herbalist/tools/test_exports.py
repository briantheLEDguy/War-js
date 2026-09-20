"""Current-byte gates for all three herbalist exports and nine runtime clips."""
import hashlib,json,unittest
from pathlib import Path
WORK=Path(__file__).resolve().parents[1];KEY='frontier_sunmeadow_empire_herbalist'
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()

class HerbalistExports(unittest.TestCase):
    def test_tucked_layers_stay_inside_belt(self):
        for lod in range(3):
            report=json.loads((WORK/'review'/f'{KEY}_lod{lod}_belt_clearance.json').read_text())
            self.assertEqual(report['sha256'],sha(WORK/'runtime'/report['model']));self.assertEqual(len(report['clips']),9)
            for clip in report['clips']:
                self.assertGreater(len(clip['samples']),30)
                for sample in clip['samples']:
                    self.assertEqual(sample['edgeCrossings'],0,f'{lod}/{clip["clip"]}/{sample["seconds"]}')
                    self.assertGreater(sample['probeVertices'],100)
                    self.assertGreaterEqual(sample['minimumInnerClearanceMetres'],0,f'{lod}/{clip["clip"]}/{sample["seconds"]}')

    def test_equipment_has_continuous_supported_load_paths(self):
        for lod in range(3):
            report=json.loads((WORK/'review'/f'{KEY}_lod{lod}_equipment_attachment.json').read_text())
            self.assertEqual(report['sha256'],sha(WORK/'runtime'/report['model']))
            self.assertEqual(report['suspensionLoops'],4);self.assertEqual(report['loopNonManifoldEdges'],0)
            self.assertEqual(report['contactPairs'],15);self.assertGreaterEqual(report['minimumAssemblyHipsWeight'],.9999)
            self.assertLessEqual(report['maximumPoseRigidResidualMetres'],.00001);self.assertEqual(len(report['clips']),9)
            for clip in report['clips']:
                self.assertGreater(len(clip['samples']),30)
                for sample in clip['samples']:
                    self.assertLessEqual(sample['maximumRigidResidualMetres'],.00001)
                    for name,contact in sample['contacts'].items():self.assertTrue(contact['supported'],f'{lod}/{clip["clip"]}/{name}')

    def test_master_continuity(self):
        report=json.loads((WORK/'review/master-continuity.json').read_text())
        self.assertEqual(report['masterSha256'],sha(WORK/'sources'/f'{KEY}.blend'))
        self.assertEqual(len(report['shirtConnectedComponents']),1)
        self.assertEqual(report['shirtBoundaryLoops'],4)
        self.assertTrue(report['shirtBoundaryValenceValid'])
        self.assertEqual(report['splitHemPanels'],4)
        self.assertGreaterEqual(report['packedImages'],15)

    def test_divided_smock_and_carried_tools_clear_body(self):
        for lod in range(3):
            for kind in ('garment_clearance','tool_clearance'):
                report=json.loads((WORK/'review'/f'{KEY}_lod{lod}_{kind}.json').read_text())
                self.assertEqual(report['sha256'],sha(WORK/'runtime'/report['model']))
                self.assertEqual(len(report['clips']),9)
                self.assertGreater(report['probeVertices'],100);self.assertEqual(report.get('sampleStride',1),1)
                for clip in report['clips']:
                    self.assertGreater(len(clip['samples']),30)
                    for sample in clip['samples']:
                        self.assertEqual(sample['edgeCrossings'],0,f'{lod}/{kind}/{clip["clip"]}/{sample["seconds"]}')
                        self.assertGreaterEqual(sample['minimumSignedGap'],-.002,f'{lod}/{kind}/{clip["clip"]}/{sample["seconds"]}')

    def test_three_valid_current_exports_and_sources(self):
        build=json.loads((WORK/'review'/f'{KEY}_build.json').read_text())
        validation=json.loads((WORK/'review/draft-validation.json').read_text())
        self.assertTrue(validation['passed']);self.assertEqual(len(build['lods']),3)
        for row in build['lods']:
            self.assertEqual(sha(WORK/'runtime'/row['model']),row['sha256'])
            self.assertEqual(set(row['clips']),{'idle','walk','run','combat_idle','attack_melee','attack_ranged','cast','death','jump'})
            result=next(r for r in validation['records'] if r['model']==row['model'])
            self.assertEqual(result['errors'],0);self.assertEqual(result['warnings'],0)
        for source in build['sourceFiles']:
            self.assertEqual(sha(WORK.parents[2]/source['path']),source['sha256'],source['path'])

    def test_forearms_are_closed_full_volume(self):
        for lod in range(3):
            report=json.loads((WORK/'review'/f'arm-volume-lod{lod}.json').read_text())
            self.assertEqual(report['sourceSha256'],sha(WORK/'runtime'/f'{KEY}_lod{lod}.glb'))
            self.assertGreaterEqual(report['sampleCount'],200)
            self.assertGreaterEqual(report['minimumAreaRatio'],.8);self.assertLessEqual(report['maximumAreaRatio'],1.2)
            self.assertLessEqual(report['largestAngularGapDegrees'],75)
            self.assertGreaterEqual(report['femaleFoundation']['minimumReferenceSpanRatio'],.9)
            self.assertLessEqual(report['femaleFoundation']['maximumReferenceSpanRatio'],1.1)

    def test_nine_clips_ground_contact_and_material_deformation(self):
        for lod in range(3):
            report=json.loads((WORK/'review'/f'{KEY}_lod{lod}_motion.json').read_text())
            self.assertEqual(report['sha256'],sha(WORK/'runtime'/report['model']));self.assertEqual(len(report['clips']),9)
            for clip in report['clips']:
                self.assertGreater(len(clip['samples']),30)
                self.assertGreaterEqual(clip['minimumHeight'],-.004,clip['clip'])
                for sample in clip['samples']:
                    for material,row in sample['materials'].items():
                        self.assertLess(row['p99'],2.2,f'{lod}/{clip["clip"]}/{material}')
                        self.assertLess(row['maximumEdgeExtensionMetres'],.06,f'{lod}/{clip["clip"]}/{material}')
                    if clip['clip'] in ('idle','combat_idle','attack_melee','attack_ranged','cast'):
                        for side,height in sample['soleHeights'].items():self.assertLessEqual(height,.012,f'{clip["clip"]}/{side}')
                    if clip['clip']=='death' and sample['seconds']>clip['samples'][-1]['seconds']-.1:
                        for side,height in sample['handHeights'].items():self.assertLessEqual(height,.012,f'death/{side}')
                        for side,height in sample['soleHeights'].items():self.assertLessEqual(height,.012,f'death/{side} sole')
                        self.assertLessEqual(sample['torsoSupportHeight'],.012,'death torso support')

    def test_trousers_remain_tucked(self):
        for lod in range(3):
            report=json.loads((WORK/'review'/f'{KEY}_lod{lod}_boot_clearance.json').read_text())
            self.assertEqual(report['sha256'],sha(WORK/'runtime'/report['model']));self.assertEqual(len(report['clips']),9)
            for clip in report['clips']:
                for sample in clip['samples']:
                    for side,row in sample['sides'].items():
                        self.assertGreater(row['rays'],report['probeVertices'][side]*.60)
                        self.assertEqual(row['penetrations'],0,f'{lod}/{clip["clip"]}/{side}')
                        self.assertEqual(row['intersections'],0,f'{lod}/{clip["clip"]}/{side} hem crossing')

    def test_closed_welts_and_identical_lod_motion(self):
        fingerprints=None
        for lod in range(3):
            report=json.loads((WORK/'review'/f'{KEY}_lod{lod}_welt.json').read_text())
            self.assertEqual(report['sha256'],sha(WORK/'runtime'/report['model']))
            self.assertEqual(report['components'],2);self.assertEqual(report['nonManifoldEdges'],0)
            self.assertLessEqual(report['maximumRestDistance'],.0035)
            if fingerprints is None:fingerprints=report['animationChannelSha256']
            self.assertEqual(report['animationChannelSha256'],fingerprints)
            for clip in report['clips']:
                for sample in clip['samples']:self.assertLessEqual(sample['maximumPoseDistance'],.0035)

if __name__=='__main__':unittest.main()
