"""Create staged NPC visuals and equipment; publication is a separate reviewed step."""
import json
import math
import runpy
import sys
from pathlib import Path
import unreal
sys.path.insert(0,str(Path(__file__).parent))
from imported_population import ROOT, OUT, BASE, LEDGER, digest, models, verify_sources
from world_actor_state import transform

verify_sources()
runpy.run_path(str(Path(__file__).with_name('adapt-population-materials.py')))
library = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
sets = json.loads((OUT/'presentations.json').read_text())['profiles']
bodies = json.loads((OUT/'bodies.json').read_text())['profiles']
template = unreal.load_asset('/Game/MigrationProof/Visual_civic_sunfire_templar_m')
if not template: raise RuntimeError('Reviewed Templar equipment is unavailable')
catalog_path = BASE+'/StagedLoadouts'
catalog = unreal.load_asset(catalog_path) if library.does_asset_exist(catalog_path) else None
if catalog and library.get_metadata_tag(catalog,'WarPopulationOwner') != 'schema-1':
    raise RuntimeError('Unowned staged equipment catalog')
if not catalog:
    factory = unreal.DataAssetFactory(); factory.set_editor_property('data_asset_class',unreal.WarNpcEquipmentCatalog)
    catalog = tools.create_asset('StagedLoadouts',BASE,unreal.WarNpcEquipmentCatalog,factory)
loadouts, receipts = [], {}


def reference(mesh, animation, bone):
    options = unreal.AnimPoseEvaluationOptions(); options.optional_skeletal_mesh = mesh
    pose = unreal.AnimPoseExtensions.get_anim_pose_at_time(animation,0,options)
    return unreal.AnimPoseExtensions.get_ref_bone_pose(pose,bone,unreal.AnimPoseSpaces.WORLD)


def forward_yaw(mesh, animation):
    direction = sum((reference(mesh,animation,'toe_'+s).translation-reference(mesh,animation,'foot_'+s).translation
                     for s in ('L','R')),unreal.Vector())
    if math.hypot(direction.x,direction.y)<.01: raise RuntimeError('Cannot measure authored foot forward axis')
    return math.degrees(math.atan2(direction.y,direction.x))


