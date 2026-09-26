"""Prepare fixed native proof viewpoints; this module cannot access Unreal levels."""
import json
from pathlib import Path
from capital_expansion import ZONES, rotate, walking_route, validate_plan


def placement_transform(row, template, origin):
    ox,oy=rotate(template['origin'][0],template['origin'][1],row['yaw'])
    return [origin[0]+row['position'][0]-ox,origin[1]+row['position'][1]-oy,
            row['position'][2]-(template['origin'][2]-template['extent'][2])]


def proof_config(plan, assets, baseline):
    views=[];routes=[]
    for zone in ZONES:
        rows=[p for p in plan['placements'] if p['zone']==zone]
        origin=baseline[zone]['origin']
        for row in rows:
            t=assets['templates'][row['recipe']]
            location=placement_transform(row,t,origin)
            def point(p):
                x,y=rotate(p[0],p[1],row['yaw'])
                return [location[0]+x,location[1]+y,location[2]+p[2]]
            if row['interior']:
                points=[point(p) for p in walking_route(t)]
                routes.append({'id':row['id'],'zone':zone,'points':points})
                views.append({'id':row['id'],'zone':zone,'feet':points[0],
                              'eye':point([t['entrance'][0],t['entrance'][1]+260,175]),
                              'target':point([0,t['roomSize'][1]/2-80,135])})
        if zone=='aegis_capital':
            feet=[-11800,0,10]
            city_views=(('aerial',[-37000,-31000,23500],[12000,0,5200]),
                        ('street',[-11000,0,190],[-7000,0,450]))
        else:
            feet=[origin[0]+42100,origin[1],10]
            city_views=(('aerial',[origin[0]+55000,origin[1]-58000,42000],[origin[0],origin[1],-9000]),
                        ('street',[origin[0]+42500,origin[1]+100,190],[origin[0]+40000,origin[1],150]))
        for name,eye,target in city_views:
            views.insert(0,{'id':zone+'_'+name,'zone':zone,'feet':feet,'eye':eye,'target':target})
    return {'views':views,'routes':routes,'planSignature':plan['signature']}


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    directory=root/'artifacts/unreal/capital-expansion'
    plan=json.loads((directory/'plan.json').read_text());validate_plan(plan)
    config=proof_config(plan,json.loads((directory/'assets.json').read_text()),json.loads((directory/'baseline.json').read_text()))
    output=root/'unreal/AegisWar/Content/Migration/capital-expansion-proof.json'
    output.write_text(json.dumps(config,indent=2)+'\n')
    print('Prepared proof configuration:',len(config['views']),'views,',len(config['routes']),'interior routes')
