"""Build an authored-ground workbench, not a completed capital or GM editor."""
import importlib.util
import json
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
DESTINATION = "/Game/Capitals/aegis_capital"
OWNER = "WarCapitalWorkbench"
spec = importlib.util.spec_from_file_location("war_imports", Path(__file__).with_name("import-models.py"))
imports = importlib.util.module_from_spec(spec)
spec.loader.exec_module(imports)
require = imports.require


def owned_asset(path):
    asset = unreal.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else None
    if asset:
        require(unreal.EditorAssetLibrary.get_metadata_tag(asset, OWNER) == "schema-1", f"Refusing to replace unowned workbench asset: {path}")
    return asset


def own(asset):
    unreal.EditorAssetLibrary.set_metadata_tag(asset, OWNER, "schema-1")
    return asset


def material(kind):
    name = "TerrainMaterial_" + kind
    result = owned_asset(DESTINATION + "/" + name)
    if result:
        if kind == "ground":
            texture = owned_asset(DESTINATION + "/Textures/GroundFlagstone")
            expected = imports.sha256(ROOT / "public/assets/textures/aegis_city/flagstone_baseColor.png")
            require(texture is not None and unreal.EditorAssetLibrary.get_metadata_tag(texture, "SourceSha256") == expected,
                    "Ground texture changed; explicitly reimport the owned material and texture before rebuilding")
        return result
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    result = tools.create_asset(name, DESTINATION, unreal.Material, unreal.MaterialFactoryNew())
    require(result is not None, "Could not create terrain material")
    own(result)
    library = unreal.MaterialEditingLibrary
    if kind == "ground":
        source = ROOT / "public/assets/textures/aegis_city/flagstone_baseColor.png"
        expected = imports.sha256(source)
        task = imports.task_for(unreal, source, DESTINATION + "/Textures")
        task.set_editor_property("destination_name", "GroundFlagstone")
        owned_asset(DESTINATION + "/Textures/GroundFlagstone")
        tools.import_asset_tasks([task])
        objects = task.get_objects()
        require(len(objects) == 1 and isinstance(objects[0], unreal.Texture2D), "Ground texture import failed")
        texture = own(objects[0])
        texture.set_editor_property("srgb", True)
        unreal.EditorAssetLibrary.set_metadata_tag(texture, "SourceSha256", expected)
        require(imports.sha256(source) == expected, "Ground texture changed during import")
        color = library.create_material_expression(result, unreal.MaterialExpressionTextureSample)
        color.set_editor_property("texture", texture)
        color.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
        require(library.connect_material_property(color, "RGB", unreal.MaterialProperty.MP_BASE_COLOR), "Ground color pin failed")
    else:
        color = library.create_material_expression(result, unreal.MaterialExpressionConstant3Vector)
        color.set_editor_property("constant", unreal.LinearColor(0.137, 0.263, 0.267, 1) if kind == "water" else unreal.LinearColor(0.141, 0.169, 0.149, 1))
        require(library.connect_material_property(color, "", unreal.MaterialProperty.MP_BASE_COLOR), "Canal color pin failed")
    roughness = library.create_material_expression(result, unreal.MaterialExpressionConstant)
    roughness.set_editor_property("r", 0.28 if kind == "water" else 0.9)
    require(library.connect_material_property(roughness, "", unreal.MaterialProperty.MP_ROUGHNESS), "Roughness pin failed")
    if kind == "water":
        result.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
        opacity = library.create_material_expression(result, unreal.MaterialExpressionConstant)
        opacity.set_editor_property("r", 0.9)
        require(library.connect_material_property(opacity, "", unreal.MaterialProperty.MP_OPACITY), "Water opacity pin failed")
    library.recompile_material(result)
    return result


