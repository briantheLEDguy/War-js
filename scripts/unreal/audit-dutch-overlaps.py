"""Audit exported house vertices and floor faces, independent of native traversal."""
import json
import sys
from dutch_bastion import OUT, digest
sys.path.insert(0,str(OUT/'python'))
import numpy as np
from shapely import contains_xy
from shapely.geometry import Polygon
from dutch_mesh_clipping import city_envelopes


def audit():
    plan=json.loads((OUT/'city-plan.json').read_text())
    architecture=json.loads((OUT/'city-architecture.json').read_text())
    lots={r['id']:r for b in plan['blocks'] for r in b['lots']}
    envelopes=city_envelopes(list(lots.values()));failures=[];triangles=0;floors=0
    for row in architecture['houses']:
        mesh=json.loads((OUT/row['meshFile']).read_text())
        vertices=np.array(mesh['positions'],dtype=float)
        vertices+=np.array(row['position'])
        x,y=vertices[:,1]/100,vertices[:,0]/100
        inside=contains_xy(envelopes[row['id']].buffer(2e-6),x,y)
        if not inside.all(): failures.append(dict(id=row['id'],reason='exported trim outside owned envelope',vertices=int((~inside).sum())))
        indices=np.array(mesh['indices']).reshape((-1,3));triangles+=len(indices)
        # Midpoints also catch a face bridging a reentrant corner after export.
        centres=vertices[indices].mean(axis=1)
        if not contains_xy(envelopes[row['id']].buffer(2e-6),centres[:,1]/100,centres[:,0]/100).all():
            failures.append(dict(id=row['id'],reason='triangle spans unowned corner'))
        positions=np.array(mesh['positions']);z=positions[indices,2];materials=np.array(mesh['triangleMaterials'])
        stone_at_floor=(np.abs(z)<1e-5).all(axis=1)&(materials==1)
        core=Polygon(lots[row['id']]['polygon']).buffer(-.30,join_style='mitre')
        if stone_at_floor.any() and contains_xy(core,centres[stone_at_floor,1]/100,centres[stone_at_floor,0]/100).any():
            failures.append(dict(id=row['id'],reason='foundation shares the occupied floor plane'))
        for floor in range(lots[row['id']]['storeys']):
            top=(np.abs(z-floor*300)<1e-5).all(axis=1)&(materials==3)
            if not top.any(): continue
            floors+=1;points=vertices[indices[top]].reshape((-1,3))
            core=Polygon(lots[row['id']]['polygon']).buffer(-.119,join_style='mitre')
            if not contains_xy(core,points[:,1]/100,points[:,0]/100).all():
                failures.append(dict(id=row['id'],reason='floor edge reaches exterior wall',floor=floor))
    result=dict(geometrySignature=architecture['geometrySignature'],houses=len(lots),triangles=triangles,
                floors=floors,failures=failures,passed=not failures)
    result['signature']=digest(result)
    (OUT/'overlap-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
    if failures: raise SystemExit(1)


if __name__=='__main__': audit()
