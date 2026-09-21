"""Assemble original city terrain and existing gameplay actors in the main game."""
import hashlib
import json
import math
from pathlib import Path
import unreal
from capital_geography import ROOT, source_map, point, road_surface, mountain_surface
from capital_resources import resource_bindings, PROFILE


def build_terrain(actors):
    def spawn(mesh, label, position=(0,0,0), collision=True):
        if not mesh:
            raise RuntimeError("Required capital terrain is unavailable: " + label)
        actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*position))
        actor.set_actor_label(label)
        actor.tags = ["WarCrownwardTerrain"]
        actor.static_mesh_component.set_static_mesh(mesh)
        actor.static_mesh_component.set_collision_profile_name("BlockAll" if collision else "NoCollision")
        return actor
    original = json.loads((ROOT / "artifacts/unreal/capitals/aegis_capital/terrain-import.json").read_text())
    source = ROOT / "public/assets/maps/aegis_capital.json"
    if hashlib.sha256(source.read_bytes()).hexdigest() != original["sourceSha256"]:
        raise RuntimeError("Reimport changed source terrain before rebuilding the city")
    ground_actor = None
    for source_surface in original["surfaces"]:
        actor = spawn(unreal.load_asset(source_surface["mesh"]), "Crownward original " + source_surface["kind"], collision=source_surface["collision"])
        if source_surface["kind"] == "ground":
            ground_actor = actor

    def surface(kind, data, material):
        mesh = unreal.WarImportLibrary.create_capital_surface("crownward",kind,
            [unreal.Vector(*p) for p in data["positions"]],data["indices"],
            [unreal.Vector(*p) for p in data["normals"]],[unreal.Vector2D(*p) for p in data["uvs"]],material,True)
        if not mesh or not unreal.EditorAssetLibrary.save_loaded_asset(mesh, only_if_is_dirty=False):
            raise RuntimeError("Capital surface import failed: " + kind)
        return mesh
    roads_material = unreal.load_asset("/Game/Capitals/aegis_capital/TerrainMaterial_ground")
    spawn(surface("roads", road_surface(), roads_material), "Crownward source road network")
    mountain, doc, images = mountain_surface()
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    path = "/Game/Capitals/crownward/MountainGranite"
    material = unreal.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else None
    if material and unreal.EditorAssetLibrary.get_metadata_tag(material,"WarMountainSource") != "aegis_granite":
        raise RuntimeError("Refusing to change unowned granite material")
    if not material:
        material = tools.create_asset("MountainGranite", "/Game/Capitals/crownward", unreal.Material, unreal.MaterialFactoryNew())
        unreal.EditorAssetLibrary.set_metadata_tag(material,"WarMountainSource","aegis_granite")
        library = unreal.MaterialEditingLibrary
        source_material = doc["materials"][0]
        textures = [(source_material["pbrMetallicRoughness"]["baseColorTexture"]["index"],"BaseColor",unreal.MaterialProperty.MP_BASE_COLOR,True),
                    (source_material["normalTexture"]["index"],"Normal",unreal.MaterialProperty.MP_NORMAL,False)]
        for index, name, pin, srgb in textures:
            mime, data = images[doc["textures"][index]["source"]]
            if mime != "image/png":
                raise RuntimeError("Unreviewed mountain texture format")
            file = ROOT / "artifacts/unreal/licensed-kits" / ("mountain-"+name+".png")
            file.write_bytes(data)
            task = unreal.AssetImportTask()
            task.filename=str(file); task.destination_path="/Game/Capitals/crownward/Textures"
            task.destination_name="Mountain"+name; task.automated=True; task.save=True
            tools.import_asset_tasks([task]); texture = task.get_objects()[0]
            texture.set_editor_property("srgb",srgb)
            if not srgb:
                texture.set_editor_property("compression_settings",unreal.TextureCompressionSettings.TC_NORMALMAP)
            expression = library.create_material_expression(material,unreal.MaterialExpressionTextureSample)
            expression.set_editor_property("texture",texture)
            expression.set_editor_property("sampler_type",unreal.MaterialSamplerType.SAMPLERTYPE_COLOR if srgb else unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
            library.connect_material_property(expression,"RGB",pin)
            unreal.EditorAssetLibrary.save_loaded_asset(texture,only_if_is_dirty=False)
        roughness = library.create_material_expression(material,unreal.MaterialExpressionConstant)
        roughness.set_editor_property("r",.9)
        library.connect_material_property(roughness,"",unreal.MaterialProperty.MP_ROUGHNESS)
        material.set_editor_property("two_sided",True)
        library.recompile_material(material)
        unreal.EditorAssetLibrary.save_loaded_asset(material,only_if_is_dirty=False)
    ground_actor.static_mesh_component.set_material(0,material)
    mountain_prop = next(p for p in source_map()["props"] if p["id"]=="aegis_mountain_massif")
    # The source massif's base is ground level, not the 42m citadel terrace.
    spawn(surface("mountain",mountain,material),"Crownward authored mountain massif",
          (mountain_prop["z"]*100,mountain_prop["x"]*100,mountain_prop.get("y",0)*100))
    return {"sourceSha256": original["sourceSha256"],"mountainTriangles": len(mountain["indices"])//3,
            "removedDegenerateTriangles": mountain["removedDegenerateTriangles"],
            "mountainSourceSha256": hashlib.sha256((ROOT/"public/assets/models/prop_aegis_mountain_massif.glb").read_bytes()).hexdigest()}


def build_gameplay(actors):
    source = source_map()
    npc_source = next(n for n in source["npcs"] if n["id"] == "quest-1")
    visual = unreal.load_asset("/Game/MigrationProof/Visual_npc_aegis_mara_vell_brightfen_dispatch_officer")
    if not visual or not visual.skeletal_mesh:
        raise RuntimeError("Required capital dispatch character is not imported")
    npc = actors.spawn_actor_from_class(unreal.WarQuestNpc, unreal.Vector(*point(npc_source)))
    npc.set_actor_label(npc_source["name"] + " - Brightfen dispatch")
    npc.tags=["WarCapitalGameplay"]
    npc.set_editor_property("zone_id","aegis_capital"); npc.set_editor_property("npc_id",npc_source["id"])
    npc.set_editor_property("visual",visual)
    mesh = npc.get_editor_property("mesh")
    mesh.set_skeletal_mesh_asset(visual.skeletal_mesh)
    mesh.set_relative_transform(visual.mesh_transform,False,True)
    table = json.loads((ROOT/"artifacts/unreal/converted/frontier_field_command_table/editor-import.json").read_text())
    if not table["importSucceeded"]:
        raise RuntimeError("Required crafting table import is missing")
    stations=[]
    for station in source["craftingStations"]:
        for index, part in enumerate(table["meshes"]):
            asset = unreal.load_asset(part["path"])
            if not isinstance(asset,unreal.StaticMesh):
                raise RuntimeError("Missing authored crafting table part")
            actor = actors.spawn_actor_from_class(unreal.WarCraftingStation if index==0 else unreal.StaticMeshActor,
                                                  unreal.Vector(*point(station)))
            actor.set_actor_label(station["label"]+f" part {index}")
            actor.tags=["WarCapitalGameplay",station["id"]]
            actor.static_mesh_component.set_static_mesh(asset)
            if index==0:
                actor.set_editor_property("station_kind",station["kind"])
                actor.set_editor_property("interaction_radius",station["radius"]*100)
        stations.append({"id":station["id"],"kind":station["kind"],"position":point(station)})
    resources=[]
    receipt=json.loads((ROOT/"artifacts/unreal/converted"/PROFILE/"editor-import.json").read_text())
    source_file=ROOT/"public/assets/models/prop_aegis_flowerbed_violets.glb"
    if (receipt.get("importSucceeded") is not True or receipt.get("sourceSha256") != hashlib.sha256(source_file.read_bytes()).hexdigest()
            or len(receipt["meshes"]) != 1):
        raise RuntimeError("Capital gathering import is missing or stale")
    asset=unreal.load_asset(receipt["meshes"][0]["path"])
    if not isinstance(asset,unreal.StaticMesh):
        raise RuntimeError("Capital gathering mesh is unavailable")
    for binding in resource_bindings(source):
        node,prop=binding["node"],binding["prop"]
        actor=actors.spawn_actor_from_class(unreal.WarResourceNode,unreal.Vector(*point(prop,prop.get("y",0)*100)),
            unreal.Rotator(yaw=90-math.degrees(prop.get("rotY",0))))
        actor.set_actor_label(node["label"])
        actor.tags=["WarCapitalGameplay",node["id"]]
        actor.set_actor_scale3d(unreal.Vector(*([prop.get("scale",1)]*3)))
        actor.static_mesh_component.set_static_mesh(asset)
        actor.static_mesh_component.set_collision_profile_name("NoCollision")
        actor.set_editor_property("zone_id","aegis_capital")
        actor.set_editor_property("node_id",node["id"])
        actor.set_editor_property("visual_prop_id",prop["id"])
        resources.append({"id":node["id"],"visualPropId":prop["id"],"profile":PROFILE,"position":point(prop)})
    return {"zoneId":"aegis_capital","questNpcId":npc_source["id"],"questNpcPosition":point(npc_source),
            "resources":resources,"pendingResources":[n["id"] for n in source["resourceNodes"] if n["id"] not in {r["id"] for r in resources}],
            "stations":stations,"nativeGameMode":"/Script/AegisWar.WarGameMode","developmentOnly":True,
            "npcArtApproved":False,"fullGameplayParity":False}
