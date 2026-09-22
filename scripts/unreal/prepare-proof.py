"""Create a reproducible development map from actual imported repository assets."""
import importlib.util
import json
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("war_imports", Path(__file__).with_name("import-models.py"))
imports = importlib.util.module_from_spec(spec)
spec.loader.exec_module(imports)
require = imports.require
DESTINATION = "/Game/MigrationProof"
OWNER = "WarMigrationProof"


def own(asset):
    unreal.EditorAssetLibrary.set_metadata_tag(asset, OWNER, "schema-1")
    return asset


def existing_asset(path):
    asset = unreal.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else None
    if asset:
        require(unreal.EditorAssetLibrary.get_metadata_tag(asset, OWNER) == "schema-1",
                f"Refusing to overwrite an unowned proof asset: {path}")
    return asset


def imported(profile):
    context = imports.validate_inputs(profile)
    receipt = imports.load_json(context["directory"] / "editor-import.json")
    require(receipt["importSucceeded"] and receipt["sourceSha256"] == context["conversion"]["sourceSha256"]
            and receipt["conversionSha256"] == context["conversionSha256"], "Stale Unreal import evidence")
    return receipt


def visual(profile, race, class_id, realm, body="m", source_profile=None):
    source_profile = source_profile or profile
    receipt = imported(source_profile)
    context = imports.validate_inputs(source_profile)
    registry = imports.load_json(ROOT / "public/assets/models/asset-index.json")
    require(registry["characterProfiles"][source_profile]["bodyVariant"] == body, "Source body variant does not match playable identity")
    name = "Visual_" + profile
    asset = existing_asset(DESTINATION + "/" + name)
    if not asset:
        factory = unreal.DataAssetFactory()
        factory.set_editor_property("data_asset_class", unreal.WarCharacterVisualDefinition)
        asset = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, DESTINATION, unreal.WarCharacterVisualDefinition, factory)
    require(asset is not None, "Could not create a native visual DataAsset")
    clips = {entry["sourceClipName"]: entry["path"] for entry in receipt["animations"]}
    properties = {
        "profile_key": profile, "source_profile_key": source_profile, "race_id": race, "class_id": class_id, "body_variant": body, "realm": realm,
        "source_model": context["conversion"]["source"], "source_sha256": receipt["sourceSha256"],
        "complex_authored_model": True, "skeletal_mesh": unreal.load_asset(receipt["meshes"][0]["path"]),
        "idle_animation": unreal.load_asset(clips["idle"]),
        "imported_animations": {name: unreal.load_asset(asset_path) for name, asset_path in clips.items()},
        "mesh_transform": unreal.Transform(location=unreal.Vector(0, 0, -96), rotation=unreal.Rotator(yaw=-90)),
    }
    for key, value in properties.items():
        asset.set_editor_property(key, value)
    own(asset)
    unreal.EditorAssetLibrary.set_metadata_tag(asset, "ArtApproval", "pending")
    unreal.EditorAssetLibrary.set_metadata_tag(asset, "DevelopmentOnly", "true")
    return asset


def terrain_material():
    name = "TerrainMaterial"
    material = existing_asset(DESTINATION + "/" + name)
    if material:
        return material
    material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, DESTINATION, unreal.Material, unreal.MaterialFactoryNew())
    own(material)
    library = unreal.MaterialEditingLibrary
    color = library.create_material_expression(material, unreal.MaterialExpressionConstant3Vector)
    color.set_editor_property("constant", unreal.LinearColor(0.11, 0.16, 0.07, 1))
    require(library.connect_material_property(color, "", unreal.MaterialProperty.MP_BASE_COLOR), "Terrain color pin failed")
    roughness = library.create_material_expression(material, unreal.MaterialExpressionConstant)
    roughness.set_editor_property("r", 0.9)
    require(library.connect_material_property(roughness, "", unreal.MaterialProperty.MP_ROUGHNESS), "Terrain roughness pin failed")
    library.recompile_material(material)
    return material


