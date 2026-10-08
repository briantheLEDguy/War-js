import copy
import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_review import arrival_point, review_map, launch_arguments


class ReviewTests(unittest.TestCase):
    def receipt(self):
        signature = 'abcdef123456'+'0'*52
        package = review_map(signature,'sunmeadow_march')
        return dict(schemaVersion=1,signature=signature,sourcePackagesUnchanged=True,requiresDevelopmentGM=True,
                    published=False,packageHashes={package:'a'*64},zones=[dict(id='sunmeadow_march',map=package,
                    nativeArrivalClear=True,parentContentUnchanged=True)])

    def test_authored_arrival_conversion(self):
        self.assertEqual(arrival_point(dict(id='sunmeadow_march',spawnPoint=dict(x=-585,y=5,z=-280))),[-28000,-58500,500])
        for n in (math.nan,math.inf,4000):
            with self.assertRaises(ValueError): arrival_point(dict(id='sunmeadow_march',spawnPoint=dict(x=n,y=5,z=-280)))

    def test_selected_map_and_gm_flag(self):
        r = self.receipt(); args = launch_arguments('project.uproject',r,'sunmeadow_march')
        self.assertIn('-WarDevelopmentGM',args)
        self.assertIn('-game',args)
        self.assertEqual([a for a in args if a.startswith('-ini:')],
                         ['-ini:Engine:[/Script/EngineSettings.GameMapsSettings]:GameDefaultMap='+r['zones'][0]['map']])
        self.assertFalse(any('Proof' in a for a in args))

    def test_no_unverified_or_shared_launch(self):
        r = self.receipt()
        for key in ('sourcePackagesUnchanged','requiresDevelopmentGM'):
            bad = copy.deepcopy(r); bad[key]=False
            with self.assertRaises(ValueError): launch_arguments('p',bad,'sunmeadow_march')
        for key in ('nativeArrivalClear','parentContentUnchanged'):
            bad = copy.deepcopy(r); bad['zones'][0][key]=False
            with self.assertRaises(ValueError): launch_arguments('p',bad,'sunmeadow_march')
        bad = copy.deepcopy(r); bad['zones'][0]['map']='/Game/Capitals/aegis_capital/AegisCapital_Workbench'
        with self.assertRaises(ValueError): launch_arguments('p',bad,'sunmeadow_march')
        bad = copy.deepcopy(r); bad['zones']*=2
        with self.assertRaises(ValueError): launch_arguments('p',bad,'sunmeadow_march')

    def test_region_and_revision_isolation(self):
        self.assertNotEqual(review_map('a'*64,'sunmeadow_march'),review_map('a'*64,'cinderfen_outskirts'))
        for sig,zone in [('A'*64,'sunmeadow_march'),('a'*12,'sunmeadow_march'),('a'*64,'brightfen_approach')]:
            with self.assertRaises(ValueError): review_map(sig,zone)


if __name__=='__main__': unittest.main()
