"""Bake authored preview/paint materials into one runtime glTF atlas.

This module imports no character geometry. It receives an already evaluated,
joined runtime object. Material copies and a mesh copy isolate all temporary
UV/material work from shared authoring data.
"""
from __future__ import annotations

import math
import re
from pathlib import Path

import bpy
import numpy as np


def _source_shader(material):
    if not material or not material.use_nodes:
        raise ValueError("Atlas baking requires authored node-based materials")
    outputs = [node for node in material.node_tree.nodes
               if node.type == "OUTPUT_MATERIAL" and node.is_active_output]
    if len(outputs) != 1 or not outputs[0].inputs["Surface"].is_linked:
        raise ValueError(f"{material.name}: missing active material surface")
    shader = outputs[0].inputs["Surface"].links[0].from_node
    if shader.type != "BSDF_PRINCIPLED":
        raise ValueError(f"{material.name}: the atlas helper expects a direct Principled surface")
    return outputs[0], shader


def _pin_source_uv(material, uv_name):
    tree = material.node_tree
    nodes = list(tree.nodes)
    explicit_uv = tree.nodes.new("ShaderNodeUVMap")
    explicit_uv.name = "atlas_source_uv"
    explicit_uv.uv_map = uv_name
    for node in nodes:
        if node.type == "TEX_IMAGE" and not node.inputs["Vector"].is_linked:
            tree.links.new(explicit_uv.outputs["UV"], node.inputs["Vector"])
        elif node.type == "TEX_COORD":
            for link in list(node.outputs["UV"].links):
                target = link.to_socket
                tree.links.remove(link)
                tree.links.new(explicit_uv.outputs["UV"], target)
        elif node.type == "UVMAP" and not node.uv_map:
            node.uv_map = uv_name
        elif node.type == "NORMAL_MAP" and not node.uv_map:
            node.uv_map = uv_name


def _new_image(name, resolution, color_space):
    image = bpy.data.images.new(name, width=resolution, height=resolution,
                                alpha=True, float_buffer=False)
    image.colorspace_settings.name = color_space
    image.alpha_mode = "STRAIGHT"
    return image


def _save(image, path):
    image.filepath_raw = str(path)
    image.file_format = "PNG"
    image.save()
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"Blender did not write atlas image: {path}")


def _gltf_occlusion_group():
    name = "glTF Material Output"
    group = bpy.data.node_groups.get(name)
    if group is None:
        group = bpy.data.node_groups.new(name, "ShaderNodeTree")
        group.interface.new_socket("Occlusion", in_out="INPUT", socket_type="NodeSocketFloat")
        group.interface.new_socket("Thickness", in_out="INPUT", socket_type="NodeSocketFloat").default_value = 0
        group.nodes.new("NodeGroupInput")
        group.nodes.new("NodeGroupOutput")
    if not any(item.name == "Occlusion" and item.in_out == "INPUT"
               for item in group.interface.items_tree if item.item_type == "SOCKET"):
        raise ValueError("Existing glTF Material Output group has no Occlusion input")
    return group


