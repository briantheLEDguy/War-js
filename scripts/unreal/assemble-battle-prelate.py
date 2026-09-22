"""Recover the complete authored Prelate as a native import source, without replacing browser modules."""
import importlib.util
import json
from pathlib import Path
import sys
import bpy
from mathutils import Matrix

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from equipped_source import PROFILE, digest, module_sources


def main():
    registry = json.loads((ROOT / "public/assets/models/asset-index.json").read_text())
    modules = module_sources(ROOT, registry)
    helper = ROOT / "authoring/blender/battle-prelate-reference-rebuild/tools/reimport_review.py"
    spec = importlib.util.spec_from_file_location("prelate_review", helper)
    review = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(review)
    review.bpy, review.Matrix = bpy, Matrix
    assembly = review.assemble(ROOT / "public/assets/models", 0)
    rig = assembly["rig"]
    # The original weapon is socketed. Bake that rigid binding into skin weights
    # so Unreal imports it with the body, retaining the exact exported grip.
    socket = assembly["sockets"]["socket_hand_R"]
    review.require(socket.parent == rig and socket.parent_type == "BONE", "Weapon socket must bind to the body rig")
    for mesh in assembly["all_meshes"]:
        if mesh in assembly["weapon"]:
            matrix = mesh.matrix_world.copy()
            mesh.parent = rig
            mesh.matrix_parent_inverse = rig.matrix_world.inverted()
            mesh.matrix_world = matrix
            group = mesh.vertex_groups.new(name=socket.parent_bone)
            group.add(list(range(len(mesh.data.vertices))), 1.0, "REPLACE")
            modifier = mesh.modifiers.new("Authored weapon grip", "ARMATURE")
            modifier.object = rig
    for obj in list(bpy.data.objects):
        if obj != rig and obj not in assembly["all_meshes"]:
            bpy.data.objects.remove(obj, do_unlink=True)
    rig.data.pose_position = "POSE"
    rig.animation_data.action = None
    rig.animation_data.use_nla = True
    for track in rig.animation_data.nla_tracks:
        track.mute = False
        for strip in track.strips:
            strip.mute = False
    directory = ROOT / "artifacts/unreal/equipped" / PROFILE
    directory.mkdir(parents=True, exist_ok=True)
    receipt = directory / "assembly.json"
    receipt.unlink(missing_ok=True)
    output = directory / "equipped.glb"
    bpy.ops.export_scene.gltf(filepath=str(output), export_format="GLB", export_animations=True,
        export_animation_mode="NLA_TRACKS", export_force_sampling=True, export_frame_range=False)
    receipt.write_text(json.dumps({"schemaVersion": 1, "profileKey": PROFILE,
        "modules": modules, "sourceSha256": digest(output), "assemblyToolSha256": digest(Path(__file__)),
        "rebindToolSha256": digest(helper), "unrealApproved": False,
        "equipmentPolicy": "Fixed recovered outfit and hammer; runtime equipment swapping remains pending."}, indent=2) + "\n")
    print("WAR_PRELATE_ASSEMBLED=" + str(output))


if __name__ == "__main__":
    main()