def main():
    require(Path(unreal.Paths.project_dir()).resolve() == imports.PROJECT.resolve(), "Wrong Unreal project")
    proof_receipt = ROOT / "artifacts/unreal/proof-map.json"
    proof_receipt.unlink(missing_ok=True)
    table = imported("frontier_field_command_table")
    aegis = visual("civic_battle_prelate_m", "empire", "battle_prelate", unreal.WarRealm.AEGIS)
    riftbound = visual("mire_warbrute_m", "greenskin", "warbrute", unreal.WarRealm.RIFTBOUND)
    dispatch = visual("npc_aegis_mara_vell_brightfen_dispatch_officer", "empire", "questgiver", unreal.WarRealm.AEGIS,
                      body="f", source_profile="npc_frontier_sunmeadow_empire_herbalist")
    officer = visual("npc_aegis_ari_vell_brightfen_field_officer", "empire", "questgiver", unreal.WarRealm.AEGIS,
                     body="f", source_profile="npc_frontier_sunmeadow_empire_herbalist")
    for npc_visual in (dispatch, officer):
        npc_visual.set_editor_property("mesh_transform", unreal.Transform(rotation=unreal.Rotator(yaw=-90)))
    terrain = unreal.WarImportLibrary.create_proof_terrain(terrain_material())
    require(terrain is not None, "Terrain generation failed")
    own(terrain)
    subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    map_path = DESTINATION + "/EngineProof"
    # Do not retain a Python reference to a World across load_level: Unreal must collect the old world.
    has_previous = existing_asset(map_path) is not None
    world = subsystem.load_level(map_path) if has_previous else subsystem.new_level(map_path)
    require(world, "Could not create the proof map")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    existing_actors = {actor.get_actor_label(): actor for actor in actors.get_all_level_actors()}

    def spawn(kind, name, position, rotation=None):
        actor = existing_actors.get(name)
        require(actor is None or isinstance(actor, kind), f"Proof actor class changed: {name}")
        if actor is None:
            actor = actors.spawn_actor_from_class(kind, unreal.Vector(*position), rotation or unreal.Rotator())
        else:
            actor.set_actor_location_and_rotation(unreal.Vector(*position), rotation or unreal.Rotator(), False, True)
        require(actor is not None, f"Could not spawn {name}")
        actor.set_actor_label(name)
        return actor

    ground = spawn(unreal.StaticMeshActor, "Development terrain (allowed terrain construction)", (0, 0, 0))
    ground.static_mesh_component.set_static_mesh(terrain)
    ground.static_mesh_component.set_collision_profile_name("BlockAll")
    for index, mesh in enumerate(table["meshes"]):
        name = f"Authored command table part {index}"
        kind = unreal.WarCraftingStation if index == 0 else unreal.StaticMeshActor
        old = existing_actors.get(name)
        if index == 0 and old is not None and not isinstance(old, unreal.WarCraftingStation):
            require(isinstance(old, unreal.StaticMeshActor)
                    and old.static_mesh_component.static_mesh.get_path_name() == mesh["path"],
                    "Refusing to replace an unrelated proof actor")
            require(actors.destroy_actor(old), "Could not upgrade the owned proof table to a station")
            del existing_actors[name]
        actor = spawn(kind, name, (250, 250, 0))
        actor.static_mesh_component.set_static_mesh(unreal.load_asset(mesh["path"]))
    spawn(unreal.PlayerStart, "Aegis safe start", (-100, 0, 100))
    npc_mappings = []
    for name, zone, npc_id, npc_visual, position in (
        ("Mara Vell quest interaction proof", "aegis_capital", "quest-1", dispatch, (-350, 0, 0)),
        ("Ari Vell quest turn-in proof", "brightfen_approach", "brightfen_approach_dispatch", officer, (650, 0, 0)),
    ):
        npc = spawn(unreal.WarQuestNpc, name, position)
        npc.set_editor_property("zone_id", zone)
        npc.set_editor_property("npc_id", npc_id)
        npc.set_editor_property("visual", npc_visual)
        npc_mesh = npc.get_editor_property("mesh")
        npc_mesh.set_skeletal_mesh_asset(unreal.load_asset(imported("npc_frontier_sunmeadow_empire_herbalist")["meshes"][0]["path"]))
        npc_mesh.set_relative_transform(npc_visual.mesh_transform, False, True)
        npc_mappings.append({"zoneId": zone, "npcId": npc_id,
            "profileKey": str(npc_visual.get_editor_property("profile_key")),
            "sourceProfileKey": "npc_frontier_sunmeadow_empire_herbalist",
            "nativeVisual": npc_visual.get_path_name(), "developmentOnly": True, "artApproved": False})
    spawn(unreal.PlayerStart, "Riftbound safe start", (100, 0, 100), unreal.Rotator(yaw=180))
    sun = spawn(unreal.DirectionalLight, "Sun", (0, 0, 700), unreal.Rotator(pitch=-45, yaw=-35))
    sun.light_component.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
    sun.light_component.set_editor_property("intensity", 3.0)
    sky = spawn(unreal.SkyLight, "Sky fill", (0, 0, 600))
    sky.light_component.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
    sky.light_component.set_editor_property("intensity", 1.0)
    spawn(unreal.SkyAtmosphere, "Atmosphere", (0, 0, 0))
    editor_world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    own(editor_world)
    require(subsystem.save_current_level(), "Proof map save failed")
    require(unreal.EditorAssetLibrary.save_directory(DESTINATION, only_if_is_dirty=False, recursive=True), "Proof assets save failed")
    proof_receipt.write_text(json.dumps({"schemaVersion": 1, "map": map_path,
        "aegisVisual": aegis.get_path_name(), "riftboundVisual": riftbound.get_path_name(),
        "terrain": terrain.get_path_name(), "authoredTableMeshes": len(table["meshes"]),
        "questNpcMappings": npc_mappings,
        "visualApproval": False, "networkProof": False, "developmentOnly": True}, indent=2) + "\n")
    unreal.log("WAR_PROOF_MAP_CREATED=" + map_path)


if __name__ == "__main__":
    main()
