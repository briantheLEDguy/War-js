"""Check room volumes against foreign geometry, including nonblocking cliff meshes."""
import hashlib
import json
import math
from pathlib import Path
import sys
import unreal

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from capital_expansion import SpatialIndex,rectangle,city_candidates,source_obstacles,require_unchanged,digest,rotate
from capital_expansion_proof import placement_transform
OUT=ROOT/'artifacts/unreal/capital-expansion'
CONTENT=ROOT/'unreal/AegisWar/Content'


def main():
    receipt=json.loads((OUT/'applied.json').read_text());plan=json.loads((OUT/'plan.json').read_text())
    baseline=json.loads((OUT/'baseline.json').read_text());assets=json.loads((OUT/'assets.json').read_text())
    for p,sha in receipt['packageHashes'].items():
        require_unchanged(sha,hashlib.sha256((CONTENT/(p.removeprefix('/Game/')+'.umap')).read_bytes()).hexdigest())
    build=json.loads((ROOT/'artifacts/unreal/world-portals/build.json').read_text())
    if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(build['map']): raise RuntimeError('World missing')
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.GameplayStatics.flush_level_streaming(world)
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    by_key={(a.get_outer().get_path_name().split('.')[0],a.get_name()):a for a in actors}
    added={r['id']:r for r in receipt['added']};changed=[]
    # Collision is enabled only in this unsaved survey world. Large background
    # rock meshes are deliberately absent from gameplay's coarse collision.
    for actor in actors:
        if not isinstance(actor,unreal.StaticMeshActor) or not actor.static_mesh_component.static_mesh: continue
        component=actor.static_mesh_component
        if any(n in component.static_mesh.get_path_name().lower() for n in ('rock_','terrain','mountain')):
            changed.append((component,component.get_collision_profile_name()))
            component.set_collision_profile_name('BlockAll')
    report={'planSignature':plan['signature'],'packageHashes':receipt['packageHashes'],'checked':0,'intrusions':[],'refits':[]}

    def obstruction(row,actor):
        t=assets['templates'][row['recipe']]; location=placement_transform(row,t,baseline[row['zone']]['origin'])
        volumes=[(0,0,160+f*300,t['roomSize'][0]/2-40,t['roomSize'][1]/2-40,120,f)
                 for f in range(2 if row['upperFloor'] else 1)]
        volumes.append((t['entrance'][0],-t['roomSize'][1]/2-140,140,60,180,110,'entrance'))
        for x,y,z,ex,ey,ez,floor in volumes:
            x,y=rotate(x,y,row['yaw'])
            start=unreal.Vector(location[0]+x,location[1]+y,location[2]+z)
            hit=unreal.SystemLibrary.box_trace_single(world,start,start+unreal.Vector(0,0,1),
                unreal.Vector(ex,ey,ez),unreal.Rotator(yaw=row['yaw']),
                unreal.TraceTypeQuery.ECC_VISIBILITY,True,[actor],unreal.DrawDebugTrace.NONE,True)
            parts=hit.to_tuple() if hit else None
            if parts and parts[0]:
                other=parts[9]
                return {'floor':floor,'actor':other.get_path_name() if other else 'unknown'}
        return None

    try:
        for row in plan['placements']:
            if not row['interior']: continue
            record=added[row['id']];actor=by_key[(record['package'],record['actor'])]
            problem=obstruction(row,actor);report['checked']+=1
            if not problem: continue
            report['intrusions'].append({'id':row['id'],**problem})
            zone=row['zone'];origin=baseline[zone]['origin'];t=assets['templates'][row['recipe']]
            source=json.loads((ROOT/'public/assets/maps'/(zone+'.json')).read_text());index=SpatialIndex()
            for old in baseline[zone]['actors']:
                text=' '.join(c.get('mesh') or '' for c in old['state']['components']).lower()
                if not text.strip() or any(n in text for n in ('rock_','terrain','ground','mountain','floor','deck','bridge','stairs','path')): continue
                center,extent=old['center'],old['extent']
                if max(extent[:2])>6000 or extent[2]<30: continue
                index.add(rectangle([center[0]-origin[0],center[1]-origin[1]],[e*2 for e in extent[:2]],0,60),center[2]-extent[2]-40,center[2]+extent[2])
            for p in plan['placements']+report['refits']:
                if p['zone']==zone and p['id']!=row['id']: index.add(p['footprint'],p['position'][2]-40,p['position'][2]+p['height'])
            for polygon in source_obstacles({**source,'props':[]}): index.add([(y,x) for x,y in polygon])
            candidates=[{'xy':[row['position'][0]+dx,row['position'][1]+dy],'z':row['position'][2],
                         'yaw':row['yaw'],'district':row['district']} for dx in range(-600,601,100) for dy in range(-600,601,100)]
            candidates+=city_candidates(zone,source)
            candidates.sort(key=lambda c:(c['district']!=row['district'],math.dist(c['xy'],row['position'][:2])))
            selected=None;size=[e*2 for e in t['extent'][:2]]
            for candidate in candidates:
                for turn in (0,90):
                    xy=candidate['xy'];yaw=candidate['yaw']+turn;z=candidate['z'];polygon=rectangle(xy,size,yaw,80)
                    if index.blocked(polygon,z+40,z+row['height']): continue
                    heights=[]
                    for px,py in [xy]+rectangle(xy,[max(100,s-60) for s in size],yaw):
                        hit=unreal.SystemLibrary.line_trace_single(world,unreal.Vector(origin[0]+px,origin[1]+py,z+350),
                            unreal.Vector(origin[0]+px,origin[1]+py,z-350),unreal.TraceTypeQuery.ECC_VISIBILITY,True,[actor],unreal.DrawDebugTrace.NONE,True)
                        parts=hit.to_tuple() if hit else None
                        heights.append(parts[5].z if parts and parts[0] and parts[7].z>.8 else None)
                    if any(h is None for h in heights) or max(heights)-min(heights)>45: continue
                    trial={**row,'position':xy+[max(heights)+2],'yaw':yaw,'district':candidate['district'],'footprint':polygon}
                    if obstruction(trial,actor): continue
                    selected=trial;break
                if selected: break
            if not selected: raise RuntimeError('No clear replacement lot for '+row['id'])
            report['refits'].append(selected)
            unreal.log('WAR_CAPITAL_ROOM_REFIT='+row['id'])
    finally:
        for component,profile in changed: component.set_collision_profile_name(profile)
        report['signature']=digest(report)
        (OUT/'room-clearance.json').write_text(json.dumps(report,indent=2)+'\n')
    unreal.log('WAR_CAPITAL_ROOM_VOLUMES='+str(report['checked'])+' REFITS='+str(len(report['refits'])))


main()
