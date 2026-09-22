"""Blender: preserve the equipped body and move the hammer grip down its haft."""
import hashlib
import importlib.util
import json
from pathlib import Path
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts/unreal/two-handed"
OUT.mkdir(parents=True, exist_ok=True)
source = ROOT / "artifacts/unreal/equipped/civic_battle_prelate_m/equipped.glb"
spec = importlib.util.spec_from_file_location("review", ROOT / "authoring/blender/battle-prelate-reference-rebuild/tools/reimport_review.py")
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)
review.bpy, review.Matrix = bpy, Matrix
bpy.ops.wm.read_factory_settings(use_empty=True)
assembly = review.assemble(ROOT / "public/assets/models", 0)
rig = assembly["rig"]
rig.animation_data_clear()
rig.data.pose_position = "REST"
bpy.context.view_layer.update()
weapon = next(obj for obj in assembly["weapon"] if "head_center_local" in obj)
grips = {key: list(weapon.matrix_world @ Vector(weapon[key]))
         for key in ("primary_grip_local", "secondary_grip_local", "head_center_local")}
left_palm = list(assembly["sockets"]["socket_hand_L"].matrix_world.translation)
axis = (Vector(grips["head_center_local"]) - Vector(grips["primary_grip_local"])).normalized()
# Move the same mesh along its own shaft. Both hands now hold below the head,
# rather than leaving a sword-length pommel to sweep through the legs.
shift = axis * .72
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(source), disable_bone_shape=True)
for obj in bpy.data.objects:
    if obj.animation_data:
        obj.animation_data_clear()
    if obj.type == "ARMATURE":
        for bone in obj.pose.bones:
            bone.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()
weapons = [obj for obj in bpy.data.objects if obj.type == "MESH" and "weapon" in obj.name.lower()]
if len(weapons) != 1:
    raise RuntimeError("Expected the one equipped authored hammer")
mesh = weapons[0]
delta = mesh.matrix_world.to_3x3().inverted() @ shift
for vertex in mesh.data.vertices:
    vertex.co += delta
mesh.data.update()
bpy.context.view_layer.update()
weapon_bounds = [list(mesh.matrix_world @ Vector(corner)) for corner in mesh.bound_box]
output = OUT / "prelate-two-handed.fbx"
bpy.ops.export_scene.fbx(filepath=str(output), object_types={"MESH", "ARMATURE", "EMPTY"},
    axis_forward="-Y", axis_up="Z", global_scale=1., apply_unit_scale=True,
    apply_scale_options="FBX_SCALE_NONE", add_leaf_bones=False, use_armature_deform_only=False,
    use_triangles=True, bake_anim=False, path_mode="COPY", embed_textures=False)
(OUT / "weapon.json").write_text(json.dumps(dict(gripsWorld=grips, leftPalmWorld=left_palm,
    weaponBoundsWorld=weapon_bounds,
    hammerShiftMeters=list(shift), sourceSha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    fbxSha256=hashlib.sha256(output.read_bytes()).hexdigest()), indent=2) + "\n")
