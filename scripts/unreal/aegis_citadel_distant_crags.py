"""Opt-in original distant backdrop for copied private lighting studies only."""
import copy
import hashlib
import json
import math
import re
from pathlib import Path

OPTION = 'connected_original_v1'
REFERENCE = Path('artifacts/unreal/citadel-reference/reference-fidelity-proposal')
FROZEN_INPUTS = {
    'optional_distant_crags.py': '207ad7055f861fcf5ff16709d314ab2fc2c372c940baca9732b6fffb16d3ed95',
    'measurements.json': 'eb9a6c15c7100df7c9db6cadc7799e79b85ab8d17f94dffa51f8e682ba91d51f',
    'patch-src/output/aegis_citadel_mesh.py': 'a43444660458cb474f69c26c760fc26e02bed3c47b77b2542d6c0b4679b1fbcc',
    'optional-prototype/connected-crags.mesh.json': '3c4703f93b95de6fd6b3edf88bef69ebe3df8a0721e7f5bfb230910b6e452998',
    'optional-prototype/report.json': '10216280d77410efbdf8ae77158df676e3ca4c14fc3834542a0b084b5dcd8813',
    'optional-prototype/final-hashes.json': 'b8bc8247920520f1b17833e1c34e78ecffd13fc372562102bfd009bd54af7a76',
}
SHADOW_FIELDS = ('cast_shadow', 'cast_dynamic_shadow', 'cast_static_shadow',
    'cast_volumetric_translucent_shadow', 'cast_contact_shadow', 'self_shadow_only',
    'cast_far_shadow', 'cast_inset_shadow', 'cast_cinematic_shadow', 'cast_hidden_shadow',
    'cast_shadow_as_two_sided')
BOOLEAN_POLICY = {name: False for name in (*SHADOW_FIELDS, 'can_ever_affect_navigation',
    'generate_overlap_events', 'affect_distance_field_lighting', 'affect_dynamic_indirect_lighting',
    'affect_indirect_lighting_while_hidden', 'visible_in_ray_tracing')}
ROLES = ('prototype_crag_rock', 'prototype_crag_dark_seam', 'prototype_crag_snow')

# Original world-space stone shading. This changes no vertices or silhouette.
GRAIN = '''float3 q=P/65.0;
float grain=(sin(dot(q,float3(1.37,.71,.43)))+sin(dot(q,float3(-.59,1.81,.83)))
    +sin(dot(q,float3(.31,-.67,2.47))))/6.0+.5;
'''
COLOR_SHADER = GRAIN + '''float strata=sin((P.z+.12*P.y-.07*P.x)/1700.0);
return Base*lerp(.78,1.12,grain)*lerp(.93,1.03,strata*.5+.5);'''
HEIGHT_SHADER = GRAIN + 'return grain*.7;'
NORMAL_SHADER = '''float3 n=normalize(N),px=ddx(P),py=ddy(P);
float3 r1=cross(py,n),r2=cross(n,px);
float determinant=dot(px,r1);
float3 gradient=sign(determinant)*(ddx(H)*r1+ddy(H)*r2);
return abs(determinant)>1e-8 ? normalize(abs(determinant)*n-gradient) : n;'''


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def protected_records(blueprint):
    keys = [key for key in blueprint if any(word in key.lower() for word in
        ('route', 'gate', 'objective', 'room', 'spawn', 'gameplay', 'stair', 'collision'))]
    return {key: digest(blueprint[key]) for key in sorted(keys)}


def checked_option(value):
    if value not in ('', OPTION):
        raise ValueError('Unknown private distant-crag option')
    return value == OPTION