def _atlas_material(slot, images):
    material = bpy.data.materials.new(f"prelate.atlas.{slot}")
    material.use_nodes = True
    tree = material.node_tree
    tree.nodes.clear()
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    shader = tree.nodes.new("ShaderNodeBsdfPrincipled")
    shader.inputs["Metallic"].default_value = 1
    shader.inputs["Roughness"].default_value = 1
    tree.links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    uv = tree.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "runtime_atlas"
    uv.location = (-850, 100)
    base = tree.nodes.new("ShaderNodeTexImage")
    base.name = "Base Color Atlas"
    base.image = images["baseColor"]
    base.location = (-600, 250)
    normal_image = tree.nodes.new("ShaderNodeTexImage")
    normal_image.name = "Normal Atlas"
    normal_image.image = images["normal"]
    normal_image.location = (-600, -50)
    orm = tree.nodes.new("ShaderNodeTexImage")
    orm.name = "Occlusion Roughness Metallic Atlas"
    orm.image = images["orm"]
    orm.location = (-600, -350)
    for node in (base, normal_image, orm):
        node.extension = "EXTEND"
        tree.links.new(uv.outputs["UV"], node.inputs["Vector"])
    tree.links.new(base.outputs["Color"], shader.inputs["Base Color"])
    if "emission" in images:
        emission_image = tree.nodes.new("ShaderNodeTexImage")
        emission_image.name = "Ember emission atlas"
        emission_image.image = images["emission"]
        tree.links.new(uv.outputs["UV"], emission_image.inputs["Vector"])
        tree.links.new(emission_image.outputs["Color"], shader.inputs["Emission Color"])
        shader.inputs["Emission Strength"].default_value = 2.0
    normal = tree.nodes.new("ShaderNodeNormalMap")
    normal.uv_map = "runtime_atlas"
    normal.location = (-290, -50)
    tree.links.new(normal_image.outputs["Color"], normal.inputs["Color"])
    tree.links.new(normal.outputs["Normal"], shader.inputs["Normal"])
    channels = tree.nodes.new("ShaderNodeSeparateColor")
    channels.mode = "RGB"
    channels.location = (-290, -350)
    tree.links.new(orm.outputs["Color"], channels.inputs["Color"])
    tree.links.new(channels.outputs["Green"], shader.inputs["Roughness"])
    tree.links.new(channels.outputs["Blue"], shader.inputs["Metallic"])
    occlusion = tree.nodes.new("ShaderNodeGroup")
    occlusion.node_tree = _gltf_occlusion_group()
    occlusion.name = "glTF Material Output"
    occlusion.location = (0, -350)
    tree.links.new(channels.outputs["Red"], occlusion.inputs["Occlusion"])
    shader.location = (0, 100)
    output.location = (330, 100)
    material["atlas_origin"] = "Baked authored material colors/shading and authored mesh occlusion"
    material["orm_channels"] = "R=occlusion, G=roughness, B=metallic"
    return material


