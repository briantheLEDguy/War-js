"""Reject incomplete or unbound native ground evidence before authoring supports."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from citadel_wing_support_evidence import survey_points,checked_ground_summary


def fixture(version=2):
    revision='0123456789ab'
    map='/Game/WorldRebuild/AegisCitadel_'+revision+'/ReviewCandidate'
    package='/Game/WorldRebuild/AegisCitadel_'+revision+'/Layers/RetainedCity_0'
    actor=package+'.RetainedCity_0:PersistentLevel.Terrain'
    rows=[]
    for (x,y),regions in survey_points(version).items():
        z=1055 if y<0 else 3000
        rows.append(dict(xCm=x,yCm=y,regions=regions,groundFound=True,
            pointCm=[x,y,z],normal=[0,0,1],actor=actor,component=actor+'.Mesh',
            gapBelowCurrentEditFloorCm=max(0,2400-z)))
    return dict(schemaVersion=1,samplingVersion=version,revision=revision,signature=revision+'0'*52,
        map=map,mapSha256='a'*64,packageHashes={map:'a'*64,package:'b'*64},
        sourceAndCandidateHashesUnchanged=True,diagnosticOnly=True,groundContactApproved=False,
        samples=rows,groundActors=[dict(actor=actor,package=package)])


class WingGroundEvidenceTests(unittest.TestCase):
    def test_complete_native_grid_reports_the_unsupported_depth_without_approval(self):
        summary=checked_ground_summary(fixture())
        self.assertEqual(summary['samples'],144)
        self.assertEqual(summary['maximumGapBelowCurrentEditFloorCm'],1345)
        self.assertEqual(summary['samplesBelowCurrentEditFloor'],72)
        self.assertFalse(summary['continuousGroundContactProven'])
        self.assertFalse(summary['nativeFoundationApproved'])
        self.assertTrue(any(abs(y)>9530 for x,y in survey_points()))

    def test_prior_sampling_version_retains_its_recorded_two_tower_scope(self):
        report=fixture(1)
        report.pop('samplingVersion')
        self.assertEqual(checked_ground_summary(report)['samples'],126)

    def test_missing_duplicate_and_displaced_samples_are_rejected(self):
        for change in ('missing','duplicate','displaced','no_hit','wrong_normal','gap'):
            report=fixture()
            if change=='missing':report['samples'].pop()
            if change=='duplicate':report['samples'].append(copy.deepcopy(report['samples'][0]))
            if change=='displaced':report['samples'][0]['pointCm'][0]+=1
            if change=='no_hit':report['samples'][0]['groundFound']=False
            if change=='wrong_normal':report['samples'][0]['normal']=[0,0,0]
            if change=='gap':report['samples'][0]['gapBelowCurrentEditFloorCm']=0
            with self.subTest(change=change),self.assertRaises(ValueError):
                checked_ground_summary(report)

    def test_changed_sources_and_unbound_ground_actor_packages_are_rejected(self):
        for change in ('revision','sources','map_hash','actor','package','approval'):
            report=fixture()
            if change=='revision':report['revision']='111111111111'
            if change=='sources':report['sourceAndCandidateHashesUnchanged']=False
            if change=='map_hash':report['mapSha256']='c'*64
            if change=='actor':report['samples'][0]['actor']='another-actor'
            if change=='package':report['groundActors'][0]['package']='/Game/Unbound'
            if change=='approval':report['groundContactApproved']=True
            with self.subTest(change=change),self.assertRaises(ValueError):
                checked_ground_summary(report)


if __name__=='__main__':
    unittest.main()