def bind_backdrop(root, blueprint, revision):
    if not re.fullmatch('[a-f0-9]{12}', revision):
        raise ValueError('Explicit source revision is required')
    root = Path(root)
    blueprint_file = root / 'artifacts/unreal/aegis-citadel' / revision / 'blueprint.json'
    if json.loads(blueprint_file.read_text()) != blueprint:
        raise ValueError('Backdrop requires the exact source blueprint, including gameplay records')
    for name, wanted in FROZEN_INPUTS.items():
        if hashlib.sha256((root / REFERENCE / name).read_bytes()).hexdigest() != wanted:
            raise ValueError('Frozen original crag input changed: ' + name)
    report = json.loads((root / REFERENCE / 'optional-prototype/report.json').read_text())
    controls = json.loads((root / REFERENCE / 'measurements.json').read_text())['distantRidgeCompositionSeeds']
    mesh = json.loads((root / REFERENCE / 'optional-prototype/connected-crags.mesh.json').read_text())
    if (len(controls) != 8 or report['compositionSeeds'] != controls or mesh['collision'] is not False
            or len(mesh['indices']) != 4996*3 or tuple(mesh['materials']) != ROLES
            or report['triangles'] != 4996 or report['connectedComponents'] != 1
            or report['boundsCm'][0][1] != 70000):
        raise ValueError('The exact original connected crag prototype is required')
    spec = dict(schemaVersion=1, diagnosticOnly=True, option=OPTION, sourceRevision=revision,
        sourceHashes=copy.deepcopy(FROZEN_INPUTS), geometrySha256=report['meshSha256'],
        controls=copy.deepcopy(controls), controlValuesSha256=digest(controls),
        blueprintSha256=hashlib.sha256(blueprint_file.read_bytes()).hexdigest(),
        blueprintValuesSha256=digest(blueprint), protectedGameplayRecords=protected_records(blueprint),
        prototypeMaterialSpec=copy.deepcopy(report['spec']['materialSource']),
        nativeMaterialRecipe=dict(roles=list(ROLES), colorShader=COLOR_SHADER,
            heightShader=HEIGHT_SHADER, normalShader=NORMAL_SHADER, vertexDisplacement=False),
        nativeImporterSourceSha256=hashlib.sha256((root / 'unreal/AegisWar/Source/AegisWarEditorTools/Private/WarImportLibrary.cpp').read_bytes()).hexdigest(),
        nativeContractSourceSha256=hashlib.sha256((root / 'scripts/unreal/citadel_stage_contract.py').read_bytes()).hexdigest(),
        requiredNativePolicy=dict(collisionEnabled='NO_COLLISION', **BOOLEAN_POLICY),
        coordinates='final_unreal_world_cm', actorTransform=dict(location=[0,0,0],rotation=[0,0,0],scale=[1,1,1]),
        triangles=4996, boundsCm=copy.deepcopy(report['boundsCm']),
        nativeFlagsVerified=False, runtimeFlagsVerified=False, visualApproved=False,
        traversalApproved=False, gameplayApproved=False, releaseAcceptance=False)
    return spec, mesh


def checked_native_policy(collision_enabled, no_collision, values):
    if collision_enabled != no_collision:
        raise ValueError('Native crag component must have NoCollision')
    if set(values) != set(BOOLEAN_POLICY) or any(values[name] is not False for name in BOOLEAN_POLICY):
        raise ValueError('Native crag navigation, overlap, lighting and every shadow flag must be false')
    return dict(collisionEnabled=str(collision_enabled), properties=dict(values))


def owned_destination(destination, signature):
    if (not re.fullmatch('[a-f0-9]{64}', signature)
            or destination != '/Game/WorldRebuild/AegisCitadel_' + signature[:12]):
        raise ValueError('Backdrop writes require the exact fresh private study destination')
    return destination


def checked_retained_collision(expected, actual):
    if expected != actual:
        raise ValueError('Backdrop assembly changed retained scenery collision, transforms or shadow state')
    return digest(actual)


def collision_snapshot(unreal, rows):
    """Read retained primitive state without modifying collision or authored actors."""
    from world_actor_state import transform
    result = {}
    for actor in rows:
        components = {}
        for component in actor.get_components_by_class(unreal.PrimitiveComponent):
            if unreal.WarNpcEquipmentLibrary.is_generated_attachment(component):
                continue
            components[component.get_name()] = dict(klass=component.get_class().get_name(),
                worldTransform=transform(component.get_world_transform()),
                relativeTransform=transform(component.get_relative_transform()),
                collisionEnabled=str(component.get_collision_enabled()),
                collisionProfile=str(component.get_collision_profile_name()),
                properties={name:component.get_editor_property(name) for name in BOOLEAN_POLICY})
        result[actor.get_name()] = dict(actorTransform=transform(actor.get_actor_transform()), components=components)
    return result


