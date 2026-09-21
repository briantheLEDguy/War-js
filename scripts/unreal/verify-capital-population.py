import json, sys
from pathlib import Path
import unreal
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/unreal'))
from capital_population import official_map, POPULATION_MAP
level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
assert level.load_level(official_map())
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
if not unreal.GameplayStatics.get_streaming_level(world,POPULATION_MAP):
    unreal.EditorLevelUtils.add_level_to_world(world,POPULATION_MAP,unreal.LevelStreamingAlwaysLoaded)
unreal.GameplayStatics.flush_level_streaming(world)
r=json.loads((ROOT/'artifacts/unreal/population/population-build.json').read_text())
results=[]
for row in r['actors']:
 x,y,z=row['position'];z=row['feetZ']
 hit=unreal.SystemLibrary.line_trace_single(world,unreal.Vector(x,y,z+100),unreal.Vector(x,y,z-250),unreal.TraceTypeQuery.ECC_VISIBILITY,True,[],unreal.DrawDebugTrace.NONE)
 if not hit: raise RuntimeError('No ground under '+row['id'])
 data=hit.to_tuple();position=data[5];normal=data[7]
 if abs(position.z-z)>15 or normal.z<0.65: raise RuntimeError('Ungrounded or steep placement '+row['id']+': '+str(position))
 center=unreal.Vector(x,y,position.z+96)
 obstruction=unreal.SystemLibrary.capsule_trace_single(world,center,center+unreal.Vector(0,0,1),42,90,
     unreal.TraceTypeQuery.ECC_VISIBILITY,False,[],unreal.DrawDebugTrace.NONE)
 if obstruction: raise RuntimeError('Population placement overlaps blocking architecture: '+row['id'])
 results.append({'id':row['id'],'groundZ':position.z,'feetZ':z,'errorCm':abs(position.z-z),'groundActor':data[9].get_actor_label()})
(ROOT/'artifacts/unreal/population/ground-probe.json').write_text(json.dumps(results,indent=2))
