"""Read saved population layers, verify identities, and capture unsaved inspection views."""
import json
import sys
from pathlib import Path
import unreal
sys.path.insert(0,str(Path(__file__).parent))
from imported_population import ROOT, OUT, digest
from capital_population import official_map
from importlib import import_module

def main():
    receipt=OUT/'placement.json'
    if not receipt.exists():
        unreal.log('Population is staged; saved-world review awaits admission')
        return
    placed=json.loads(receipt.read_text())
    for file,expected in placed['packages'].items():
        if digest(ROOT/file)!=expected: raise RuntimeError('Placed package changed: '+file)
    if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(official_map()): raise RuntimeError('City unavailable')
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.GameplayStatics.flush_level_streaming(world)
    subsystem=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors=subsystem.get_all_level_actors()
    identities={str(a.get_editor_property('enemy_id' if isinstance(a,unreal.WarEnemy) else 'npc_id')):a
        for a in actors if isinstance(a,(unreal.WarCityNpc,unreal.WarEnemy))}
    state=import_module('place-imported-population').actor_state
    for row in placed['actors']:
        if row['id'] not in identities or state(identities[row['id']])!=row['state']:
            raise RuntimeError('Saved actor differs: '+row['id'])
    for actor in actors:
        if isinstance(actor,unreal.WarCityNpc):
            label=actor.get_component_by_class(unreal.TextRenderComponent)
            if label: label.set_visibility(False)
    anchors={str(a.get_editor_property('zone_id')):a for a in actors if isinstance(a,unreal.WarZoneAnchor)}
    fill=subsystem.spawn_actor_from_class(unreal.DirectionalLight,unreal.Vector(0,0,20000))
    fill.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    fill.light_component.set_editor_property('atmosphere_sun_light',False)
    fill.light_component.set_intensity(18000); fill.light_component.set_cast_shadows(False)
    capture=subsystem.spawn_actor_from_class(unreal.SceneCapture2D,unreal.Vector())
    c=capture.capture_component2d
    c.texture_target=unreal.RenderingLibrary.create_render_target2d(world,1280,800,unreal.TextureRenderTargetFormat.RTF_RGBA8)
    c.capture_source=unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
    c.capture_every_frame=False; c.capture_on_movement=False; c.always_persist_rendering_state=True
    c.fov_angle=58; c.post_process_blend_weight=0
    output=OUT/'placed-views'; output.mkdir(exist_ok=True)
    frames=[]
    survey=json.loads((OUT/'placement-survey.json').read_text())
    groups={}
    for row in survey['actors']: groups.setdefault((row['zone'],row['district']),[]).append(row['id'])
    views=[(r['id'],r['zone'],[r['id']],500) for r in placed['actors']]
    views += [(zone+'_'+district,zone,ids,950) for (zone,district),ids in groups.items()]
    for name,zone,ids,distance in views:
        unreal.WarZoneLightingSubsystem.preview_world(world,zone,anchors[zone].get_editor_property('zone_origin'))
        focus=sum((identities[i].get_actor_location() for i in ids),unreal.Vector())/len(ids)+unreal.Vector(0,0,100)
        camera=None
        for dx,dy in ((1,0),(0,1),(-1,0),(0,-1),(.7,.7),(-.7,.7),(-.7,-.7),(.7,-.7)):
            candidate=focus+unreal.Vector(dx*distance,dy*distance,80 if len(ids)==1 else 200)
            hit=unreal.SystemLibrary.line_trace_single(world,focus,candidate,unreal.TraceTypeQuery.ECC_VISIBILITY,
                True,[identities[i] for i in ids],unreal.DrawDebugTrace.NONE)
            if not hit: camera=candidate; break
        if camera is None: raise RuntimeError('Inspection camera blocked: '+name)
        capture.set_actor_location_and_rotation(camera,unreal.MathLibrary.find_look_at_rotation(camera,focus),False,True)
        fill.light_component.set_visibility(True)
        fill.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(camera+unreal.Vector(0,0,300),focus),False)
        for _ in range(5): unreal.WarImportLibrary.prepare_world_preview_frame(world); c.capture_scene()
        unreal.RenderingLibrary.export_render_target(world,c.texture_target,str(output),name+'.png')
        frames.append(dict(name=name,zone=zone,ids=ids,file=name+'.png'))
    (OUT/'placed-review.json').write_text(json.dumps(dict(placementSha256=digest(receipt),frames=frames,
        savedActorsVerified=len(placed['actors']),temporaryInspectionFillLux=18000,savedLightingChanged=False,approved=False),indent=2)+'\n')

if __name__=='__main__': main()
