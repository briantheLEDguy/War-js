from pathlib import Path
import sys,math,unittest,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_landscape_walks import ground_walk,landscape_walks

class LandscapeWalkTest(unittest.TestCase):
    def test_search_goes_around_obstructions_and_keeps_native_coordinates(self):
        h=lambda x,z:x*10
        clear=lambda x,z:not (abs(x)<8 and abs(z)<12)
        bounds=dict(minX=-40,maxX=40,minZ=-40,maxZ=40)
        route=ground_walk(h,(-30,0),(30,0),bounds,clear)
        self.assertEqual(route[0],[0,-3000,-300]);self.assertEqual(route[-1],[0,3000,300])
        self.assertTrue(any(abs(p[0])>=1200 for p in route))
        self.assertEqual(route,ground_walk(h,(-30,0),(30,0),bounds,clear))
        for z,x,y in route:
            self.assertTrue(clear(x/100,z/100));self.assertAlmostEqual(y,h(x/100,z/100))
        with self.assertRaises(ValueError):ground_walk(h,(-30,0),(30,0),bounds,lambda x,z:False)
        with self.assertRaises(ValueError):ground_walk(lambda x,z:x*100,(-30,0),(30,0),bounds,lambda x,z:True)
        with self.assertRaises(ValueError):ground_walk(h,(math.nan,0),(0,0),bounds,clear)

    def test_counter_pair_replans_around_native_blockers_without_editing_source(self):
        source=dict(id='sunmeadow_march',spatial=dict(playableOutline=[dict(x=x,z=z) for x,z in [(-500,-500),(500,-500),(500,500),(-500,500)]]))
        before=json.dumps(source,sort_keys=True);calls=[]
        def native(x,z):
            calls.append((x,z));return not (-214<x<-186 and -20<z<70)
        routes=landscape_walks(source,lambda x,z:z*10,[],native)
        self.assertEqual(len(routes),2);self.assertEqual(json.dumps(source,sort_keys=True),before)
        self.assertTrue(any(-214<x<-186 and -20<z<70 for x,z in calls))
        for route in routes:
            self.assertFalse(route['walkingAccepted']);self.assertFalse(route['drivingAccepted'])
            for z,x,_ in route['points']:self.assertTrue(native(x/100,z/100))
        with self.assertRaises(ValueError):landscape_walks(source,lambda x,z:0,[],lambda x,z:False)

    def test_authored_pair_checks_whole_links_and_rejects_incomplete_or_blocked_access(self):
        identity='sunmeadow_march'
        climbs=[dict(id=identity+'_scarp_'+side+'_climb',points=[dict(x=x,z=z) for x,z in points]) for side,points in (
            ('west',[(-275,137),(-200,105),(-145,75)]),('east',[(-100,172),(-145,75)]))]
        source=dict(id=identity,paths=[{},dict(points=[{}, {},dict(x=-310,z=130),dict(x=-60,z=180)])],
            orvrLayout=dict(terrain=dict(clearCorridors=climbs)))
        before=json.dumps(source,sort_keys=True);seen=[]
        def clear(x,z):seen.append((x,z));return True
        routes=landscape_walks(source,lambda x,z:x*10,[],clear)
        self.assertEqual(len(routes),2);self.assertGreater(len(seen),100)
        self.assertEqual(routes[0]['points'][-1],[7500,-14500,-1450])
        self.assertTrue(all(r['terrainAndCapsuleChecked'] and not r['walkingAccepted'] for r in routes))
        self.assertEqual(json.dumps(source,sort_keys=True),before)
        with self.assertRaises(ValueError):landscape_walks(source,lambda x,z:x*10,[],lambda x,z:not(-275<x<-200))
        with self.assertRaises(ValueError):landscape_walks(source,lambda x,z:x*100,[],lambda x,z:True)
        source['orvrLayout']['terrain']['clearCorridors']=climbs[:1]
        with self.assertRaises(ValueError):landscape_walks(source,lambda x,z:0,[],lambda x,z:True)

if __name__=='__main__':unittest.main()
