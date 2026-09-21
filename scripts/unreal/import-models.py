"""Import verified conversion examples in UE 5.8's unattended Python commandlet.

UnrealEditor-Cmd AegisWar.uproject -unattended -run=pythonscript
  -script=".../import-models.py --profile npc_frontier_sunmeadow_empire_herbalist"

Omit --profile for all admitted examples. This creates import evidence, never art
approval, character identity assignments, generated collision, or fallback art.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import importlib.util
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "unreal/AegisWar"
PROFILES = (
    "npc_frontier_sunmeadow_empire_herbalist",
    "npc_frontier_cinderfen_dark_elf_supply_officer",
    "frontier_field_command_table",
    "mire_warbrute_m",
    "aegis_house_1",
    "aegis_house_2",
    "aegis_house_3",
    "aegis_house_4",
    "aegis_house_5",
    "aegis_house_6",
    "aegis_rowhouse_1",
    "aegis_rowhouse_2",
    "aegis_wall",
    "npc_frontier_sunmeadow_empire_farmer",
)
PROFILE_TAG = "WarMigrationProfile"
SOURCE_TAG = "WarMigrationSourceSha256"
VISUAL_REGISTRY = PROJECT / "Content/Migration/visual-imports.json"


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contained(path, parent):
    resolved = path.resolve()
    require(resolved.is_relative_to(parent.resolve()), f"Path escapes {parent}: {path}")
    return resolved


def relative_path(value, parent=ROOT):
    require(isinstance(value, str) and not Path(value).is_absolute(), "Expected a relative path")
    return contained(ROOT / value, parent)


def verified_file(path, expected):
    require(isinstance(expected, str) and re.fullmatch(r"[a-f0-9]{64}", expected), "Invalid SHA-256")
    require(path.is_file() and sha256(path) == expected, f"Byte hash mismatch: {path}")
    return path


def load_json(path):
    def reject_constant(value):
        raise ValueError(f"Non-finite JSON value: {value}")
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_constant)


def update_visual_registry(profiles, entries=()):
    """Only generated import evidence is changed; existing unrelated bindings survive."""
    path = contained(VISUAL_REGISTRY, PROJECT / "Content/Migration")
    document = load_json(path) if path.exists() else {"schemaVersion": 1, "entries": []}
    require(document.get("schemaVersion") == 1 and isinstance(document.get("entries"), list), "Invalid visual binding registry")
    names = [entry["profileKey"] for entry in document["entries"]]
    require(len(names) == len(set(names)), "Duplicate visual registry profiles")
    retained = [entry for entry in document["entries"] if entry["profileKey"] not in profiles]
    document["entries"] = sorted(retained + list(entries), key=lambda entry: entry["profileKey"])
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(document, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def safe_name(name):
    return re.sub(r"[^A-Za-z0-9_]", "_", name)


def material_slot_mapping(names):
    # Match UE 5.8 FFbxImporter::MakeName, which preserves hyphens and removes namespaces.
    result = {}
    for original in names:
        imported = re.sub(r"[.,/`%]", "_", original.rsplit(":", 1)[-1])
        require(imported not in result, f"Source material names collide in the FBX importer: {imported}")
        result[imported] = original
    return result


def read_glb(path):
    data = path.read_bytes()
    require(len(data) >= 20, "Truncated GLB")
    magic, version, length = struct.unpack_from("<4sII", data)
    require(magic == b"glTF" and version == 2 and length == len(data), "Invalid GLB header")
    chunks = {}
    offset = 12
    while offset < length:
        size, kind = struct.unpack_from("<II", data, offset)
        offset += 8
        require(offset + size <= length and kind not in chunks, "Invalid GLB chunk")
        chunks[kind] = data[offset:offset + size]
        offset += size
    gltf = json.loads(chunks[0x4E4F534A])
    binary = chunks.get(0x004E4942, b"")
    require(not gltf.get("extensionsRequired"), "Unsupported required glTF extension")
    images = []
    for index, image in enumerate(gltf.get("images", [])):
        mime = image.get("mimeType")
        source_path = None
        if "uri" in image:
            require("bufferView" not in image and isinstance(image["uri"], str), "Ambiguous texture source")
            uri = urlsplit(image["uri"])
            require(not uri.scheme and not uri.netloc and not uri.query and not uri.fragment,
                    "External textures must be local repository files")
            decoded = unquote(uri.path, errors="strict")
            require(decoded and not any(character in decoded for character in ("\\", ":", "\0"))
                    and not Path(decoded).is_absolute(), "Invalid relative texture URI")
            texture = contained(path.parent / decoded, ROOT / "public/assets/textures")
            expected_mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}.get(texture.suffix.lower())
            require(expected_mime is not None and (mime is None or mime == expected_mime), "Texture MIME type and filename disagree")
            mime = expected_mime
            require(texture.is_file(), f"Repository texture is missing: {texture}")
            pixels = texture.read_bytes()
            require(pixels.startswith(b"\x89PNG\r\n\x1a\n") if mime == "image/png" else pixels.startswith(b"\xff\xd8\xff"),
                    "Repository texture signature is invalid")
            source_path = texture.relative_to(ROOT.resolve()).as_posix()
        else:
            require("bufferView" in image, "Texture has no source")
            view = gltf["bufferViews"][image["bufferView"]]
            require(view.get("buffer", 0) == 0, "Texture references an external buffer")
            start = view.get("byteOffset", 0)
            end = start + view["byteLength"]
            require(0 <= start < end <= len(binary), "Texture buffer view is outside GLB")
            pixels = binary[start:end]
        require(mime in ("image/png", "image/jpeg"), f"Unsupported texture MIME type: {mime}")
        images.append({"index": index, "name": image.get("name", f"image_{index}"), "sourcePath": source_path,
                       "extension": ".png" if mime == "image/png" else ".jpg", "bytes": pixels})
    material_names = [material["name"] for material in gltf.get("materials", [])]
    require(len(set(material_names)) == len(material_names), "Duplicate source material names")
    require(len(set(map(safe_name, material_names))) == len(material_names), "Material names collide after Unreal sanitization")
    return gltf, images


def image_dependencies(images):
    return [{"index": image["index"], "sourcePath": image["sourcePath"],
             "sha256": hashlib.sha256(image["bytes"]).hexdigest()} for image in images]


def validate_inputs(profile):
    require(profile in PROFILES, f"Not one of the reviewed conversion examples: {profile}")
    directory = contained(ROOT / "artifacts/unreal/converted" / profile, ROOT / "artifacts/unreal/converted")
    conversion_path = contained(directory / "conversion.json", directory)
    conversion = load_json(conversion_path)
    require(conversion.get("schemaVersion") == 1 and conversion.get("profileKey") == profile, "Conversion identity mismatch")
    require(conversion.get("status") == "converted-unverified-in-unreal" and conversion.get("unrealApproved") is False,
            "Expected an unapproved, verified Blender conversion")
    kind = conversion.get("kind")
    require(kind in ("characterProfiles", "staticProps"), "Unsupported registry kind")
    registry = load_json(ROOT / "public/assets/models/asset-index.json")
    record = registry[kind][profile]
    require(record.get("approvalState") == "approved" and record.get("runtimeReady") is True,
            "Source is no longer permitted by its existing browser registry")
    source = relative_path(conversion["source"], ROOT / "public/assets/models")
    require(source == contained(ROOT / "public/assets/models" / record["model"], ROOT / "public/assets/models"),
            "Conversion source no longer matches the registry")
    require(conversion["sourceSha256"] == record["modelSha256"], "Registry source SHA differs")
    verified_file(source, conversion["sourceSha256"])
    reviews = load_json(ROOT / "migration/visual-reviews.json")
    require(reviews.get("schemaVersion") == 1, "Unsupported visual review schema")
    require(not any(row["status"] == "rejected" and row["sourceSha256"] == conversion["sourceSha256"] for row in reviews["reviews"]),
            "Source failed nonprimitive visual review")
    qc = contained(ROOT / "public/assets/models" / record["qc"], ROOT / "public/assets/models")
    require(conversion["qcSha256"] == record["qcSha256"], "Registry QC SHA differs")
    verified_file(qc, conversion["qcSha256"])
    fbx = relative_path(conversion["output"], directory)
    require(fbx.suffix.lower() == ".fbx", "Expected FBX output")
    verified_file(fbx, conversion["outputSha256"])
    verification = conversion["verification"]
    require(verification.get("status") == "blender-roundtrip-passed", "Blender roundtrip has not passed")
    sample_path = relative_path(verification["sampleEvidence"], directory)
    verified_file(sample_path, verification["sampleEvidenceSha256"])
    clips = conversion["sourceAnimationNames"]
    require(len(clips) == len(set(clips)), "Duplicate source clip names")
    require(len(clips) == (9 if kind == "characterProfiles" else 0), "Unexpected example clip count")
    require(sorted(clip["name"] for clip in verification["animations"]) == sorted(clips), "Animation evidence is incomplete")
    require(all(clip["status"] == "passed" for clip in verification["animations"]), "Animation verification failed")
    require(verification["fbxGlobalSettings"]["UnitScaleFactor"] == 1, "Expected FBX centimeter units")
    gltf, images = read_glb(source)
    # A Blender bone-display custom shape is not source geometry. Comparing only
    # Blender's before/after counts would allow that generated helper to survive.
    source_mesh_count = sum("mesh" in node for node in gltf.get("nodes", []))
    require(conversion["before"]["meshes"] == source_mesh_count
            and conversion["after"]["meshes"] == source_mesh_count,
            "Conversion mesh count differs from source GLB nodes; generated helper geometry is forbidden")
    require(sorted(animation["name"] for animation in gltf.get("animations", [])) == sorted(clips), "Source clip names differ")
    return {"profile": profile, "directory": directory, "conversion": conversion,
            "conversionPath": conversion_path, "conversionSha256": sha256(conversion_path),
            "source": source, "qc": qc, "fbx": fbx, "samples": sample_path,
            "gltf": gltf, "images": images, "imageDependencies": image_dependencies(images), "destination": f"/Game/Imported/{profile}"}


def asset_record(asset):
    return {"name": asset.get_name(), "path": asset.get_path_name(), "class": asset.get_class().get_name()}


def mark_owned(unreal, asset, context):
    unreal.EditorAssetLibrary.set_metadata_tag(asset, PROFILE_TAG, context["profile"])
    unreal.EditorAssetLibrary.set_metadata_tag(asset, SOURCE_TAG, context["conversion"]["sourceSha256"])


def require_owned(unreal, asset, context):
    require(unreal.EditorAssetLibrary.get_metadata_tag(asset, PROFILE_TAG) == context["profile"],
            f"Refusing to replace an asset not created by this importer: {asset.get_path_name()}")
    require(unreal.EditorAssetLibrary.get_metadata_tag(asset, SOURCE_TAG) == context["conversion"]["sourceSha256"],
            f"Existing imported asset belongs to different source bytes: {asset.get_path_name()}")


def task_for(unreal, path, destination):
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(path))
    task.set_editor_property("destination_path", destination)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("replace_existing_settings", True)
    task.set_editor_property("save", False)
    return task


def import_mesh(unreal, context):
    skeletal = context["conversion"]["kind"] == "characterProfiles"
    options = unreal.FbxImportUI()
    mesh_type = unreal.FBXImportType.FBXIT_SKELETAL_MESH if skeletal else unreal.FBXImportType.FBXIT_STATIC_MESH
    properties = {"automated_import_should_detect_type": False, "mesh_type_to_import": mesh_type,
                  "original_import_type": mesh_type, "import_as_skeletal": skeletal, "import_mesh": True,
                  "import_animations": skeletal, "create_physics_asset": False,
                  "import_materials": False, "import_textures": False}
    for name, value in properties.items():
        options.set_editor_property(name, value)
    for name in ("static_mesh_import_data", "skeletal_mesh_import_data", "anim_sequence_import_data"):
        data = options.get_editor_property(name)
        data.set_editor_property("convert_scene", True)
        data.set_editor_property("convert_scene_unit", True)
        data.set_editor_property("force_front_x_axis", False)
        data.set_editor_property("import_uniform_scale", 1.0)
    static_data = options.get_editor_property("static_mesh_import_data")
    static_data.set_editor_property("combine_meshes", False)
    static_data.set_editor_property("auto_generate_collision", False)
    skeletal_data = options.get_editor_property("skeletal_mesh_import_data")
    skeletal_data.set_editor_property("use_t0_as_ref_pose", False)
    skeletal_data.set_editor_property("update_skeleton_reference_pose", True)
    skeletal_data.set_editor_property("import_morph_targets", True)
    skeletal_data.set_editor_property("import_meshes_in_bone_hierarchy", True)
    for data in (static_data, skeletal_data):
        data.set_editor_property("vertex_color_import_option", unreal.VertexColorImportOption.REPLACE)
    animation = options.get_editor_property("anim_sequence_import_data")
    animation.set_editor_property("animation_length", unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    animation.set_editor_property("use_default_sample_rate", False)
    animation.set_editor_property("custom_sample_rate", context["conversion"]["verification"]["bakeFramesPerSecond"])
    animation.set_editor_property("snap_to_closest_frame_boundary", False)
    animation.set_editor_property("import_bone_tracks", True)
    # Reconstruct in the same converted scene basis as the mesh bind pose.
    animation.set_editor_property("preserve_local_transform", False)
    animation.set_editor_property("remove_redundant_keys", False)
    task = task_for(unreal, context["fbx"], context["destination"])
    task.set_editor_property("factory", unreal.FbxFactory())
    task.set_editor_property("options", options)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    require(task.get_objects(), "FBX importer returned no assets")
    return list(task.get_editor_property("imported_object_paths"))


def emissive_color(material):
    extensions = material.get("extensions", {})
    require(isinstance(extensions, dict) and set(extensions).issubset({"KHR_materials_emissive_strength"}),
            "Unsupported material extension")
    extension = extensions.get("KHR_materials_emissive_strength", {})
    require(isinstance(extension, dict) and set(extension).issubset({"emissiveStrength"}),
            "Unsupported material emissive properties")
    strength = extension.get("emissiveStrength", 1)
    factor = material.get("emissiveFactor", [0, 0, 0])
    require(type(strength) in (int, float) and math.isfinite(strength) and strength >= 0,
            "Invalid emissive strength")
    require(isinstance(factor, list) and len(factor) == 3
            and all(type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1 for value in factor),
            "Invalid emissive factor")
    return [value * strength for value in factor]


def texture_roles(gltf):
    roles = {}
    for material in gltf.get("materials", []):
        require(set(material).issubset({"name", "doubleSided", "normalTexture", "occlusionTexture",
                                       "pbrMetallicRoughness", "extras", "alphaMode", "alphaCutoff",
                                       "extensions", "emissiveFactor", "emissiveTexture"}),
                f"Unsupported material properties: {material['name']}")
        emissive_color(material)
        require(material.get("alphaMode", "OPAQUE") in ("OPAQUE", "MASK", "BLEND"), "Unsupported alpha mode")
        pbr = material.get("pbrMetallicRoughness", {})
        require(set(pbr).issubset({"baseColorFactor", "baseColorTexture", "metallicFactor", "roughnessFactor", "metallicRoughnessTexture"}),
                "Unsupported PBR material properties")
        for info, role in ((pbr.get("baseColorTexture"), "color"),
                           (pbr.get("metallicRoughnessTexture"), "linear"), (material.get("normalTexture"), "normal"),
                           (material.get("occlusionTexture"), "linear"), (material.get("emissiveTexture"), "color")):
            if info is not None:
                require(set(info).issubset({"index", "texCoord", "scale", "strength"}), "Unsupported texture transform or extension")
                require(info.get("texCoord", 0) == 0, "Only source UV channel 0 is supported by these examples")
                index = gltf["textures"][info["index"]]["source"]
                roles.setdefault(index, set()).add(role)
    require(all(len(values) == 1 for values in roles.values()), "One source image requires conflicting Unreal color spaces")
    return {index: next(iter(values)) for index, values in roles.items()}


def import_textures(unreal, context):
    roles = texture_roles(context["gltf"])
    textures = {}
    records = []
    directory = contained(context["directory"] / "source-textures", context["directory"])
    directory.mkdir(exist_ok=True)
    for image in context["images"]:
        asset_name = f"T_{image['index']:03d}_{safe_name(image['name'])}"
        path = contained(directory / (asset_name + image["extension"]), directory)
        path.write_bytes(image["bytes"])
        task = task_for(unreal, path, context["destination"] + "/Textures")
        task.set_editor_property("destination_name", asset_name)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        objects = task.get_objects()
        require(len(objects) == 1 and isinstance(objects[0], unreal.Texture2D), f"Texture import failed: {image['name']}")
        texture = objects[0]
        role = roles.get(image["index"], "linear")
        texture.set_editor_property("srgb", role == "color")
        compression = unreal.TextureCompressionSettings.TC_NORMALMAP if role == "normal" else (
            unreal.TextureCompressionSettings.TC_DEFAULT if role == "color" else unreal.TextureCompressionSettings.TC_MASKS)
        texture.set_editor_property("compression_settings", compression)
        texture.set_editor_property("flip_green_channel", role == "normal")
        mark_owned(unreal, texture, context)
        unreal.EditorAssetLibrary.set_metadata_tag(texture, "WarOriginalImageName", image["name"])
        textures[image["index"]] = texture
        records.append({**asset_record(texture), "sourceImageIndex": image["index"], "sourceImageName": image["name"],
                        "sourceBytesSha256": hashlib.sha256(image["bytes"]).hexdigest(), "colorSpaceRole": role})
    return textures, records


def create_materials(unreal, context, textures):
    """Rebuild the source GLB's PBR channels; FBX does not preserve this graph."""
    library = unreal.MaterialEditingLibrary
    result = {}
    records = []
    for source in context["gltf"].get("materials", []):
        source_name = source["name"]
        name = safe_name(source_name)
        package = context["destination"] + "/Materials"
        material = unreal.load_asset(f"{package}/{name}")
        if material:
            require_owned(unreal, material, context)
            require(isinstance(material, unreal.Material), "Unexpected material asset class")
            library.delete_all_material_expressions(material)
        else:
            material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, package, unreal.Material, unreal.MaterialFactoryNew())
        require(material is not None, f"Material creation failed: {source_name}")
        mark_owned(unreal, material, context)
        unreal.EditorAssetLibrary.set_metadata_tag(material, "WarOriginalMaterialName", source_name)
        unreal.EditorAssetLibrary.set_metadata_tag(material, "WarOriginalGltfMaterial", json.dumps(source, sort_keys=True))
        # Game/cooked loading cannot rely on the editor discovering this usage after import.
        material.set_editor_property("used_with_skeletal_mesh", context["conversion"]["kind"] == "characterProfiles")
        material.set_editor_property("two_sided", source.get("doubleSided", False))
        alpha_mode = source.get("alphaMode", "OPAQUE")
        material.set_editor_property("blend_mode", {"OPAQUE": unreal.BlendMode.BLEND_OPAQUE,
            "MASK": unreal.BlendMode.BLEND_MASKED, "BLEND": unreal.BlendMode.BLEND_TRANSLUCENT}[alpha_mode])
        if alpha_mode == "MASK":
            material.set_editor_property("opacity_mask_clip_value", source.get("alphaCutoff", 0.5))
        if alpha_mode == "BLEND":
            material.set_editor_property("translucency_lighting_mode", unreal.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)

        def node(kind):
            return library.create_material_expression(material, kind)

        def scalar(value):
            expression = node(unreal.MaterialExpressionConstant)
            expression.set_editor_property("r", float(value))
            return expression

        def vector(value):
            expression = node(unreal.MaterialExpressionConstant3Vector)
            expression.set_editor_property("constant", unreal.LinearColor(*value[:3], 1.0))
            return expression

        def connect(expression, output, target, pin):
            require(library.connect_material_expressions(expression, output, target, pin), f"Cannot connect material pin {pin}")

        def product(left, output, right):
            expression = node(unreal.MaterialExpressionMultiply)
            connect(left, output, expression, "A")
            connect(right, "", expression, "B")
            return expression

        def sample(info, role):
            expression = node(unreal.MaterialExpressionTextureSample)
            image_index = context["gltf"]["textures"][info["index"]]["source"]
            expression.set_editor_property("texture", textures[image_index])
            sampler = {"color": unreal.MaterialSamplerType.SAMPLERTYPE_COLOR,
                       "linear": unreal.MaterialSamplerType.SAMPLERTYPE_MASKS,
                       "normal": unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL}[role]
            expression.set_editor_property("sampler_type", sampler)
            return expression

        def output(expression, property_name):
            require(library.connect_material_property(expression, "", property_name), "Cannot connect material output")

        pbr = source.get("pbrMetallicRoughness", {})
        factor = pbr.get("baseColorFactor", [1, 1, 1, 1])
        base = vector(factor)
        color_sample = None
        if "baseColorTexture" in pbr:
            color_sample = sample(pbr["baseColorTexture"], "color")
            base = product(color_sample, "RGB", base)
        output(base, unreal.MaterialProperty.MP_BASE_COLOR)
        emissive = vector(emissive_color(source))
        if "emissiveTexture" in source:
            emissive = product(sample(source["emissiveTexture"], "color"), "RGB", emissive)
        output(emissive, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        if alpha_mode != "OPAQUE":
            alpha = scalar(factor[3])
            if color_sample is not None:
                alpha = product(color_sample, "A", alpha)
            output(alpha, unreal.MaterialProperty.MP_OPACITY_MASK if alpha_mode == "MASK" else unreal.MaterialProperty.MP_OPACITY)
        metallic = scalar(pbr.get("metallicFactor", 1.0))
        roughness = scalar(pbr.get("roughnessFactor", 1.0))
        if "metallicRoughnessTexture" in pbr:
            packed = sample(pbr["metallicRoughnessTexture"], "linear")
            metallic = product(packed, "B", metallic)
            roughness = product(packed, "G", roughness)
        output(metallic, unreal.MaterialProperty.MP_METALLIC)
        output(roughness, unreal.MaterialProperty.MP_ROUGHNESS)
        if "occlusionTexture" in source:
            info = source["occlusionTexture"]
            occlusion = node(unreal.MaterialExpressionLinearInterpolate)
            connect(scalar(1), "", occlusion, "A")
            connect(sample(info, "linear"), "R", occlusion, "B")
            connect(scalar(info.get("strength", 1)), "", occlusion, "Alpha")
            output(occlusion, unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
        if "normalTexture" in source:
            info = source["normalTexture"]
            normal = sample(info, "normal")
            scaled = product(normal, "RGB", vector([info.get("scale", 1), info.get("scale", 1), 1]))
            normalized = node(unreal.MaterialExpressionNormalize)
            connect(scaled, "", normalized, "VectorInput")
            output(normalized, unreal.MaterialProperty.MP_NORMAL)
        library.layout_material_expressions(material)
        errors = library.recompile_material(material)
        require(not errors, f"Material compilation errors for {source_name}: {errors}")
        result[source_name] = material
        records.append({**asset_record(material), "sourceMaterialName": source_name, "sourceDefinition": source,
                        "skeletalMeshUsage": bool(material.get_editor_property("used_with_skeletal_mesh"))})
    return result, records


def collect_assets(unreal, context):
    result = []
    for path in sorted(unreal.EditorAssetLibrary.list_assets(context["destination"], recursive=True, include_folder=False)):
        asset = unreal.load_asset(path)
        require(asset is not None, f"Cannot load imported asset: {path}")
        result.append(asset)
    return result


def inspect_assets(unreal, context, assets, materials):
    skeletal = context["conversion"]["kind"] == "characterProfiles"
    meshes = [asset for asset in assets if isinstance(asset, (unreal.SkeletalMesh, unreal.StaticMesh))]
    skeletons = [asset for asset in assets if isinstance(asset, unreal.Skeleton)]
    animations = [asset for asset in assets if isinstance(asset, unreal.AnimSequence)]
    require(meshes, "Import contains no meshes")
    require(all(isinstance(mesh, unreal.SkeletalMesh if skeletal else unreal.StaticMesh) for mesh in meshes), "Unexpected imported mesh class")
    require(len(skeletons) == (1 if skeletal else 0), "Unexpected skeleton count")
    require(len(animations) == len(context["conversion"]["sourceAnimationNames"]), "Animation clip count changed during Unreal import")
    allowed = (unreal.SkeletalMesh, unreal.StaticMesh, unreal.Skeleton, unreal.AnimSequence, unreal.Material, unreal.Texture2D,
               unreal.AnimBoneCompressionSettings)
    require(all(isinstance(asset, allowed) for asset in assets), "Unexpected imported asset class")
    mesh_records = []
    used_materials = set()
    by_imported_name = material_slot_mapping(materials)
    for mesh in meshes:
        property_name = "materials" if skeletal else "static_materials"
        slots = list(mesh.get_editor_property(property_name))
        slot_records = []
        for slot in slots:
            imported_name = str(slot.get_editor_property("imported_material_slot_name"))
            current_name = str(slot.get_editor_property("material_slot_name"))
            original = next((value for value in (imported_name, current_name) if value in materials), None)
            if original is None:
                original = by_imported_name.get(imported_name) or by_imported_name.get(current_name)
            require(original is not None, f"Material slot has no exact source mapping: {mesh.get_name()}/{imported_name}")
            require(not skeletal or materials[original].get_editor_property("used_with_skeletal_mesh"),
                    f"Character material lacks skeletal-mesh shader usage: {original}")
            slot.set_editor_property("material_interface", materials[original])
            slot.set_editor_property("material_slot_name", original)
            used_materials.add(original)
            slot_records.append({"sourceMaterialName": original, "importedSlotName": imported_name,
                                 "materialPath": materials[original].get_path_name()})
        mesh.set_editor_property(property_name, slots)
        record = {**asset_record(mesh), "materialSlots": slot_records}
        if skeletal:
            skeleton = mesh.get_editor_property("skeleton")
            require(skeleton is not None and skeleton == skeletons[0], "Mesh has an unexpected skeleton")
            record["skeletonPath"] = skeleton.get_path_name()
        mesh_records.append(record)
    require(used_materials == set(materials), f"Source materials lost from mesh slots: {sorted(set(materials) - used_materials)}")
    expected = {clip["name"]: clip for clip in context["conversion"]["verification"]["animations"]}
    animation_records = []
    for animation in animations:
        source_name = unreal.WarImportLibrary.get_source_animation_name(animation)
        require(source_name in expected, f"Unexpected imported animation: {source_name}")
        length = float(unreal.AnimationLibrary.get_sequence_length(animation))
        require(math.isfinite(length) and abs(length - expected[source_name]["sourceDurationSeconds"]) <= 1 / 120 + 1e-5,
                f"Animation duration changed: {source_name}")
        tracks = sorted(str(name) for name in unreal.AnimationLibrary.get_animation_track_names(animation))
        require(len(tracks) >= context["conversion"]["before"]["joints"], f"Animation lost bone tracks: {source_name}")
        require(animation.get_editor_property("skeleton") == skeletons[0], "Animation uses an unexpected skeleton")
        animation_records.append({**asset_record(animation), "sourceClipName": source_name,
                                  "durationSeconds": length, "sourceDurationSeconds": expected[source_name]["sourceDurationSeconds"],
                                  "frameCount": unreal.AnimationLibrary.get_num_frames(animation),
                                  "boneCompressionSettings": animation.get_editor_property("bone_compression_settings").get_path_name(),
                                  "allowFrameStripping": animation.get_editor_property("allow_frame_stripping"),
                                  "boneTrackCount": len(tracks), "boneTrackNames": tracks,
                                  "skeletonPath": skeletons[0].get_path_name()})
    require(sorted(record["sourceClipName"] for record in animation_records) == sorted(expected), "Duplicate or missing animation clips")
    return mesh_records, [asset_record(skeleton) for skeleton in skeletons], sorted(animation_records, key=lambda record: record["sourceClipName"])


def configure_animation_compression(unreal, context):
    animations = [asset for asset in collect_assets(unreal, context) if isinstance(asset, unreal.AnimSequence)]
    if not animations:
        return None
    name = "SourcePoseCompression"
    path = context["destination"] + "/" + name
    settings = unreal.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else None
    if settings:
        require_owned(unreal, settings, context)
        require(isinstance(settings, unreal.AnimBoneCompressionSettings), "Unexpected compression settings asset class")
    else:
        settings = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, context["destination"],
            unreal.AnimBoneCompressionSettings, unreal.AnimBoneCompressionSettingsFactory())
        require(settings is not None, "Could not create source animation compression settings")
    # ACL does not use AnimSequence.CompressionErrorThresholdScale. Configure
    # the actual codec, keeping both the source samples and parity limit intact.
    codec_class = unreal.load_class(None, "/Script/ACLPlugin.AnimBoneCompressionCodec_ACL")
    require(codec_class is not None, "ACL animation codec is unavailable")
    codec = unreal.new_object(codec_class, outer=settings)
    codec.set_editor_property("ErrorThreshold", 0.0001)
    codec.set_editor_property("DefaultVirtualVertexDistance", 100.0)
    codec.set_editor_property("SafeVirtualVertexDistance", 100.0)
    settings.set_editor_property("codecs", [codec])
    mark_owned(unreal, settings, context)
    for animation in animations:
        animation.set_editor_property("allow_frame_stripping", False)
        animation.set_editor_property("bone_compression_settings", settings)
    return {"settingsPath": settings.get_path_name(), "codecClass": codec_class.get_path_name(),
            "errorThresholdCm": codec.get_editor_property("ErrorThreshold"),
            "virtualVertexDistanceCm": codec.get_editor_property("DefaultVirtualVertexDistance"),
            "safeVirtualVertexDistanceCm": codec.get_editor_property("SafeVirtualVertexDistance"),
            "allowFrameStripping": False}


def import_profile(unreal, context):
    receipt = contained(context["directory"] / "editor-import.json", context["directory"])
    # Any new attempt invalidates the old success, including failed preflight.
    receipt.unlink(missing_ok=True)
    existing = collect_assets(unreal, context)
    for asset in existing:
        require_owned(unreal, asset, context)
    # Atomic FBX reimport can retain previous animation settings even when the
    # task requests replacement settings. Rebuild only our generated geometry
    # and rig packages so mesh bind poses and animation use the same options.
    rebuild_order = {"AnimSequence": 0, "SkeletalMesh": 1, "Skeleton": 2, "StaticMesh": 3}
    for asset in sorted(existing, key=lambda item: rebuild_order.get(item.get_class().get_name(), 4)):
        if asset.get_class().get_name() in rebuild_order:
            path = asset.get_path_name()
            require(unreal.EditorAssetLibrary.delete_asset(path), f"Could not replace generated asset: {path}")
    texture_roles(context["gltf"])
    imported_paths = import_mesh(unreal, context)
    for asset in collect_assets(unreal, context):
        mark_owned(unreal, asset, context)
    textures, texture_records = import_textures(unreal, context)
    materials, material_records = create_materials(unreal, context, textures)
    compression = configure_animation_compression(unreal, context)
    assets = collect_assets(unreal, context)
    meshes, skeletons, animations = inspect_assets(unreal, context, assets, materials)
    pose_evidence = None
    if animations:
        spec = importlib.util.spec_from_file_location("war_pose_parity", Path(__file__).with_name("pose_parity.py"))
        parity = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(parity)
        unreal.WarImportLibrary.prepare_preview_frame(None)
        pose_evidence = parity.verify_animations(unreal, animations, load_json(context["samples"])["source"])
    for asset in assets:
        mark_owned(unreal, asset, context)
    require(unreal.EditorAssetLibrary.save_directory(context["destination"], only_if_is_dirty=False, recursive=True),
            "Unreal failed to save imported packages")
    # Re-read all evidence after the expensive import before publishing success.
    current = validate_inputs(context["profile"])
    require(current["conversionSha256"] == context["conversionSha256"], "Conversion evidence changed during import")
    require(current["imageDependencies"] == context["imageDependencies"], "Source texture bytes changed during import")
    result = {"schemaVersion": 1, "profileKey": context["profile"], "kind": context["conversion"]["kind"],
              "status": "editor-import-succeeded-unreviewed", "importSucceeded": True, "unrealApproved": False,
              "artApproved": False, "unrealVersion": unreal.SystemLibrary.get_engine_version(),
              "project": "unreal/AegisWar/AegisWar.uproject", "destination": context["destination"],
              "conversionSha256": context["conversionSha256"], "sourceSha256": context["conversion"]["sourceSha256"],
              "fbxSha256": context["conversion"]["outputSha256"], "sampleEvidenceSha256": context["conversion"]["verification"]["sampleEvidenceSha256"],
              "fbxTaskImportedPaths": imported_paths,
              "importSettings": {"factory": "FbxFactory", "interchangeFbx": False, "convertScene": True,
                                 "convertSceneUnit": True, "forceFrontXAxis": False, "uniformScale": 1,
                                 "createPhysicsAsset": False, "autoGenerateCollision": False,
                                 "materials": "source GLB PBR reconstruction; exact embedded or repository texture bytes",
                                 "animationCompression": compression,
                                 "sampleRate": context["conversion"]["verification"]["bakeFramesPerSecond"]},
              "counts": dict(sorted(Counter(asset.get_class().get_name() for asset in assets).items())),
              "meshes": meshes, "skeletons": skeletons, "animations": animations,
              "materials": material_records, "textures": texture_records, "sourceImageDependencies": context["imageDependencies"], "poseParity": pose_evidence,
              "limitations": ["Import evidence is not visual, gameplay, performance, licensing, or art approval.",
                              "Sampled raw and compressed bone and skinning transforms are verified; rendered skin, materials, and animation transitions still require visual review.",
                              "Source-authored geometry is retained. No playable identity mapping or replacement art is approved by this receipt."]}
    temporary = receipt.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    if context["conversion"]["kind"] == "characterProfiles":
        require(len(meshes) == 1, "Native visual evidence requires one imported skeletal mesh per profile")
        update_visual_registry([context["profile"]], [{"profileKey": context["profile"],
            "sourceModel": context["conversion"]["source"], "sourceSha256": context["conversion"]["sourceSha256"],
            "skeletalMeshPath": meshes[0]["path"], "animationPaths": [animation["path"] for animation in animations],
            "artApproval": False, "developmentOnly": True}])
    temporary.replace(receipt)
    unreal.log(f"Imported {context['profile']}: {result['counts']}; art approval remains false")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", action="append", choices=PROFILES)
    args = parser.parse_args()
    selected = list(dict.fromkeys(args.profile or PROFILES))
    # Remove receipts before validating bytes so a rejected attempt cannot leave stale success.
    for profile in selected:
        directory = contained(ROOT / "artifacts/unreal/converted" / profile, ROOT / "artifacts/unreal/converted")
        contained(directory / "editor-import.json", directory).unlink(missing_ok=True)
    import unreal
    require(Path(unreal.Paths.project_dir()).resolve() == PROJECT.resolve(), "Run this importer in the AegisWar project")
    require(unreal.SystemLibrary.get_engine_version().startswith("5.8."), "This importer is validated against UE 5.8 APIs")
    command_line = unreal.SystemLibrary.get_command_line()
    require(re.search(r"(?:^|\s)-run=pythonscript(?:\s|$)", command_line, re.IGNORECASE)
            and re.search(r"(?:^|\s)-unattended(?:\s|$)", command_line, re.IGNORECASE),
            "Run through the unattended PythonScript commandlet")
    update_visual_registry(selected)
    contexts = [validate_inputs(profile) for profile in selected]
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.SystemLibrary.execute_console_command(world, "Interchange.FeatureFlags.Import.FBX 0")
    require(not unreal.SystemLibrary.get_console_variable_bool_value("Interchange.FeatureFlags.Import.FBX"),
            "Could not select the explicit legacy FBX importer")
    for context in contexts:
        import_profile(unreal, context)


if __name__ == "__main__":
    main()