def read_component_policy(unreal, component):
    if str(component.get_collision_profile_name()) != 'NoCollision' or component.get_editor_property('use_default_collision') is not False:
        raise ValueError('Backdrop must override the mesh default with its persistent NoCollision profile')
    result = checked_native_policy(component.get_collision_enabled(), unreal.CollisionEnabled.NO_COLLISION,
        {name:component.get_editor_property(name) for name in BOOLEAN_POLICY})
    return dict(result, collisionProfile='NoCollision', useDefaultCollision=False)


def configure_component_policy(unreal, component):
    # StaticMeshComponent's explicit profile setter disables bUseDefaultCollision;
    # SetCollisionEnabled alone is overwritten from the mesh during PostLoad.
    component.set_collision_profile_name('NoCollision')
    component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    for name, value in BOOLEAN_POLICY.items():
        component.set_editor_property(name, value)


def _materials(unreal, destination, spec, record):
    from citadel_stage_contract import lighting_readback
    assets, lib = unreal.EditorAssetLibrary, unreal.MaterialEditingLibrary
    materials, readbacks = [], []
    for role in ROLES:
        settings = spec['prototypeMaterialSpec'][role]
        name = 'M_DistantCrag_' + role.removeprefix('prototype_crag_')
        path = destination + '/Materials/' + name
        if assets.does_asset_exist(path):
            raise RuntimeError('Preserve an existing private crag material')
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, destination+'/Materials',
            unreal.Material, unreal.MaterialFactoryNew())
        if not material:
            raise RuntimeError('Cannot create original private crag material')
        record(path)
        requested = dict(material_domain=unreal.MaterialDomain.MD_SURFACE,
            blend_mode=unreal.BlendMode.BLEND_OPAQUE, shading_model=unreal.MaterialShadingModel.MSM_DEFAULT_LIT,
            two_sided=False, cast_dynamic_shadow_as_masked=False, cast_ray_traced_shadows=False)
        material_policy_readback = {}
        for key, value in requested.items():
            material.set_editor_property(key, value)
            actual = material.get_editor_property(key)
            if actual != value:
                raise RuntimeError('Native crag material policy changed: ' + key)
            material_policy_readback[key] = lighting_readback(actual,value) if isinstance(value,bool) else str(actual)
        base = lib.create_material_expression(material, unreal.MaterialExpressionConstant3Vector)
        base.constant = unreal.LinearColor(r=settings['baseColorLinear'][0],g=settings['baseColorLinear'][1],
                                          b=settings['baseColorLinear'][2],a=1)
        actual_color = lighting_readback(base.constant, dict(kind='linear_color', value=[*settings['baseColorLinear'],1]))
        targets = [(base, unreal.MaterialProperty.MP_BASE_COLOR)]
        actual_scalars = {}
        for key, prop in (('roughness', unreal.MaterialProperty.MP_ROUGHNESS),('metallic', unreal.MaterialProperty.MP_METALLIC)):
            node = lib.create_material_expression(material, unreal.MaterialExpressionConstant)
            node.r = settings[key]
            actual_scalars[key] = lighting_readback(node.r, settings[key])
            targets.append((node, prop))
        shader_readbacks = {}
        if role == 'prototype_crag_rock':
            position = lib.create_material_expression(material, unreal.MaterialExpressionWorldPosition)
            vertex_normal = lib.create_material_expression(material, unreal.MaterialExpressionVertexNormalWS)
            def custom(label, code, kind, inputs):
                node = lib.create_material_expression(material, unreal.MaterialExpressionCustom)
                node.set_editor_property('description', label)
                node.set_editor_property('output_type', kind)
                entries = []
                for pin in inputs:
                    entry = unreal.CustomInput();entry.set_editor_property('input_name', pin);entries.append(entry)
                node.set_editor_property('inputs', entries);node.set_editor_property('code', code)
                if node.get_editor_property('code') != code:
                    raise RuntimeError('Original crag shader did not retain its bound source')
                shader_readbacks[label] = dict(code=node.get_editor_property('code'),
                    inputs=[str(entry.get_editor_property('input_name')) for entry in node.get_editor_property('inputs')])
                if shader_readbacks[label]['inputs'] != list(inputs):
                    raise RuntimeError('Original crag shader input identities changed')
                return node
            color = custom('Original connected crag stone', COLOR_SHADER, unreal.CustomMaterialOutputType.CMOT_FLOAT3, ('P','Base'))
            height = custom('Original crag shallow grain', HEIGHT_SHADER, unreal.CustomMaterialOutputType.CMOT_FLOAT1, ('P',))
            normal = custom('Original crag world-space bump', NORMAL_SHADER, unreal.CustomMaterialOutputType.CMOT_FLOAT3, ('P','N','H'))
            for source, target, pin in ((position,color,'P'),(base,color,'Base'),(position,height,'P'),
                                       (position,normal,'P'),(vertex_normal,normal,'N'),(height,normal,'H')):
                if not lib.connect_material_expressions(source,'',target,pin):
                    raise RuntimeError('Original crag shader graph is disconnected')
            targets[0] = (color, unreal.MaterialProperty.MP_BASE_COLOR)
            targets.append((normal, unreal.MaterialProperty.MP_NORMAL))
            material.set_editor_property('tangent_space_normal', False)
            lighting_readback(material.get_editor_property('tangent_space_normal'), False)
        for node, prop in targets:
            if not lib.connect_material_property(node,'',prop) or lib.get_material_property_input_node(material,prop) != node:
                raise RuntimeError('Original crag material property is disconnected')
        if lib.get_material_property_input_node(material, unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET):
            raise RuntimeError('Backdrop material must not displace the bound geometry')
        errors = lib.recompile_material(material)
        if errors:
            raise RuntimeError('Original crag material compilation failed: ' + str(errors))
        if not assets.save_loaded_asset(material, only_if_is_dirty=False):
            raise RuntimeError('Cannot save fresh private crag material')
        materials.append(material)
        readbacks.append(dict(role=role, material=material.get_path_name(), baseColorLinear=actual_color,
            **actual_scalars, shaderReadbacks=shader_readbacks, compileErrors=list(errors), nativePolicyReadback=material_policy_readback,
            vertexDisplacement=False, nativePixelReviewRequired=True, visualApproved=False))
    return materials, readbacks