def bake_module_atlas(obj, slot, output_dir, resolution=1024, high_sources=None,
                      transfer_surface_channels=False):
    """Return six absolute PNG paths and leave one material/UV map on ``obj``.

    The images are baseColor (sRGB), normal, roughness, metallic, occlusion and
    packed orm (all Non-Color). High sources normally affect only tangent normal.
    With transfer_surface_channels=True, isolated high-source copies also supply
    color-only baseColor, roughness and metallic. This transfers retained modeled
    applique onto a cloth runtime surface without deforming separate ornaments.
    AO multiplies authored target occlusion by module self-occlusion in
    linear space, avoiding duplicate cages and any AO in the base-color pass.
    Scene visibility/selection/settings
    are restored. On failure the original object mesh/materials are restored.
    """
    if not isinstance(slot, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", slot):
        raise ValueError("slot must be a safe nonempty asset identifier")
    if isinstance(resolution, bool) or not isinstance(resolution, int) or not 32 <= resolution <= 2048:
        raise ValueError("Atlas resolution must be an integer from 32 to 2048")
    if not isinstance(transfer_surface_channels, bool):
        raise ValueError("transfer_surface_channels must be a boolean")
    if obj.type != "MESH" or not obj.data.polygons:
        raise ValueError("Atlas baking requires a nonempty evaluated mesh object")
    bpy.context.view_layer.update()
    if obj.name not in bpy.context.view_layer.objects:
        raise ValueError("Runtime object must belong to the active view layer")
    original_mesh = obj.data
    original_materials = list(original_mesh.materials)
    if not original_materials or any(material is None for material in original_materials):
        raise ValueError("Every material slot must contain an authored material")
    for material in original_materials:
        _source_shader(material)
    if not original_mesh.uv_layers:
        raise ValueError("The evaluated source mesh must retain its authored UV map")
    source_uv = original_mesh.uv_layers.get("authored_uv") or original_mesh.uv_layers.active
    source_uv_name = source_uv.name
    sources = list(dict.fromkeys(high_sources or []))
    if obj in sources or any(source.type != "MESH" for source in sources):
        raise ValueError("high_sources must contain distinct source mesh objects, excluding the runtime target")
    if any(source.name not in bpy.context.view_layer.objects for source in sources):
        raise ValueError("Every high source must belong to the active view layer")
    if transfer_surface_channels and not sources:
        raise ValueError("Surface-channel transfer requires retained high_sources")
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    old_active = bpy.context.view_layer.objects.active
    old_mode = old_active.mode if old_active else "OBJECT"
    old_selected = list(bpy.context.selected_objects)
    old_visibility = [(item, item.hide_render, item.hide_get(), item.hide_select)
                      for item in bpy.context.view_layer.objects]
    old_engine, old_samples = scene.render.engine, scene.cycles.samples
    working_mesh, temporary_materials, images = None, [], {}
    source_clones, source_clone_meshes = [], []
    bake_sources = sources
    temporary_images = []
    atlas_material = None
    succeeded = False
    try:
        if bpy.context.object and bpy.context.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        working_mesh = original_mesh.copy()
        working_mesh.name = original_mesh.name + ".atlas"
        obj.data = working_mesh
        source_indices = [polygon.material_index for polygon in working_mesh.polygons]
        copies = {}
        working_mesh.materials.clear()
        for material in original_materials:
            if material not in copies:
                copied = material.copy()
                copied.name = material.name + ".atlas_bake_temporary"
                _pin_source_uv(copied, source_uv_name)
                copies[material] = copied
                temporary_materials.append(copied)
            working_mesh.materials.append(copies[material])
        for polygon, index in zip(working_mesh.polygons, source_indices):
            polygon.material_index = index
        target_materials = list(dict.fromkeys(working_mesh.materials))
        if transfer_surface_channels:
            # Copies retain authored topology, UVs, placement and finishing
            # modifiers. Source materials may be shared elsewhere in the master;
            # never redirect or suppress their shader inputs during a bake.
            source_copies = {}
            for source in sources:
                clone = source.copy()
                source_clones.append(clone)
                clone.name = source.name + ".atlas_high_temporary"
                clone.data = source.data.copy()
                source_clone_meshes.append(clone.data)
                bpy.context.scene.collection.objects.link(clone)
                clone.hide_render = True
                clone.hide_viewport = False
                clone.hide_set(True)
                clone.hide_select = False
                uv = clone.data.uv_layers.get("authored_uv") or clone.data.uv_layers.active
                if uv is None:
                    raise ValueError(f"{source.name}: surface transfer requires an authored UV map")
                source_indices = [polygon.material_index for polygon in clone.data.polygons]
                materials = list(clone.data.materials)
                if not materials or any(material is None for material in materials):
                    raise ValueError(f"{source.name}: every high-source material slot must be assigned")
                clone.data.materials.clear()
                for material in materials:
                    key = (material, uv.name)
                    if key not in source_copies:
                        _source_shader(material)
                        copied = material.copy()
                        temporary_materials.append(copied)
                        copied.name = material.name + ".atlas_high_material_temporary"
                        _pin_source_uv(copied, uv.name)
                        source_copies[key] = copied
                    clone.data.materials.append(source_copies[key])
                for polygon, index in zip(clone.data.polygons, source_indices):
                    polygon.material_index = index
            bake_sources = source_clones
        # Copying mesh data preserves face material indices and all authored UVs.
        target_uv = working_mesh.uv_layers.new(name="__runtime_bake_uv", do_init=False)
        target_uv_name = target_uv.name
        working_mesh.uv_layers.active = target_uv
        target_uv.active_render = True
        for item, _, _, _ in old_visibility:
            item.select_set(False)
            if item.type == "MESH":
                item.hide_render = item != obj
        obj.hide_select = False
        obj.hide_set(False)
        obj.hide_render = False
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=math.radians(66), margin_method="SCALED",
                                 island_margin=max(.012, 6 / resolution),
                                 area_weight=0, correct_aspect=True, scale_to_bounds=False)
        bpy.ops.object.mode_set(mode="OBJECT")
        scene.render.engine = "CYCLES"
        scene.cycles.samples = 16
        targets = {}
        surfaces = {}
        for material in temporary_materials:
            output, shader = _source_shader(material)
            surfaces[material] = (output, shader, output.inputs["Surface"].links[0].from_socket)
            if material in target_materials:
                target = material.node_tree.nodes.new("ShaderNodeTexImage")
                target.name = "atlas_bake_target"
                targets[material] = target

        def bake(channel, kind, selected_to_active=False, pass_filter=None, persist=True):
            image = _new_image(f"prelate.{slot}.{channel}", resolution,
                               "sRGB" if channel == "baseColor" else "Non-Color")
            if persist:
                images[channel] = image
            else:
                temporary_images.append(image)
            for material, target in targets.items():
                target.image = image
                for node in material.node_tree.nodes:
                    node.select = False
                target.select = True
                material.node_tree.nodes.active = target
            for item in bpy.context.selected_objects:
                item.select_set(False)
            for source in bake_sources:
                source.hide_render = not selected_to_active
                if selected_to_active:
                    source.hide_select = False
                    source.hide_set(False)
                    source.select_set(True)
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            kwargs = dict(type=kind, target="IMAGE_TEXTURES", save_mode="INTERNAL",
                          use_selected_to_active=selected_to_active, use_clear=True,
                          margin=max(4, round(resolution / 128)), margin_type="EXTEND",
                          normal_space="TANGENT", uv_layer=target_uv_name)
            if pass_filter is not None:
                kwargs["pass_filter"] = pass_filter
            if selected_to_active:
                kwargs.update(cage_extrusion=.010, max_ray_distance=.040, use_cage=False)
            result = bpy.ops.object.bake(**kwargs)
            if result != {"FINISHED"}:
                raise RuntimeError(f"Blender bake failed for {slot}/{channel}: {result}")
            if persist:
                _save(image, output_dir / f"{slot}_{channel}.png")
            print(f"ATLAS_CHANNEL {slot} {channel}", flush=True)
            return image

        # Metal reflection contributes no diffuse BSDF. On temporary copies only,
        # suppress metallic during the color-only diffuse pass, then restore it.
        metallic_links = []
        for material, (_, shader, _) in surfaces.items():
            socket = shader.inputs["Metallic"]
            links = [link.from_socket for link in socket.links]
            metallic_links.append((material, socket, socket.default_value, links))
            for link in list(socket.links):
                material.node_tree.links.remove(link)
            socket.default_value = 0
        bake("baseColor", "DIFFUSE", selected_to_active=transfer_surface_channels, pass_filter={"COLOR"})
        for material, socket, value, links in metallic_links:
            socket.default_value = value
            for source in links:
                material.node_tree.links.new(source, socket)
        bake("normal", "NORMAL", selected_to_active=bool(sources))

        if slot.startswith("weapon"):
            for material, (output, shader, _) in surfaces.items():
                tree = material.node_tree
                emission = tree.nodes.new("ShaderNodeEmission")
                emission.inputs["Color"].default_value = shader.inputs["Emission Color"].default_value if shader.inputs["Emission Strength"].default_value > 0 else (0, 0, 0, 1)
                for link in list(output.inputs["Surface"].links):
                    tree.links.remove(link)
                tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
            bake("emission", "EMIT", selected_to_active=transfer_surface_channels)

        for channel, input_name in (("roughness", "Roughness"), ("metallic", "Metallic")):
            for material, (output, shader, _) in surfaces.items():
                tree = material.node_tree
                emission = tree.nodes.get("atlas_scalar_emission") or tree.nodes.new("ShaderNodeEmission")
                emission.name = "atlas_scalar_emission"
                for link in list(emission.inputs["Color"].links):
                    tree.links.remove(link)
                source = shader.inputs[input_name]
                if source.is_linked:
                    tree.links.new(source.links[0].from_socket, emission.inputs["Color"])
                else:
                    value = source.default_value
                    emission.inputs["Color"].default_value = (value, value, value, 1)
                for link in list(output.inputs["Surface"].links):
                    tree.links.remove(link)
                tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
            bake(channel, "EMIT", selected_to_active=transfer_surface_channels)
        source_occlusion = None
        if any(material.node_tree.nodes.get("Authored source occlusion") for material in target_materials):
            for material, (output, _, _) in surfaces.items():
                tree = material.node_tree
                emission = tree.nodes.get("atlas_scalar_emission")
                for link in list(emission.inputs["Color"].links):
                    tree.links.remove(link)
                emission.inputs["Color"].default_value = (1, 1, 1, 1)
                source = tree.nodes.get("Authored source occlusion")
                if source:
                    if source.type != "TEX_IMAGE" or source.image is None or source.image.colorspace_settings.name != "Non-Color":
                        raise ValueError("Authored source occlusion must be a Non-Color image node")
                    tree.links.new(source.outputs["Color"], emission.inputs["Color"])
                for link in list(output.inputs["Surface"].links):
                    tree.links.remove(link)
                tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
            source_occlusion = bake("source_occlusion", "EMIT", persist=False)
        for material, (output, _, original_socket) in surfaces.items():
            for link in list(output.inputs["Surface"].links):
                material.node_tree.links.remove(link)
            material.node_tree.links.new(original_socket, output.inputs["Surface"])
        bake("occlusion", "AO")
        if source_occlusion:
            module_pixels = np.empty(resolution * resolution * 4, dtype=np.float32)
            source_pixels = np.empty_like(module_pixels)
            images["occlusion"].pixels.foreach_get(module_pixels)
            source_occlusion.pixels.foreach_get(source_pixels)
            module_pixels = module_pixels.reshape((-1, 4))
            source_pixels = source_pixels.reshape((-1, 4))
            if not np.isfinite(module_pixels).all() or not np.isfinite(source_pixels).all():
                raise ValueError("Occlusion bake contains nonfinite pixels")
            combined = np.clip(module_pixels[:, 0] * source_pixels[:, 0], 0, 1)
            module_pixels[:, :3] = combined[:, None]
            images["occlusion"].pixels.foreach_set(module_pixels.ravel())
            images["occlusion"].update()
            _save(images["occlusion"], output_dir / f"{slot}_occlusion.png")
        packed = np.ones((resolution * resolution, 4), dtype=np.float32)
        for index, channel in enumerate(("occlusion", "roughness", "metallic")):
            pixels = np.empty(resolution * resolution * 4, dtype=np.float32)
            images[channel].pixels.foreach_get(pixels)
            packed[:, index] = pixels.reshape((-1, 4))[:, 0]
        images["orm"] = _new_image(f"prelate.{slot}.orm", resolution, "Non-Color")
        images["orm"].pixels.foreach_set(packed.ravel())
        images["orm"].update()
        _save(images["orm"], output_dir / f"{slot}_orm.png")
        material = _atlas_material(slot, images)
        atlas_material = material
        working_mesh.materials.clear()
        working_mesh.materials.append(material)
        for polygon in working_mesh.polygons:
            polygon.material_index = 0
        for name in [layer.name for layer in working_mesh.uv_layers]:
            if name != target_uv_name:
                working_mesh.uv_layers.remove(working_mesh.uv_layers[name])
        working_mesh.uv_layers[0].name = "runtime_atlas"
        working_mesh.uv_layers.active_index = 0
        working_mesh.uv_layers[0].active_render = True
        working_mesh.update()
        obj["atlas_resolution"] = resolution
        obj["atlas_channels"] = "baseColor,normal,roughness,metallic,occlusion; ORM packed"
        obj["atlas_normal_source"] = "selected high sources" if sources else "evaluated mesh and authored material normal"
        obj["atlas_surface_source"] = "selected retained high-source copies" if transfer_surface_channels else "runtime target authored materials"
        obj["atlas_ao_scope"] = "authored source AO multiplied by joined module self-occlusion in linear space" if source_occlusion else "joined module self-occlusion"
        succeeded = True
        return {channel: str((output_dir / f"{slot}_{channel}.png").resolve()) for channel in images}
    finally:
        if bpy.context.object and bpy.context.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        if not succeeded:
            obj.data = original_mesh
            if working_mesh and working_mesh.users == 0:
                bpy.data.meshes.remove(working_mesh)
            if atlas_material and atlas_material.users == 0:
                bpy.data.materials.remove(atlas_material)
        for clone in source_clones:
            bpy.data.objects.remove(clone, do_unlink=True)
        for mesh in source_clone_meshes:
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        for material in temporary_materials:
            if material.users == 0:
                bpy.data.materials.remove(material)
        if not succeeded:
            # Bake target nodes retain image users until their temporary
            # materials are removed. Release failed-pass images afterwards.
            for image in images.values():
                if image.users == 0:
                    bpy.data.images.remove(image)
        for image in temporary_images:
            if image.users == 0:
                bpy.data.images.remove(image)
        scene.render.engine, scene.cycles.samples = old_engine, old_samples
        for item in bpy.context.selected_objects:
            item.select_set(False)
        for item, hide_render, hide_view, hide_select in old_visibility:
            item.hide_render = hide_render
            item.hide_set(hide_view)
            item.hide_select = hide_select
        for item in old_selected:
            if item.name in bpy.context.view_layer.objects:
                item.select_set(True)
        bpy.context.view_layer.objects.active = old_active
        if old_active and old_mode != "OBJECT":
            bpy.ops.object.mode_set(mode=old_mode)
