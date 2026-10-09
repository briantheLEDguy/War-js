import copy,math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_navigation import navigation_map,route_inventory,validate_probe,probe_profiles,navigation_payload,validate_navigation_parent

class NavigationTest(unittest.TestCase):
    def source(self):
        points=[dict(x=10,z=20),dict(x=30,z=40)]
        return dict(id='sunmeadow_march',paths=[dict(id='road',points=points)],orvrLayout=dict(
            caravanRoutes=[dict(id='supply_'+str(i),points=points) for i in range(6)],
            terrain=dict(clearCorridors=[dict(id=k,points=points) for k in ('road','west_field_counter','sunmeadow_march_scarp_west_climb','village_ground_entry','sunmeadow_march_pocket_brook_approach')])) )
    def test_private_first_pair_map_scope(self):
        self.assertEqual(navigation_map('a'*64,'sunmeadow_march'),'/Game/WorldRebuild/T1Redesign_Atmosphere_aaaaaaaaaaaa_Navigation/sunmeadow_march/Review')
        for signature,zone in [('A'*64,'sunmeadow_march'),('a'*12,'sunmeadow_march'),('a'*64,'brightfen_approach')]:
            with self.assertRaises(ValueError):navigation_map(signature,zone)
    def test_exact_vehicle_routes_and_coordinate_conversion(self):
        routes=route_inventory(self.source(),lambda x,z:x+z)
        self.assertEqual(len(routes),8);self.assertEqual(routes[0]['points'],[[2000,1000,50],[4000,3000,90]])
        self.assertEqual(routes[-1]['id'],'west_field_counter');self.assertEqual(sum(r['kind']=='supply' for r in routes),6)
    def test_narrow_walking_counters_do_not_claim_convoy_access(self):
        s=self.source();s['paths'].append(dict(id='walking_counter',width=4,points=[dict(x=0,z=0),dict(x=10,z=10)]))
        routes=route_inventory(s,lambda x,z:0);walking=next(r for r in routes if r['id']=='walking_counter')
        self.assertEqual(walking['kind'],'pedestrian');self.assertEqual(probe_profiles(walking),(False,))
        self.assertEqual(probe_profiles(routes[0]),(False,True));self.assertEqual(sum(r['kind']=='supply' for r in routes),6)
        with self.assertRaises(ValueError):probe_profiles(dict(kind='unknown'))
    def test_missing_supply_duplicate_or_nonfinite_route_fails(self):
        source=self.source();source['orvrLayout']['caravanRoutes'].pop()
        with self.assertRaises(ValueError):route_inventory(source,lambda x,z:0)
        source=self.source();source['paths'].append(source['paths'][0])
        with self.assertRaises(ValueError):route_inventory(source,lambda x,z:0)
        with self.assertRaises(ValueError):route_inventory(self.source(),lambda x,z:math.nan)
    def test_profile_coverage_and_unverified_driving_are_enforced(self):
        route=route_inventory(self.source(),lambda x,z:0)[0]
        probe=dict(passed=True,profile='SiegeConvoy',physicalDrivingVerified=False,queryBudget=2048,
            points=[dict(index=i,projected=True,connected=True,withinOutline=True,searchLimit=False,lengthCm=i*100) for i in range(2)])
        self.assertTrue(validate_probe(probe,route,True))
        for key,value in [('profile','Default'),('physicalDrivingVerified',True),('passed',False),('queryBudget',0),('queryBudget',True)]:
            bad=copy.deepcopy(probe);bad[key]=value
            with self.assertRaises(ValueError):validate_probe(bad,route,True)
        for key,value in [('withinOutline',False),('searchLimit',True),('lengthCm',math.inf),('index',99),('index',True)]:
            bad=copy.deepcopy(probe);bad['points'][1][key]=value
            with self.assertRaises(ValueError):validate_probe(bad,route,True)
        bad=copy.deepcopy(probe);bad['points'].pop()
        with self.assertRaises(ValueError):validate_probe(bad,route,True)

    def description(self):
        return dict(actors=[dict(profile=p,actor='original.actor',package='original',activeTiles=12,tileCapacity=16384,
            registered=True,needsRebuild=False,needsRebuildOnLoad=False,tileSnapshot=p+'|exact') for p in ('Default','SiegeConvoy')])
    def test_routing_copy_preserves_exact_tiles_without_package_identity(self):
        before=self.description();after=copy.deepcopy(before)
        for r in after['actors']:r.update(actor='copied.actor',package='copied')
        self.assertEqual(navigation_payload(before),navigation_payload(after))
        after['actors'][0]['tileSnapshot']+='changed'
        self.assertNotEqual(navigation_payload(before),navigation_payload(after))
        for key,value in [('registered',False),('needsRebuild',True),('needsRebuildOnLoad',True),('activeTiles',0),('activeTiles',True),('tileCapacity',99),('tileSnapshot','')]:
            bad=self.description();bad['actors'][0][key]=value
            with self.assertRaises(ValueError):navigation_payload(bad)
    def test_safe_staging_rejects_diagnostic_stale_or_incomplete_navigation(self):
        parent=dict(signature='a'*64,study='battlefield-navigation',navigationVerified=True,diagnostic=False,failures=[],parentSignature='scene',
            zones=[dict(id=z,map=navigation_map('a'*64,z),navigation=dict(saveReloadVerified=True,failures=[],reloaded=self.description())) for z in ('sunmeadow_march','cinderfen_outskirts')])
        self.assertTrue(validate_navigation_parent(parent,'scene'))
        for key,value in [('diagnostic',True),('navigationVerified',False),('parentSignature','stale'),('failures',['failed']),('zones',parent['zones'][:1])]:
            bad=copy.deepcopy(parent);bad[key]=value
            with self.assertRaises(ValueError):validate_navigation_parent(bad,'scene')
        bad=copy.deepcopy(parent);bad['zones'][0]['map']='/Game/Capitals/AegisCapital'
        with self.assertRaises(ValueError):validate_navigation_parent(bad,'scene')

if __name__=='__main__':unittest.main()
