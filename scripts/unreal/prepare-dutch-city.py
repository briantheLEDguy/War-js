"""Record protected native interiors/services and deliberate city gathering areas."""
import json
from dutch_bastion import ROOT, OUT, digest

survey=json.loads((OUT/'city-source-survey.json').read_text())
sites=[]
for actor in survey['actors']:
    state=actor['state'];kind=state['class'];tags=state['tags']
    if 'WarCapitalInterior' not in tags and kind not in ('WarCityNpc','WarQuestNpc','WarCraftingStation','PlayerStart'): continue
    cx,cy,cz,ex,ey,ez=actor['bounds']
    # Full existing interior, roof, attached props and a walkable perimeter.
    radius=2 if 'WarCapitalInterior' in tags else 2.5
    ex=max(ex/100,.5)+radius;ey=max(ey/100,.5)+radius;x=cy/100;z=cx/100
    sites.append(dict(id='retained_'+actor['name'].lower(),actor=actor['name'],layer=actor['layer'],
                      stateSignature=digest(state),kind='existing_interior' if 'WarCapitalInterior' in tags else 'service_access',
                      name=state['label'],polygon=[[x-ey,z-ex],[x+ey,z-ex],[x+ey,z+ex],[x-ey,z+ex]]))
target=ROOT/'scripts/campaign/dutch-bastion-layout.json';layout=json.loads(target.read_text())
if 'protectedSites' in layout and layout['protectedSites']!=sites: raise RuntimeError('Retained actors changed; reconcile before applying')
layout['protectedSites']=sites
layout['revision']='dutch-blocks-v2'
layout['gatheringAreas']=[
    dict(id='gateward_exchange',name='Gateward Exchange',purpose='combat_market',polygon=[[-25,-126],[26,-126],[26,-92],[-25,-92]]),
    dict(id='cinderbank_workyard',name='Cinderbank Workyard',purpose='crafting_ambiance',polygon=[[-97,-47],[-48,-47],[-48,-31],[-97,-31]]),
    dict(id='lantern_muster',name='Lantern Muster',purpose='combat_waterfront',polygon=[[104,-25],[135,-25],[135,-3],[104,-3]]),
    dict(id='bellfound_forum',name='Bellfound Forum',purpose='civic_gathering',polygon=[[-44,49],[-13,49],[-13,62],[-44,62]]),
    dict(id='crownwatch_vigil',name='Crownwatch Vigil',purpose='guarded_ambiance',polygon=[[70,99],[101,99],[101,113],[70,113]])]
target.write_text(json.dumps(layout,indent=2)+'\n')
print(f'Recorded {len(sites)} retained sites and five district gathering areas')