for row in models().values():
    profile = row['profile']; entry = sets[profile]; body = bodies[profile]
    mesh = unreal.load_asset(entry['mesh'])
    animations = {k:unreal.load_asset(v) for k,v in entry['bindings'].items()}
    if not mesh or any(not a for a in animations.values()): raise RuntimeError('Missing native profile: '+profile)
    path = BASE+'/Visual_'+profile
    visual = unreal.load_asset(path) if library.does_asset_exist(path) else None
    if visual and library.get_metadata_tag(visual,'WarPopulationOwner') != 'schema-1':
        raise RuntimeError('Unowned population visual: '+path)
    if not visual: visual = library.duplicate_asset(template.get_path_name(),path)
    visual.set_editor_properties(dict(profile_key=profile,source_profile_key=profile,class_id='resident',
        race_id=row['species'],body_variant='source',realm=unreal.WarRealm.RIFTBOUND if row['alignment']=='evil' else unreal.WarRealm.AEGIS,
        source_model=body['originalSource'],source_sha256=body['originalSha256'],skeletal_mesh=mesh,
        animation_blueprint=None,idle_animation=animations['idle'],imported_animations=animations,
        animation_style=entry['style'],ability_presentations={},basic_contact_seconds=entry['basicContactSeconds'],
        locomotion_speeds=entry['locomotionSpeeds'],weapon_mesh=None,shield_mesh=None,
        mesh_transform=unreal.Transform(location=unreal.Vector(0,0,-96),rotation=unreal.Rotator(yaw=180))))
    equipment = []
    slots = []
    if row['key'] == 'paladin_prop': slots = ['Paladin_MAT']
    elif row['key'] == 'archer': slots = ['Bow_MAT','Arrow_MAT']
    elif row['equipment'] == 'sword-shield':
        equipment_template = unreal.load_asset('/Game/MigrationProof/Visual_mire_warbrute_m') if row['key'] in ('brute','cultist','maw','oathguard') else template
        if not equipment_template: raise RuntimeError('Reviewed scavenged equipment is unavailable')
        correction = forward_yaw(mesh,animations['idle'])-forward_yaw(equipment_template.skeletal_mesh,equipment_template.idle_animation)
        alignment = unreal.Transform(rotation=unreal.Rotator(yaw=correction))
        for slot, bone in [('weapon','hand_R'),('shield','hand_L')]:
            source_mesh = equipment_template.get_editor_property(slot+'_mesh')
            if not source_mesh: raise RuntimeError('Missing reviewed equipment: '+slot)
            source_ref = reference(equipment_template.skeletal_mesh,equipment_template.idle_animation,bone)
            target_ref = reference(mesh,animations['idle'],bone)
            desired = equipment_template.get_editor_property(slot+'_grip') * source_ref * alignment
            source_hand = unreal.MathLibrary.transform_location(alignment,source_ref.translation)
            desired.translation = desired.translation + target_ref.translation-source_hand
            grip = desired * target_ref.inverse()
            if slot == 'shield':
                # Match the shield face to the imported rig's ready pose; the original
                # player's authored hand axes otherwise put the board above its fist.
                options=unreal.AnimPoseEvaluationOptions(); options.optional_skeletal_mesh=mesh
                pose=unreal.AnimPoseExtensions.get_anim_pose_at_time(animations['idle'],.3,options)
                hand=unreal.AnimPoseExtensions.get_bone_pose(pose,bone,unreal.AnimPoseSpaces.WORLD)
                fitted=grip*hand
                turn=unreal.Transform(rotation=unreal.Rotator(pitch=90))
                offset=fitted.translation-hand.translation
                fitted=unreal.Transform(location=hand.translation+unreal.MathLibrary.transform_direction(turn,offset),
                    rotation=(fitted*turn).rotation.rotator(),scale=fitted.scale3d)
                grip=fitted*hand.inverse()
            attachment = unreal.WarNpcWeaponAttachment()
            package = ROOT/'unreal/AegisWar/Content'/(source_mesh.get_path_name().split('.')[0].removeprefix('/Game/')+'.uasset')
            attachment.set_editor_properties(dict(id='import_'+slot,bone=bone,mesh=source_mesh,
                relative_transform=grip,source_sha256=digest(package)))
            equipment.append(attachment)
    for role in ('guard','marshal','enemy') if equipment or slots else ():
        binding = unreal.WarNpcLoadout()
        binding.set_editor_properties(dict(profile=profile,role=role,body=mesh,body_source_sha256=row['sha256'],
            attachments=equipment,embedded_weapon_material_slots=slots))
        loadouts.append(binding)
    error = visual.validate_for_spawn(visual.realm)
    if error: raise RuntimeError(profile+': '+error)
    library.set_metadata_tag(visual,'WarPopulationOwner','schema-1')
    if not library.save_loaded_asset(visual,False): raise RuntimeError('Could not save '+path)
    receipts[profile] = dict(visual=visual.get_path_name(),mesh=mesh.get_path_name(),source=row['source'],sha256=row['sha256'],
        embeddedWeaponMaterialSlots=slots,attachments=[dict(bone=str(a.get_editor_property('bone')),mesh=a.get_editor_property('mesh').get_path_name(),relativeTransform=transform(a.get_editor_property('relative_transform'))) for a in equipment])
catalog.set_editor_property('loadouts',loadouts)
library.set_metadata_tag(catalog,'WarPopulationOwner','schema-1')
if not library.save_loaded_asset(catalog,False): raise RuntimeError('Could not save staged equipment')
(OUT/'installed.json').write_text(json.dumps(dict(schemaVersion=1,ledgerSha256=digest(LEDGER),
    presentationsSha256=digest(OUT/'presentations.json'),profiles=receipts,catalog=catalog.get_path_name(),
    published=False,nativeVisualVerified=False,gameplayVerified=False),indent=2)+'\n')
