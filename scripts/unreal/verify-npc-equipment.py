"""Saved-map equipment coverage, bone-following checks and player-height captures."""
import hashlib
import json
import sys
from pathlib import Path
import unreal

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
from world_actor_state import snapshot, transform

OUT=ROOT/'artifacts/unreal/npc-equipment'
directory=ROOT/'artifacts/unreal/world-portals'
build=json.loads((directory/'build.json').read_text())
manifest=json.loads((directory/'zone-manifest.json').read_text())
equipment=json.loads((OUT/'import.json').read_text())
records={row['id']:row for row in equipment['records']}
packages={build['map']:manifest['mainSha256'],**manifest['packageHashes']}


def check_packages():
    for path,fingerprint in packages.items():
        file=ROOT/'unreal/AegisWar/Content'/(path.removeprefix('/Game/')+'.umap')
        if hashlib.sha256(file.read_bytes()).hexdigest()!=fingerprint: raise RuntimeError('Saved world changed: '+path)


check_packages()
if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(build['map']): raise RuntimeError('Main map unavailable')
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.GameplayStatics.flush_level_streaming(world)
subsystem=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors=subsystem.get_all_level_actors()
zones={path:zone['id'] for zone in manifest['zones'] for path in zone['levels'].values()}
anchors={str(a.get_editor_property('zone_id')):a for a in actors if isinstance(a,unreal.WarZoneAnchor)}
capture=subsystem.spawn_actor_from_class(unreal.SceneCapture2D,unreal.Vector())
c=capture.capture_component2d
c.texture_target=unreal.RenderingLibrary.create_render_target2d(world,1280,900,unreal.TextureRenderTargetFormat.RTF_RGBA8)
c.capture_source=unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
c.capture_every_frame=False; c.capture_on_movement=False; c.always_persist_rendering_state=True
c.fov_angle=48; c.post_process_blend_weight=0
# Inspection fill is transient and called out in the evidence; no saved zone lighting changes.
fill=subsystem.spawn_actor_from_class(unreal.DirectionalLight,unreal.Vector(0,0,10000),unreal.Rotator(pitch=-35,yaw=-120))
fill.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
fill.light_component.set_editor_property('atmosphere_sun_light',False)
fill.light_component.set_cast_shadows(False)
fill.light_component.set_intensity(18000)
results=[]
for actor in actors:
    if isinstance(actor,unreal.WarEnemy):
        identity=str(actor.get_editor_property('enemy_id'))
        profile=str(actor.get_editor_property('visual').get_editor_property('source_profile_key')); role='enemy'
    elif isinstance(actor,unreal.WarCityNpc):
        identity=str(actor.get_editor_property('npc_id'))
        profile=str(actor.get_editor_property('character_profile')); role=str(actor.get_editor_property('city_role'))
        if role not in ('guard','marshal'): continue
    else: continue
    if identity not in records: raise RuntimeError('Uncovered combat NPC: '+identity)
    expected=len(records[identity]['attachments'])
    editor_weapons=[c for c in actor.get_components_by_class(unreal.StaticMeshComponent)
                    if unreal.WarNpcEquipmentLibrary.is_generated_attachment(c)]
    if len(editor_weapons)!=expected: raise RuntimeError('Saved NPC did not restore its equipment in the editor: '+identity)
    before=snapshot(actor)
    mesh=actor.get_component_by_class(unreal.SkeletalMeshComponent)
    unreal.WarImportLibrary.prepare_preview_frame(mesh)
    for _ in range(2):
        error=unreal.WarNpcEquipmentLibrary.apply(mesh,profile,identity,role)
        # Unreal's Python bool/out convention returns None on false, otherwise the out string.
        if error != '': raise RuntimeError(identity+': '+str(error))
    components=[a for a in actor.get_components_by_class(unreal.StaticMeshComponent) if 'WarNpcEquipment' in map(str,a.component_tags)]
    if len(components)!=expected: raise RuntimeError('Equipment duplicates or missing components')
    after=snapshot(actor)
    after['components']=[row for row in after['components'] if 'WarNpcEquipment' not in row['tags']]
    if before!=after: raise RuntimeError('Equipment changed authored actor state')
    for weapon in components:
        if weapon.get_collision_enabled()!=unreal.CollisionEnabled.NO_COLLISION: raise RuntimeError('Weapon has blocking collision')
        if weapon.get_attach_parent()!=mesh: raise RuntimeError('Weapon lost its skeletal parent')
    nameplate=actor.get_component_by_class(unreal.TextRenderComponent)
    if nameplate: nameplate.set_visibility(False)
    zone=zones[actor.get_outer().get_path_name().split('.')[0]]
    unreal.WarZoneLightingSubsystem.preview_world(world,zone,anchors[zone].get_editor_property('zone_origin'))
    fill.light_component.set_visibility(True)
    center,extent,_=unreal.SystemLibrary.get_component_bounds(mesh)
    feet=center.z-extent.z
    # Front three-quarter camera at player eye height; scout also receives a back view for the bow.
    views=[('front',unreal.Vector(310,410,0))]
    if 'scout' in profile: views.append(('back',unreal.Vector(310,-410,0)))
    for name,local in views:
        focus=unreal.Vector(center.x,center.y,feet+112)
        camera=None
        alternatives=[local,*[unreal.Vector(x,y,0) for x,y in ((0,480),(480,0),(-480,0),(0,-480),(-310,410),(-310,-410))]]
        for offset in alternatives:
            delta=unreal.MathLibrary.transform_direction(mesh.get_world_transform(),offset)
            candidate=unreal.Vector(center.x+delta.x,center.y+delta.y,feet+170)
            hit=unreal.SystemLibrary.line_trace_single(world,focus,candidate,unreal.TraceTypeQuery.ECC_VISIBILITY,
                True,[actor],unreal.DrawDebugTrace.NONE,True)
            if not hit or not hit.to_tuple()[0]: camera=candidate; break
        if camera is None: raise RuntimeError('No unobstructed equipment review camera: '+identity)
        capture.set_actor_location_and_rotation(camera,unreal.MathLibrary.find_look_at_rotation(camera,focus),False,True)
        fill.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(camera+unreal.Vector(0,0,200),focus),False)
        for _ in range(6):
            unreal.WarImportLibrary.prepare_world_preview_frame(world);c.capture_scene()
        unreal.RenderingLibrary.export_render_target(world,c.texture_target,str(OUT),identity+'_'+name+'.png')
    samples=[]
    if isinstance(actor,unreal.WarEnemy):
        visual=actor.get_editor_property('visual')
        clips=visual.get_editor_property('imported_animations')
        for clip in ('idle','run','attack_melee','death'):
            animation=unreal.load_asset(str(clips[clip])) if isinstance(clips[clip],str) else clips[clip]
            for fraction in (0,.5,1):
                mesh.override_animation_data(animation,False,False,animation.sequence_length*fraction,1)
                unreal.WarImportLibrary.prepare_preview_frame(mesh)
                for weapon in components:
                    bone=mesh.get_socket_transform(weapon.get_attach_socket_name(),unreal.RelativeTransformSpace.RTS_WORLD)
                    relative=unreal.MathLibrary.make_relative_transform(weapon.get_world_transform(),bone)
                    if any(abs(a-b)>.001 for a,b in zip(transform(relative),transform(weapon.get_relative_transform()))):
                        raise RuntimeError('Weapon detached during animation')
                samples.append({'clip':clip,'fraction':fraction})
    results.append({'id':identity,'zone':zone,'weapons':records[identity]['weapons'],'attachmentCount':len(components),
                    'boneFollowSamples':samples,'idempotent':True,'authoredActorUnchanged':True})
if set(records)!={row['id'] for row in results}: raise RuntimeError('Bound combat NPC not found in saved world')
check_packages()
(OUT/'verification.json').write_text(json.dumps({'combatActors':len(results),'results':results,'mapPackagesUnchanged':True,
    'temporaryInspectionFillLux':18000,'nativeArtApproved':False},indent=2)+'\n')
unreal.log('WAR_NPC_EQUIPMENT_VERIFIED='+str(len(results)))
