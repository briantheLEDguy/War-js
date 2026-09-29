"""Read-only survey of saved portal triggers against the currently installed world."""
import json
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'artifacts/unreal/portal-models'
build = json.loads((ROOT/'artifacts/unreal/world-portals/build.json').read_text())
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if not levels.load_level(build['map']):
    raise RuntimeError('Installed campaign map is unavailable')
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.GameplayStatics.flush_level_streaming(world)
unreal.WarImportLibrary.prepare_world_preview_frame(world)
rows = []
for portal in actors.get_all_level_actors():
    if not isinstance(portal, unreal.WarZonePortal):
        continue
    point = portal.get_actor_location()
    hit = unreal.SystemLibrary.line_trace_single(world, point+unreal.Vector(0,0,2000),
        point-unreal.Vector(0,0,10000), unreal.TraceTypeQuery.ECC_VISIBILITY, True, [portal], unreal.DrawDebugTrace.NONE, True)
    row = dict(route=str(portal.get_editor_property('route_id')), position=[point.x,point.y,point.z],
               radius=portal.get_editor_property('radius'),collision=portal.get_actor_enable_collision(),
               destinationBuilt=portal.get_editor_property('destination_built'))
    if hit:
        values = hit.to_tuple()
        row['groundHit'] = bool(values[0])
        if values[0]:
            point, normal = values[5], values[6]
            row['groundPoint'] = [point.x,point.y,point.z]
            row['groundNormal'] = [normal.x,normal.y,normal.z]
            row['groundActor'] = values[9].get_path_name() if values[9] else None
    rows.append(row)
(OUT/'entry-survey.json').write_text(json.dumps(dict(map=build['map'],routes=rows),indent=2)+'\n')
unreal.log('WAR_PORTAL_ENTRY_SURVEY='+str(len(rows)))
