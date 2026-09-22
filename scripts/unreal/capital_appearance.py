"""Build an isolated, editable city appearance preview without changing the working map."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE_MAP = '/Game/Capitals/crownward/AegisCapital_Workbench'
PALETTES = {
    'weathered_stone': (0.42, 0.43, 0.44),
    'charcoal': (0.26, 0.28, 0.30),
    'muted_rust': (0.40, 0.33, 0.29),
    'moss_stone': (0.33, 0.36, 0.32),
    'cold_limestone': (0.48, 0.49, 0.50),
}


def palette_for(identity):
    """Stable variation survives regenerating the layout or reordering actors."""
    return tuple(PALETTES)[int(hashlib.sha256(identity.encode()).hexdigest()[:8], 16) % len(PALETTES)]


def apply_appearance(unreal, actors, destination):
    library = unreal.MaterialEditingLibrary
    assets = unreal.EditorAssetLibrary
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    cache = {}
    material_records = []

    def tint(source, name, color):
        key = (source.get_path_name(), name)
        if key in cache:
            return cache[key]
        suffix = hashlib.sha256(source.get_path_name().encode()).hexdigest()[:8]
        asset_name = 'MI_' + name + '_' + suffix
        material = tools.create_asset(asset_name, destination, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        if not material:
            raise RuntimeError('Appearance destination must be new; preserve existing material edits')
        library.set_material_instance_parent(material, source)
        # UE 5.8.2's setter returns false even on success; validate the actual readback.
        library.set_material_instance_vector_parameter_value(material, 'Base_Color_Tint', unreal.LinearColor(*color, 1))
        actual = library.get_material_instance_vector_parameter_value(material, 'Base_Color_Tint')
        if any(abs(a-b) > .00001 for a,b in zip((actual.r,actual.g,actual.b),color)):
            raise RuntimeError('Required material tint parameter was not applied')
        if not assets.save_loaded_asset(material, only_if_is_dirty=False):
            raise RuntimeError('Could not save appearance instance')
        cache[key] = material
        material_records.append({'source':source.get_path_name(), 'instance':material.get_path_name(), 'tint':color})
        return material

    def terrain_material(source, name, color):
        # Only the new private graph changes; the original textured granite is retained.
        target = destination + '/M_' + name
        material = assets.duplicate_asset(source.get_path_name(), target)
        if not isinstance(material, unreal.Material):
            raise RuntimeError('Terrain appearance requires the authored granite material')
        original = library.get_material_property_input_node(material, unreal.MaterialProperty.MP_BASE_COLOR)
        output = library.get_material_property_input_node_output_name(material, unreal.MaterialProperty.MP_BASE_COLOR)
        if not original:
            raise RuntimeError('Missing authored granite base-color connection')
        multiply = library.create_material_expression(material, unreal.MaterialExpressionMultiply)
        parameter = library.create_material_expression(material, unreal.MaterialExpressionVectorParameter)
        parameter.set_editor_property('parameter_name', 'Base_Color_Tint')
        parameter.set_editor_property('default_value', unreal.LinearColor(1,1,1,1))
        library.connect_material_expressions(original, output, multiply, 'A')
        library.connect_material_expressions(parameter, '', multiply, 'B')
        library.connect_material_property(multiply, '', unreal.MaterialProperty.MP_BASE_COLOR)
        library.recompile_material(material)
        if not assets.save_loaded_asset(material, only_if_is_dirty=False):
            raise RuntimeError('Could not save private terrain graph')
        return tint(material, name, color)

    all_actors = list(actors.get_all_level_actors())
    required = {'Aegis workbench sun', 'Aegis daylight exposure', 'Crownward original ground', 'Crownward authored mountain massif'}
    if not required.issubset({actor.get_actor_label() for actor in all_actors}):
        raise RuntimeError('Required authored city lighting or terrain is missing; preserve current edits')
    for actor in all_actors:
        if actor.get_actor_label() in ['Crownward original ground', 'Crownward authored mountain massif']:
            if not isinstance(actor, unreal.StaticMeshActor) or not isinstance(actor.static_mesh_component.get_material(0), unreal.Material):
                raise RuntimeError('Preserve customized terrain material; reconcile appearance before applying')
    terrain = {}
    changed = 0
    preserved_materials = set()
    for actor in all_actors:
        label = actor.get_actor_label()
        if label == 'Aegis workbench sun':
            actor.modify()
            actor.light_component.modify()
            actor.light_component.set_editor_property('forward_shading_priority', 1)
            actor.light_component.set_editor_property('intensity', 18000.0)
            actor.light_component.set_editor_property('use_temperature', True)
            actor.light_component.set_editor_property('temperature', 7800.0)
            actor.set_actor_rotation(unreal.Rotator(pitch=-38, yaw=-35), False)
        elif label == 'Aegis daylight exposure':
            actor.modify()
            settings = actor.get_editor_property('settings')
            settings.set_editor_property('override_auto_exposure_bias', True)
            settings.set_editor_property('auto_exposure_bias', 0.0)
            settings.set_editor_property('override_color_saturation', True)
            settings.set_editor_property('color_saturation', unreal.Vector4(0.65,0.65,0.65,1))
            actor.set_editor_property('settings', settings)
        if not isinstance(actor, unreal.StaticMeshActor):
            continue
        component = actor.static_mesh_component
        tags = [str(tag) for tag in actor.tags]
        if 'WarCrownward' in tags:
            actor.modify()
            component.modify()
            identity = next((tag for tag in tags if tag.startswith('WarWorldObject_')), label)
            palette = palette_for(identity) if 'house' in identity.lower() else 'cold_limestone'
            for index in range(component.get_num_materials()):
                source = component.get_material(index)
                if source and 'Base_Color_Tint' in [str(n) for n in library.get_vector_parameter_names(source)]:
                    component.set_material(index, tint(source, palette, PALETTES[palette]))
                    changed += 1
                elif source:
                    preserved_materials.add(source.get_path_name())
        elif label in ['Crownward original ground', 'Crownward authored mountain massif']:
            actor.modify()
            component.modify()
            name = 'Ground' if label.endswith('ground') else 'Mountain'
            color = (0.30,0.32,0.29) if name == 'Ground' else (0.37,0.40,0.44)
            if name not in terrain:
                terrain[name] = terrain_material(component.get_material(0), name, color)
            component.set_material(0, terrain[name])
    fill = actors.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0,0,20000), unreal.Rotator(pitch=-35,yaw=145))
    fill.set_actor_label('Crownward soft sky fill')
    fill.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    fill.light_component.set_editor_property('intensity', 9000.0)
    fill.light_component.set_editor_property('forward_shading_priority', 0)
    fill.light_component.set_editor_property('cast_shadows', False)
    fill.light_component.set_editor_property('atmosphere_sun_light', False)
    fill.light_component.set_editor_property('use_temperature', True)
    fill.light_component.set_editor_property('temperature', 8500.0)
    fog = actors.spawn_actor_from_class(unreal.ExponentialHeightFog, unreal.Vector(0,0,1000))
    fog.set_actor_label('Crownward cold distance haze')
    fog.component.set_fog_density(0.005)
    fog.component.set_fog_height_falloff(0.1)
    fog.component.set_start_distance(3500.0)
    fog.component.set_fog_max_opacity(0.45)
    fog.component.set_fog_inscattering_color(unreal.LinearColor(0.12,0.15,0.19,1))
    return {'materialSlotsChanged':changed, 'materials':material_records,
            'preservedMaterialsWithoutTintParameter':sorted(preserved_materials),
            'style':'gritty-dark-fantasy', 'sunLux':18000, 'sunTemperatureKelvin':7800,
            'exposureBias':0, 'softFillLux':9000, 'saturation':0.65,
            'fogDensity':0.005, 'fogStartCm':3500, 'fogMaxOpacity':0.45,
            'sourceTexturesPreserved':True, 'visualApproved':False}


def main():
    import datetime
    import unreal
    if Path(unreal.Paths.project_dir()).resolve() != (ROOT/'unreal/AegisWar').resolve():
        raise RuntimeError('Appearance preview belongs in the main AegisWar project')
    # Unique package names never overwrite the working map or a previous preview the owner edited.
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S_%f')
    destination = '/Game/Capitals/crownward/Appearance_' + stamp
    target = destination + '/AegisCapital_AppearancePreview'
    source_file = ROOT/'unreal/AegisWar/Content/Capitals/crownward/AegisCapital_Workbench.umap'
    before = hashlib.sha256(source_file.read_bytes()).hexdigest()
    if not unreal.EditorAssetLibrary.duplicate_asset(SOURCE_MAP, target):
        raise RuntimeError('Could not duplicate saved city for appearance preview')
    level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not level.load_level(target):
        raise RuntimeError('Could not open isolated appearance preview')
    receipt = apply_appearance(unreal, unreal.get_editor_subsystem(unreal.EditorActorSubsystem), destination)
    if not level.save_current_level():
        raise RuntimeError('Could not save appearance preview')
    after = hashlib.sha256(source_file.read_bytes()).hexdigest()
    if after != before:
        (ROOT/'artifacts/unreal/licensed-kits/capital-appearance-concurrent-save.json').write_text(json.dumps({
            **receipt, 'map':target, 'sourceMap':SOURCE_MAP, 'sourceHashBefore':before,
            'sourceHashAfter':after, 'concurrentSourceChange':True,
            'note':'Preview is a saved snapshot; preserve the owner working map and reconcile before applying.'}, indent=2)+'\n')
        raise RuntimeError('Working city changed concurrently; preview saved separately, original receipt retained')
    (ROOT/'artifacts/unreal/licensed-kits/capital-appearance-preview.json').write_text(json.dumps({
        **receipt, 'map':target, 'sourceMap':SOURCE_MAP, 'sourceMapSha256':before,
        'workingMapUnchanged':True}, indent=2)+'\n')
    unreal.log('WAR_CAPITAL_APPEARANCE_PREVIEW='+target)


if __name__ == '__main__':
    main()
