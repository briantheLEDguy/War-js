import json
from pathlib import Path
import unreal
root=Path(__file__).resolve().parents[2]
directory=root/'artifacts/unreal/world-portals'
receipt=json.loads((directory/'build.json').read_text())
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(receipt['map'])
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.GameplayStatics.flush_level_streaming(world)
unreal.WarImportLibrary.prepare_preview_frame(None)
rows=[]
for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if not isinstance(actor,unreal.WarZonePortal):continue
    point=actor.get_editor_property('arrival_location')
    hit=unreal.SystemLibrary.line_trace_single(world,point+unreal.Vector(0,0,5000),point-unreal.Vector(0,0,5000),unreal.TraceTypeQuery.ECC_VISIBILITY,True,[],unreal.DrawDebugTrace.NONE,True)
    row={'route':str(actor.get_editor_property('route_id')),'arrival':[point.x,point.y,point.z]}
    if hit:
        values=hit.to_tuple(); row['hit']=[str(v) for v in values]
    rows.append(row)
(directory/'landing-diagnostics.json').write_text(json.dumps(rows,indent=2))
