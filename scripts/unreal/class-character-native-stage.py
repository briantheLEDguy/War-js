"""UE: import, retarget, verify and install source-bound class-body revisions."""
import importlib.util
import hashlib
import json
import math
import os
from pathlib import Path
import re
import runpy
import sys
import uuid
import unreal

sys.path.insert(0, str(Path(__file__).parent))
from class_character_native import ROOT, OUT, read, sha, roster_config, gltf_joint_positions
import animation_replacement as animation

TOOLS = Path(__file__).parent
library = unreal.EditorAssetLibrary
manifest = read(OUT / 'model-sources.json')
records = manifest['profiles']
if len(records) != 48:
    raise RuntimeError('All 48 body conversions are required')
for key, row in records.items():
    if sha(ROOT / row['source']) != row['sourceSha256'] or sha(ROOT / row['fbx']) != row['fbxSha256']:
        raise RuntimeError('Changed native source: ' + key)
OWNER = 'WarClassBodySource'


def visual_path(key):
    return '/Game/Characters/ClassBodies/Visual_' + key


def package_fingerprint():
    sets = read(OUT / 'presentations.json')['profiles']
    paths = set()
    for key, row in sets.items():
        paths.update([visual_path(key), row['mesh'], *row['bindings'].values()])
    hashes = {path: sha(ROOT / 'unreal/AegisWar/Content' / (path.split('.')[0].removeprefix('/Game/') + '.uasset'))
              for path in sorted(paths)}
    return hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()


def save(asset, key):
    library.set_metadata_tag(asset, OWNER, records[key]['sourceSha256'])
    if not library.save_loaded_asset(asset, False):
        raise RuntimeError('Could not save owned class-body asset')


def configure_contract():
    original = animation.locomotion
    recipes = dict(animation.RECIPES)
    previous = os.environ.get('WAR_ANIMATION_SET')
    try:
        os.environ['WAR_ANIMATION_SET'] = 'siege-casters'
        spec = importlib.util.spec_from_file_location('class_body_siege_recipes', TOOLS / 'animation_replacement.py')
        siege = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(siege)
        recipes.update(siege.RECIPES)
    finally:
        if previous is None: os.environ.pop('WAR_ANIMATION_SET', None)
        else: os.environ['WAR_ANIMATION_SET'] = previous
    animation.OUT = OUT
    animation.PROFILES = {key: (row['classId'], row['style']) for key, row in records.items()}
    animation.RECIPES = {row['classId']: recipes.get(row['classId'], []) for row in records.values()}
    animation.selected = lambda key: key in records
    animation.visual_path = visual_path
    # Common basic states are supplied sources; unknown class abilities stay
    # unimplemented instead of borrowing another class's choreography.
    def movement(style):
        return dict(original(style), attack_melee={'two': 'two.slash', 'shield': 'shield.slash', 'spell': 'spell.bolt'}[style],
                    attack_ranged='spell.bolt', cast='spell.focus')
    animation.locomotion = movement


DONORS = {
    'battle_prelate': '/Game/MigrationProof/Visual_civic_battle_prelate_m',
    'sunfire_templar': '/Game/MigrationProof/Visual_civic_sunfire_templar_m',
    'ember_arcanist': '/Game/MigrationProof/Visual_civic_ember_arcanist_m',
    'warbrute': '/Game/MigrationProof/Visual_mire_warbrute_m',
    'void_magister': '/Game/Characters/SiegeStaging/Visual_riven_void_magister_m',
    'ruin_oracle': '/Game/Characters/SiegeStaging/Visual_riven_ruin_oracle_m',
}


