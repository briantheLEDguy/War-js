"""Synchronize only admitted gate-house/leaf lateral scales with the private shared source."""
import copy,math


def adapt_gate_passages(states,previous,source):
    if source['id']!=previous['id'] or source['id'] not in ('sunmeadow_march','cinderfen_outskirts'):
        raise ValueError('Gate passage identities differ')
    old={p['id']:p for p in previous['props']};new={p['id']:p for p in source['props']}
    result=copy.deepcopy(states);adapted=[];pending=[]
    for keep in source['orvrLayout']['keeps']:
        for gate in keep['gates']:
            for label,leaf in ((keep['objectiveId']+'_'+gate['stage']+'_gatehouse',False),(gate['propId'],True)):
                a,b=old[label],new[label]
                if any(a.get(k)!=b.get(k) for k in ('x','z','rotY','kind','assetKey','colliders','colliderSpace','interaction')):
                    raise ValueError('Gate passage must preserve complete assembly positions, intrinsic colliders and interactions')
                if b.get('scaleX')!=1.25 or any(b.get(k,1)!=a.get(k,1) for k in ('scale','scaleY','scaleZ')) or gate['width']!=7.5:
                    raise ValueError('Unexpected gate passage adaptation')
                if label not in result:
                    if not leaf:raise ValueError('Native gatehouse binding is missing')
                    pending.append(label);continue
                state=result[label]
                if state['kind']!='mesh' or len(state['scale'])!=3 or any(not math.isfinite(v) or v<=0 for v in state['scale']):
                    raise ValueError('Native gate assembly has no bounded source mesh scale')
                ratio=b['scaleX']/a.get('scaleX',a.get('scale',1))
                state['scale'][1]*=ratio
                adapted.append(dict(id=label,sourceScaleX=b['scaleX'],nativeScale=state['scale'][:],widthMetres=gate['width']))
    if len(adapted)!=4 or len(pending)!=4:raise ValueError('Current gate-house/leaf native inventory differs; review integration before adapting')
    return result,dict(adapted=adapted,pendingGateLeaves=pending,sourceCollisionDimensionsAligned=True,
        nativeClosedGateBehaviorVerified=False,vehicleDrivingVerified=False)
