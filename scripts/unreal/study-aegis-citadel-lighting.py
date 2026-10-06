"""Unsaved native lighting study; not a saved-scene or gameplay acceptance receipt."""
import json
import math
import os
import re
import sys
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from aegis_citadel_blueprint import OUT, sha
from aegis_citadel_lighting import FIXTURES, reference_fixture_requests, CLOUD_PROPERTIES, REVIEWED_CLOUD_MATERIAL
from citadel_stage_contract import native_lighting_value, lighting_readback
from shared_city_sources import package_file

revision = os.environ.get('WAR_CITADEL_INSPECT_REVISION', '')
if not re.fullmatch('[a-f0-9]{12}', revision):
    raise RuntimeError('Explicit native study revision required')
directory = OUT / revision
candidate = json.loads((directory / 'candidate.json').read_text())
blueprint = json.loads((directory / 'blueprint.json').read_text())
expected = {**candidate['sourceHashes'], **candidate['packageHashes']}
before = {p: sha(package_file(ROOT, p)) for p in expected}
if before != expected:
    raise RuntimeError('Preserve independently changed native packages')
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if not levels.load_level(candidate['siegeMap']):
    raise RuntimeError('Exact private study map unavailable')
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.GameplayStatics.flush_level_streaming(world)
fixtures = actors.get_all_level_actors()
requests = reference_fixture_requests(blueprint['lightingTreatment']['fixtures'])
readbacks = []
for request in requests:
    identity = next(row for row in FIXTURES if row[0] == request['id'])
    _, name, klass, label, component_name, _, tag = identity
    matches = [a for a in fixtures if a.get_name() == name and a.get_class().get_name() == klass
               and a.get_actor_label() == label and tag in [str(t) for t in a.tags]]
    if len(matches) != 1:
        raise RuntimeError('Ambiguous exact native study fixture: ' + request['id'])
    actor = matches[0]
    target = actor.get_component_by_class(getattr(unreal, component_name)) if component_name else actor.get_editor_property('settings')
    if component_name:
        target.set_mobility(unreal.ComponentMobility.MOVABLE)
    actual = {}
    for key, wanted in request['properties'].items():
        target.set_editor_property(key, native_lighting_value(wanted))
        actual[key] = lighting_readback(target.get_editor_property(key), wanted)
    if not component_name:
        actor.set_editor_property('settings', target)
    if request.get('rotationDegrees'):
        pitch, yaw, roll = request['rotationDegrees']
        actor.set_actor_rotation(unreal.Rotator(pitch=pitch, yaw=yaw, roll=roll), False)
    readbacks.append(dict(id=request['id'], path=actor.get_path_name(), properties=actual))
for actor in fixtures:
    if isinstance(actor, unreal.PointLight) and '/Layers/GothicCitadel.' in actor.get_path_name():
        actor.point_light_component.set_cast_shadows(True)
glass = unreal.load_asset('/Game/WorldRebuild/AegisCitadel_' + revision + '/Materials/M_glass')
for node in unreal.MaterialEditingLibrary.get_material_expressions(glass):
    if isinstance(node, unreal.MaterialExpressionConstant3Vector):
        emission = unreal.MaterialEditingLibrary.get_material_property_input_node(glass, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        if node == emission:
            node.constant = unreal.LinearColor(r=10, g=3.1, b=.4, a=1)
unreal.MaterialEditingLibrary.recompile_material(glass)
cloud = actors.spawn_actor_from_class(unreal.VolumetricCloud, unreal.Vector())
cloud_component = cloud.get_component_by_class(unreal.VolumetricCloudComponent)
cloud_material = unreal.load_asset(REVIEWED_CLOUD_MATERIAL)
if not cloud_material:
    raise RuntimeError('Reviewed Engine cloud material missing')
engine_content = Path(unreal.Paths.engine_content_dir()).resolve()
cloud_file = (engine_content / (REVIEWED_CLOUD_MATERIAL.removeprefix('/Engine/') + '.uasset')).resolve()
cloud_file.relative_to(engine_content)
cloud_hash = sha(cloud_file)
cloud_component.set_material(cloud_material)
for key, value in CLOUD_PROPERTIES.items():
    cloud_component.set_editor_property(key, value)
    lighting_readback(cloud_component.get_editor_property(key), value)
capture = actors.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector())
component = capture.capture_component2d
component.texture_target = unreal.RenderingLibrary.create_render_target2d(world, 1920, 1080, unreal.TextureRenderTargetFormat.RTF_RGBA8)
component.capture_source = unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
component.capture_every_frame = False
component.capture_on_movement = False
component.always_persist_rendering_state = True
component.post_process_blend_weight = 0
output = directory / 'native-lighting-study'
output.mkdir(exist_ok=True)
for view in blueprint['reviewViews']:
    if view['id'] not in ('hero', 'central_plaza', 'commander_hall'):
        continue
    component.fov_angle = 2 * math.atan(18 / view['focalLengthMm']) * 180 / math.pi
    eye, target = unreal.Vector(*view['eyeCm']), unreal.Vector(*view['targetCm'])
    capture.set_actor_location_and_rotation(eye, unreal.MathLibrary.find_look_at_rotation(eye, target), False, True)
    for _ in range(24):
        unreal.WarImportLibrary.prepare_world_preview_frame(world)
        component.capture_scene()
    unreal.RenderingLibrary.export_render_target(world, component.texture_target, str(output), view['id'] + '.png')
    if not (output / (view['id'] + '.png')).exists():
        raise RuntimeError('Native study capture missing')
after = {p: sha(package_file(ROOT, p)) for p in expected}
if before != after:
    raise RuntimeError('Unsaved study changed native files')
report = dict(schemaVersion=1, diagnosticOnly=True, savedPackagesChanged=False,
              nativeSceneCapture=True, effectiveGameCameraExposureVerified=False,
              revision=revision, signature=blueprint['signature'], fixtures=readbacks,
              cloudMaterial=REVIEWED_CLOUD_MATERIAL,
              cloudMaterialSha256=cloud_hash,
              sourceAndCandidateHashesUnchanged=True, visualApproved=False,
              lightingApproved=False, physicalTraversalApproved=False, releaseAcceptance=False)
(output / 'study.json').write_text(json.dumps(report, indent=2) + '\n')
unreal.log('WAR_CITADEL_LIGHTING_STUDY=' + str(output))