def provisional_visuals():
    bodies = read(OUT / 'bodies.json')['profiles']
    for key, row in records.items():
        path = visual_path(key)
        visual = unreal.load_asset(path) if library.does_asset_exist(path) else None
        if visual and library.get_metadata_tag(visual, OWNER) != row['sourceSha256']:
            raise RuntimeError('Refuse to overwrite unowned class visual: ' + path)
        donor = unreal.load_asset(DONORS.get(row['classId'], DONORS['battle_prelate']))
        if not donor:
            raise RuntimeError('Missing retained native equipment/visual source')
        if row['classId'] not in DONORS:
            if not visual:
                factory = unreal.DataAssetFactory()
                factory.set_editor_property('data_asset_class', unreal.WarCharacterVisualDefinition)
                visual = unreal.AssetToolsHelpers.get_asset_tools().create_asset(path.rsplit('/', 1)[1],
                    path.rsplit('/', 1)[0], unreal.WarCharacterVisualDefinition, factory)
        elif not visual:
            visual = library.duplicate_asset(donor.get_path_name(), path)
        if not visual: raise RuntimeError('Could not create own-class visual: ' + key)
        visual.set_editor_properties(dict(profile_key=key, source_profile_key=key, playable_profile_key=row['profileKey'],
            race_id=row['race'], class_id=row['classId'], body_variant=row['bodyVariant'],
            realm=unreal.WarRealm.AEGIS if row['race'] in ('empire', 'dwarf', 'high_elf') else unreal.WarRealm.RIFTBOUND,
            source_model=row['source'], source_sha256=row['sourceSha256'], complex_authored_model=True,
            skeletal_mesh=unreal.load_asset(bodies[key]['mesh']), animation_blueprint=None,
            animation_style=row['style'], ability_presentations={}, mesh_transform=donor.mesh_transform))
        if row['classId'] not in DONORS:
            if not unreal.WarImportLibrary.clear_class_body_equipment(visual):
                raise RuntimeError('Could not clear serialized donor equipment paths')
        save(visual, key)


def compose():
    provisional_visuals()
    runpy.run_path(str(TOOLS / 'fit-class-character-equipment.py'), run_name='__main__')
    import supplied_stow
    # Each new rig retains a separate stow profile. Existing local equipment
    # transforms are a starting fit and must pass the new rig's native review.
    supplied_stow.stored_transform = lambda key, slot, mesh, grip, chest: unreal.load_asset(visual_path(key)).get_editor_property(slot + '_stowed')
    runpy.run_path(str(TOOLS / 'compose-animation-presentations.py'), run_name='__main__')


def bind_visuals():
    sets = read(OUT / 'presentations.json')['profiles']
    for key, entry in sets.items():
        visual = unreal.load_asset(visual_path(key))
        bindings = {role: unreal.load_asset(path) for role, path in entry['bindings'].items()}
        presentations = {}
        for ability, recipe in entry['presentations'].items():
            value = unreal.WarAbilityPresentation()
            value.set_editor_properties(dict(variant_roles=recipe['variantRoles'], supplied_sources=recipe['suppliedSources'],
                duration=recipe['duration'], contact_seconds=recipe['contactSeconds'], blend_seconds=recipe['blendSeconds'],
                stow_equipment=recipe['stowEquipment'], movement=recipe['movement'], capsule_heights=recipe['capsuleHeights']))
            presentations[ability] = value
        visual.set_editor_properties(dict(idle_animation=bindings['idle'], imported_animations=bindings,
            ability_presentations=presentations, basic_contact_seconds=entry['basicContactSeconds'],
            locomotion_speeds=entry['locomotionSpeeds']))
        error = visual.validate_for_spawn(visual.realm)
        if error:
            raise RuntimeError('Class body cannot spawn: ' + key + ': ' + error)
        save(visual, key)


