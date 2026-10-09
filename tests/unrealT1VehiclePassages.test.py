import copy,math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_vehicle_passages import adapt_gate_passages

class VehiclePassageTests(unittest.TestCase):
    def fixture(self):
        props=[];keeps=[];states={}
        for realm in ('aegis','rift'):
            identity=realm+'_keep';gates=[]
            for stage in ('outer','inner'):
                house=identity+'_'+stage+'_gatehouse';leaf=identity+'_'+stage+'_leaf'
                gates.append(dict(stage=stage,propId=leaf,width=6))
                for label in (house,leaf):props.append(dict(id=label,kind='mesh',x=1,z=2,rotY=3,scale=1,colliderSpace='model',colliders=[dict(width=6,depth=.45)]))
                states[house]=dict(kind='mesh',scale=[2,3,4],location=[100,200,300])
            keeps.append(dict(objectiveId=identity,gates=gates))
        before=dict(id='sunmeadow_march',props=props,orvrLayout=dict(keeps=keeps))
        after=copy.deepcopy(before)
        for p in after['props']:p['scaleX']=1.25
        for k in after['orvrLayout']['keeps']:
            for g in k['gates']:g['width']=7.5
        return states,before,after
    def test_exact_native_lateral_axis_and_nonmutation(self):
        states,before,after=self.fixture();original=copy.deepcopy((states,before,after))
        result,receipt=adapt_gate_passages(states,before,after)
        self.assertEqual((states,before,after),original)
        for label,row in result.items():self.assertEqual(row,dict(kind='mesh',scale=[2,3.75,4],location=[100,200,300]))
        self.assertEqual(len(receipt['adapted']),4);self.assertEqual(len(receipt['pendingGateLeaves']),4)
        self.assertTrue(receipt['sourceCollisionDimensionsAligned']);self.assertFalse(receipt['nativeClosedGateBehaviorVerified']);self.assertFalse(receipt['vehicleDrivingVerified'])
    def test_missing_binding_bad_scale_or_changed_assembly_fails(self):
        for corruption in ('missing','scale','position','collider','identity','width','leaf'):
            states,before,after=self.fixture();label=next(iter(states))
            if corruption=='missing':states.pop(label)
            elif corruption=='scale':states[label]['scale'][1]=math.nan
            elif corruption=='position':after['props'][0]['x']+=1
            elif corruption=='collider':after['props'][0]['colliders'][0]['width']=7.5
            elif corruption=='identity':after['id']='brightfen_approach'
            elif corruption=='width':after['orvrLayout']['keeps'][0]['gates'][0]['width']=8
            elif corruption=='leaf':states[after['orvrLayout']['keeps'][0]['gates'][0]['propId']]=copy.deepcopy(states[label])
            with self.assertRaises(ValueError,msg=corruption):adapt_gate_passages(states,before,after)

if __name__=='__main__':unittest.main()
