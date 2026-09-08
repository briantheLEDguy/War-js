"""Regression gates over current binary exports and exact-pose audit evidence."""
import hashlib
import json
import unittest
from pathlib import Path

WORK=Path(__file__).resolve().parents[1]
KEY='frontier_sunmeadow_dwarf_artisan'
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()


class InhabitantExportTests(unittest.TestCase):
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

    def test_exposed_sections_are_complete_and_retain_volume(self):
        for lod in range(3):
            report=json.loads((WORK/'review'/f'arm-volume-lod{lod}.json').read_text())
            self.assertEqual(report['sourceSha256'],sha(WORK/'runtime'/f'{KEY}_lod{lod}.glb'))
            self.assertGreaterEqual(report['sampleCount'],200)
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
                for sample in clip['samples']:
                    if clip['clip'] in ('idle','combat_idle','attack_melee','attack_ranged','cast'):
                        self.assertLessEqual(sample['minimumHeight'],.012,clip['clip'])
                        for side,height in sample['soleHeights'].items():
                            self.assertGreaterEqual(height,-.004,f'{clip["clip"]}/{side} sole')
                            self.assertLessEqual(height,.012,f'{clip["clip"]}/{side} sole')
                    for material,measurement in sample['materials'].items():
                        self.assertLess(measurement['p99'],2.2,f'{clip["clip"]}/{material}')
                        self.assertLess(measurement['maximumEdgeExtensionMetres'],.06,f'{clip["clip"]}/{material}')

    def test_actual_apron_clears_raised_knees(self):
        for lod in range(3):
            report=json.loads((WORK/'review'/f'{KEY}_lod{lod}_garment_clearance.json').read_text())
            self.assertEqual(report['sha256'],sha(WORK/'runtime'/report['model']))
            self.assertGreater(report['probeVertices'],100)
            self.assertEqual({clip['clip'] for clip in report['clips']},{'walk','run','jump'})
            for clip in report['clips']:
                self.assertGreater(len(clip['samples']),30)
                self.assertLessEqual(clip['maximumPenetration'],.002,clip['clip'])


if __name__=='__main__':unittest.main()