def verify():
    provisional_visuals()
    bind_visuals()
    sets = read(OUT / 'presentations.json')['profiles']
    report = dict(schemaVersion=1, profiles={}, passed=False, artApproval=False, gameplayVerified=False,
                  presentationsSha256=sha(OUT / 'presentations.json'), failures=[])
    for key, entry in sets.items():
        mesh = unreal.load_asset(entry['mesh'])
        if len(mesh.materials) != 3 or any(not slot.material_interface for slot in mesh.materials):
            raise RuntimeError('Native materials lost: ' + key)
        component = unreal.new_object(unreal.SkeletalMeshComponent)
        component.set_skeletal_mesh_asset(mesh)
        source_joints = gltf_joint_positions(ROOT / records[key]['source'])
        native_bones = [str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
        if len(source_joints) != 56 or not set(source_joints).issubset(native_bones):
            raise RuntimeError('Native import lost canonical source bones: ' + key)
        reference = unreal.AnimPoseExtensions.get_reference_pose(mesh.skeleton)
        rest_error = max((unreal.AnimPoseExtensions.get_ref_bone_pose(reference, bone, unreal.AnimPoseSpaces.WORLD).translation
                          - unreal.Vector(*point)).length() for bone, point in source_joints.items())
        if rest_error > .1:
            raise RuntimeError('Native bind positions changed: ' + key + ': ' + str(rest_error) + ' cm')
        options = []
        for kind in (unreal.AnimDataEvalType.RAW, unreal.AnimDataEvalType.COMPRESSED):
            option = unreal.AnimPoseEvaluationOptions()
            option.set_editor_properties(dict(optional_skeletal_mesh=mesh, evaluation_type=kind))
            options.append(option)
        measurements = []
        for path in sorted(set(entry['bindings'].values())):
            sequence = unreal.load_asset(path)
            if not sequence or sequence.get_editor_property('skeleton') != mesh.skeleton:
                raise RuntimeError('Wrong native animation skeleton: ' + key)
            duration = unreal.AnimationLibrary.get_sequence_length(sequence)
            maximum_error, maximum_length_delta = 0., 0.
            for sample in range(17):
                poses = [unreal.AnimPoseExtensions.get_anim_pose_at_time(sequence, duration * sample / 16, option) for option in options]
                for bone in unreal.AnimPoseExtensions.get_bone_names(poses[0]):
                    raw, compressed = [unreal.AnimPoseExtensions.get_bone_pose(pose, bone, unreal.AnimPoseSpaces.WORLD) for pose in poses]
                    values = (raw.translation.x, raw.translation.y, raw.translation.z, raw.scale3d.x, raw.scale3d.y,
                              raw.scale3d.z, raw.rotation.x, raw.rotation.y, raw.rotation.z, raw.rotation.w)
                    if not all(math.isfinite(value) for value in values):
                        raise RuntimeError('Non-finite native pose: ' + key)
                    maximum_error = max(maximum_error, (raw.translation-compressed.translation).length())
                    if str(bone) not in ('root', 'hips'):
                        local = unreal.AnimPoseExtensions.get_bone_pose(poses[0], bone, unreal.AnimPoseSpaces.LOCAL)
                        reference = unreal.AnimPoseExtensions.get_ref_bone_pose(poses[0], bone, unreal.AnimPoseSpaces.LOCAL)
                        maximum_length_delta = max(maximum_length_delta, abs(local.translation.length()-reference.translation.length()))
            passed = duration > 0 and maximum_error < .25 and maximum_length_delta < .005
            measurements.append(dict(animation=path, samples=17, maximumCompressionErrorCm=maximum_error,
                                     maximumLocalLimbLengthDeltaCm=maximum_length_delta, passed=passed))
            if not passed: report['failures'].append(dict(profile=key, **measurements[-1]))
        report['profiles'][key] = dict(mesh=entry['mesh'], visual=visual_path(key), animations=measurements,
            bones=native_bones, canonicalSourceBones=len(source_joints), maximumRestJointErrorCm=rest_error,
            materials=len(mesh.materials), abilities=len(entry['presentations']))
        (OUT / 'technical-verification.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
        unreal.log('WAR_CLASS_NATIVE_VERIFIED=' + key)
    report['passed'] = len(report['profiles']) == 48 and not report['failures']
    report['nativePackagesSha256'] = package_fingerprint()
    (OUT / 'technical-verification.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    if not report['passed']: raise RuntimeError('Native class-body pose checks failed')


def install():
    verified = read(OUT / 'technical-verification.json')
    if not verified['passed'] or verified['presentationsSha256'] != sha(OUT / 'presentations.json'):
        raise RuntimeError('Current native verification is required before installation')
    sets = read(OUT / 'presentations.json')['profiles']
    equipped = read(OUT / 'equipped-motion-measurements.json')
    frames = read(OUT / 'review/frames.json')
    current = sha(OUT / 'presentations.json')
    native_hash = package_fingerprint()
    if (not equipped['passed'] or equipped['presentationManifestSha256'] != current
            or frames['presentationsSha256'] != current or len(frames['frames']) != 304
            or {row['profile'] for row in frames['frames']} != set(records)
            or any(receipt.get('nativePackagesSha256') != native_hash for receipt in (verified, equipped, frames))):
        raise RuntimeError('Current equipped-motion and actual native-render evidence is required')
    for frame in frames['frames']:
        if sha(OUT / 'review' / frame['file']) != frame['sha256']:
            raise RuntimeError('Changed native review frame')
    decision = read(OUT / 'review/inspection.json')
    if (not decision['developmentAccepted'] or decision['framesSha256'] != sha(OUT / 'review/frames.json')
            or set(decision['inspectedProfiles']) != set(records)):
        raise RuntimeError('Inspect the native renders before admitting the development roster')
    config_path = ROOT / 'unreal/AegisWar/Config/DefaultGame.ini'
    before_config = config_path.read_text(encoding='utf-8-sig')
    after_config = roster_config(before_config, records)
    registry_path = ROOT / 'unreal/AegisWar/Content/Migration/visual-imports.json'
    registry = read(registry_path)
    backup = OUT / 'visual-imports-before.json'
    if not backup.exists(): backup.write_bytes(registry_path.read_bytes())
    entries = {entry['profileKey']: entry for entry in registry['entries']}
    for key, row in records.items():
        entry = sets[key]
        entries[key] = dict(profileKey=key, sourceModel=row['source'], sourceSha256=row['sourceSha256'],
            skeletalMeshPath=entry['mesh'], animationPaths=sorted(set(entry['bindings'].values())),
            artApproval=False, developmentOnly=True)
    registry['entries'] = sorted(entries.values(), key=lambda entry: entry['profileKey'])
    temporary = registry_path.with_suffix('.class-bodies.tmp')
    temporary.write_text(json.dumps(registry, indent=2)+'\n', encoding='utf-8')
    temporary.replace(registry_path)
    config_backup = OUT / 'DefaultGame-before.ini'
    if not config_backup.exists(): config_backup.write_bytes(config_path.read_bytes())
    config_path.write_text(after_config, encoding='utf-8')
    (OUT / 'installed.json').write_text(json.dumps(dict(schemaVersion=1, profiles={
        records[key]['profileKey']: dict(visual=visual_path(key), sourceProfileKey=key, mesh=entry['mesh'])
        for key, entry in sets.items()}, registrySha256=sha(registry_path), rosterConfigSha256=sha(config_path),
        equippedMotionSha256=sha(OUT / 'equipped-motion-measurements.json'),
        nativeReviewSha256=sha(OUT / 'review/frames.json'), developmentOnly=True,
        artApproval=False, gameplayVerified=False), indent=2)+'\n', encoding='utf-8')
    unreal.log('WAR_CLASS_BODIES_INSTALLED=48')


def review():
    from supplied_stow import inverse
    verified = read(OUT / 'technical-verification.json')
    if not verified['passed']: raise RuntimeError('Native structural verification must pass before review')
    native_hash = package_fingerprint()
    if verified['nativePackagesSha256'] != native_hash: raise RuntimeError('Native packages changed after verification')
    sets = read(OUT / 'presentations.json')['profiles']
    output = OUT / 'review'
    output.mkdir(exist_ok=True)
    editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not editor.new_level('/Game/Characters/Reviews/ClassBodies_' + uuid.uuid4().hex[:12]):
        raise RuntimeError('Could not create temporary native review world')
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for pitch, yaw, power in [(-35, -90, 12000.), (-25, 40, 8000.), (-20, 180, 7000.)]:
        light = actors.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 400), unreal.Rotator(pitch, yaw, 0))
        light.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
        light.light_component.set_editor_property('intensity', power)
        light.light_component.set_editor_property('forward_shading_priority', 1 if yaw == -90 else 0)
        light.light_component.set_editor_property('cast_shadows', yaw == -90)
    sky = actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 300))
    sky.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    sky.light_component.set_editor_properties(dict(intensity=300., source_type=unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP,
        cubemap=unreal.load_asset('/Engine/MapTemplates/Sky/DaylightAmbientCubemap')))
    capture = actors.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector())
    camera = capture.capture_component2d
    camera.texture_target = unreal.RenderingLibrary.create_render_target2d(world, 600, 800, unreal.TextureRenderTargetFormat.RTF_RGBA8)
    camera.capture_source = unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
    camera.capture_every_frame = False; camera.capture_on_movement = False
    camera.always_persist_rendering_state = True; camera.fov_angle = 32
    settings = camera.get_editor_property('post_process_settings')
    settings.set_editor_properties(dict(override_auto_exposure_method=True, auto_exposure_method=unreal.AutoExposureMethod.AEM_MANUAL,
        override_auto_exposure_bias=True, auto_exposure_bias=1.5,
        override_auto_exposure_apply_physical_camera_exposure=True, auto_exposure_apply_physical_camera_exposure=True))
    camera.post_process_settings = settings
    actor = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector())
    body = actor.skeletal_mesh_component
    body.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    equipment = {slot: actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector()) for slot in ('weapon', 'shield')}
    for part in equipment.values(): part.static_mesh_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    frames = []
    for key, entry in sets.items():
        visual = unreal.load_asset(visual_path(key))
        body.set_skeletal_mesh_asset(visual.skeletal_mesh)
        for slot, part in equipment.items(): part.static_mesh_component.set_static_mesh(visual.get_editor_property(slot + '_mesh'))
        for role in ('idle', 'walk', 'attack_melee'):
            sequence = unreal.load_asset(entry['bindings'][role])
            seconds = unreal.AnimationLibrary.get_sequence_length(sequence) * .5
            body.play_animation(sequence, False); body.set_position(seconds, False)
            unreal.WarImportLibrary.prepare_preview_frame(body)
            for slot, part in equipment.items():
                hand = 'hand_R' if slot == 'weapon' else 'hand_L'
                stored = entry['style'] == 'spell'
                transform = visual.get_editor_property(slot + ('_stowed' if stored else '_grip')) * body.get_socket_transform('upper_chest' if stored else hand)
                part.set_actor_transform(transform, False, True)
            height = records[key]['expectedHeightM'] * 100
            views = [('front', unreal.Vector(0, height * 2.9, height * .58)),
                     ('side', unreal.Vector(height * 2.9, 0, height * .58))]
            if role == 'idle' and records[key]['race'] == 'greenskin':
                views += [('face_front', unreal.Vector(0, height * .55, height * .9)),
                          ('face_side', unreal.Vector(height * .55, 0, height * .9))]
            for view, location in views:
                for part in equipment.values():
                    part.static_mesh_component.set_visibility(not view.startswith('face_'), False)
                target = unreal.Vector(0, 0, height * .51)
                if view.startswith('face_'):
                    reference = unreal.AnimPoseExtensions.get_reference_pose(visual.skeletal_mesh.skeleton)
                    bind_head = unreal.AnimPoseExtensions.get_ref_bone_pose(reference, 'head', unreal.AnimPoseSpaces.WORLD)
                    facing = body.get_socket_transform('head').rotation * inverse(bind_head.rotation)
                    up = facing.rotate_vector(unreal.Vector(0, 0, 1))
                    target = (body.get_socket_location('eye_L') + body.get_socket_location('eye_R'))*.5 - up*height*.035
                    axis = facing.rotate_vector(unreal.Vector(0, 1, 0) if view == 'face_front' else unreal.Vector(1, 0, 0))
                    location = target + axis*height*.55 + up*height*.015
                capture.set_actor_location_and_rotation(location, unreal.MathLibrary.find_look_at_rotation(location, target), False, True)
                for _ in range(3):
                    unreal.WarImportLibrary.prepare_world_preview_frame(world); camera.capture_scene()
                filename = key + '_' + role + '_' + view + '.png'
                unreal.RenderingLibrary.export_render_target(world, camera.texture_target, str(output), filename)
                if not (output / filename).exists(): raise RuntimeError('Missing actual native render')
                frames.append(dict(profile=key, role=role, seconds=seconds, view=view,
                    equipmentVisible=not view.startswith('face_'), file=filename, sha256=sha(output / filename)))
        (output / 'frames.json').write_text(json.dumps(dict(presentationsSha256=sha(OUT / 'presentations.json'),
            nativePackagesSha256=native_hash, frames=frames,
            artApproval=False, developmentOnly=True), indent=2)+'\n', encoding='utf-8')
        unreal.log('WAR_CLASS_NATIVE_RENDERED=' + key)


configure_contract()
match = re.search(r'-WarClassNativeStage=(import|retarget|compose|verify|equipment|review|install)\b', unreal.SystemLibrary.get_command_line())
if not match: raise RuntimeError('An explicit class native stage is required')
stage = match[1]
if stage == 'import': runpy.run_path(str(TOOLS / 'import-playable-models.py'), run_name='__main__')
elif stage == 'retarget': runpy.run_path(str(TOOLS / 'import-animation-replacement.py'), run_name='__main__')
elif stage == 'compose': compose()
elif stage == 'verify': verify()
elif stage == 'equipment':
    native_hash = package_fingerprint()
    if read(OUT / 'technical-verification.json')['nativePackagesSha256'] != native_hash:
        raise RuntimeError('Native packages changed after verification')
    runpy.run_path(str(TOOLS / 'measure-equipped-motion.py'), run_name='__main__')
    measured = read(OUT / 'equipped-motion-measurements.json')
    measured['nativePackagesSha256'] = native_hash
    (OUT / 'equipped-motion-measurements.json').write_text(json.dumps(measured, indent=2)+'\n', encoding='utf-8')
elif stage == 'review': review()
elif stage == 'install': install()
