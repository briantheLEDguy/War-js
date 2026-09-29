"""Continuous raised city paving over retained terrain, with bounded gradients."""
import heapq
import json
import math
from functools import lru_cache
from dutch_bastion import OUT, digest
from capital_geography import height

LOW=-160
HIGH=140
SIZE=HIGH-LOW+1
GRADE=.70


def build():
    values=[]
    for z in range(LOW,HIGH+1):
        for x in range(LOW,HIGH+1):
            # Include half-grid samples so small terrain peaks cannot poke
            # through the paving between its shared vertices.
            values.append(max(height(x+dx,z+dz) for dx,dz in ((0,0),(.5,0),(0,.5),(.5,.5))))
    queue=[(-h,i) for i,h in enumerate(values)];heapq.heapify(queue)
    steps=[(dx,dz,GRADE*math.hypot(dx,dz)) for dx in (-1,0,1) for dz in (-1,0,1) if dx or dz]
    while queue:
        negative,i=heapq.heappop(queue);current=-negative
        if current<values[i]-1e-9: continue
        x,z=i%SIZE,i//SIZE
        for dx,dz,cost in steps:
            nx,nz=x+dx,z+dz
            if not 0<=nx<SIZE or not 0<=nz<SIZE: continue
            j=nz*SIZE+nx;candidate=current-cost
            if candidate>values[j]+1e-9:
                values[j]=candidate;heapq.heappush(queue,(-candidate,j))
    result=dict(low=LOW,high=HIGH,grade=GRADE,heights=values)
    result['signature']=digest(result)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'city-ground.json').write_text(json.dumps(result,separators=(',',':'))+'\n')
    return result


@lru_cache(maxsize=1)
def data():
    result=json.loads((OUT/'city-ground.json').read_text())
    if (result['signature']!=digest({k:v for k,v in result.items() if k!='signature'})
            or (result['low'],result['high'],result['grade'])!=(LOW,HIGH,GRADE)
            or len(result['heights'])!=SIZE*SIZE):
        raise RuntimeError('Changed city height field; regenerate dependent geometry')
    return result


def paving_height(x,z):
    if not LOW<=x<HIGH or not LOW<=z<HIGH: return height(x,z)
    a=math.floor(x)-LOW;b=math.floor(z)-LOW;tx=x-math.floor(x);tz=z-math.floor(z)
    values=data()['heights'];h00=values[b*SIZE+a];h10=values[b*SIZE+a+1]
    h01=values[(b+1)*SIZE+a];h11=values[(b+1)*SIZE+a+1]
    return h00+tz*(h01-h00)+tx*(h11-h01) if tz>=tx else h00+tx*(h10-h00)+tz*(h11-h10)


if __name__=='__main__':
    result=build();print('Graded city paving: '+result['signature'])
