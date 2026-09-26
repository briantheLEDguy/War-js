"""Survey explicit, full-scale replacements for unchanged repetitive Aegis houses."""
import hashlib
import json
import math
from pathlib import Path
import sys
import unreal

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from capital_expansion import SpatialIndex,rectangle,source_obstacles,rotate,digest,require_unchanged
from world_actor_state import snapshot
OUT=ROOT/'artifacts/unreal/capital-expansion'
CONTENT=ROOT/'unreal/AegisWar/Content'


def main():
    baseline=json.loads((OUT/'baseline.json').read_text())['aegis_capital']
    receipt=json.loads((OUT/'applied.json').read_text())
    for p,sha in receipt['packageHashes'].items():
        require_unchanged(sha,hashlib.sha256((CONTENT/(p.removeprefix('/Game/')+'.umap')).read_bytes()).hexdigest())
    assets=json.loads((OUT/'assets.json').read_text())
    expansion=json.loads((OUT/'plan.json').read_text())
    source=json.loads((ROOT/'public/assets/maps/aegis_capital.json').read_text())
    build=json.loads((ROOT/'artifacts/unreal/world-portals/build.json').read_text())
    level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not level.load_level(build['map']): raise RuntimeError('World missing')
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.GameplayStatics.flush_level_streaming(world)
    current={(a.get_outer().get_path_name().split('.')[0],a.get_name()):a
             for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()}
    palette={(r['package'],r['actor']):r for r in receipt['paletteEdits']}
    index=SpatialIndex(); houses=[]
    for row in baseline['actors']:
        key=(row['package'],row['name']); actor=current[key]
        require_unchanged(palette[key]['after'] if key in palette else row['state'],snapshot(actor))
        text=' '.join(c.get('mesh') or '' for c in row['state']['components']).lower()
        if key in palette: houses.append((row,actor))
        if not text.strip() or any(n in text for n in ('rock_','terrain','ground','mountain','floor','deck','bridge','stairs','path')): continue
        center,extent=row['center'],row['extent']
        if max(extent[:2])>6000 or extent[2]<30: continue
        index.add(rectangle(center[:2],[e*2 for e in extent[:2]],0,70),center[2]-extent[2]-40,center[2]+extent[2],key)
    for polygon in source_obstacles({**source,'props':[]}): index.add([(y,x) for x,y in polygon])
    for p in expansion['placements']:
        if p['zone']=='aegis_capital': index.add(p['footprint'],p['position'][2]-40,p['position'][2]+p['height'])
    draft_path=ROOT/'unreal/AegisWar/Saved/WorldEdit/crownward-draft.json'
    draft=json.loads(draft_path.read_text(encoding='utf-8-sig')) if draft_path.exists() else None
    old_rows={r['id']:r for r in json.loads(draft['baseline'])['objects']} if draft else {}
    edited={r['id'] for r in draft['objects'] if r!=old_rows.get(r['id'])} if draft else set()
    copied={r.get('templateId') for r in draft['objects']} if draft else set()
    choices={'gateward':[1,2,0,4,8],'cinderbank':[4,6,10,0,9],
             'lantern_quays':[3,9,0,7,2],'bellfound':[5,8,1,10,4],'crownwatch':[11,6,7,10,9]}
    result=[]; counts={}; trace_cache={}
    houses.sort(key=lambda item:digest(item[0]['name']))
    for old,actor in houses:
        identity=next(str(t)[15:] for t in actor.tags if str(t).startswith('WarWorldObject_'))
        if identity in edited or identity in copied: continue
        key=(old['package'],old['name']); center=old['center']; ground=center[2]-old['extent'][2]
        district=min(source['cityDistricts'],key=lambda d:(d['x']*100-center[1])**2+(d['z']*100-center[0])**2)['id']
        if counts.get(district,0)>=12: continue
        variants=sorted(choices[district],key=lambda i:(sum(r['recipe']==f'aegis_compact_{i:02d}' for r in result),choices[district].index(i)))
        selected=None
        for i in variants:
            template=assets['templates'][f'aegis_compact_{i:02d}']
            size=[e*2 for e in template['extent'][:2]]
            for yaw in (actor.get_actor_rotation().yaw,actor.get_actor_rotation().yaw+90):
                for dx,dy in ((0,0),(-100,0),(100,0),(0,-100),(0,100)):
                    xy=[center[0]+dx,center[1]+dy]; polygon=rectangle(xy,size,yaw,60)
                    if index.blocked(polygon,ground+40,ground+template['extent'][2]*2,ignore=key): continue
                    if any(r['recipe']==template['id'] and math.dist(r['position'][:2],xy)<2400 for r in result+expansion['placements'] if r['zone']=='aegis_capital'): continue
                    heights=[]
                    for px,py in [xy]+rectangle(xy,[max(100,s-60) for s in size],yaw):
                        cache_key=(round(px,2),round(py,2),round(ground,2))
                        if cache_key not in trace_cache:
                            hit=unreal.SystemLibrary.line_trace_single(world,unreal.Vector(px,py,ground+350),
                                unreal.Vector(px,py,ground-350),unreal.TraceTypeQuery.ECC_VISIBILITY,True,[actor],unreal.DrawDebugTrace.NONE,True)
                            parts=hit.to_tuple() if hit else None
                            trace_cache[cache_key]=parts[5].z if parts and parts[0] and parts[7].z>.8 else None
                        heights.append(trace_cache[cache_key])
                    if any(h is None for h in heights) or max(heights)-min(heights)>45: continue
                    transform=actor.get_actor_transform();p,q,s=transform.translation,transform.rotation,transform.scale3d
                    selected={'id':identity,'zone':'aegis_capital','district':district,'recipe':template['id'],
                        'position':xy+[max(heights)+2],'yaw':yaw,'footprint':polygon,'height':template['extent'][2]*2,
                        'package':old['package'],'actor':old['name'],'before':snapshot(actor),
                        'previousTransform':[p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z],
                        'previousSourceIdentity':actor.static_mesh_component.static_mesh.get_path_name()+':'+
                            next(str(t)[15:] for t in actor.tags if str(t).startswith('WarModelSha256_'))}
                    break
                if selected: break
            if selected: break
        if selected:
            result.append(selected);counts[district]=counts.get(district,0)+1
            index.add(selected['footprint'],ground-40,ground+selected['height'])
    plan={'schemaVersion':1,'packageHashes':receipt['packageHashes'],'assetsSha256':hashlib.sha256((OUT/'assets.json').read_bytes()).hexdigest(),
          'ownerDraftSha256':hashlib.sha256(draft_path.read_bytes()).hexdigest() if draft else None,'replacements':result}
    plan['signature']=digest(plan)
    (OUT/'replacement-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    unreal.log('WAR_EXPANSION_REPLACEMENTS_SURVEYED='+str(len(result))+' '+str(counts))


main()