def main():
    require(Path(unreal.Paths.project_dir()).resolve() == imports.PROJECT.resolve(), "Wrong Unreal project")
    directory = ROOT / "artifacts/unreal/capitals/aegis_capital"
    receipt_path = directory / "terrain-import.json"
    receipt_path.unlink(missing_ok=True)
    data = imports.load_json(directory / "terrain.json")
    require(data["schemaVersion"] == 1 and data["zoneId"] == "aegis_capital" and data["units"] == "centimeters", "Invalid terrain input")
    source = imports.relative_path(data["source"], ROOT / "public/assets/maps")
    imports.verified_file(source, data["sourceSha256"])
    require([surface["kind"] for surface in data["surfaces"]] == ["ground", "water", "bed"], "Missing capital surface")
    terrain_hash = imports.sha256(directory / "terrain.json")
    meshes = []
    for surface in data["surfaces"]:
        mesh = unreal.WarImportLibrary.create_capital_surface(data["zoneId"], surface["kind"],
            [unreal.Vector(*value) for value in surface["positions"]], surface["indices"],
            [unreal.Vector(*value) for value in surface["normals"]],
            [unreal.Vector2D(*value) for value in surface["uvs"]], material(surface["kind"]), surface["collision"])
        require(mesh is not None, f"Native terrain construction failed: {surface['kind']}")
        meshes.append((surface, mesh))
    level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    map_path = DESTINATION + "/AegisCapital_Workbench"
    has_previous = owned_asset(map_path) is not None
    require(level.load_level(map_path) if has_previous else level.new_level(map_path), "Could not load/create capital workbench")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    existing = {actor.get_actor_label(): actor for actor in actors.get_all_level_actors()}

    def spawn(kind, name, position, rotation=None):
        actor = existing.get(name)
        require(actor is None or (isinstance(actor, kind) and "WarCapitalWorkbench" in [str(tag) for tag in actor.tags]), "Refusing to overwrite an unrelated actor")
        if actor is None:
            actor = actors.spawn_actor_from_class(kind, unreal.Vector(*position), rotation or unreal.Rotator())
        else:
            actor.set_actor_location_and_rotation(unreal.Vector(*position), rotation or unreal.Rotator(), False, True)
        require(actor is not None, f"Could not create {name}")
        actor.set_actor_label(name)
        actor.set_editor_property("tags", ["WarCapitalWorkbench"])
        return actor

    records = []
    for surface, mesh in meshes:
        actor = spawn(unreal.StaticMeshActor, "Authored Aegis " + surface["kind"], (0, 0, 0))
        actor.static_mesh_component.set_static_mesh(mesh)
        actor.static_mesh_component.set_collision_profile_name("BlockAll" if surface["collision"] else "NoCollision")
        records.append({"kind": surface["kind"], "mesh": mesh.get_path_name(), "triangles": len(surface["indices"]) // 3, "collision": surface["collision"]})
    map_data = imports.load_json(source)
    start = map_data["spawnPoint"]
    spawn(unreal.PlayerStart, "Aegis authored arrival", (start["z"] * 100, start["x"] * 100, start["y"] * 100 + 100))
    light = spawn(unreal.DirectionalLight, "Aegis workbench sun", (0, 0, 20000), unreal.Rotator(pitch=-45, yaw=-35))
    light.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    light.light_component.set_editor_property("intensity", 50000.0)
    sky = spawn(unreal.SkyLight, "Aegis workbench sky", (0, 0, 15000))
    sky.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    sky.light_component.set_real_time_capture(True)
    spawn(unreal.SkyAtmosphere, "Aegis atmosphere", (0, 0, 0))
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    own(world)
    unreal.WarImportLibrary.prepare_preview_frame(None)
    imports.verified_file(source, data["sourceSha256"])
    require(imports.sha256(directory / "terrain.json") == terrain_hash, "Terrain input changed during construction")
    require(unreal.EditorAssetLibrary.save_directory(DESTINATION, only_if_is_dirty=False, recursive=True), "Could not save terrain packages")
    require(level.save_current_level(), "Could not save workbench map")
    receipt_path.write_text(json.dumps({"schemaVersion": 1, "zoneId": data["zoneId"], "sourceSha256": data["sourceSha256"],
        "terrainInputSha256": terrain_hash, "map": map_path, "engineVersion": unreal.SystemLibrary.get_engine_version(),
        "surfaces": records, "capitalReady": False, "gmBuilderReady": False,
        "limitations": ["Terrain construction only; city models, NPCs, encounters, travel and runtime GM tools are incomplete.",
                        "Native collision and rendered traversal require separate acceptance."]}, indent=2) + "\n", encoding="utf-8")
    unreal.log("WAR_CAPITAL_TERRAIN_CREATED=" + str(receipt_path))


if __name__ == "__main__":
    main()