def stage_backdrop(unreal, root, destination, signature, binding, mesh, record, duplicate, load, own, save):
    """Only fresh owned mesh/material/empty-source/copied-layer packages may change."""
    from citadel_stage_contract import checked_render_audit
    owned_destination(destination, signature)
    assets = unreal.EditorAssetLibrary
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    materials, material_readbacks = _materials(unreal, destination, binding, record)
    mesh_path = destination + '/Meshes/SM_DistantCrags'
    if assets.does_asset_exist(mesh_path):
        raise RuntimeError('Preserve an existing private crag mesh')
    unit_normals = [[c/math.sqrt(sum(v*v for v in normal)) for c in normal] for normal in mesh['normals']]
    native = unreal.WarImportLibrary.create_composite_world_surface('AegisCitadel_'+signature[:12],
        'SM_DistantCrags', [unreal.Vector(*p) for p in mesh['positions']], mesh['indices'],
        [unreal.Vector(*n) for n in unit_normals], [unreal.Vector2D(*uv) for uv in mesh['uvs']], [],
        mesh['triangleMaterials'], materials, False)
    if not native:
        raise RuntimeError('Cannot construct the original owned crag mesh')
    record(mesh_path)
    if not unreal.WarImportLibrary.configure_citadel_surface_lods(native):
        raise RuntimeError('Cannot build the private crag render LODs')
    render_audit = json.loads(unreal.WarImportLibrary.describe_static_mesh_render_data(native))
    checked_render_audit(render_audit, native.get_path_name())
    if native.get_num_triangles(0) != 4996 or len(native.get_editor_property('static_materials')) != 3:
        raise RuntimeError('Native crag geometry or original material slots changed')
    slot_paths = [native.get_material(i).get_path_name() for i in range(3)]
    if slot_paths != [m.get_path_name() for m in materials]:
        raise RuntimeError('Native crag material order changed')
    if not assets.save_loaded_asset(native, only_if_is_dirty=False):
        raise RuntimeError('Cannot save the owned original crag mesh')
    source_layer = destination + '/Layers/DistantCrags_Source'
    layer = destination + '/Layers/DistantCrags'
    if assets.does_asset_exist(source_layer) or assets.does_asset_exist(layer) or not levels.new_level(source_layer):
        raise RuntimeError('Cannot create a fresh private backdrop source layer')
    record(source_layer)
    # Only fresh template PlayerStarts may be removed; canonical scene actors are never selected.
    for actor in own(source_layer):
        if isinstance(actor, unreal.PlayerStart):
            if not actors.destroy_actor(actor):
                raise RuntimeError('Cannot remove fresh backdrop template gameplay')
        elif actor.get_class().get_name() not in ('WorldSettings','LevelScriptActor','Brush'):
            raise RuntimeError('Unexpected actor in the fresh empty backdrop template')
    save(source_layer)
    duplicate(source_layer, layer)
    load(layer)
    if not levels.set_current_level_by_name(layer.rsplit('/',1)[1]):
        raise RuntimeError('Cannot select the exact copied backdrop layer')
    actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector())
    if not actor or actor.get_outer().get_path_name().split('.')[0] != layer:
        raise RuntimeError('Backdrop actor did not enter its owned copied layer')
    actor.set_actor_label('Bastion original distant crags')
    actor.tags = ['WarCitadelPrivateBackdrop', 'WarModelSha256_'+binding['geometrySha256']]
    actor.set_actor_rotation(unreal.Rotator(),False);actor.set_actor_scale3d(unreal.Vector(1,1,1))
    component = actor.static_mesh_component
    configure_component_policy(unreal, component)
    component.set_static_mesh(native)
    component.set_visibility(True);component.set_hidden_in_game(False);actor.set_actor_hidden_in_game(False)
    actual_policy = read_component_policy(unreal, component)
    save(layer)
    load(layer)
    matching = [a for a in own(layer) if 'WarCitadelPrivateBackdrop' in [str(tag) for tag in a.tags]]
    if len(matching) != 1:
        raise RuntimeError('Saved backdrop actor identity is missing or ambiguous')
    saved = matching[0]
    saved_policy = read_component_policy(unreal, saved.static_mesh_component)
    if actual_policy != saved_policy or saved.static_mesh_component.static_mesh.get_path_name() != native.get_path_name():
        raise RuntimeError('Saved backdrop policy or mesh differs from native readback')
    location, rotation, scale = saved.get_actor_location(), saved.get_actor_rotation(), saved.get_actor_scale3d()
    actual_transform = dict(location=[location.x,location.y,location.z],rotation=[rotation.pitch,rotation.yaw,rotation.roll],scale=[scale.x,scale.y,scale.z])
    if actual_transform != binding['actorTransform']:
        raise RuntimeError('Backdrop transform changed final world-centimetre source placement')
    visibility = dict(actorHidden=saved.get_editor_property('hidden'), componentVisible=saved.static_mesh_component.is_visible(),
        componentHiddenInGame=saved.static_mesh_component.get_editor_property('hidden_in_game'))
    if visibility != dict(actorHidden=False, componentVisible=True, componentHiddenInGame=False):
        raise RuntimeError('Saved backdrop must retain actual visible raster components')
    return layer, dict(binding=copy.deepcopy(binding), sourceLayer=source_layer, layer=layer,
        actor=saved.get_path_name(), component=saved.static_mesh_component.get_path_name(), mesh=native.get_path_name(),
        materialReadbacks=material_readbacks, nativeMaterialSlots=slot_paths, renderAudit=render_audit,
        lodTriangles=[native.get_num_triangles(i) for i in range(native.get_num_lods())],
        componentReadback=saved_policy, actorTransform=actual_transform, visibilityReadback=visibility,
        nativeEditorFlagsReadBack=True, runtimeFlagsVerified=False, rendererStateVerified=False,
        visualApproved=False, traversalApproved=False, gameplayApproved=False, releaseAcceptance=False)
